# S2-PROCESS Pipeline

## Project Overview
Pipeline de procesamiento Sentinel-2 que descarga imágenes L1C, ejecuta Sen2Cor con parámetros custom (GIPP XMLs de SOFT) y genera productos L2A con corrección atmosférica a medida.

## Project Structure
- `SOFT_new/` — Pipeline activo
  - `src/s2_process/` — Código fuente
    - `main.py` — Orquestador, loop state-based
    - `config.py` — Carga pipeline.json + .env
    - `download/` — Clientes de descarga
      - `dataspace_client.py` — API OData de Copernicus DataSpace
      - `s3_downloader.py` — Descarga de bandas individuales via S3
      - `granule_downloader.py` — Descarga de .SAFE completo via OData (curl)
    - `processing/` — Procesamiento
      - `cog_builder.py` — COG 4-bandas L1C (v5: post-fix B1↔B3)
      - `l1c_mosaic.py` — Mosaico L1C (referencia)
      - `l2a_10b_mosaic.py` — Mosaico 10-bandas L2A (BOA offset/gain + VRT + COG)
      - `scl_extractor.py` — Extractor SCL + mosaico (reproj 20m→10m + COG)
      - `ndvi_calculator.py` — NDVI listo
      - `quicklook_generator.py` — QuickLook listo
      - `mask_generator.py` — Máscaras
    - `utils/` — Utilidades
      - `state_tracker.py` — State machine con steps: downloaded, l1c_processed, l2a_generated, l2a_processed, quicklook, l2a_demcat_generated, l2a_demcat_processed
      - `gdal_helpers.py` — Funciones GDAL helper
      - `offset_gain.py` — Lectura offset/gain de MTD_DS.xml
  - `Dockerfile.sen2cor` — Imagen custom con Sen2Cor + GDAL + Python 3
  - `Dockerfile.sen2cor.wine` — Ubuntu 22.04 + Sen2Cor 2.12.03 via Wine 11.0 + GDAL 3.4.1
  - `docker-compose.yml` — Servicios `s2` y `s2-wine`
  - `configs/` — Configuración
    - `pipeline.json` — Orbits R051, R008, fechas, área, polígono
    - `gipp/` — GIPP XMLs de SOFT (NO-DEM, DEM-CAT, DEM-SRTM)
  - `requirements.txt` — numpy<2, opencv, requests, boto3, botocore

## Pipeline Flow
1. `downloaded` — Buscar productos en OData + guardar products.json
2. `l1c_processed` — Descargar bandas L1C de S3 → offset/gain → reproject → VRT → COG 4B → post-fix B1↔B3
3. `l2a_generated` — Descargar .SAFE completo → Sen2Cor 2.12.03 via Wine con GIPP NO-DEM
4. `l2a_processed` — Mosaico 10-bandas L2A (10B) + SCL vía VRT sin `-separate`
5. `quicklook` — [PENDIENTE] NDVI + QuickLook
6. `l2a_demcat_generated` — [PENDIENTE] Sen2Cor con GIPP DEM-CAT
7. `l2a_demcat_processed` — [PENDIENTE] Mosaico 10B + SCL DEM-CAT

## Key Configs
- Pipeline: `SOFT_new/configs/pipeline.json`
- GIPP NO-DEM: `SOFT_new/configs/gipp/L2A_GIPP_NO_DEM.xml`
- GIPP DEM-CAT: `SOFT_new/configs/gipp/L2A_GIPP_DEM_CAT.xml`
- GIPP DEM-SRTM: `SOFT_new/configs/gipp/L2A_GIPP_DEM_SRTM.xml`
- .env: AWS_S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CDSE_USERNAME, CDSE_PASSWORD

## Docker
- Imagen `s2-process-l2a`: basada en kappazeta/sen2cor:v2.11.00 (solo Sen2Cor 2.11, sin PSD-15)
- Imagen `s2-process-l2a-wine`: Ubuntu 22.04 + Sen2Cor 2.12.03 via Wine 11.0 + GDAL 3.4.1
  - Build: `docker compose build s2-wine` (desde `SOFT_new/Dockerfile.sen2cor.wine`)
  - Run: `docker compose up s2-wine`
- Wrapper scripts instalados en `/usr/local/bin/L2A_Process_{VARIANT}.sh`
- Runtime Wine prefix creado en `/tmp/wine_prefix` (no baked en imagen)

## Output Naming
- `S2X_L1C_{orbit}_{compact}.btf` — L1C 4-bandas (TOA)
- `S2X_L2A_{orbit}_{compact}.btf` — L2A 10-bandas (NO-DEM)
- `S2X_L2A_{orbit}_{compact}_DEMCAT.btf` — L2A 10-bandas (DEM-CAT)
- `S2X_SCL_{orbit}_{compact}.tif` — Scene Classification Layer

## Known Issues
- GDAL Bug en `BuildVRT(separate=True)` causa band swap B1↔B3 en COG 4B. Workaround: post-fix swap con gdal_translate -b 3,2,1,4 (v5)
- Sen2Cor 2.11.00 necesita Python 2.7 (bundled en /opt/sen2cor), no interfiere con Python 3 del pipeline
- `build_vrt_separate` (con `-separate`) solo preserva 1ª banda para inputs multi-banda. Workaround: `build_vrt_mosaic` sin `-separate` para mosaicar TIFFs multi-banda

## Sen2Cor Details
- Binario: `/usr/local/bin/L2A_Process` (wrapper que sourcea `/opt/sen2cor/L2A_Bashrc`)
- Parámetros: `--GIP_L2A /workspace/configs/gipp/L2A_GIPP_*.xml`
- Input: .SAFE L1C completo (estructura de directorios standard)
- Output: .SAFE L2A con bandas en R10m/, R20m/, R60m/
