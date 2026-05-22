# Guía de Instalación y Ejecución desde Cero (SOFT_new)

## Index

1. [Prerrequisitos de Sistema](#1-prerrequisitos-de-sistema)
2. [Creación del Entorno Conda](#2-creación-del-entorno-conda)
3. [Configuración de Credenciales y Parámetros](#3-configuración-de-credenciales-y-parámetros)
4. [Validación Inicial (Test)](#4-validación-inicial-test)
5. [Ejecución Batch en Producción](#5-ejecución-batch-en-producción)
6. [Mantenimiento y Actualización](#6-mantenimiento-y-actualización)

---

## 1 Prerrequisitos de Sistema

- ***Instrucción***: Asegúrate de tener instalado Anaconda o Miniconda en tu sistema Windows (arquitectura nativa, sin Docker).
- ***Visuals***: Si no lo tienes, descárgalo desde la página oficial de [Miniconda](https://docs.anaconda.com/free/miniconda/miniconda-install/).
- ***Comprobación***: Abre tu terminal **Anaconda Prompt** y verifica la instalación escribiendo:
  ```powershell
  conda --version
  ```

[←Index](#index)

## 2 Creación del Entorno Conda

- ***Instrucción***: Instala todas las dependencias del proyecto de forma aislada y precompilada usando el archivo de entorno. Esto incluye GDAL, Numpy y las librerías gráficas para la consola (`rich`).
- ***Pasos***:
  1. Sitúate en la raíz del nuevo proyecto a través de tu terminal:
     ```powershell
     cd f:\Disc_F\Orto_S2_CAT\antonio\open_code_project\SOFT_new
     ```
  2. Crea el entorno virtual leyendo las recetas de Conda Forge:
     ```powershell
     conda env create -f environment.yml
     ```
  3. Activa el entorno recién creado:
     ```powershell
     conda activate soft_new_env
     ```
- ***File References***:
  - Lee dependencias precompiladas de [environment.yml](../SOFT_new/environment.yml)

[←Index](#index)

## 3 Configuración de Credenciales y Parámetros

- ***Instrucción***: Antes de ejecutar, asegúrate de que el software tenga credenciales válidas y las fechas correctas para descargar las imágenes.
- ***Pasos***:
  1. Abre el archivo de variables ocultas y verifica tu usuario/contraseña de Copernicus DataSpace:
     - Editar [.env](../SOFT_new/.env)
  2. Abre el archivo principal de configuración para ajustar las fechas del rango de procesamiento (`date_range_start`, `date_range_end`) y las órbitas (`orbits`):
     - Editar [pipeline.json](../SOFT_new/pipeline.json)
- ***File References***:
  - Variables de entorno: [.env](../SOFT_new/.env)
  - Configuración del pipeline: [pipeline.json](../SOFT_new/pipeline.json)

[←Index](#index)

## 4 Validación Inicial (Test)

- ***Instrucción***: Lanza el script de testeo interactivo para validar que todas las librerías están correctamente cargadas y arrancar el pipeline de prueba (seteará automáticamente el PYTHONPATH).
- ***Pasos***:
  1. Con el entorno `soft_new_env` activado, ejecuta:
     ```powershell
     python test_pipeline.py
     ```
  2. El sistema validará tu entorno y te pedirá confirmación (`S` o `N`) para arrancar la prueba con los parámetros indicados en tu JSON. Verás la nueva interfaz de consola elegante desplegarse.
- ***File References***:
  - Script verificador: [test_pipeline.py](../SOFT_new/test_pipeline.py)

[←Index](#index)

## 5 Ejecución Batch en Producción

- ***Instrucción***: Cuando el software esté desplegado, se ejecutará directamente el motor principal para un procesamiento desatendido y silencioso.
- ***Pasos***:
  1. Configura la ruta de importación de Python para que los módulos internos sean reconocidos, y luego lanza `main.py`:
     ```powershell
     set PYTHONPATH=src
     python src\s2_process\main.py --config pipeline.json
     ```
  2. Gracias al módulo `PipelineConsoleUI`, podrás ver el ETA de la corrección atmosférica de Sen2Cor en vivo y comprobar el flujo sin que la consola se inunde de logs intermedios.
  3. En caso de depuración, revisa los archivos físicos en disco.
- ***File References***:
  - Script orquestador principal: [main.py](../SOFT_new/src/s2_process/main.py)
  - Interfaz Gráfica: [console_ui.py](../SOFT_new/src/s2_process/utils/console_ui.py)
  - Carpeta de reportes: [output/logs/](../SOFT_new/output/logs/)

[←Index](#index)

## 6 Mantenimiento y Actualización

- ***Instrucción***: Si en un futuro se añaden dependencias nuevas al `environment.yml` (por ejemplo, actualizando `rich` o `gdal`), NO hace falta borrar el entorno. Se puede actualizar rápidamente en caliente.
- ***Pasos***:
  ```powershell
  conda deactivate
  conda env update -n soft_new_env -f environment.yml --prune
  conda activate soft_new_env
  ```
- ***File References***:
  - Tips Generales: [000_tips.md](../000_documentation/000_tips.md)

[←Index](#index)
