# Objetivos: Pipeline S2-PROCESS Cloud-Native (Sin Sen2Cor)

## Index

1. [Desacoplar el Motor Atmosférico](#1-desacoplar-el-motor-atmosférico)
2. [Arquitectura Cloud-Native (Docker/WSL2)](#2-arquitectura-cloud-native-dockerwsl2)
3. [Estandarización de Datos a COG](#3-estandarización-de-datos-a-cog)
4. [Benchmarking Estadístico (RMSE)](#4-benchmarking-estadístico-rmse)

---

## 1 Desacoplar el Motor Atmosférico

- ***Instrucción***: Sustituye la dependencia de Sen2Cor por procesadores de código abierto (FORCE, SIAC, ACOLITE).
- ***Visuals***:
    ![Arquitectura de Motores](./img/engines_architecture.png)
- ***File References***:
    - Revisa el script orquestador en [main.py](../SOFT_without_sen2cor/src/s2_process_cloud/main.py).

[←Index](#index)

## 2 Arquitectura Cloud-Native (Docker/WSL2)

- ***Instrucción***: Aísla el entorno de ejecución utilizando contenedores bajo WSL2 (Linux) para maximizar el I/O y elimina las rutas absolutas de Windows montando volúmenes relativos (`./data` y `./output`).
- ***Visuals***:
    ![Mapeo de Volúmenes](./img/docker_volumes.png)
- ***File References***:
    - Edita [docker-compose.yml](../SOFT_without_sen2cor/docker-compose.yml).
    - Configura credenciales en [.env.example](../SOFT_without_sen2cor/.env.example).

[←Index](#index)

## 3 Estandarización de Datos a COG

- ***Instrucción***: Abandona los formatos pesados `.SAFE` o JPEG2000. Utiliza descargas directas S3 y convierte todos los raster de entrada (L1C y MDT) y de salida (L2A) al estándar Cloud Optimized GeoTIFF (.btf).
- ***File References***:
    - Configura rutas relativas en [pipeline.json](../SOFT_without_sen2cor/pipeline.json).
    - Revisa el módulo de descarga optimizada [s3_streamer.py](../SOFT_without_sen2cor/src/s2_process_cloud/download/s3_streamer.py).

[←Index](#index)

## 4 Benchmarking Estadístico (RMSE)

- ***Instrucción***: Automatiza la validación de los tres motores. Compara los resultados L2A generados por FORCE, SIAC y ACOLITE contra una imagen de control histórica de Sen2Cor, calculando el error cuadrático medio para decidir el ganador final.
- ***File References***:
    - Ejecuta el test de validación con [validate.py](../SOFT_without_sen2cor/scripts/validate.py).

[←Index](#index)
