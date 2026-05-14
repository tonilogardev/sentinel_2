# SOFT_new — Pipeline S2-PROCESS

## Index

1. [Overview](#1-overview)
2. [Pipeline Flow](#2-pipeline-flow)
3. [Configuration](#3-configuration)
4. [Run](#4-run)
5. [Band Order & Color Interpretation](#5-band-order--color-interpretation)
6. [Key Files](#6-key-files)
7. [Next steps](#7-next-steps)

---

## 1 Overview

Migrate ICGC S2-PROCESS from Excel + full `.SAFE` downloads to a **Python pipeline** that reads Sentinel-2 bands directly from **Copernicus DataSpace S3** and outputs a **single COG (`.btf`)** per orbit+date.

- ***Language***: Python 3 (GDAL, boto3)
- ***Runtime***: Docker container (`ghcr.io/osgeo/gdal:ubuntu-small-latest`)
- ***Input***: JP2 bands from S3 (boto3 download → local)
- ***Output***: `S2_L1C_{orbit}_{compactDate}.btf` (COG, UInt16, 4 bands)
- ***Secrets***: `.env` file (AWS credentials)
- ***Config***: `pipeline.json` (no Excel)

[←Index](#index)

## 2 Pipeline Flow

- ***Download***: `discover_and_download()` → for each tile, download 4 JP2 bands (B02, B03, B04, B08) from S3 + MTD_DS.xml for offset/gain.
- ***Offset/Gain Correction***: `_correct_band()` → `DN_out = DN_raw * 10000/gain + 10000*offset/gain` via `gdal_calc.Calc`.
- ***Reprojection***: `_reproject_band()` (if tile UTM zone ≠ target) → `gdal.Warp` cubic, 10m, targetAlignedPixels.
- ***Mosaic***: Per-band VRT → Stack VRT (`separate=True`) → `gdal_translate` to COG with `-b` reorder + color interpretation.
- ***Cleanup***: Temp directory deleted after COG creation.

[←Index](#index)

## 3 Configuration

Edit [`../SOFT_new/configs/pipeline.json`](../SOFT_new/configs/pipeline.json):

- ***`orbits`***: List of orbit numbers (e.g. `["R051"]`).
- ***`dateRange`***: `start` / `end` in `YYYY-MM-DD`.
- ***`area.limitsUTM`***: Per-orbit extent `[xmin, xmax, ymax, ymin]`.
- ***`area.granulesPerOrbit`***: List of tile IDs for each orbit.
- ***`satellites.platforms`***: `["S2A", "S2B", "S2C"]`.

Set credentials in [`../SOFT_new/.env`](../SOFT_new/.env):

```
AWS_S3_ENDPOINT=eodata.dataspace.copernicus.eu
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

[←Index](#index)

## 4 Run

From the project root:

```bash
docker compose -f SOFT_new/docker-compose.yml run --rm s2
```

The container:
1. Reads `pipeline.json` config.
2. Searches Copernicus DataSpace for matching products.
3. Downloads JP2 bands via **boto3** (S3 path-style, `AWS_VIRTUAL_HOSTING=NO`).
4. Applies offset/gain correction per tile.
5. Reprojects tiles not in target UTM zone.
6. Builds VRT mosaic and translates to COG.
7. Output: `output/{date}_{orbit}/S2_L1C_{orbit}_{compactDate}.btf`.

- ***First run*** downloads ~1.1 GB (4 bands × 11 tiles). Subsequent runs use cached JP2s.
- ***`gdal_translate` COG creation*** takes ~2-3 minutes.

[←Index](#index)

## 5 Band Order & Color Interpretation

The final COG matches **SOFT reference** pixel-perfect:

| COG Band | Label | Sentinel-2 Band | Physical |
|----------|-------|-----------------|----------|
| 1 | Red | B04 | Red (665 nm) |
| 2 | Green | B03 | Green (560 nm) |
| 3 | Blue | B02 | Blue (490 nm) |
| 4 | Undefined | B08 | NIR (842 nm) |

The stack VRT order is `[B02, B03, B04, B08]` but `gdal_translate -b 3 -b 2 -b 1 -b 4` reorders to `[B04, B03, B02, B08]` so color labels match the actual spectral bands.

[←Index](#index)

## 6 Key Files

- [../SOFT_new/src/s2_process/main.py](../SOFT_new/src/s2_process/main.py) — Pipeline orchestrator, step timing, state tracker.
- [../SOFT_new/src/s2_process/processing/cog_builder.py](../SOFT_new/src/s2_process/processing/cog_builder.py) — Core COG generation: correction, reprojection, VRT stacking, `gdal_translate`.
- [../SOFT_new/src/s2_process/download/s3_downloader.py](../SOFT_new/src/s2_process/download/s3_downloader.py) — S3 discovery and JP2 download per tile.
- [../SOFT_new/src/s2_process/utils/offset_gain.py](../SOFT_new/src/s2_process/utils/offset_gain.py) — Parse `MTD_DS.xml` for RADIO_ADD_OFFSET and QUANTIFICATION_VALUE.
- [../SOFT_new/src/s2_process/utils/state_tracker.py](../SOFT_new/src/s2_process/utils/state_tracker.py) — Persist pipeline state across runs.
- [../SOFT_new/configs/pipeline.json](../SOFT_new/configs/pipeline.json) — Pipeline configuration.
- [../SOFT_new/docker-compose.yml](../SOFT_new/docker-compose.yml) — Service definition.
- [../SOFT_new/Dockerfile](../SOFT_new/Dockerfile) — GDAL + Python image.

[←Index](#index)

## 7 Next steps

- Implement L2A generation (Sen2Cor).
- Implement L2A processing, quicklook, DEMCat steps.
- Validate pixel-level match for multiple dates and orbits.
- Restore full date range in `pipeline.json`.
- Add `gdal.UseExceptions()` to suppress FutureWarning.

[←Index](#index)
