# S2-PROCESS Pipeline (SOFT_new)

> [!NOTE]
> Este documento es un mapa mental técnico (AI rules) para desarrollo interno. Para el Manual de Usuario, flujos de salida y comandos de ejecución, consultar [000_documentation/SOFT_new.md](file:///f:/Disc_F/Orto_S2_CAT/antonio/open_code_project/000_documentation/SOFT_new.md).

## Project Overview
Pipeline de procesamiento Sentinel-2 modernizado para entornos Windows nativos. Descarga imágenes L1C de Copernicus, ejecuta el motor de corrección atmosférica Sen2Cor (local en Windows), y genera productos L2A y L1C calibrados con parámetros customizados.

## Technical Architecture & Code Structure
- `SOFT_new/` — Directorio raíz del Pipeline Activo
  - `src/s2_process/` — Código fuente Python
    - `main.py` — Orquestador principal del flujo
    - `config.py` — Carga e inyección de `pipeline.json` + variables `.env`
    - `download/` — Módulos de descarga de la ESA
      - `dataspace_client.py` — API OData Copernicus DataSpace
      - `s3_downloader.py` — Descarga selectiva de bandas individuales vía AWS S3
      - `granule_downloader.py` — Descarga del gránulo .SAFE completo
    - `processing/` — Módulos de cálculo y GDAL
      - `cog_builder.py` — Mosaico COG 4-bandas L1C calibrado
      - `l2a_10b_mosaic.py` — Mosaico COG 10-bandas L2A (BOA)
      - `scl_extractor.py` — Extracción y remuestreo 20m→10m de máscara SCL
      - `ndvi_calculator.py` — Calculadora de NDVI
      - `quicklook_generator.py` — Generador de QuickLooks RGB y RGBI
      - `mask_generator.py` — Generador de máscaras vectoriales (Cutline)
    - `utils/` — Utilidades core
      - `state_tracker.py` — Tracking de estado del pipeline (downloaded, l1c_processed, l2a_generated...)
      - `gdal_helpers.py` — Wrappers nativos de GDAL y VRTs
      - `offset_gain.py` — Lector de metadatos radiométricos (MTD_DS.xml)
      - `sen2cor_patch.py` — Parche inyector de Baseline 05.11 para Sen2Cor
  - `environment.yml` — Entorno de dependencias Conda (GDAL, Numpy, Rasterio...)
  - `pipeline.json` — Configuración de órbitas, fechas y bounding boxes.
  - `.env` — Credenciales de CDSE y S3.
  - `Sen2Cor-02.12.03-win64/` — Motor compilado nativo de Sen2Cor para Windows.

## Entorno Local (Windows NATIVO)
- **Eliminación de dependencias pesadas**: No se requiere Docker, Wine, ni Linux Subsystems.
- **Python Environment**: Administrado con Conda/Miniconda a través del `environment.yml` (e.g., entorno `sentinel2`). Incluye dependencias críticas como `libgdal-jp2openjpeg` para acelerar el procesamiento de JP2000.
- **Sen2Cor**: Se usa la build oficial para Windows nativa (`L2A_Process.bat`).

## Sen2Cor Windows Details
- **Motor Local**: Carpeta embebida junto al código fuente: `Sen2Cor-02.12.03-win64/L2A_Process.bat`.
- **Compatibilidad Baseline 05.11**: Un sistema de parcheo automático (`sen2cor_patch.py`) reescribe dinámicamente el schema XSD problemático de la nueva Baseline ESA (`psd-14` y `psd-15`) para evitar bloqueos del binario de Windows (`Syntax error in metadata`).
- **GIPP Custom**: Configuración de procesado inyectada vía argumento `--GIP_L2A configs\gipp\L2A_GIPP_*.xml`

## Technical Known Issues
- GDAL no preserva todas las bandas cuando se usa `-separate` con TIFFs que ya son multi-banda. Workaround actual: usar el flag por defecto de GDAL sin separar a la hora de hacer el mosaico general en `l2a_10b_mosaic.py`.
