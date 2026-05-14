"""Scene Classification Layer (SCL) extraction and mosaic."""

from __future__ import annotations

from pathlib import Path

from osgeo import gdal

from s2_process.utils.gdal_helpers import build_vrt_separate, translate_to_cog


def extract_scl_granule(
    safe_dir: str | Path,
    granule_name: str,
    granule_id: str,
    work_dir: str | Path,
) -> str:
    work_dir = Path(work_dir)
    file_in = f"{safe_dir}/GRANULE/{granule_name}/IMG_DATA/R20m/{granule_id[:22]}_SCL_20m.jp2"
    file_out = str(work_dir / f"{granule_id}_SCL.tif")

    warp_options = gdal.WarpOptions(
        xRes=10.0, yRes=10.0, targetAlignedPixels=True,
        srcNodata=0, dstNodata=0, format="GTiff",
    )
    gdal.Warp(file_out, file_in, options=warp_options)
    return file_out


def mosaic_scl(
    scl_tifs: list[str],
    output_name: str,
    work_dir: str | Path,
    limits: tuple[float, float, float, float] | None = None,
) -> str:
    work_dir = Path(work_dir)
    vrt_path = str(work_dir / f"{output_name}.vrt")
    bounds = (limits[0], limits[2], limits[1], limits[3]) if limits else None
    build_vrt_separate(scl_tifs, vrt_path, bounds=bounds)

    cog_path = str(work_dir / f"{output_name}.tif")
    translate_to_cog(vrt_path, cog_path)

    Path(vrt_path).unlink(missing_ok=True)
    return cog_path
