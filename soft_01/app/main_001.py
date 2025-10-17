"""
Descarga interactiva de productos Sentinel-2 L1C desde Copernicus Data Space (CDSE).

Menos es más:
- Dependencias mínimas (requests + stdlib).
- Pide los datos al usuario (sin depender de ficheros en SOFT).
- Descarga desde el host de descarga (evita 401 por redirecciones).
- Maneja tokens: refresca antes de caducar y reintenta 401 una vez.
"""

import json
import os
import sys
import time
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional

import requests
from urllib.parse import quote


def read_default_config() -> Dict[str, Optional[str]]:
    """URLs por defecto. No usa ficheros de SOFT."""
    return {
        "downloadURL": "https://catalogue.dataspace.copernicus.eu/",
        "authentificationURL": "https://identity.dataspace.copernicus.eu/",
        "polySearch": None,  # Se pedirá al usuario
    }


def ask(prompt: str, default: str = None) -> str:
    """Entrada con valor por defecto opcional."""
    if default:
        v = input(f"{prompt} [{default}]: ").strip()
        return v or default
    return input(f"{prompt}: ").strip()


def ask_date(label: str) -> str:
    """Pide fecha YYYY-MM-DD y valida formato."""
    while True:
        v = input(f"{label} (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            print("Formato inválido. Ejemplo: 2025-01-31")


def ask_out_dir() -> Path:
    """Pide carpeta absoluta; crea si no existe (previa confirmación)."""
    while True:
        raw = input("Carpeta de salida (elige carpeta absoluta): ").strip()
        if not raw:
            print("Debes indicar una carpeta de salida.")
            continue
        # Quitar comillas si vienen pegadas
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            raw = raw[1:-1]
        expanded = os.path.expandvars(os.path.expanduser(raw))
        p = Path(expanded)
        if p.exists():
            if p.is_dir():
                return p
            print("La ruta existe pero no es un directorio.")
            continue
        resp = input(f"La carpeta no existe. ¿Crear {p}? [s/N]: ").strip().lower()
        if resp == "s":
            try:
                p.mkdir(parents=True, exist_ok=True)
                return p
            except Exception as e:
                print(f"No se pudo crear: {e}")


CATALUNYA_WKT = (
    "POLYGON((0.1873941083836813 40.46212014624089,"
    "3.6319312482049257 40.46212014624089,"
    "3.6319312482049257 42.91398496782941,"
    "0.1873941083836813 42.91398496782941,"
    "0.1873941083836813 40.46212014624089))"
)


def ask_poly_menu() -> str:
    """Menú de selección de área (WKT)."""
    print("\nSelecciona el área de búsqueda:")
    print("1. Coordenadas Catalunya")
    print("2. Coordenadas manuales (no habilitado)")
    while True:
        opt = input("Opción [1]: ").strip() or "1"
        if opt == "1":
            return CATALUNYA_WKT
        if opt == "2":
            print("Opción no habilitada todavía. Saliendo.")
            sys.exit(0)
        print("Opción inválida. Elige 1 o 2.")


def fetch_tokens(auth_url: str, *, username: str = None, password: str = None, refresh_token: str = None) -> Dict[str, str]:
    """Obtiene o refresca tokens en CDSE."""
    url = auth_url.rstrip("/") + "/auth/realms/CDSE/protocol/openid-connect/token"
    if refresh_token:
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": "cdse-public"}
    else:
        data = {"grant_type": "password", "username": username, "password": password, "client_id": "cdse-public"}
    r = requests.post(url, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


class TokenManager:
    """Gestiona access/refresh token con auto‑refresh y reintento 401."""

    def __init__(self, auth_url: str, access_token: str, refresh_token: str, expires_in: int, refresh_expires_in: int):
        self.auth_url = auth_url
        self.access_token = access_token
        self.refresh_token = refresh_token
        now = time.time()
        self.access_expiry = now + max(0, int(expires_in))
        self.refresh_expiry = now + max(0, int(refresh_expires_in))

    @classmethod
    def from_password(cls, auth_url: str, username: str, password: str) -> "TokenManager":
        data = fetch_tokens(auth_url, username=username, password=password)
        return cls(
            auth_url,
            data.get("access_token"),
            data.get("refresh_token"),
            data.get("expires_in", 0),
            data.get("refresh_expires_in", 0),
        )

    def _refresh(self):
        if not self.refresh_token or time.time() >= self.refresh_expiry:
            raise RuntimeError("Refresh token expirado o ausente")
        data = fetch_tokens(self.auth_url, refresh_token=self.refresh_token)
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        now = time.time()
        self.access_expiry = now + max(0, int(data.get("expires_in", 0)))
        self.refresh_expiry = now + max(0, int(data.get("refresh_expires_in", 0)))

    def _ensure_valid(self):
        # Refrescar si el token caduca en <60s
        if time.time() > (self.access_expiry - 60):
            self._refresh()

    def headers(self) -> Dict[str, str]:
        self._ensure_valid()
        return {"Authorization": f"Bearer {self.access_token}"}

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET con Authorization y reintento único en 401."""
        self._ensure_valid()
        headers = kwargs.pop("headers", {})
        headers.update(self.headers())
        resp = requests.get(url, headers=headers, **kwargs)
        if resp.status_code == 401:
            self._refresh()
            headers.update(self.headers())
            resp = requests.get(url, headers=headers, **kwargs)
        return resp


def search_products(catalog_url: str, poly_wkt: str, date_from: str, date_to: str, top: int = 100) -> List[Dict]:
    """Consulta pública al catálogo para listar L1C por rango y área."""
    base = catalog_url.rstrip("/") + "/odata/v1/Products?$top=" + str(top) + "&$filter="
    filt = (
        f"ContentDate/Start ge {date_from}T00:00:00.000Z and "
        f"ContentDate/Start le {date_to}T23:59:59.999Z and "
        f"contains(Name,'MSIL1C') and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{poly_wkt}')"
    )
    url = quote(base + filt, safe=":()[]/?=,&'")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data.get("value", [])


def _download_base_from_catalog(catalog_url: str) -> str:
    base = catalog_url.rstrip("/")
    return base.replace("catalogue.dataspace.copernicus.eu", "download.dataspace.copernicus.eu")


def download_product(catalog_url: str, uuid: str, out_dir: Path, name: str, tm: TokenManager) -> Path:
    """Descarga un producto por UUID gestionando autenticación vía TokenManager."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{name}.zip"
    base = _download_base_from_catalog(catalog_url)
    url = base + f"/odata/v1/Products({uuid})/$value"
    with tm.get(url, stream=True, allow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest


def main():
    """Punto de entrada: pide datos, busca y descarga con tokens auto‑refresh."""
    print("download_sentinel_2 — descarga L1C mínima (CDSE)")

    # 1) Valores por defecto
    cfg = read_default_config()
    catalog = cfg["downloadURL"]
    auth = cfg["authentificationURL"]
    poly = cfg.get("polySearch")

    print("\nParámetros por defecto (Enter para aceptar):")
    print(f"- Catálogo: {catalog}")
    print(f"- Auth:     {auth}")
    print(f"- Área:     {'(defínela a continuación)'}")

    # 2) Credenciales y fechas
    username = ask("Usuario CDSE (email)")
    password = getpass("Contraseña CDSE: ")
    date_from = ask_date("Fecha inicio")
    date_to = ask_date("Fecha fin  ")
    # Selección de área por menú
    poly = ask_poly_menu()

    # 3) Carpeta de destino
    out_dir = ask_out_dir()

    # 4) Token manager
    try:
        tm = TokenManager.from_password(auth, username, password)
    except Exception as e:
        print(f"Error autenticando: {e}")
        sys.exit(1)

    # 5) Verificación rápida en host de descarga
    try:
        dl_base = _download_base_from_catalog(catalog)
        probe = tm.get(dl_base + "/odata/v1/Products?$top=1", timeout=60)
        if probe.status_code in (401, 403):
            print("\nNo autorizado en el host de descarga (401/403). Revisa usuario/contraseña o términos de uso en CDSE.")
            sys.exit(1)
    except Exception:
        # Si falla, continuamos; la descarga lo revelará.
        pass

    # 6) Búsqueda pública
    try:
        items = search_products(catalog, poly, date_from, date_to)
    except Exception as e:
        print(f"Error buscando productos: {e}")
        sys.exit(1)

    if not items:
        print("Sin resultados para el rango/área indicados.")
        return

    print(f"Encontrados {len(items)} productos. Ejemplos:")
    for it in items[:5]:
        print("-", it.get("Name"))

    resp = input("\n¿Descargar todos? [s/N]: ").strip().lower()
    if resp != "s":
        print("Cancelado por el usuario.")
        return

    # 7) Descarga secuencial
    ok, fail = 0, 0
    for it in items:
        uuid = it.get("Id") or it.get("id")
        name = it.get("Name") or it.get("name")
        if not uuid or not name:
            continue
        try:
            dest = download_product(catalog, uuid, out_dir, name, tm)
            ok += 1
            print(f"OK: {dest}")
        except Exception as e:
            fail += 1
            print(f"Fallo {name}: {e}")

    print(f"\nDescargas completadas. OK={ok}  FAIL={fail}  Carpeta={out_dir}")


if __name__ == "__main__":
    main()
