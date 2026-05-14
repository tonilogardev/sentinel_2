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
    scene = f"S2_L1C_{orbit}_{compact}"
    out_path = seg_folder / f"{scene}.btf"

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1e6
        _log(seg_folder, f"  EXISTS: {out_path.name} ({size_mb:.0f} MB)")
        return True

    result = build_cog(products, out_path, orbit, area, target_epsg)
    return result is not None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m s2_process.main <pipeline.json>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
