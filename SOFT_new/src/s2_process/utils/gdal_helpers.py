from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from osgeo import gdal


def correct_jp2_data(
    img_in: str | Path,
    offset: int = 1000,
    img_out: str | Path | None = None,
) -> str:
    import numpy as np

    ds = gdal.Open(str(img_in))
    band = ds.GetRasterBand(1)
    data = band.ReadAsArray().astype(np.float64)

    geotransform = ds.GetGeoTransform()
    projection = ds.GetProjection()
    nx, ny = ds.RasterXSize, ds.RasterYSize
    dtype = band.DataType
    ds = None

    mask = (data > 0) & (data < offset)
    if not mask.any():
        return str(img_in)

    data[mask] = offset + 1
    if img_out is None:
        img_out = Path(str(img_in).replace(".jp2", ".tif"))

    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(
        str(img_out), nx, ny, 1, dtype,
        options=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"],
    )
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)
    out_ds.GetRasterBand(1).WriteArray(data)
    out_ds = None

    return str(img_out)


def build_vrt_separate(
    input_files: list[str],
    output_vrt: str,
    bounds: tuple[float, float, float, float] | None = None,
    epsg: str | None = None,
) -> str:
    """Stack single-band files into a multi-band VRT."""
    cmd = ["gdalbuildvrt", "-separate", "-overwrite"]
    if epsg:
        cmd += ["-a_srs", epsg]
    if bounds:
        cmd += ["-te"] + [str(b) for b in bounds]
    cmd += [output_vrt] + input_files
    subprocess.run(cmd, check=True)
    return output_vrt


def build_vrt_mosaic(
    input_files: list[str],
    output_vrt: str,
    bounds: tuple[float, float, float, float] | None = None,
) -> str:
    """Mosaic multi-band files preserving all bands."""
    cmd = ["gdalbuildvrt", "-overwrite"]
    if bounds:
        cmd += ["-te"] + [str(b) for b in bounds]
    cmd += [output_vrt] + input_files
    subprocess.run(cmd, check=True)
    return output_vrt


def warp_to_cutline(
    input_file: str,
    output_file: str,
    mask_file: str,
    dst_epsg: str | None = None,
    res: float = 10.0,
) -> str:
    cmd = [
        "gdalwarp",
        "-cutline", mask_file,
        "-crop_to_cutline",
        "-tr", str(res), str(res),
        "-tap",
        "-srcnodata", "0",
        "-dstnodata", "0",
    ]
    if dst_epsg:
        cmd += ["-s_srs", dst_epsg]
    cmd += [input_file, output_file]
    subprocess.run(cmd, check=True)
    return output_file


def translate_to_cog(
    input_file: str,
    output_file: str,
    options: dict[str, Any] | None = None,
) -> str:
    opts = {
        "format": "COG",
        "noData": 0,
        "creationOptions": [
            "COMPRESS=LZW",
            "PREDICTOR=STANDARD",
            "BIGTIFF=YES",
        ],
    }
    if options:
        opts.update(options)

    gdal.Translate(output_file, input_file, **opts)
    return output_file
