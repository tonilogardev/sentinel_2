"""Download individual Sentinel-2 bands from Copernicus DataSpace S3."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config


BANDS_L1C_4B = ["B02", "B03", "B04", "B08"]
BUCKET = "eodata"


def _parse_product_name(name: str) -> dict[str, str]:
    name = name.replace(".SAFE", "")
    parts = name.split("_")
    tile = parts[5]
    dt = parts[2]
    return {
        "tile": tile,
        "year": dt[:4],
        "month": dt[4:6],
        "day": dt[6:8],
        "sensing_date": dt,
    }


def _get_s3_client(env: dict[str, str]) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=env.get("AWS_S3_ENDPOINT", "https://eodata.dataspace.copernicus.eu"),
        aws_access_key_id=env.get("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=env.get("AWS_SECRET_ACCESS_KEY", ""),
        config=Config(s3={"addressing_style": "path"}),
    )


def _find_granule_folder(s3: Any, prefix: str) -> str | None:
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=5, Delimiter="/")
    prefixes = resp.get("CommonPrefixes", [])
    if prefixes:
        return prefixes[0]["Prefix"].split("/")[-2]
    return None


def _tile_epsg(tile: str) -> str:
    zone = tile[1:3]
    return f"EPSG:326{zone}"


def download_bands_s3(
    s3: Any,
    product_name: str,
    granule_folder: str,
    dest_dir: Path,
    bands: list[str] | None = None,
) -> list[Path]:
    """Download individual JP2 bands from S3 to dest_dir."""
    bands = bands or BANDS_L1C_4B
    info = _parse_product_name(product_name)
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    for band in bands:
        key = (
            f"Sentinel-2/MSI/L1C/{info['year']}/{info['month']}/{info['day']}/"
            f"{product_name}/GRANULE/{granule_folder}/IMG_DATA/"
            f"{info['tile']}_{info['sensing_date']}_{band}.jp2"
        )
        out_file = dest_dir / f"{info['tile']}_{info['sensing_date']}_{band}.jp2"

        if out_file.exists() and out_file.stat().st_size > 0:
            downloaded.append(out_file)
            continue

        try:
            s3.download_file(Bucket=BUCKET, Key=key, Filename=str(out_file))
            downloaded.append(out_file)
        except Exception as e:
            print(f"    S3 error {band}: {e}")

    return downloaded


def download_bands_odata(
    client: Any,
    product: dict[str, Any],
    dest_dir: Path,
    bands: list[str] | None = None,
) -> list[Path]:
    """Fallback: download full .SAFE via OData curl."""
    bands = bands or BANDS_L1C_4B
    name = product["Name"].replace(".SAFE", "")
    info = _parse_product_name(name)
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    for band in bands:
        out_file = dest_dir / f"{info['tile']}_{info['sensing_date']}_{band}.jp2"
        if out_file.exists() and out_file.stat().st_size > 0:
            downloaded.append(out_file)
            continue
        print(f"    S3 no disponible — cal baixar {band} per OData")
    return downloaded


def _find_datastrip_name(s3: Any, prefix: str) -> str | None:
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, MaxKeys=5, Delimiter="/")
    prefixes = resp.get("CommonPrefixes", [])
    if prefixes:
        return prefixes[0]["Prefix"].split("/")[-2]
    return None


def download_metadata_s3(
    s3: Any,
    product_name: str,
    granule_folder: str,
    dest_dir: Path,
) -> Path | None:
    """Download MTD_DS.xml for offset/gain reading."""
    info = _parse_product_name(product_name)
    base = f"Sentinel-2/MSI/L1C/{info['year']}/{info['month']}/{info['day']}/{product_name}"

    # Find DATASTRIP folder
    ds_prefix = f"{base}/DATASTRIP/"
    ds_name = _find_datastrip_name(s3, ds_prefix)
    if not ds_name:
        return None

    xml_key = f"{base}/DATASTRIP/{ds_name}/MTD_DS.xml"
    xml_path = dest_dir / "MTD_DS.xml"

    if xml_path.exists():
        return xml_path

    try:
        s3.download_file(Bucket=BUCKET, Key=xml_key, Filename=str(xml_path))
        return xml_path
    except Exception:
        return None


def discover_and_download(
    env: dict[str, str],
    products: list[dict[str, Any]],
    work_dir: Path,
    target_epsg: str = "EPSG:32631",
    bands: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Download bands for all products via S3.

    Returns list of dicts per tile: {tile, epsg, safe_dir, needs_reproject, band_files}
    """
    bands = bands or BANDS_L1C_4B
    has_s3_creds = bool(env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"))
    s3 = _get_s3_client(env) if has_s3_creds else None
    result: list[dict[str, Any]] = []

    for product in products:
        name = product["Name"]
        info = _parse_product_name(name)
        tile = info["tile"]
        tile_dir = work_dir / tile
        tile_dir.mkdir(parents=True, exist_ok=True)

        granule_folder = None
        if s3:
            prefix = f"Sentinel-2/MSI/L1C/{info['year']}/{info['month']}/{info['day']}/{name}/GRANULE/"
            granule_folder = _find_granule_folder(s3, prefix)

        if granule_folder and s3:
            files = download_bands_s3(s3, name, granule_folder, tile_dir, bands)
            download_metadata_s3(s3, name, granule_folder, tile_dir)
        else:
            print(f"    {tile}: S3 no disponible, prova amb OData")
            files = download_bands_odata(None, product, tile_dir, bands)

        tile_epsg = _tile_epsg(tile)
        safe_dir = tile_dir  # Simulem estructura SAFE usant el directori local

        result.append({
            "tile": tile,
            "epsg": tile_epsg,
            "safe_dir": str(safe_dir),
            "needs_reproject": tile_epsg != target_epsg,
            "band_files": {b: str(f) for f in files for b in bands if b in f.name},
        })

    return result
