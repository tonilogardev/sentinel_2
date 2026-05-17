"""Download full .SAFE and run Sen2Cor to generate L2A products."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path
from typing import Any

from s2_process.download.dataspace_client import DataSpaceClient
from s2_process.download.granule_downloader import download_product


def _safe_name(product: dict[str, Any]) -> str:
    return product["Name"]

def _download_safe(
    client: DataSpaceClient,
    product: dict[str, Any],
    safes_dir: Path,
) -> Path | None:
    tile = product["Name"].split("_")[5]
    sname = _safe_name(product)
    safe_dir = safes_dir / sname

    if (safe_dir / "MTD_MSIL1C.xml").exists():
        return safe_dir

    tile_dir = safes_dir / tile
    if (tile_dir / "MTD_MSIL1C.xml").exists():
        return tile_dir

    zip_path = safes_dir / f"{sname}.zip"
    if not zip_path.exists():
        print(f"    Download .SAFE {tile}...")
        ok = download_product(client, product["Id"], zip_path)
        if not ok:
            print(f"    FAILED download {tile}")
            return None

    if not (safe_dir / "MTD_MSIL1C.xml").exists():
        print(f"    Unzip {tile}...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(safes_dir)

    zip_path.unlink(missing_ok=True)
    return safe_dir if (safe_dir / "MTD_MSIL1C.xml").exists() else None


def run_sen2cor_group(
    seg_folder: Path,
    products: list[dict[str, Any]],
    config: dict[str, Any],
    gipp_name: str = "L2A_GIPP_NO_DEM.xml",
    out_subdir: str = "l2a_nodem",
) -> bool:
    safes_dir = seg_folder / "safes"
    safes_dir.mkdir(parents=True, exist_ok=True)
    l2a_dir = seg_folder / out_subdir
    l2a_dir.mkdir(parents=True, exist_ok=True)

    # Map GIPP to Wine shell wrapper
    wrapper_map = {
        "L2A_GIPP_NO_DEM.xml": "L2A_Process_NO-DEM.sh",
        "L2A_GIPP_DEM_CAT.xml": "L2A_Process_DEM-CAT.sh",
        "L2A_GIPP_DEM_SRTM.xml": "L2A_Process_DEM-SRTM.sh",
    }
    wrapper_name = wrapper_map.get(gipp_name, "L2A_Process_NO-DEM.sh")

    client = DataSpaceClient.from_config(config)

    all_ok = True
    for product in products:
        tile = product["Name"].split("_")[5]
        print(f"  L2A tile {tile}...")

        safe_dir = _download_safe(client, product, safes_dir)
        if not safe_dir:
            all_ok = False
            continue

        tile_out = l2a_dir / tile
        tile_out.mkdir(parents=True, exist_ok=True)

        existing = list(tile_out.glob("S2*MSIL2A*.SAFE"))
        if existing:
            print(f"    L2A .SAFE already exists for {tile}, skip")
            continue

        if not safe_dir.name.endswith(".SAFE"):
            sname = _safe_name(product)
            link = safe_dir.parent / sname
            if not link.exists():
                print(f"    Symlink {link.name} -> {safe_dir.name}")
                link.symlink_to(safe_dir.name)
            input_dir = link
        else:
            input_dir = safe_dir

        print(f"    {wrapper_name} {tile}...")
        result = subprocess.run(
            [wrapper_name, str(input_dir),
             "--output_dir", str(tile_out)],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"    Sen2Cor FAILED for {tile} (code {result.returncode})")
            all_ok = False
        else:
            print(f"    Sen2Cor OK for {tile}")
            # L2A .SAFE is generated directly in tile_out (--output_dir)
            l2a_safes = sorted(tile_out.glob("S2*MSIL2A*.SAFE"))
            if l2a_safes:
                print(f"    L2A generated: {l2a_safes[-1].name}")
            else:
                print(f"    WARNING: no L2A .SAFE found after Sen2Cor")

    return all_ok


def find_l2a_safes(
    seg_folder: Path,
    products: list[dict[str, Any]],
    out_subdir: str = "l2a_nodem",
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    l2a_dir = seg_folder / out_subdir
    for product in products:
        tile = product["Name"].split("_")[5]
        tile_dir = l2a_dir / tile
        safes = sorted(tile_dir.glob("S2*MSIL2A*.SAFE"))
        if safes:
            result[tile] = safes[-1]
    return result
