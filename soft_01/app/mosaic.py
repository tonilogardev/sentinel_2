"""
Mosaico L1C 10 m RGB (B04,B03,B02) por fecha y órbita.

Entrada mínima:
- Directorio padre con carpetas .SAFE (extraídas)
- Fecha (YYYY-MM-DD)
- Directorio de salida

Salida:
- Un GeoTIFF por órbita detectada: S2_RGB_10m_YYYYMMDD_Rxxx.tif
- Rejilla fija en EPSG:25831 (Catalunya):
  bbox (xmin,ymin,xmax,ymax) = (240005, 4480005, 539995, 4779995), pixel 10 m

Requisitos: GDAL disponible en el entorno (from osgeo import gdal)
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from osgeo import gdal


CATALUNYA_BOUNDS = (240005.0, 4480005.0, 539995.0, 4779995.0)  # EPSG:25831
DST_SRS = "EPSG:25831"
XRES = 10.0
YRES = 10.0


def ask(prompt: str, default: Optional[str] = None) -> str:
    v = input(f"{prompt}{' ['+default+']' if default else ''}: ").strip()
    return v or (default or "")


def ask_dir(msg: str, default: Optional[str] = None) -> Path:
    raw = ask(msg, default)
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]
    p = Path(os.path.expandvars(os.path.expanduser(raw)))
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_yyyymmdd(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")


def detect_orbit_from_name(name: str) -> Optional[str]:
    m = re.search(r"_R(\d{3})_", name)
    return f"R{m.group(1)}" if m else None


def find_safe_dirs(root: Path, yyyymmdd: str) -> List[Path]:
    return [p for p in root.glob("*.SAFE") if yyyymmdd in p.name]


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
        for b in ("B02", "B03", "B04"):
            for jp2 in r10.glob(f"*_{b}_10m.jp2"):
                bands[b].append(str(jp2))
            for jp2 in r10.glob(f"*_{b}.jp2"):
                bands[b].append(str(jp2))
    return bands


def build_vrt(out_vrt: Path, inputs: List[str]) -> None:
    if not inputs:
        raise RuntimeError("No hay entradas para el mosaico")
    opts = gdal.BuildVRTOptions(resolution="highest", srcNodata=0, VRTNodata=0, separate=False)
    ds = gdal.BuildVRT(str(out_vrt), inputs, options=opts)
    if ds is None:
        raise RuntimeError("Error al crear VRT")
    ds = None


def stack_and_warp_rgb(vrt_r: Path, vrt_g: Path, vrt_b: Path, out_tif: Path) -> None:
    # 1) Apilar R,G,B en un VRT de 3 bandas
    stack_vrt = out_tif.with_suffix(".stack.vrt")
    ds = gdal.BuildVRT(str(stack_vrt), [str(vrt_r), str(vrt_g), str(vrt_b)], options=gdal.BuildVRTOptions(separate=True))
    if ds is None:
        raise RuntimeError("Error al crear VRT RGB")
    ds = None

    # 2) Reproyectar/recortar/alinear a la rejilla objetivo (EPSG:25831, 10 m, bbox Catalunya)
    xmin, ymin, xmax, ymax = CATALUNYA_BOUNDS
    warp_tmp = out_tif.with_suffix(".warp.tif")
    gdal.Warp(
        str(warp_tmp),
        str(stack_vrt),
        dstSRS=DST_SRS,
        outputBounds=(xmin, ymin, xmax, ymax),
        xRes=XRES,
        yRes=YRES,
        targetAlignedPixels=True,
        dstNodata=0,
        resampleAlg="nearest",
        format="GTiff",
        creationOptions=["COMPRESS=LZW", "PREDICTOR=2", "BIGTIFF=YES"],
    )

    # 3) Intentar COG; si falla, dejamos el GTiff warp_tmp
    try:
        gdal.Translate(str(out_tif), str(warp_tmp), format="COG", creationOptions=["COMPRESS=LZW", "BIGTIFF=YES"], noData=0)
        warp_tmp.unlink(missing_ok=True)
    except Exception:
        # mantener warp_tmp como salida
        if out_tif.exists():
            out_tif.unlink(missing_ok=True)
        warp_tmp.rename(out_tif)


def main():
    # Entradas
    safes_root = ask_dir("Carpeta con .SAFE (extraídas)")
    date_str = ask("Fecha (YYYY-MM-DD)")
    out_dir = ask_dir("Carpeta de salida de mosaicos")

    try:
        yyyymmdd = to_yyyymmdd(date_str)
    except ValueError:
        print("Fecha inválida.")
        sys.exit(1)

    safes = find_safe_dirs(safes_root, yyyymmdd)
    if not safes:
        print("No se encontraron .SAFE para esa fecha.")
        sys.exit(0)

    # Agrupar por órbita detectada
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
        build_vrt(vrt_b04, b04_list)
        build_vrt(vrt_b03, b03_list)
        build_vrt(vrt_b02, b02_list)

        out_tif = out_dir / f"S2_RGB_10m_{yyyymmdd}_{orbit}.tif"
        print("  Generando mosaico RGB…")
        stack_and_warp_rgb(vrt_b04, vrt_b03, vrt_b02, out_tif)
        print(f"  Listo: {out_tif}")

    print("\nTerminado.")


if __name__ == "__main__":
    main()
