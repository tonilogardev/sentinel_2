# S2-PROCESS Cloud-Native (Without Sen2Cor)

Este es el espacio de trabajo rediseñado para orquestar la corrección atmosférica de imágenes Sentinel-2 utilizando contenedores Docker en un entorno Linux (WSL2), eliminando la dependencia rígida de los binarios locales de Sen2Cor.

## Estructura del Proyecto

* **`.env`** (No incluido en el repositorio): Contiene las credenciales críticas (OData, S3). Cópialo de `.env.example`.
* **`pipeline.json`**: Define el rango de fechas, órbitas y rutas relativas para los mosaicos COG de entrada.
* **`docker-compose.yml`**: Configuración de microservicios para aislar la ejecución de `FORCE`, `SIAC` y `ACOLITE`.
* **`data/`**: Volumen de entrada (solo lectura). Aquí descargaremos los TIF de L1C por streaming y alojaremos el `dem.btf` (MDT).
* **`output/`**: Volumen de salida. Donde cada contenedor escupirá los COGs de reflectancia de fondo (BOA) corregidos.
* **`src/s2_process_cloud/`**: Código orquestador en Python.
* **`scripts/`**: Utilidades satélite, incluyendo el validador estadístico `validate.py` para comparar los candidatos con Sen2Cor mediante RMSE.

## Preparación en WSL2 (Recomendado)

Para evitar los enormes cuellos de botella de velocidad (I/O) que sufre WSL2 al leer el disco NTFS de Windows (`F:\`), asegúrate de **clonar o mover esta carpeta al interior del sistema de ficheros de Linux** (`~` o `/home/usuario/`) antes de ejecutar el pipeline sobre datos reales.

## Flujo de Trabajo Teórico

1. `main.py` lee credenciales y valida la seguridad.
2. `s3_streamer.py` descarga solo las bandas necesarias L1C directamente en GeoTIFF.
3. Se ensambla el mosaico virtual y se inyecta en Docker.
4. `docker_runner.py` invoca al contenedor seleccionado (FORCE/SIAC) montando los volúmenes.
5. El contenedor extrae el MDT (si es ejecución Topográfica) y deposita el L2A en `output/`.
6. Python retoma el control y `derived_products.py` extrae el SCL y genera el NDVI.
