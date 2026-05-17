"""L2A 10-band mosaic generation (B02-B12, 10m resolution)."""

from __future__ import annotations

from pathlib import Path

from osgeo import gdal

from s2_process.utils.offset_gain import search_gain, search_offset
from s2_process.utils.gdal_helpers import build_vrt_mosaic, build_vrt_separate, translate_to_cog


BANDS_10B = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
GSD_10B = [10, 10, 10, 20, 20, 20, 10, 20, 20, 20]


def _granule_and_id(safe_dir: Path) -> tuple[str, str]:
    granule_dir = next((safe_dir / "GRANULE").iterdir())
    gname = granule_dir.name
    sample_jp2 = next(granule_dir.rglob("*_B02_*.jp2"), None)
    if sample_jp2:
        band_id = sample_jp2.name.replace("_B02_10m.jp2", "").replace("_B02_20m.jp2", "")
    else:
        band_id = gname.split("_", 1)[1] if "_" in gname else gname
    return gname, band_id


def _jp2_path(
    safe_dir: Path, granule_name: str, band_id: str, band: str, gsd: int
) -> Path:
    subdir = "R10m" if gsd == 10 else "R20m"
    return safe_dir / "GRANULE" / granule_name / "IMG_DATA" / subdir / f"{band_id}_{band}_{gsd}m.jp2"


def _vrt_with_offset(src_path: str | Path, gain_f: float, offset_f: float) -> gdal.Dataset:
    src_ds = gdal.Open(str(src_path))
    vrt_ds = gdal.GetDriverByName("VRT").CreateCopy("", src_ds)
    vrt_ds.GetRasterBand(1).SetScale(gain_f)
    vrt_ds.GetRasterBand(1).SetOffset(offset_f)
    src_ds = None
    return vrt_ds


def process_granule_10b(
    safe_dir: str | Path,
    work_dir: str | Path,
) -> str | None:
    safe_dir = Path(safe_dir)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    gain = search_gain("L2A", safe_dir)
    gain = 10000.0 if gain == -9999 else gain

    granule_name, band_id = _granule_and_id(safe_dir)

    sources: list[str] = []
    for i, band in enumerate(BANDS_10B):
        offset = search_offset("L2A", safe_dir, i + 1)
        offset = 0.0 if offset == -9999 else offset

        gain_f = 10000.0 / gain
        offset_f = 10000.0 * offset / gain
        need_correction = abs(gain_f - 1.0) > 1e-6 or abs(offset_f) > 1e-6

        jp2 = _jp2_path(safe_dir, granule_name, band_id, band, GSD_10B[i])
        if not jp2.exists():
            return None

        src: str | gdal.Dataset
        if need_correction:
            src = _vrt_with_offset(jp2, gain_f, offset_f)
        else:
            src = str(jp2)

        out = str(work_dir / f"{band_id}_{band}_10m.tif")
        if GSD_10B[i] == 20:
            gdal.Warp(
                out, src,
                xRes=10.0, yRes=10.0, targetAlignedPixels=True,
                srcNodata=0, dstNodata=0, format="GTiff",
                outputType=gdal.GDT_UInt16,
                creationOptions=["COMPRESS=LZW", "TILED=YES"],
            )
        else:
            gdal.Translate(
                out, src,
                outputType=gdal.GDT_UInt16, noData=0,
                creationOptions=["COMPRESS=LZW", "TILED=YES"],
            )
        sources.append(out)

    vrt_path = str(work_dir / f"{band_id}.vrt")
    build_vrt_separate(sources, vrt_path)

    return vrt_path


def build_l2a_mosaic(
    safe_dirs: list[Path],
    output_path: str | Path,
    work_dir: str | Path,
    limits: list[float] | None = None,
) -> Path | None:
    output_path = Path(output_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    granule_vrts: list[str] = []
    for safe_dir in safe_dirs:
        vrt = process_granule_10b(safe_dir, work_dir)
        if vrt:
            granule_vrts.append(vrt)

    if not granule_vrts:
        return None

    bounds = (limits[0], limits[3], limits[1], limits[2]) if limits else None
    vrt_path = str(work_dir / f"{output_path.stem}.vrt")
    build_vrt_mosaic(granule_vrts, vrt_path, bounds=bounds)

    translate_to_cog(vrt_path, str(output_path))

    return output_path
