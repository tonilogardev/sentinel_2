#!/usr/bin/env python3
"""Search Sentinel-2 products in date range and print tile coverage per orbit."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from s2_process.config import load_config
from s2_process.download.dataspace_client import DataSpaceClient


def dates_in_range(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    return [(s + timedelta(days=d)).strftime("%Y-%m-%d") for d in range((e - s).days + 1)]


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/pipeline.json"
    config_path = Path(config_path)
    dotenv = config_path.parent / ".env"

    config = load_config(config_path, dotenv)
    client = DataSpaceClient.from_config(config)

    area = config.get("area", {})
    poly = area.get("polySearch", "")
    dr = config.get("dateRange", {"start": "2025-01-01", "end": "2025-01-01"})
    orbits = config.get("orbits", ["R051"])
    granules = area.get("granulesPerOrbit", {})

    dates = dates_in_range(dr["start"], dr["end"])
    print(f"Date range: {dr['start']} to {dr['end']} ({len(dates)} days)")
    print(f"Orbits: {orbits}")

    for orbit in orbits:
        expected = set(granules.get(orbit, []))
        print(f"\n{'='*50}")
        print(f"Orbit {orbit} — expected tiles: {len(expected)}")

        for date in dates:
            prods = client.search(date=date, orbit=orbit, polygon_wkt=poly)
            tiles = set()
            for p in prods:
                name = p["Name"]
                if "MSIL1C" in name:
                    tile = name.split("_")[5][1:]
                    if tile in expected:
                        tiles.add(tile)

            missing = expected - tiles
            status = "OK" if len(tiles) == len(expected) else f"MISSING {missing}"
            if missing:
                print(f"  {date}: {len(tiles)}/{len(expected)} tiles — {status}")
            else:
                print(f"  {date}: {len(tiles)}/{len(expected)} tiles — {status}")


if __name__ == "__main__":
    main()
