"""Granule download from Copernicus DataSpace with checksum verification."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any

from s2_process.download.dataspace_client import DataSpaceClient


def md5_checksum(filepath: str | Path) -> str:
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_product(
    client: DataSpaceClient,
    product_id: str,
    destination: str | Path,
    max_retries: int = 3,
) -> bool:
    destination = Path(destination)
    token = client.token_mgr.access_token
    url = client.get_download_url(product_id)
    checksum_web = client.get_checksum(product_id)

    cmd = [
        "curl", "--progress-bar",
        "-H", f"Authorization: Bearer {token}",
        url,
        "--location-trusted",
        "--output", str(destination),
    ]

    for attempt in range(max_retries):
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            continue

        if destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            continue

        if checksum_web and md5_checksum(destination) != checksum_web:
            print(f"  CHECKSUM ERROR, retrying ({attempt + 1}/{max_retries})")
            destination.unlink(missing_ok=True)
            continue

        return True

    return False


def download_granules(
    client: DataSpaceClient,
    products: list[dict[str, Any]],
    output_dir: str | Path,
) -> list[Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for product in products:
        product_id = product["Id"]
        name = product["Name"].replace(".SAFE", ".zip")
        dest = output_dir / name

        if dest.exists() and dest.stat().st_size > 0:
            downloaded.append(dest)
            continue

        print(f"  Downloading {name}...")
        ok = download_product(client, product_id, str(dest))
        if ok:
            downloaded.append(dest)
            print(f"    OK")
        else:
            print(f"    FAILED after retries")

    return downloaded
