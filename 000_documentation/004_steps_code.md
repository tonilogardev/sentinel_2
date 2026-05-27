# Trazabilidad del Código S2-PROCESS (Como un Compilador)

## Index

1. [El Arranque del Motor (main.py)](#1-el-arranque-del-motor-mainpy)
2. [El Bucle de Segmentos](#2-el-bucle-de-segmentos)
3. [Etapa 1 y 2: Preparando el L1C](#3-etapa-1-y-2-preparando-el-l1c)
4. [Etapa 3 y 4: Las dos caras de Sen2Cor](#4-etapa-3-y-4-las-dos-caras-de-sen2cor)
5. [Etapa 5: Los Productos Derivados (GDAL)](#5-etapa-5-los-productos-derivados-gdal)

---

## 1 El Arranque del Motor (main.py)

- ***Instrucción***: Cuando el usuario lanza el comando, Python entra directamente al bloque `if __name__ == "__main__":` del archivo orquestador.
- ***Traza de funciones***:
  1. Se llama a `main()`. Lo primero que hace es leer los argumentos de la consola (si los hay) para buscar el archivo JSON.
  2. Crea la instancia `config = PipelineConfig(args.config)`. Esta clase se mete en [config.py](../SOFT_new/src/s2_process/config.py), parsea el JSON y lee tu fichero `.env` en busca de `CDSE_USERNAME`.
  3. Llama a `setup_logger(...)` en [logger.py](../SOFT_new/src/s2_process/utils/logger.py) para abrir el canal de texto hacia tu archivo `.log` en la carpeta `output/logs/`.
  4. Levanta el cliente de red instanciando `CopernicusDataspaceClient`. Todavía no descarga nada, solo inicia sesión en la API de OData para pillar el Token.
- ***File References***:
  - Archivo maestro: [main.py](../SOFT_new/src/s2_process/main.py)

[←Index](#index)

## 2 El Bucle de Segmentos

- ***Instrucción***: El código prepara la lista de fechas y órbitas para empezar a iterar.
- ***Traza de funciones***:
  1. La función `get_date_list` crea un array de días desde tu `date_range_start` hasta `date_range_end`.
  2. Empieza el doble bucle anidado: `for date_str in dates: for orbit in orbits:`.
  3. Por cada pareja (ej. `2026-05-01` y `R051`), invoca a la megamáquina de estado: `process_segment(date_str, orbit, ...)`.

[←Index](#index)

## 3 Etapa 1 y 2: Preparando el L1C

- ***Instrucción***: Dentro de `process_segment`, el programa intenta conseguir la materia prima cruda.
- ***Traza de funciones***:
  1. Llama a `client.search_and_download_l1c()`. Esta función busca en el catálogo del satélite. Si hay gránulos, se los baja en formato `.zip` y devuelve una lista con las rutas físicas en disco: `zip_paths`.
  2. Inmediatamente empieza un bucle por cada `.zip`:
     - Llama a `granule_downloader.extract_granule(zip)`. Lo descomprime usando `zipfile` y te deja una carpeta `.SAFE`.
  3. Ahora que están descomprimidos, llama a `cog_builder.build_l1c_4band_mosaic()`. Esto enciende **GDAL**, fusiona las mallas sueltas, las aplica calibración (x / 10000.0) y genera el archivo L1C `.btf`.
  4. Llama a `mask_generator.create_vector_mask()`. Enciende **OpenCV** y el módulo `fiona`, lee la banda B04, quita los "dientes de sierra" negros de los bordes con matemáticas morfológicas y escribe el Shapefile poligonal.
- ***File References***:
  - Descarga L1C: [dataspace_client.py](../SOFT_new/src/s2_process/download/dataspace_client.py)
  - Mosaico crudo: [cog_builder.py](../SOFT_new/src/s2_process/processing/cog_builder.py)

[←Index](#index)

## 4 Etapa 3 y 4: Las dos caras de Sen2Cor

- ***Instrucción***: Entramos en el bloque de procesamiento pesado. Aquí el código de Python interactúa con un binario externo (Sen2Cor) haciendo llamadas al sistema operativo (`subprocess.run`).
- ***Traza de funciones***:
  1. **Motor Plano (`is_demcat=False`)**: Un bucle itera sobre todos los `.SAFE` crudos. Llama a `sen2cor_wrapper.run_sen2cor()`. Python abre una terminal invisible, lanza el archivo `.bat` de Sen2Cor pasándole tu `.SAFE` y se queda congelado esperando a que termine.
  2. Cuando el subproceso acaba, llama a `sen2cor_wrapper.apply_l2a_xml_patch()`. Esta función localiza la carpeta recién parida (usando `glob`/`fnmatch`), edita su XML interno por si Sen2Cor 2.12 lo corrompió, y cambia brutalmente el nombre de la carpeta entera añadiéndole la coletilla `_NODEM.SAFE`.
  3. **Motor DEMCAT (`is_demcat=True`)**: Se vuelve a lanzar el bucle por los mismos `.SAFE` iniciales. Pero esta vez, `run_sen2cor()` le inyecta el flag `--GIP_L2A configs/...xml`. Sen2Cor entiende que tiene que bajarse/leer el modelo de elevaciones y vuelve a pensar.
  4. Termina de pensar, y el parcheador de Python salta de nuevo, nombrando a la nueva carpeta resultante `_DEMCAT.SAFE`.
- ***File References***:
  - Invocador de Sen2Cor: [sen2cor_wrapper.py](../SOFT_new/src/s2_process/processing/sen2cor_wrapper.py)

[←Index](#index)

## 5 Etapa 5: Los Productos Derivados (GDAL)

- ***Instrucción***: El código Python coge las salidas generadas y las pasa por el embudo de GDAL y OpenCV.
- ***Traza de funciones***:
  1. El código pregunta: ¿Tengo salidas Planas? Si sí:
     - Llama a `l2a_10b_mosaic.build_l2a_10band_mosaic(..., is_demcat=False)`. Enciende `gdal.BuildVRT`, agarra todos los `_NODEM.SAFE`, y los suelda en un solo `.btf`.
     - Llama a `scl_extractor.build_l2a_scl_mosaic()`. Entra al `_NODEM.SAFE`, rebusca la carpeta `IMG_DATA/R20m/` para sacar el TIF de nubes (SCL), lo remuestrea y lo devuelve.
     - Llama a `ndvi_calculator.calculate_l2a_ndvi()`. Lee tu L2A `.btf`, hace la división `(B08-B04)/(B08+B04)`, y escupe el TIFF de NDVI normal.
  2. El código pregunta: ¿Tengo salidas Topográficas? Si sí:
     - Ejecuta exactamente las mismas tres funciones anteriores de GDAL, pero pasándoles el flag `is_demcat=True`. Así GDAL suelda los `_DEMCAT.SAFE` y genera un TIFF que acaba en `_DEMCAT.tif`.
  3. Al final, se llama a `quicklook_generator.generate_quicklook_8b()` para coger las bandas Roja, Verde y Azul del Mosaico `.btf` L2A, estirar su histograma para darles brillo, y comprimirlas en un JPG/TIF miniatura de 8 bits para que lo veas rápido.
  4. El script imprime en pantalla `SEGMENTO COMPLETADO CON ÉXITO`, y el bucle principal (`main.py`) salta a la siguiente fecha/órbita.
- ***File References***:
  - Mosaico L2A: [l2a_10b_mosaic.py](../SOFT_new/src/s2_process/processing/l2a_10b_mosaic.py)
  - Extractor SCL: [scl_extractor.py](../SOFT_new/src/s2_process/processing/scl_extractor.py)
  - Calculadora Vegetación: [ndvi_calculator.py](../SOFT_new/src/s2_process/processing/ndvi_calculator.py)

[←Index](#index)
