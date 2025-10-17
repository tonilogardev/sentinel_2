# Start Project — Entorno S2-PROCESS (solo environment.yml)

Objetivo: crear y activar el entorno con Conda usando el archivo `soft_01/environment.yml`.

Contenido principal del entorno (resumen):
- Python 3.8, pip
- numpy, openpyxl, opencv, requests, pyproj, shapely, certifi
- gdal 3.2.*, curl, setuptools, wheel

## Crear y activar el entorno

```powershell
conda env create -f soft_01/environment.yml -n s2-process
conda activate s2-process
```

## Verificación rápida
```powershell
python - << 'PY'
from osgeo import gdal
import cv2, shapely, pyproj, requests, openpyxl
print('GDAL', gdal.VersionInfo('--version'))
PY
```

Si falla la importación de GDAL:
- Asegura que el canal `conda-forge` está activo y recrea el entorno con el mismo `environment.yml`.
- Si persiste, elimina y vuelve a crear el entorno: `conda env remove -n s2-process` y repite los comandos de creación.

## WSL (Ubuntu)
- Abre la terminal WSL y sitúate en el repo (ejemplo):
  - `cd /mnt/x/antonio/trabajos/sentinel_2/sentinel_2`
- Crea/activa el entorno (mismos comandos):
  - `conda env create -f soft_01/environment.yml -n s2-process`
  - `conda activate s2-process`
- Verifica:
  - `python -c "from osgeo import gdal; print('GDAL', gdal.VersionInfo('--version'))"`
