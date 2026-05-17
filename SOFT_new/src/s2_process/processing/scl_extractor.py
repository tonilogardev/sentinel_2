"""Scene Classification Layer (SCL) extraction and mosaic."""

from __future__ import annotations

from pathlib import Path

from osgeo import gdal

from s2_process.utils.gdal_helpers import build_vrt_mosaic, translate_to_cog


def _granule_and_id(safe_dir: Path) -> tuple[str, str]:
    granule_dir = next((safe_dir / "GRANULE").iterdir())
    gname = granule_dir.name
    sample_jp2 = next(granule_dir.rglob("*_SCL_*.jp2"), None)
    if sample_jp2:
        band_id = sample_jp2.name.replace("_SCL_20m.jp2", "").replace("_SCL_60m.jp2", "")
    else:
        band_id = gname.split("_", 1)[1] if "_" in gname else gname
    return gname, band_id


def extract_scl_granule(
    safe_dir: str | Path,
    work_dir: str | Path,
) -> str | None:
    safe_dir = Path(safe_dir)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    granule_name, band_id = _granule_and_id(safe_dir)
    jp2_path = safe_dir / "GRANULE" / granule_name / "IMG_DATA" / "R20m" / f"{band_id}_SCL_20m.jp2"

    if not jp2_path.exists():
        return None

    out_tif = str(work_dir / f"{band_id}_SCL.tif")
    gdal.Warp(
        out_tif, str(jp2_path),
        xRes=10.0, yRes=10.0, targetAlignedPixels=True,
        srcNodata=0, dstNodata=0, format="GTiff",
        creationOptions=["COMPRESS=LZW", "TILED=YES"],
    )
    return out_tif


def build_scl_mosaic(
    safe_dirs: list[Path],
    output_path: str | Path,
    work_dir: str | Path,
    limits: list[float] | None = None,
) -> Path | None:
    output_path = Path(output_path)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    scl_tifs: list[str] = []
    for safe_dir in safe_dirs:
        tif = extract_scl_granule(safe_dir, work_dir)
        if tif:
            scl_tifs.append(tif)

    if not scl_tifs:
        return None

    bounds = (limits[0], limits[3], limits[1], limits[2]) if limits else None
    vrt_path = str(work_dir / f"{output_path.stem}.vrt")
    build_vrt_mosaic(scl_tifs, vrt_path, bounds=bounds)

    translate_to_cog(vrt_path, str(output_path))
    Path(vrt_path).unlink(missing_ok=True)

    return output_path
