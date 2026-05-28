import os
import time
import requests
import logging
import zipfile
from src.s2_process_cloud.config import PipelineConfig

class CDSEAuthError(Exception):
    pass

class CopernicusSession(requests.Session):
    """
    Sesión personalizada para evitar que requests elimine el header 'Authorization'
    al seguir redirecciones HTTP 302 entre subdominios de CDSE.
    """
    def rebuild_auth(self, prepared_request, response):
        super().rebuild_auth(prepared_request, response)
        # Si la URL destino pertenece a copernicus.eu, re-inyectamos el token
        if 'copernicus.eu' in prepared_request.url:
            if 'Authorization' in response.request.headers:
                prepared_request.headers['Authorization'] = response.request.headers['Authorization']

class CDSEDownloader:
    """
    Gestiona la autenticación, búsqueda en catálogo OData y descarga 
    de productos Sentinel-2 desde Copernicus Data Space Ecosystem (CDSE).
    """
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        self.download_url = "https://catalogue.dataspace.copernicus.eu/"
        
        self.access_token = None
        self.token_expiry_time = 0
        self.session = CopernicusSession()
        
    def _authenticate(self):
        """Obtiene un nuevo token de acceso a CDSE usando las credenciales del .env"""
        logging.info("Solicitando nuevo token de acceso a CDSE...")
        
        data = {
            "client_id": "cdse-public",
            "username": self.config.cdse_username,
            "password": self.config.cdse_password,
            "grant_type": "password",
        }
        
        try:
            response = self.session.post(self.auth_url, data=data, timeout=30)
            response.raise_for_status()
            
            json_resp = response.json()
            self.access_token = json_resp.get("access_token")
            expires_in = json_resp.get("expires_in", 600) # Por defecto 10 minutos si falla
            
            # Guardamos el timestamp en el que expirará el token (restamos 60s por margen de seguridad)
            self.token_expiry_time = time.time() + expires_in - 60
            
            # Inyectar el token globalmente en la sesión
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            
            logging.info("Token obtenido correctamente.")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error de autenticación contra CDSE: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Respuesta del servidor: {e.response.text}")
            raise CDSEAuthError("Fallo crítico al obtener el token OData.")

    def get_valid_token(self) -> str:
        """Lógica 'Keep-Alive'."""
        if not self.access_token or time.time() >= self.token_expiry_time:
            self._authenticate()
        return self.access_token

    def search_products(self, orbit: str, date_str: str, poly_wkt: str, platforms=None):
        """
        Busca productos MSIL1C en Copernicus DataSpace para una órbita y fecha determinadas.
        """
        self.get_valid_token() # Asegurar token antes de buscar
        platforms = platforms or ["S2A", "S2B", "S2C"]
        
        filter_str = (
            f"ContentDate/Start ge {date_str}T00:00:00.000Z and "
            f"ContentDate/Start le {date_str}T23:59:59.999Z and "
            f"contains(Name,'MSIL1C') and "
            f"contains(Name,'_{orbit}_') and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}')"
        )
        
        url = f"{self.download_url}odata/v1/Products?$filter={filter_str}&$top=100"
        
        try:
            logging.info(f"Buscando productos OData para {orbit} en fecha {date_str}...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            products = data.get('value', [])
            logging.info(f"Se encontraron {len(products)} productos en el catálogo.")
            
            filtered_products = [p for p in products if p.get('Name', '')[:3] in platforms]
            logging.info(f"Productos filtrados por plataforma {platforms}: {len(filtered_products)}")
            
            return self.filter_latest_baseline(filtered_products)
            
        except Exception as e:
            logging.error(f"Error durante la búsqueda OData: {e}")
            return []

    def filter_latest_baseline(self, products):
        """Deduplica productos basándose en el footprint y se queda con la baseline más reciente."""
        if not products:
            return []

        grouped = {}
        for p in products:
            name = p.get('Name', '')
            tile_pos = name.find('_T')
            tile = name[tile_pos + 1: tile_pos + 7] if tile_pos != -1 else "UNKNOWN"
                
            baseline_pos = name.find('_N')
            baseline = name[baseline_pos + 1: baseline_pos + 6] if baseline_pos != -1 else "N0000"
                
            if tile not in grouped:
                grouped[tile] = []
            grouped[tile].append((baseline, p))
            
        final_products = []
        for tile, list_products in grouped.items():
            list_products.sort(key=lambda x: x[0], reverse=True) # Sort desc by baseline
            chosen_product = list_products[0][1]
            logging.info(f"Seleccionado para tile {tile}: {chosen_product.get('Name')} (Baseline: {list_products[0][0]})")
            final_products.append(chosen_product)
            
        return final_products

    def _is_valid_zip(self, filepath: str) -> bool:
        """Verifica instantáneamente si un archivo ZIP es válido leyendo su cabecera central."""
        if not os.path.exists(filepath):
            return False
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                return True
        except zipfile.BadZipFile:
            return False

    def download_product_zip(self, product_id: str, product_name: str, output_dir: str):
        """Descarga el producto completo (ZIP) con reintentos ante cortes de red."""
        download_url = f"{self.download_url}odata/v1/Products({product_id})/$value"
        
        os.makedirs(output_dir, exist_ok=True)
        zip_path = os.path.join(output_dir, f"{product_name}.zip")
        
        if os.path.exists(zip_path):
            if self._is_valid_zip(zip_path):
                logging.info(f"El archivo {zip_path} ya existe y es un ZIP válido. Saltando descarga.")
                return zip_path
            else:
                logging.warning(f"El archivo {zip_path} está corrupto o incompleto. Borrando y re-descargando...")
                os.remove(zip_path)
            
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logging.info(f"Reintentando descarga de {product_name} (Intento {attempt}/{max_retries})...")
                else:
                    logging.info(f"Iniciando descarga de {product_name}...")
                    
                self.get_valid_token() # Refrescar token antes de conectar
                
                with self.session.get(download_url, stream=True, timeout=(30, 90)) as r:
                    r.raise_for_status()
                    total_length = r.headers.get('content-length')
                    
                    with open(zip_path, 'wb') as f:
                        if total_length is None:
                            f.write(r.content)
                        else:
                            for chunk in r.iter_content(chunk_size=8192 * 1024):
                                if chunk:
                                    f.write(chunk)
                                    
                logging.info(f"Descarga completada: {zip_path}")
                return zip_path
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Error de red durante la descarga de {product_name}: {e}")
                if os.path.exists(zip_path):
                    os.remove(zip_path) # Limpiar archivo corrupto
                
                if attempt == max_retries:
                    logging.error(f"Se agotaron los {max_retries} reintentos para {product_name}. Abortando.")
                    raise
                    
                time.sleep(5) # Esperar antes de reintentar
