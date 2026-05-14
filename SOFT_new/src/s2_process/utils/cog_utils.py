"""COG conversion utilities."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def tiff_to_cog(gdal_bin: str | Path, input_file: str, output_file: str | None = None) -> int:
    """Convert TIFF to Cloud Optimized GeoTIFF."""
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_cog{ext}"

    translate = os.path.join(gdal_bin, "gdal_translate.bat")
    cmd = (
        f'"{translate}" -of cog -a_nodata 0 '
        f'-co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES '
        f'"{input_file}" "{output_file}"'
    )
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        os.replace(output_file, input_file)
    return result.returncode


def quicklook_8bit(
    gdal_bin: str | Path,
    input_file: str,
    output_file: str,
) -> int:
    """Generate 8-bit RGB JPEG QuickLook COG."""
    translate = os.path.join(gdal_bin, "gdal_translate.bat")
    cmd = (
        f'"{translate}" -ot byte -a_nodata 0 -b 3 -b 2 -b 1 '
        f'-co COMPRESS=JPEG -co QUALITY=75 -of COG '
        f'-scale 0 1 0 0.1 -co BIGTIFF=YES '
        f'"{input_file}" "{output_file}"'
    )
    result = subprocess.run(cmd, shell=True)
    aux = output_file + ".aux.xml"
    if os.path.exists(aux):
        os.remove(aux)
    return result.returncode


def quicklook_16bit(
    gdal_bin: str | Path,
    input_file: str,
    output_file: str,
) -> int:
    """Generate 16-bit RGBNir QuickLook COG."""
    translate = os.path.join(gdal_bin, "gdal_translate.bat")
    cmd = (
        f'"{translate}" -ot UInt16 -a_nodata 0 -b 3 -b 2 -b 1 -b 7 '
        f'-co COMPRESS=LZW -co PREDICTOR=STANDARD -of COG '
        f'-co BIGTIFF=YES '
        f'"{input_file}" "{output_file}"'
    )
    result = subprocess.run(cmd, shell=True)
    aux = output_file + ".aux.xml"
    if os.path.exists(aux):
        os.remove(aux)
    return result.returncode
