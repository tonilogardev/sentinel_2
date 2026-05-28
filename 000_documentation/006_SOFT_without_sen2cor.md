# SOFT_without_sen2cor: Arquitectura Cloud-Native

Este documento refleja el estado de desarrollo actual del proyecto `SOFT_without_sen2cor`. 
> **Estado Actual**: Implementado y funcional únicamente el Orquestador y el flujo de descarga de datos crudos (`.zip` / `.SAFE`) desde CDSE.

## Index

1. [Orquestador Dockerizado](#1-orquestador-dockerizado)
2. [Motor de Red y Descarga OData](#2-motor-de-red-y-descarga-odata)
3. [Configuración y Utilidades](#3-configuración-y-utilidades)

---

## 1 Orquestador Dockerizado

- ***Instrucción***: Creación de un "cerebro" central agnóstico y aislado en un contenedor Docker (`python:3.10-slim`). Este servicio es el encargado de leer el pipeline, gestionar la red y, en futuras fases, invocar a los motores de corrección atmosférica. Se ha añadido un script de conveniencia para automatizar la limpieza de recursos residuales de Docker (prune) y lanzar el entorno limpiamente.
- ***File References***:
    - [docker-compose.yml](../SOFT_without_sen2cor/docker-compose.yml)
    - [Dockerfile del Orquestador](../SOFT_without_sen2cor/docker/orchestrator/Dockerfile)
    - [run_pipeline.sh](../SOFT_without_sen2cor/run_pipeline.sh)

[←Index](#index)

## 2 Motor de Red y Descarga OData

- ***Instrucción***: Se ha implementado un cliente robusto contra la API de Copernicus Data Space (CDSE). El orquestador es capaz de:
  1. Obtener y renovar tokens de seguridad OAuth2 (Keycloak).
  2. Consultar el catálogo vía OData filtrando por órbita, fecha temporal y polígono geográfico (WKT).
  3. Descartar versiones obsoletas deduplicando gránulos mediante la retención estricta de la *Baseline* más reciente.
  4. Descargar los productos estructurales originales (`.SAFE.zip`) de múltiples gigabytes por bloques (chunks).
  5. Soportar caídas y microcortes de red de Copernicus mediante un sistema automático de reintentos (`max_retries = 3`) ante excepciones `Read timed out`.
- ***File References***:
    - Lógica de red, OData y reintentos: [s3_streamer.py](../SOFT_without_sen2cor/src/s2_process_cloud/download/s3_streamer.py)
    - Bucle principal de ejecución: [main.py](../SOFT_without_sen2cor/src/s2_process_cloud/main.py)

[←Index](#index)

## 3 Configuración y Utilidades

- ***Instrucción***: Se han estandarizado los inputs migrando utilidades de consola avanzadas (`rich`) para ocultar la verbosidad de logs al usuario final. El sistema de logging guarda la traza rotativa en disco. La configuración se abstrae combinando un JSON estructurado de coordenadas y secretos inyectados dinámicamente mediante variables de entorno desde fuera del contenedor.
- ***File References***:
    - Archivo de credenciales inyectado por Docker: [.env](../SOFT_without_sen2cor/.env)
    - Parámetros de área, fechas y órbita: [pipeline.json](../SOFT_without_sen2cor/pipeline.json)
    - Componentes del framework: [config.py](../SOFT_without_sen2cor/src/s2_process_cloud/config.py), [logger.py](../SOFT_without_sen2cor/src/s2_process_cloud/utils/logger.py), [console_ui.py](../SOFT_without_sen2cor/src/s2_process_cloud/utils/console_ui.py)

[←Index](#index)
