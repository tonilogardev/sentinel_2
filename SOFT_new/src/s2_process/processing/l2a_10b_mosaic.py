"""L2A 10-band mosaic generation (B02-B12, 10m resolution)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from osgeo import gdal
from osgeo_utils.gdal_calc import Calc

from s2_process.utils.offset_gain import search_gain, search_offset
from s2_process.utils.gdal_helpers import correct_jp2_data, build_vrt_separate, warp_to_cutline, translate_to_cog


BANDS_10B = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
GSD_10B = [10, 10, 10, 20, 20, 20, 10, 20, 20, 20]


def process_granule_10b(
    safe_dir: str | Path,
    granule_name: str,
    granule_id: str,
    work_dir: str | Path,
) -> str:
    work_dir = Path(work_dir)
    gain = search_gain("L2A", safe_dir)
    if gain == -9999:
        gain = 10000

    band_files = []
    for i, band in enumerate(BANDS_10B):
        offset = search_offset("L2A", safe_dir, i + 1)
        if offset == -9999:
            offset = 0

        offset_f = 10000.0 * offset / gain
        gain_f = 10000.0 / gain

        if GSD_10B[i] == 10:
            file_in = f"{safe_dir}/GRANULE/{granule_name}/IMG_DATA/R10m/{granule_id[:22]}_{band}_10m.jp2"
        else:
            file_in = f"{safe_dir}/GRANULE/{granule_name}/IMG_DATA/R20m/{granule_id[:22]}_{band}_20m.jp2"

        corrected = correct_jp2_data(file_in, offset=abs(int(offset)))
        file_tmp = str(work_dir / f"{granule_id}_{band}_tmp.tif")

        Calc(
            A=corrected,
            outfile=file_tmp,
            calc=f"A*{gain_f}+{offset_f}",
            type="UInt16",
            NoDataValue=0,
        )

        if GSD_10B[i] == 20:
            file_out = str(work_dir / f"{granule_id}_{band}.tif")
            warp_options = gdal.WarpOptions(
                xRes=10.0, yRes=10.0, targetAlignedPixels=True,
                srcNodata=0, dstNodata=0, format="GTiff",
            )
            gdal.Warp(file_out, file_tmp, options=warp_options)
            Path(file_tmp).unlink(missing_ok=True)
        else:
            file_out = file_tmp

        band_files.append(file_out)

    vrt_path = str(work_dir / f"{granule_id}.vrt")
    build_vrt_separate(band_files, vrt_path)

    tif_path = str(work_dir / f"{granule_id}.tif")
    gdal.Translate(tif_path, vrt_path, noData=0, creationOptions=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"])

    for f in band_files:
        Path(f).unlink(missing_ok=True)
    Path(vrt_path).unlink(missing_ok=True)

    return tif_path


def mosaic_10b(
    granule_tifs: list[str],
    output_name: str,
    work_dir: str | Path,
    limits: tuple[float, float, float, float] | None = None,
) -> str:
    work_dir = Path(work_dir)
    vrt_path = str(work_dir / f"{output_name}.vrt")
    bounds = (limits[0], limits[2], limits[1], limits[3]) if limits else None
    build_vrt_separate(granule_tifs, vrt_path, bounds=bounds)

    cog_path = str(work_dir / f"{output_name}.btf")
    translate_to_cog(vrt_path, cog_path)

    Path(vrt_path).unlink(missing_ok=True)
    return cog_path
