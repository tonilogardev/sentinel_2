"""L1C 4-band mosaic (B02, B03, B04, B08) from individual JP2 files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from osgeo import gdal
from osgeo_utils.gdal_calc import Calc

from s2_process.utils.offset_gain import search_gain, search_offset


BANDS_4B = ["B02", "B03", "B04", "B08"]


def apply_gain_offset_band(
    jp2_path: str,
    out_path: str,
    gain: float,
    offset_f: float,
) -> str:
    Calc(
        A=jp2_path,
        outfile=out_path,
        calc=f"A*{gain}+{offset_f}",
        type="UInt16",
        NoDataValue=0,
    )
    return out_path


def reproject_tile(
    input_file: str,
    output_file: str,
    src_epsg: str,
    dst_epsg: str,
    res: float = 10.0,
) -> str:
    subprocess.run([
        "gdalwarp", "-r", "cubic",
        "-tr", str(res), str(res), "-tap",
        "-s_srs", src_epsg, "-t_srs", dst_epsg,
        "-srcnodata", "0", "-dstnodata", "0",
        input_file, output_file,
    ], check=True)
    return output_file


def process_tile_4b(
    tile_info: dict[str, Any],
    work_dir: str | Path,
    target_epsg: str = "EPSG:32631",
) -> str | None:
    """Process a single tile: apply gain/offset → reproject if needed → return merged TIFF."""
    work_dir = Path(work_dir)
    tile = tile_info["tile"]
    band_files = tile_info["band_files"]
    safe_dir = tile_info.get("safe_dir")
    needs_reproject = tile_info["needs_reproject"]

    gain = 10000.0
    if safe_dir:
        g = search_gain("L1C", safe_dir)
        if g != -9999:
            gain = g

    tile_tifs: list[str] = []
    for i, band in enumerate(BANDS_4B):
        jp2 = band_files.get(band)
        if not jp2 or not Path(jp2).exists():
            print(f"    {tile} {band}: file not found")
            continue

        offset = 0.0
        if safe_dir:
            o = search_offset("L1C", safe_dir, i + 1)
            if o != -9999:
                offset = o

        offset_f = 10000.0 * offset / gain
        gain_f = 10000.0 / gain

        out_tif = str(work_dir / f"{tile}_{band}.tif")
        apply_gain_offset_band(jp2, out_tif, gain_f, offset_f)
        tile_tifs.append(out_tif)

    if len(tile_tifs) != 4:
        print(f"    {tile}: not enough bands ({len(tile_tifs)}/4)")
        return None

    # Stack bands into single TIFF
    stacked = str(work_dir / f"{tile}_stacked.vrt")
    subprocess.run([
        "gdalbuildvrt", "-separate", "-overwrite",
        "-srcnodata", "0", "-vrtnodata", "0",
        stacked, *tile_tifs,
    ], check=True)

    stacked_tif = str(work_dir / f"{tile}_stacked.tif")
    gdal.Translate(stacked_tif, stacked, noData=0,
                   creationOptions=["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"])

    # Cleanup band tifs
    for f in tile_tifs:
        Path(f).unlink(missing_ok=True)
    Path(stacked).unlink(missing_ok=True)

    # Reproject if needed
    if needs_reproject:
        final = str(work_dir / f"{tile}_merged.tif")
        reproject_tile(stacked_tif, final, tile_info["epsg"], target_epsg)
        Path(stacked_tif).unlink(missing_ok=True)
        return final

    return stacked_tif


def build_mosaic_4b(
    tile_tifs: list[str],
    output_name: str,
    work_dir: str | Path,
    limits: tuple[float, float, float, float] | None = None,
) -> str:
    """Merge reprojected tile TIFFs into a single COG mosaic."""
    work_dir = Path(work_dir)
    vrt_path = str(work_dir / f"{output_name}.vrt")

    cmd = ["gdalbuildvrt", "-overwrite"]
    if limits:
        cmd += ["-te"] + [str(x) for x in limits]
    cmd += [vrt_path] + tile_tifs
    subprocess.run(cmd, check=True)

    cog_path = str(work_dir / f"{output_name}.btf")
    gdal.Translate(cog_path, vrt_path, noData=0, format="COG",
                   creationOptions=["COMPRESS=LZW", "PREDICTOR=STANDARD", "BIGTIFF=YES"])

    Path(vrt_path).unlink(missing_ok=True)
    return cog_path
