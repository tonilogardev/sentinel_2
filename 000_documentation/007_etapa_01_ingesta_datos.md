# Etapa 1: Ingesta de Datos (Aprovisionamiento L1C)

Este documento detalla la arquitectura y el funcionamiento de la primera etapa del pipeline `SOFT_without_sen2cor`. El objetivo exclusivo de esta etapa es asegurar que los datos crudos (Nivel 1C) lleguen de forma íntegra e ininterrumpida desde los servidores de la Agencia Espacial Europea hasta el almacenamiento local, aislando al sistema de cualquier fallo de red.

## Index

1. [Consulta al Catálogo (OData)](#1-consulta-al-catálogo-odata)
2. [Gestión de Identidad y Seguridad](#2-gestión-de-identidad-y-seguridad)
3. [Descarga Robusta e Integridad ZIP](#3-descarga-robusta-e-integridad-zip)
4. [Estructura de Salida](#4-estructura-de-salida)

---

## 1 Consulta al Catálogo (OData)

- ***Instrucción***: El orquestador no descarga a ciegas. Utiliza la API OData de Copernicus Data Space Ecosystem (CDSE) para interrogar al catálogo usando los parámetros del `pipeline.json` (Fechas temporales, Órbita específica y Polígono WKT de intersección). 
- ***Filtrado Inteligente (Baseline)***: El sistema implementa un algoritmo de deduplicación. Si Copernicus devuelve múltiples versiones de un mismo gránulo (ej. `N0500` y `N0511`), el orquestador retendrá únicamente la Baseline más reciente y descartará el resto, garantizando que siempre se procesen los datos más actualizados.
- ***File References***:
    - [s3_streamer.py (Métodos `search_products` y `filter_latest_baseline`)](../SOFT_without_sen2cor/src/s2_process_cloud/download/s3_streamer.py)

[←Index](#index)

## 2 Gestión de Identidad y Seguridad

- ***Instrucción***: CDSE requiere autenticación OAuth2. El sistema lee el usuario y contraseña del archivo `.env` local, y realiza una petición POST al servidor Keycloak para obtener un Token de Acceso.
- ***Keep-Alive***: Dado que las descargas masivas pueden extenderse durante horas, se implementa un mecanismo transparente que monitorea la caducidad del token (600 segundos). Si el token expira o es revocado por el servidor, el orquestador solicita uno nuevo de forma automática antes de la siguiente petición, evitando el error `HTTP 401 Unauthorized`. Adicionalmente se implementó un `CopernicusSession` para preservar el Token entre redirecciones `HTTP 302`.
- ***File References***:
    - [s3_streamer.py (Clase `CDSEDownloader`)](../SOFT_without_sen2cor/src/s2_process_cloud/download/s3_streamer.py)

[←Index](#index)

## 3 Descarga Robusta e Integridad ZIP

- ***Instrucción***: Las imágenes satelitales `.SAFE.zip` son archivos masivos (~1GB). Para evitar la saturación de memoria RAM, se descargan mediante *streaming* de bloques (chunks de 8MB).
- ***Tolerancia a Fallos (Retry Loop)***: Se ha programado un sistema de reintentos (`max_retries = 3`) que intercepta caídas del servidor remoto (como excepciones `Read timed out`) y retoma la conexión sin colapsar el programa principal.
- ***Validación de Integridad***: Antes de saltarse un archivo que ya existe en disco, el sistema lee la cabecera central del archivo (utilizando `zipfile.ZipFile(file).testzip()` optimizado). Si el usuario abortó la descarga previamente (ej. `Ctrl+C`) o la red se cortó abruptamente, el archivo corrupto lanzará una excepción `BadZipFile`. El orquestador detectará el daño, purgará el archivo roto y lo descargará desde cero.
- ***File References***:
    - [s3_streamer.py (Métodos `download_product_zip` y `_is_valid_zip`)](../SOFT_without_sen2cor/src/s2_process_cloud/download/s3_streamer.py)

[←Index](#index)

## 4 Estructura de Salida

- ***Instrucción***: La ingesta de datos aterriza ordenadamente en el disco duro local a través de un volumen de Docker enlazado, estructurando las imágenes de manera que los futuros motores de corrección atmosférica puedan leerlas sin ambigüedad.
- ***Ruta de Almacenamiento***: `./data/<ORBITA>/<FECHA>/crudo/<PRODUCTO.SAFE.zip>`
- ***File References***:
    - [main.py (Etapa 1)](../SOFT_without_sen2cor/src/s2_process_cloud/main.py)

[←Index](#index)
