# Band Swap — SOFT_new vs SOFT reference

## Index

1. [Problem](#1-problem)
2. [Symptoms](#2-symptoms)
3. [Investigation](#3-investigation)
4. [Solution](#4-solution)
5. [Key Files](#5-key-files)
6. [Next steps](#6-next-steps)

---

## 1 Problem

`SOFT_new` produces a COG where **bands 1 and 3 are swapped** compared to the SOFT reference.

The stack VRT built by `gdal.BuildVRT(separate=True)` does not preserve the source order, or `gdal_translate` to COG does not respect the band order. The root cause is not fully identified, so a **post-fix swap** is applied.

[←Index](#index)

---

## 2 Symptoms

**SOFT reference** (correct) — [S2A_L1C_R051_20260411_SOFT.btf](../SOFT_new/input/S2A_L1C_R051_20260411_SOFT.btf):

| Band | ColorInterp | Sentinel-2 Band | Physical | Min |
|------|-------------|-----------------|----------|-----|
| 1 | Red | B04 | Red (665 nm) | 337 |
| 2 | Green | B03 | Green (560 nm) | 695 |
| 3 | Blue | B02 | Blue (490 nm) | 586 |
| 4 | Undefined | B08 | NIR (842 nm) | 627 |

**SOFT_new output** (before fix):

| Band | ColorInterp | Actual data | Min |
|------|-------------|-------------|-----|
| 1 | Red | **B02 (Blue)** | 586 |
| 2 | Green | B03 (Green) | 695 |
| 3 | Blue | **B04 (Red)** | 337 |
| 4 | Undefined | B08 (NIR) | 627 |

Bands 1 and 3 are physically swapped while color interpretation stays correct.

[←Index](#index)

---

## 3 Investigation

### Attempt v2 — `-b 3 -b 2 -b 1 -b 4` in `gdal_translate`
- Added `-b 3 -b 2 -b 1 -b 4` to reorder VRT stack `[B02,B03,B04,B08]` → `[B04,B03,B02,B08]`.
- The `-b` reorder **works in isolation** (tested with synthetic TIFFs → COG).
- In the real pipeline with multi-tile VRT sources, the reorder **did not take effect**.

### Attempt v3 — Reorder `STACK_BANDS`
- Changed `STACK_BANDS = ["B04", "B03", "B02", "B08"]` to build the VRT stack in correct order directly.
- `gdal.BuildVRT(separate=True)` may sort source files or not preserve the order when sources are VRTs.
- Output still had swapped bands.

### Attempt v4 — Post-fix swap (current)
- Generate COG as-is, then create a corrected copy swapping bands 1↔3 with `gdal_translate -b 3 -b 2 -b 1 -b 4`.
- Works reliably regardless of VRT stacking behavior.

[←Index](#index)

---

## 4 Solution

In [cog_builder.py](../SOFT_new/src/s2_process/processing/cog_builder.py), after creating the initial COG:

```python
subprocess.run([
    "gdal_translate", str(output_path), str(fixed_path),
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
```

The final corrected file is named `S2_L1C_{orbit}_{compactDate}_def.btf` (e.g., `S2_L1C_R051_20260411_def.btf`).

The pipeline skip check in [main.py](../SOFT_new/src/s2_process/main.py) looks for the `_def` file, not the intermediate one.

[←Index](#index)

---

## 5 Key Files

- [cog_builder.py](../SOFT_new/src/s2_process/processing/cog_builder.py) — COG creation + post-fix band swap (lines ~150-180)
- [main.py](../SOFT_new/src/s2_process/main.py) — Orchestrator, skip check for `_def.btf`
- [docker-compose.yml](../SOFT_new/docker-compose.yml) — Service definition (image: `s2-process-v3`)
- [pipeline.json](../SOFT_new/configs/pipeline.json) — Pipeline configuration

[←Index](#index)

---

## 6 Next steps

- Investigate root cause: why `gdal.BuildVRT(separate=True)` does not preserve source order with VRT inputs.
- Consider fixing the VRT stacking directly once root cause is understood.
- Extend to L2A, NDVI, SCL, DEMCAT steps.

[←Index](#index)
