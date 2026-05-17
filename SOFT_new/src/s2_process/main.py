"""Main orchestrator — single COG per orbit+date via S3 /vsis3/."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

from s2_process.config import load_config
from s2_process.download.dataspace_client import DataSpaceClient
from s2_process.processing.cog_builder import build_cog
from s2_process.processing.l2a_generator import run_sen2cor_group, find_l2a_safes
from s2_process.processing.l2a_10b_mosaic import build_l2a_mosaic
from s2_process.processing.scl_extractor import build_scl_mosaic
from s2_process.utils.state_tracker import StateTracker


STATE_FILE = "pipeline_state.json"


def _log(seg_folder: Path, msg: str) -> None:
    log_path = seg_folder / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"[{t}] {msg}\n")
    print(msg)


def _step_timed(label: str, seg_folder: Path, fn, *args, **kwargs) -> bool:
    t0 = datetime.now()
    _log(seg_folder, f"  START {label}")
    try:
        ok = fn(*args, **kwargs)
        dt = (datetime.now() - t0).total_seconds()
        if ok:
            _log(seg_folder, f"  OK    {label} ({dt:.0f}s)")
        else:
            _log(seg_folder, f"  NO_DATA {label} ({dt:.0f}s)")
        return ok
    except Exception as e:
        dt = (datetime.now() - t0).total_seconds()
        _log(seg_folder, f"  FAIL  {label} ({dt:.0f}s): {e}")
        raise


COG_VERSION = "v5"  # v5: COG + post-fix B1<->B3 + delete intermediate + rename


def run_pipeline(config_path: str | Path) -> None:
    config_path = Path(config_path)
    dotenv_path = config_path.parent / ".env"
    workspace = config_path.parent.parent / "output"

    config = load_config(config_path, dotenv_path)
    pipe = config.get("pipeline", {})
    area = config.get("area", {})
    poly_search = area["polySearch"]
    target_epsg = "EPSG:32631"

    client = DataSpaceClient.from_config(config)
    state_file = workspace / STATE_FILE
    tracker = StateTracker.from_file(state_file, config)

    _log(workspace, f"SOFT_new COG{COG_VERSION} — post-fix B1<->B3 + plataforma en nombre")
    print(f"!!! VERSION MARKER: COG{COG_VERSION} — post-fix + plataforma en nombre")

    while not tracker.all_done():
        segment = tracker.first_pending()
        if not segment:
            break

        step = tracker.next_step(segment)
        date = segment["date"]
        orbit = segment["orbit"]
        seg_folder = workspace / f"{date}_{orbit}"

        _log(seg_folder, f"{'='*50}")
        _log(seg_folder, f">>> [{step.upper()}] {date} {orbit}")
        _log(seg_folder, f"{'='*50}")

        if step == "downloaded":
            ok = _step_timed("download", seg_folder, _step_download,
                             client, seg_folder, date, orbit, poly_search, area)
        elif step == "l1c_processed":
            ok = _step_timed("l1c_cog", seg_folder, _step_l1c,
                             seg_folder, date, orbit, area, target_epsg)
        elif step == "l2a_generated":
            ok = _step_timed("l2a_generate", seg_folder, _step_l2a_generate,
                             seg_folder, date, orbit, area, config)
        elif step == "l2a_processed":
            ok = _step_timed("l2a_process", seg_folder, _step_l2a_process,
                             seg_folder, date, orbit, area, target_epsg)
        else:
            _log(seg_folder, f"  Step {step} — not yet implemented")
            ok = True

        if ok is False:
            tracker.mark(segment, step, "no_data")
            for s in tracker.remaining_steps(segment, step):
                tracker.mark(segment, s, "no_data")
            _log(seg_folder, f"  -> no_data — skipping remaining steps")
        else:
            tracker.mark(segment, step)
        tracker.save()

    _log(workspace, f"Pipeline finished.")
    tracker.save()


def _step_download(
    client: DataSpaceClient,
    seg_folder: Path,
    date: str,
    orbit: str,
    poly_search: str,
    area: dict[str, Any],
) -> bool:
    """Search + validate products exist. Save list for next step."""
    granules = area.get("granulesPerOrbit", {}).get(orbit, [])
    products = client.search(date=date, orbit=orbit, polygon_wkt=poly_search)

    filtered = [p for p in products if p["Name"].split("_")[5] in granules]
    if not filtered:
        print("  No products found")
        return False

    seg_folder.mkdir(parents=True, exist_ok=True)
    import json
    with open(seg_folder / "products.json", "w") as f:
        json.dump(filtered, f, indent=2)
    print(f"  Products found: {len(filtered)} tiles")
    return True


def _step_l1c(
    seg_folder: Path,
    date: str,
    orbit: str,
    area: dict[str, Any],
    target_epsg: str,
) -> bool:
    """Build single COG from S3 via /vsis3/."""
    _log(seg_folder, f"  COG {COG_VERSION}: COG + post-fix B1<->B3 + delete intermedio + rename")
    products_file = seg_folder / "products.json"
    if not products_file.exists():
        _log(seg_folder, "  No products file — nothing to process")
        return False

    import json
    with open(products_file) as f:
        products = json.load(f)

    if not products:
        _log(seg_folder, "  Empty products list")
        return False

    compact = date.replace("-", "")
    platform = products[0]["Name"].split("_")[0]
    scene = f"{platform}_L1C_{orbit}_{compact}"
    out_path = seg_folder / f"{scene}.btf"

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1e6
        _log(seg_folder, f"  EXISTS: {out_path.name} ({size_mb:.0f} MB)")
        return True

    result = build_cog(products, out_path, orbit, area, target_epsg)
    return result is not None


def _step_l2a_generate(
    seg_folder: Path,
    date: str,
    orbit: str,
    area: dict[str, Any],
    config: dict[str, Any],
) -> bool:
    products_file = seg_folder / "products.json"
    if not products_file.exists():
        return False

    import json
    with open(products_file) as f:
        products = json.load(f)

    granules = area.get("granulesPerOrbit", {}).get(orbit, [])
    filtered = [p for p in products if p["Name"].split("_")[5] in granules]
    if not filtered:
        return False

    ok = run_sen2cor_group(seg_folder, filtered, config, "L2A_GIPP_NO_DEM.xml", "l2a_nodem")
    return ok


def _step_l2a_process(
    seg_folder: Path,
    date: str,
    orbit: str,
    area: dict[str, Any],
    target_epsg: str,
) -> bool:
    products_file = seg_folder / "products.json"
    if not products_file.exists():
        return False

    import json
    with open(products_file) as f:
        products = json.load(f)

    granules = area.get("granulesPerOrbit", {}).get(orbit, [])
    filtered = [p for p in products if p["Name"].split("_")[5] in granules]
    if not filtered:
        return False

    limits = area.get("limitsUTM", {}).get(orbit, [240000, 467500, 4780000, 4480000])
    compact = date.replace("-", "")
    platform = filtered[0]["Name"].split("_")[0]
    scene = f"{platform}_L2A_{orbit}_{compact}"
    out_path = seg_folder / f"{scene}.btf"
    scl_out = seg_folder / f"{platform}_SCL_{orbit}_{compact}.tif"

    if out_path.exists():
        return True

    safes_map = find_l2a_safes(seg_folder, filtered, "l2a_nodem")
    if not safes_map:
        return False

    work_dir = seg_folder / f"tmp_l2a_{compact}"
    work_dir.mkdir(parents=True, exist_ok=True)

    l2a_ok = build_l2a_mosaic(list(safes_map.values()), str(out_path), str(work_dir), limits)

    scl_ok = build_scl_mosaic(list(safes_map.values()), str(scl_out), str(work_dir), limits)

    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)
    return l2a_ok is not None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m s2_process.main <pipeline.json>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
