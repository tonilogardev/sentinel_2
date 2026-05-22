# Pipeline Sentinel-2 Modernizado (SOFT_new)

## Index

1. [Estructura Limpia del Directorio de Salida](#1-estructura-limpia-del-directorio-de-salida)
2. [Descripción Cronológica de Salidas por Etapa](#2-descripción-cronológica-de-salidas-por-etapa)
3. [Instrucciones de Ejecución Local en Windows](#3-instrucciones-de-ejecución-local-en-windows)
4. [Pasos Siguientes](#4-pasos-siguientes)

---

## 1 Estructura Limpia del Directorio de Salida

- ***Instrucción***: Todos los archivos generados y el motor de procesamiento (Sen2Cor) residen estrictamente bajo el directorio de trabajo limpio [SOFT_new/](../SOFT_new/). Bajo ningún concepto se utilizarán las rutas del software clásico [SOFT/](../SOFT/).
- ***Árbol de Directorios Generados***:
  El árbol de directorios de salida está estructurado y pre-inicializado de la siguiente manera:
  ```text
  SOFT_new/
  ├── Sen2Cor-02.12.03-win64/ <-- Procesador atmosférico y topográfico (Motor local)
  └── output/
      ├── QuickLooks/   <-- Vistas rápidas finales de alta calidad (RGB y RGBI)
      ├── segments/     <-- Directorios por segmento con mosaicos, capas SCL y NDVI
      └── logs/         <-- Archivos de log dedicados creados por cada sesión
  ```
- ***File References***:
  - Directorio principal de salidas: [output/](../SOFT_new/output/)
  - Destino de QuickLooks de Alta Calidad: [QuickLooks/](../SOFT_new/output/QuickLooks/)
  - Destino de Mosaicos y Segmentos: [segments/](../SOFT_new/output/segments/)
  - Directorio de Logs del Sistema: [logs/](../SOFT_new/output/logs/)

[←Index](#index)

## 2 Descripción Cronológica de Salidas por Etapa

- ***Instrucción***: Sigue el flujo batch secuencial diario y órbita por órbita para revisar las salidas que se van almacenando progresivamente.
- ***Flujo Cronológico de Salidas***:
  1. **Etapa 1: Descarga**: Guarda los gránulos comprimidos de Copernicus en [segments/[Fecha]_[Orbita]/ZIP/](../SOFT_new/output/segments/).
  2. **Etapa 2: Máscaras e Imagen L1C**: Genera las máscaras vectoriales y raster en [segments/[Fecha]_[Orbita]/MASK/](../SOFT_new/output/segments/) y el mosaico opcional calibrado `S2[A/B]_L1C_[Orbita]_[FechaCompacta].btf` en la raíz de su carpeta de segmento.
  3. **Etapa 4: Mosaico L2A y SCL (sin DEM)**: Ejecuta Sen2Cor localmente y genera el mosaico calibrado de reflectancia de 10 bandas `S2[A/B]_L2A_[Orbita]_[FechaCompacta].btf` y la clasificación de suelo remuestreada a 10m `S2[A/B]_SCL_[Orbita]_[FechaCompacta].tif` dentro de su segmento.
  4. **Etapa 5: QuickLooks**: Genera en el directorio centralizado [QuickLooks/](../SOFT_new/output/QuickLooks/) las vistas rápidas finales:
     - `S2_RGB_8b_[Fecha]_[Orbita].tif` (RGB de 8 bits comprimido con JPEG 75).
     - `S2_RGBI_16b_[Fecha]_[Orbita].btf` (RGBI de 16 bits comprimido con LZW).
  5. **Etapa 7: Mosaico L2A DEMCAT y NDVI**: Genera el mosaico corregido con relieve `S2[A/B]_L2A_[Orbita]_[FechaCompacta]_DEMCAT.btf` y el índice de vegetación re-escalado a Byte de la ICGC `S2[A/B]_NDVI_[Orbita]_[FechaCompacta].tif` en la carpeta de segmento.
- ***File References***:
  - Módulo principal orquestador: [main.py](../SOFT_new/src/s2_process/main.py)
  - Módulo de QuickLooks: [quicklook_generator.py](../SOFT_new/src/s2_process/processing/quicklook_generator.py)
  - Configuración del pipeline: [pipeline.json](../SOFT_new/pipeline.json)

[←Index](#index)

## 3 Instrucciones de Ejecución Local en Windows

- ***Instrucción***: Ejecuta los comandos nativos en la consola Conda de Windows sin usar contenedores Docker.
- ***Pasos de Ejecución***:
  1. Abre tu terminal de **Anaconda Prompt** o **Miniconda**.
  2. Activa tu entorno de ejecución de Conda preferido.
  3. Desplázate al directorio raíz de la nueva aplicación:
     ```powershell
     cd f:\Disc_F\Orto_S2_CAT\antonio\open_code_project\SOFT_new
     ```
  4. Lanza el script de testeo interactivo para validar las librerías del entorno e iniciar una ejecución:
     ```powershell
     python test_pipeline.py
     ```
- ***File References***:
  - Script de testeo y ayuda interactiva: [test_pipeline.py](../SOFT_new/test_pipeline.py)
  - Archivo de variables de entorno con credenciales: [.env](../SOFT_new/.env)

[←Index](#index)

## 4 Pasos Siguientes

- Consulta la guía de políticas y requerimientos del negocio en [politica_negocio_SOFT.md](./politica_negocio_SOFT.md).
