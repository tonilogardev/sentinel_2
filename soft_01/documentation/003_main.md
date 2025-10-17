# Verificar y extraer L1C — main_002.py

Objetivo (menos es más)
- Validar el MD5 de los ZIP L1C contra el catálogo CDSE y extraer el .SAFE de forma segura.

Uso
- Activar entorno: `conda activate s2-process`
- Ejecutar: `python soft_01/app/main_002.py`
- Se solicitará:
  - Catálogo (por defecto: `https://catalogue.dataspace.copernicus.eu/`)
  - Carpeta con `.zip` (descargas)
  - Carpeta destino para extraer `.SAFE`

Qué hace
- Calcula MD5 local del ZIP y compara con el MD5 publicado (si existe).
- Si coincide (o no hay MD5 disponible), descomprime el `.SAFE` evitando problemas de rutas.
- Muestra resumen `OK/FAIL` por archivo.

Notas
- Espera ZIPs L1C con nombre estándar (el `Name` del producto termina en `.SAFE` y coincide con el stem del ZIP).
- No modifica los ZIP; solo valida y extrae.
- Requiere red para consultar el catálogo.
