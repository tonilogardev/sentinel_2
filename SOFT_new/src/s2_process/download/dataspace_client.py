import os
import time
import hashlib
import logging
import requests
from datetime import datetime

class CopernicusSession(requests.Session):
    """
    Sesión personalizada para evitar que requests elimine el header 'Authorization'
    al seguir redirecciones HTTP 302 entre subdominios de Copernicus DataSpace.
    """
    def rebuild_auth(self, prepared_request, response):
        super().rebuild_auth(prepared_request, response)
        # Si la URL destino pertenece a copernicus.eu, re-inyectamos el token
        if 'copernicus.eu' in prepared_request.url:
            if 'Authorization' in response.request.headers:
                prepared_request.headers['Authorization'] = response.request.headers['Authorization']

class CopernicusDataspaceClient:
    def __init__(self, download_url, auth_url, username, password):
        self.download_url = download_url.rstrip('/') + '/'
        self.auth_url = auth_url.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.token = None
        self.token_expiry = None
        self.session = CopernicusSession()

    def _get_access_token(self):
        """Obtiene un token de acceso OAuth2 de Copernicus DataSpace y registra su expiración."""
        token_endpoint = f"{self.auth_url}auth/realms/CDSE/protocol/openid-connect/token"
        payload = {
            'grant_type': 'password',
            'client_id': 'cdse-public',
            'username': self.username,
            'password': self.password
        }
        
        try:
            logging.info("Solicitando token de acceso a Copernicus DataSpace...")
            response = self.session.post(token_endpoint, data=payload, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            self.token = token_data.get('access_token')
            
            # Extraer tiempo de vida y calcular timestamp de expiración (con 60s de margen)
            expires_in = token_data.get('expires_in', 600)  # Normalmente 600s en CDSE
            self.token_expiry = time.time() + expires_in - 60
            
            logging.info(f"Token de acceso obtenido. Expirará en {expires_in} segundos.")
            return self.token
        except Exception as e:
            logging.error(f"Error al obtener el token de acceso OAuth2: {e}")
            raise

    def _ensure_token_valid(self):
        """Verifica si el token no existe o está caducado, y solicita uno nuevo si es necesario."""
        if not self.token or not self.token_expiry or time.time() >= self.token_expiry:
            logging.info("Token inexistente o expirado. Renovando token...")
            self._get_access_token()

    def search_products(self, orbit, date_str, poly_wkt, platforms=None):
        """
        Busca productos MSIL1C en Copernicus DataSpace para una órbita y fecha determinadas
        que intersecten con el polígono de búsqueda.
        """
        platforms = platforms or ["S2A", "S2B", "S2C"]
        
        # Filtros de OData
        # Ejemplo de filtro: ContentDate/Start ge 2026-04-01T00:00:00.000Z and ContentDate/Start le 2026-04-01T23:59:59.999Z
        filter_str = (
            f"ContentDate/Start ge {date_str}T00:00:00.000Z and "
            f"ContentDate/Start le {date_str}T23:59:59.999Z and "
            f"contains(Name,'MSIL1C') and "
            f"contains(Name,'_{orbit}_') and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}')"
        )
        
        url = f"{self.download_url}odata/v1/Products?$filter={filter_str}&$top=100"
        
        try:
            logging.info(f"Buscando productos para la órbita {orbit} en la fecha {date_str}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            products = data.get('value', [])
            logging.info(f"Se encontraron {len(products)} productos en el catálogo.")
            
            # Filtrar por plataformas solicitadas
            filtered_products = []
            for p in products:
                name = p.get('Name', '')
                # Nombre típico: S2B_MSIL1C_20260401T105019_N0500_R051_T31TBE_20260401T112500.SAFE
                platform = name[:3]
                if platform in platforms:
                    filtered_products.append(p)
                    
            logging.info(f"Productos filtrados por plataforma {platforms}: {len(filtered_products)}")
            return filtered_products
        except Exception as e:
            logging.error(f"Error durante la búsqueda de productos en OData: {e}")
            return []

    def filter_latest_baseline(self, products):
        """
        Deduplica productos basándose en el footprint y se queda únicamente con la baseline
        más reciente para cada tile / granule en caso de existir duplicados.
        """
        if not products:
            return []

        # Agrupar por tile (ej: T31TBE) y fecha
        grouped = {}
        for p in products:
            name = p.get('Name', '')
            # Nombre típico: S2B_MSIL1C_20260401T105019_N0500_R051_T31TBE_20260401T112500.SAFE
            # Extraemos la clave del tile buscando "_T"
            tile_pos = name.find('_T')
            if tile_pos != -1:
                tile = name[tile_pos + 1: tile_pos + 7] # T31TBE
            else:
                tile = "UNKNOWN"
                
            # Extraemos el número de baseline (ej: N0500)
            baseline_pos = name.find('_N')
            if baseline_pos != -1:
                baseline = name[baseline_pos + 1: baseline_pos + 6] # N0500
            else:
                baseline = "N0000"
                
            if tile not in grouped:
                grouped[tile] = []
            grouped[tile].append((baseline, p))
            
        final_products = []
        for tile, list_products in grouped.items():
            # Ordenar por número de baseline (N0500, N0511, etc.) descendentemente
            list_products.sort(key=lambda x: x[0], reverse=True)
            chosen_product = list_products[0][1]
            logging.info(f"Seleccionado para tile {tile}: {chosen_product.get('Name')} (Baseline: {list_products[0][0]})")
            final_products.append(chosen_product)
            
        return final_products

    def download_product(self, product_id, dest_filepath, expected_md5=None):
        """
        Descarga un gránulo individual por su ID de Copernicus OData API.
        Verifica el hash MD5 después de completarse.
        """
        self._ensure_token_valid()
            
        download_endpoint = f"{self.download_url}odata/v1/Products({product_id})/$value"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        # Intentar descargar con reintentos para evitar congelamientos (Socket timeout)
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logging.info(f"Reintentando descarga del producto ID: {product_id} (Intento {attempt}/{max_retries})...")
                else:
                    logging.info(f"Iniciando descarga del producto ID: {product_id}...")
                    
                os.makedirs(os.path.dirname(dest_filepath), exist_ok=True)
                
                # Petición stream con timeout fuerte (30s connect, 90s read) para evitar cuelgues zombies
                with self.session.get(download_endpoint, headers=headers, stream=True, timeout=(30, 90)) as r:
                    # Fallback de seguridad por si la sesión de CDSE revocó el token antes de tiempo
                    if r.status_code == 401:
                        logging.warning("Token expirado (401) revocado por servidor. Renovando y reintentando descarga...")
                        self._get_access_token()
                        headers = {'Authorization': f'Bearer {self.token}'}
                        r = self.session.get(download_endpoint, headers=headers, stream=True, timeout=(30, 90))
                    
                    r.raise_for_status()
                    
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(dest_filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024): # 1 MB chunks
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    # Loguear progreso cada 10% aproximadamente
                                    if int(downloaded) % (1024 * 1024 * 100) < (1024 * 1024):
                                        logging.info(f"Progreso descarga: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB de {total_size / (1024*1024):.1f} MB)")
                
                logging.info("Descarga física completada. Iniciando verificación de checksum...")
                
                # Verificar checksum MD5 si está disponible
                if expected_md5:
                    calculated_md5 = self._calculate_md5(dest_filepath)
                    if calculated_md5.lower() == expected_md5.lower():
                        logging.info("¡Verificación de MD5 exitosa! El archivo es correcto.")
                        return True
                    else:
                        logging.error(f"¡Fallo en checksum MD5! Esperado: {expected_md5}, Calculado: {calculated_md5}")
                        if os.path.exists(dest_filepath):
                            os.remove(dest_filepath)
                        raise Exception("Fallo de integridad MD5.")
                else:
                    logging.warning("No se proporcionó MD5 esperado. Se asume descarga correcta.")
                    return True
                    
            except Exception as e:
                logging.error(f"Error descargando el producto {product_id} (Intento {attempt}/{max_retries}): {e}")
                if os.path.exists(dest_filepath):
                    os.remove(dest_filepath)
                
                if attempt == max_retries:
                    logging.error(f"Se han agotado todos los reintentos para {product_id}. Abortando.")
                    return False
                
                # Esperar 5 segundos antes del reintento
                time.sleep(5)
                
        return False

    def _calculate_md5(self, filepath):
        """Calcula el hash MD5 de un archivo local en bloques."""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"Error al calcular MD5 del archivo {filepath}: {e}")
            raise
