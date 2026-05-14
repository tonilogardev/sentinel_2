"""Build a single COG mosaic from local JP2 files (downloaded via boto3)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from osgeo import gdal
from osgeo_utils.gdal_calc import Calc

from s2_process.download.s3_downloader import BANDS_L1C_4B, discover_and_download

STACK_BANDS = ["B02", "B03", "B04", "B08"]

BAND_INDEX_MAP = {"B01": 1, "B02": 2, "B03": 3, "B04": 4,
                   "B05": 5, "B06": 6, "B07": 7, "B08": 8,
                   "B8A": 9, "B09": 10, "B10": 11, "B11": 12, "B12": 13}


def _read_offset_gain(tile_dir: str | Path) -> tuple[dict[str, float], float]:
    """Read RADIO_ADD_OFFSET per band and QUANTIFICATION_VALUE from MTD_DS.xml."""
    offsets: dict[str, float] = {}
    gain = 10000.0
    xml_path = Path(tile_dir) / "MTD_DS.xml"
    if not xml_path.exists():
        return offsets, gain

    with open(xml_path) as f:
        for line in f:
            if "<RADIO_ADD_OFFSET" in line and "band_id=" in line:
                bid = line.split('band_id="')[1].split('"')[0]
                val = float(line.split(">")[1].split("<")[0])
                for bname, bidx in BAND_INDEX_MAP.items():
                    if bid == str(bidx) or bid == f"0{bidx}":
                        offsets[bname] = val
                        break
            if "<QUANTIFICATION_VALUE" in line:
                gain = float(line.split(">")[1].split("<")[0])

    return offsets, gain


def _correct_band(src: str, dst: str, offset: float, gain: float) -> None:
    gain_f = 10000.0 / gain
    offset_f = 10000.0 * offset / gain
    Calc(A=src, outfile=dst, calc=f"A*{gain_f}+{offset_f}",
         type="UInt16", NoDataValue=0)


def _reproject_band(src: str, dst: str, src_epsg: str, dst_epsg: str) -> None:
    gdal.Warp(
        dst, src,
        srcSRS=src_epsg,
        dstSRS=dst_epsg,
        resampleAlg=gdal.GRA_Cubic,
        xRes=10.0, yRes=10.0,
        targetAlignedPixels=True,
        srcNodata=0, dstNodata=0,
        format="GTiff",
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )


def build_cog(
    products: list[dict[str, Any]],
    output_path: str | Path,
    orbit: str,
    area: dict[str, Any],
    target_epsg: str = "EPSG:32631",
) -> Path | None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    limits = area.get("limitsUTM", {}).get(orbit, [240000, 467500, 4780000, 4480000])
    te = [limits[0], limits[3], limits[1], limits[2]]

    work_dir = output_path.parent / f"tmp_{output_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = work_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corr_dir = work_dir / "corrected"
    corr_dir.mkdir(parents=True, exist_ok=True)
    reproj_dir = work_dir / "reproj"
    reproj_dir.mkdir(parents=True, exist_ok=True)

    env = {
        "AWS_S3_ENDPOINT": os.environ.get("AWS_S3_ENDPOINT", "https://eodata.dataspace.copernicus.eu"),
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    }

    tiles = discover_and_download(env, products, raw_dir, target_epsg, bands=BANDS_L1C_4B)
    total_ok = sum(1 for t in tiles if len(t["band_files"]) == 4)
    if total_ok == 0:
        print("  No bands downloaded")
        shutil.rmtree(work_dir, ignore_errors=True)
        return None

    band_files_map: dict[str, list[str]] = {b: [] for b in BANDS_L1C_4B}

    for tile_info in tiles:
        tile = tile_info["tile"]
        tile_dir = tile_info["safe_dir"]
        needs_reproj = tile_info["needs_reproject"]
        tile_epsg = tile_info["epsg"]

        offsets, gain = _read_offset_gain(tile_dir)

        for band in BANDS_L1C_4B:
            src = tile_info["band_files"].get(band)
            if not src:
                continue

            offset = offsets.get(band, 0.0)

            corrected = str(corr_dir / f"{tile}_{band}.tif")
            if not Path(corrected).exists():
                print(f"    Correct {tile} {band} (offset={offset:.0f}, gain={gain:.0f})")
                _correct_band(src, corrected, offset, gain)

            if needs_reproj:
                dst = str(reproj_dir / f"{tile}_{band}.tif")
                if not Path(dst).exists():
                    print(f"    Reproj {tile} {band} {tile_epsg} -> {target_epsg}")
                    _reproject_band(corrected, dst, tile_epsg, target_epsg)
                band_files_map[band].append(dst)
            else:
                band_files_map[band].append(corrected)

    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "YES")

    for band in BANDS_L1C_4B:
        files = band_files_map[band]
        if not files:
            print(f"  band {band}: no files, aborting")
            shutil.rmtree(work_dir, ignore_errors=True)
            return None

        vrt = work_dir / f"{band}.vrt"
        opts = gdal.BuildVRTOptions(outputBounds=te, VRTNodata=0)
        gdal.BuildVRT(str(vrt), files, options=opts)

    stack_vrt = work_dir / "stacked.vrt"
    stack_srcs = [str(work_dir / f"{b}.vrt") for b in STACK_BANDS]
    stack_opts = gdal.BuildVRTOptions(separate=True, VRTNodata=0)
    gdal.BuildVRT(str(stack_vrt), stack_srcs, options=stack_opts)

    subprocess.run([
        "gdal_translate", str(stack_vrt), str(output_path),
        "-b", "3", "-b", "2", "-b", "1", "-b", "4",
        "-of", "COG",
        "-co", "COMPRESS=LZW",
        "-co", "PREDICTOR=STANDARD",
        "-co", "BIGTIFF=YES",
        "-colorinterp_1", "red",
        "-colorinterp_2", "green",
        "-colorinterp_3", "blue",
        "-colorinterp_4", "undefined",
    ], check=True)

    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", None)
    shutil.rmtree(work_dir, ignore_errors=True)
    size_mb = output_path.stat().st_size / 1e6
    print(f"  -> {output_path.name}  ({size_mb:.0f} MB)")
    return output_path
