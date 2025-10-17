"""
Mosaico L1C (10 m RGB) por fecha y órbita.

Qué hace (menos es más)
- Busca carpetas .SAFE extraídas de L1C en una carpeta.
- Filtra por fecha (YYYY-MM-DD) y órbita relativa (R051/R008).
- Crea un mosaico RGB 10 m (B04, B03, B02) en GeoTIFF (int16) con compresión LZW.

Requisitos
- GDAL disponible en el entorno (from osgeo import gdal).
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import re

from osgeo import gdal


def ask(prompt: str, default: str = None) -> str:
    v = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
    return v or (default or "")


def ask_dir(msg: str) -> Path:
    while True:
        raw = input(f"{msg}: ").strip()
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            raw = raw[1:-1]
        if not raw:
            print("Debes indicar una carpeta.")
            continue
        p = Path(os.path.expandvars(os.path.expanduser(raw)))
        if p.exists() and not p.is_dir():
            print("La ruta existe pero no es un directorio.")
            continue
        if not p.exists():
            resp = input(f"La carpeta no existe. ¿Crear {p}? [s/N]: ").strip().lower()
            if resp != "s":
                continue
            p.mkdir(parents=True, exist_ok=True)
        return p


def find_safe_dirs(root: Path, yyyymmdd: str) -> List[Path]:
    safes = []
    for p in root.glob("*.SAFE"):
        name = p.name
        if yyyymmdd in name:
            safes.append(p)
    return safes


def detect_orbit_from_name(name: str) -> Optional[str]:
    m = re.search(r"_R(\d{3})_", name)
    return f"R{m.group(1)}" if m else None


def collect_band_files(safe_dir: Path) -> Dict[str, List[str]]:
    bands: Dict[str, List[str]] = {"B02": [], "B03": [], "B04": []}
    granule_root = safe_dir / "GRANULE"
    if not granule_root.exists():
        return bands
    for gran in granule_root.iterdir():
        if not gran.is_dir():
            continue
        r10 = gran / "IMG_DATA" / "R10m"
        if not r10.exists():
            # Algunos L1C guardan 10 m directamente bajo IMG_DATA
            r10 = gran / "IMG_DATA"
        for band in ("B02", "B03", "B04"):
            for jp2 in r10.glob(f"*_{band}_10m.jp2"):
                bands[band].append(str(jp2))
            for jp2 in r10.glob(f"*_{band}.jp2"):
                # fallback por si no incluye sufijo _10m en el nombre
                bands[band].append(str(jp2))
    return bands


def build_mosaic_vrt(out_vrt: Path, inputs: List[str]) -> None:
    if not inputs:
        raise RuntimeError("No hay entradas para el mosaico")
    opts = gdal.BuildVRTOptions(resolution="highest", srcNodata=0, VRTNodata=0, separate=False)
    ds = gdal.BuildVRT(str(out_vrt), inputs, options=opts)
    if ds is None:
        raise RuntimeError("Error al crear VRT")
    ds = None


def translate_rgb(vrt_r: Path, vrt_g: Path, vrt_b: Path, out_tif: Path) -> None:
    # Crear VRT de 3 bandas a partir de VRTs mono-banda
    opts_stack = gdal.BuildVRTOptions(separate=True)
    ds = gdal.BuildVRT(str(out_tif.with_suffix(".vrt")), [str(vrt_r), str(vrt_g), str(vrt_b)], options=opts_stack)
    if ds is None:
        raise RuntimeError("Error al crear VRT RGB")
    ds = None
    # Convertir a GeoTIFF comprimido (int16), nodata=0
    try:
        gdal.Translate(
            str(out_tif),
            str(out_tif.with_suffix(".vrt")),
            format="COG",
            creationOptions=["COMPRESS=LZW", "BIGTIFF=YES"],
            noData=0,
        )
    except Exception:
        gdal.Translate(
            str(out_tif),
            str(out_tif.with_suffix(".vrt")),
            format="GTiff",
            creationOptions=["COMPRESS=LZW", "PREDICTOR=2", "BIGTIFF=YES"],
            noData=0,
        )


def main():
    print("Mosaico L1C 10m RGB por fecha (autodetección de órbita)")
    safes_dir = ask_dir("Carpeta con .SAFE (extraídos)")
    out_dir = ask_dir("Carpeta de salida de mosaicos")
    date_str = ask("Fecha (YYYY-MM-DD)")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("Fecha inválida.")
        return
    yyyymmdd = dt.strftime("%Y%m%d")

    safes = find_safe_dirs(safes_dir, yyyymmdd)
    if not safes:
        print("No se encontraron .SAFE para esa fecha.")
        return

    # Agrupar por órbita detectada en el nombre
    groups: Dict[str, List[Path]] = {}
    for sd in safes:
        orb = detect_orbit_from_name(sd.name) or "RUNK"
        groups.setdefault(orb, []).append(sd)

    for orbit, safes_grp in groups.items():
        print(f"\nProcesando órbita {orbit} ({len(safes_grp)} granulos)…")
        b02_list: List[str] = []
        b03_list: List[str] = []
        b04_list: List[str] = []
        for sd in safes_grp:
            bands = collect_band_files(sd)
            b02_list += bands["B02"]
            b03_list += bands["B03"]
            b04_list += bands["B04"]

        if not (b02_list and b03_list and b04_list):
            print("  Faltan bandas 10 m (B02/B03/B04). Saltando.")
            continue

        tmp_dir = out_dir / f"tmp_{yyyymmdd}_{orbit}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        vrt_b04 = tmp_dir / "B04.vrt"
        vrt_b03 = tmp_dir / "B03.vrt"
        vrt_b02 = tmp_dir / "B02.vrt"

        print("  Creando VRTs por banda…")
        build_mosaic_vrt(vrt_b04, b04_list)
        build_mosaic_vrt(vrt_b03, b03_list)
        build_mosaic_vrt(vrt_b02, b02_list)

        out_tif = out_dir / f"S2_RGB_10m_{yyyymmdd}_{orbit}.tif"
        print("  Generando mosaico RGB…")
        translate_rgb(vrt_b04, vrt_b03, vrt_b02, out_tif)
        print(f"  Listo: {out_tif}")

    print("\nTerminado.")


if __name__ == "__main__":
    main()
"""
download_sentinel_2 — L1C: descargar, verificar MD5, extraer .SAFE y mosaicar 10 m RGB por fecha

Menos es más:
- Descarga directa desde el host de descarga (evita 401 por redirecciones)
- Token con auto‑refresh y reintento 401
- Verificación MD5 por UUID en el catálogo
- Descompresión segura de .SAFE
- Autodetección de órbita (Rxxx) y mosaico RGB por órbita
"""

import hashlib
import os
import re
import sys
import time
import zipfile
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional

import requests
from urllib.parse import quote
from osgeo import gdal


# ------------------------
# Utilidades de entrada/salida
# ------------------------

def ask(prompt: str, default: str = None) -> str:
    v = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
    return v or (default or "")


def ask_dir(msg: str) -> Path:
    while True:
        raw = input(f"{msg}: ").strip()
        if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
            raw = raw[1:-1]
        if not raw:
            print("Debes indicar una carpeta.")
            continue
        p = Path(os.path.expandvars(os.path.expanduser(raw)))
        if p.exists() and not p.is_dir():
            print("La ruta existe pero no es un directorio.")
            continue
        if not p.exists():
            resp = input(f"La carpeta no existe. ¿Crear {p}? [s/N]: ").strip().lower()
            if resp != "s":
                continue
            p.mkdir(parents=True, exist_ok=True)
        return p


# ------------------------
# Descarga + verificación + unzip
# ------------------------

def fetch_tokens(auth_url: str, *, username: str = None, password: str = None, refresh_token: str = None) -> Dict[str, str]:
    url = auth_url.rstrip("/") + "/auth/realms/CDSE/protocol/openid-connect/token"
    data = (
        {"grant_type": "refresh_token", "refresh_token": refresh_token, "client_id": "cdse-public"}
        if refresh_token
        else {"grant_type": "password", "username": username, "password": password, "client_id": "cdse-public"}
    )
    r = requests.post(url, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


class TokenManager:
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
        return cls(auth_url, data.get("access_token"), data.get("refresh_token"), data.get("expires_in", 0), data.get("refresh_expires_in", 0))

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
        if time.time() > (self.access_expiry - 60):
            self._refresh()

    def headers(self) -> Dict[str, str]:
        self._ensure_valid()
        return {"Authorization": f"Bearer {self.access_token}"}

    def get(self, url: str, **kwargs) -> requests.Response:
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


def file_md5(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def fetch_md5_by_id(catalog_url: str, uuid: str) -> Optional[str]:
    base = catalog_url.rstrip("/") + "/odata/v1/Products?$filter="
    filt = f"Id eq '{uuid}'"
    url = quote(base + filt, safe=":()[]/?=,&'")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = r.json().get("value", [])
    if not data:
        return None
    checksums = data[0].get("Checksum") or []
    for c in checksums:
        if (c.get("Algorithm") or "").upper() == "MD5":
            return (c.get("Value") or "").lower()
    return None


def safe_unzip(zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            target = (dest_dir / member).resolve()
            if not str(target).startswith(str(dest_dir.resolve())):
                continue
            z.extract(member, dest_dir)
    stem = zip_path.stem
    candidate = dest_dir / stem
    return candidate if candidate.exists() else dest_dir


# ------------------------
# Detección de .SAFE y bandas; mosaico RGB 10 m
# ------------------------

def find_safe_dirs(root: Path, yyyymmdd: str) -> List[Path]:
    safes = []
    for p in root.glob("*.SAFE"):
        if yyyymmdd in p.name:
            safes.append(p)
    return safes


def detect_orbit_from_name(name: str) -> Optional[str]:
    m = re.search(r"_R(\d{3})_", name)
    return f"R{m.group(1)}" if m else None


def collect_band_files(safe_dir: Path) -> Dict[str, List[str]]:
    bands: Dict[str, List[str]] = {"B02": [], "B03": [], "B04": []}
    granule_root = safe_dir / "GRANULE"
    if not granule_root.exists():
        return bands
    for gran in granule_root.iterdir():
        if not gran.is_dir():
            continue
        r10 = gran / "IMG_DATA" / "R10m"
        if not r10.exists():
            r10 = gran / "IMG_DATA"
        for band in ("B02", "B03", "B04"):
            for jp2 in r10.glob(f"*_{band}_10m.jp2"):
                bands[band].append(str(jp2))
            for jp2 in r10.glob(f"*_{band}.jp2"):
                bands[band].append(str(jp2))
    return bands


def build_mosaic_vrt(out_vrt: Path, inputs: List[str]) -> None:
    if not inputs:
        raise RuntimeError("No hay entradas para el mosaico")
    opts = gdal.BuildVRTOptions(resolution="highest", srcNodata=0, VRTNodata=0, separate=False)
    ds = gdal.BuildVRT(str(out_vrt), inputs, options=opts)
    if ds is None:
        raise RuntimeError("Error al crear VRT")
    ds = None


def translate_rgb(vrt_r: Path, vrt_g: Path, vrt_b: Path, out_tif: Path) -> None:
    # Apilar las 3 bandas (R,G,B)
    stack_vrt = out_tif.with_suffix(".vrt")
    ds = gdal.BuildVRT(str(stack_vrt), [str(vrt_r), str(vrt_g), str(vrt_b)], options=gdal.BuildVRTOptions(separate=True))
    if ds is None:
        raise RuntimeError("Error al crear VRT RGB")
    ds = None
    # Convertir a GeoTIFF/COG comprimido
    try:
        gdal.Translate(str(out_tif), str(stack_vrt), format="COG", creationOptions=["COMPRESS=LZW", "BIGTIFF=YES"], noData=0)
    except Exception:
        gdal.Translate(str(out_tif), str(stack_vrt), format="GTiff", creationOptions=["COMPRESS=LZW", "PREDICTOR=2", "BIGTIFF=YES"], noData=0)


# ------------------------
# Parámetros de área (Catalunya) y flujo principal
# ------------------------

CATALUNYA_WKT = (
    "POLYGON((0.1873941083836813 40.46212014624089,"
    "3.6319312482049257 40.46212014624089,"
    "3.6319312482049257 42.91398496782941,"
    "0.1873941083836813 42.91398496782941,"
    "0.1873941083836813 40.46212014624089))"
)


def main():
    print("Descargar L1C, verificar MD5, extraer .SAFE y mosaicar 10 m RGB")

    # Endpoints fijos
    catalog = "https://catalogue.dataspace.copernicus.eu/"
    auth = "https://identity.dataspace.copernicus.eu/"
    print("\nParametros por defecto (Enter para aceptar):")
    print(f"- Catalogo: {catalog}")
    print(f"- Auth:     {auth}")

    # Credenciales y fecha
    username = ask("Usuario CDSE (email)")
    password = getpass("Contrasena CDSE")
    date_str = ask("Fecha (YYYY-MM-DD)")
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("Fecha invalida.")
        return
    ymd = dt.strftime("%Y-%m-%d")
    yyyymmdd = dt.strftime("%Y%m%d")

    # Rutas
    zips_dir = ask_dir("Carpeta de descargas (.zip)")
    safes_dir = ask_dir("Carpeta de extraccion (.SAFE)")
    out_dir = ask_dir("Carpeta de salida mosaicos")

    # Autenticación y permisos
    try:
        tm = TokenManager.from_password(auth, username, password)
    except Exception as e:
        print(f"Error autenticando: {e}")
        sys.exit(1)
    try:
        dl_base = _download_base_from_catalog(catalog)
        probe = tm.get(dl_base + "/odata/v1/Products?$top=1", timeout=60)
        if probe.status_code in (401, 403):
            print("No autorizado en el host de descarga.")
            sys.exit(1)
    except Exception:
        pass

    # Buscar productos L1C del día sobre Catalunya
    try:
        items = search_products(catalog, CATALUNYA_WKT, ymd, ymd)
    except Exception as e:
        print(f"Error buscando productos: {e}")
        sys.exit(1)
    if not items:
        print("Sin resultados para la fecha indicada.")
        return
    print(f"Encontrados {len(items)} productos para {ymd}.")

    # Descargar, validar y extraer
    for it in items:
        uuid = it.get("Id") or it.get("id")
        name = it.get("Name") or it.get("name")
        if not uuid or not name:
            continue
        try:
            dest_zip = download_product(catalog, uuid, zips_dir, name, tm)
            expected = fetch_md5_by_id(catalog, uuid)
            actual = file_md5(dest_zip)
            if expected and expected != actual:
                print(f"  CHECKSUM ERROR {dest_zip.name}: {expected} != {actual}")
                continue
            extracted = safe_unzip(dest_zip, safes_dir)
            try:
                dest_zip.unlink(missing_ok=True)
            except Exception:
                pass
            print(f"  OK: {name} -> {extracted}")
        except Exception as e:
            print(f"  Fallo {name}: {e}")

    # Mosaico por órbita detectada
    safes = find_safe_dirs(safes_dir, yyyymmdd)
    if not safes:
        print("No se encontraron .SAFE para esa fecha.")
        return

    groups: Dict[str, List[Path]] = {}
    for sd in safes:
        orb = detect_orbit_from_name(sd.name) or "RUNK"
        groups.setdefault(orb, []).append(sd)

    for orbit, safes_grp in groups.items():
        print(f"\nProcesando órbita {orbit} ({len(safes_grp)} granulos)…")
        b02_list: List[str] = []
        b03_list: List[str] = []
        b04_list: List[str] = []
        for sd in safes_grp:
            bands = collect_band_files(sd)
            b02_list += bands["B02"]
            b03_list += bands["B03"]
            b04_list += bands["B04"]
        if not (b02_list and b03_list and b04_list):
            print("  Faltan bandas 10 m (B02/B03/B04). Saltando.")
            continue
        tmp_dir = out_dir / f"tmp_{yyyymmdd}_{orbit}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        vrt_b04 = tmp_dir / "B04.vrt"
        vrt_b03 = tmp_dir / "B03.vrt"
        vrt_b02 = tmp_dir / "B02.vrt"
        print("  Creando VRTs por banda…")
        build_mosaic_vrt(vrt_b04, b04_list)
        build_mosaic_vrt(vrt_b03, b03_list)
        build_mosaic_vrt(vrt_b02, b02_list)
        out_tif = out_dir / f"S2_RGB_10m_{yyyymmdd}_{orbit}.tif"
        print("  Generando mosaico RGB…")
        translate_rgb(vrt_b04, vrt_b03, vrt_b02, out_tif)
        print(f"  Listo: {out_tif}")

    print("\nTerminado.")


if __name__ == "__main__":
    main()
