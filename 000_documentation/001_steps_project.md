# Guía de Instalación y Etapas del Pipeline S2-PROCESS (SOFT_new)

## Index

1. [Prerrequisitos de Sistema](#1-prerrequisitos-de-sistema)
2. [Creación del Entorno Conda](#2-creación-del-entorno-conda)
3. [Configuración Inicial](#3-configuración-inicial)
4. [Las 5 Etapas del Pipeline](#4-las-5-etapas-del-pipeline)
5. [Ejecución en Producción](#5-ejecución-en-producción)

---

## 1 Prerrequisitos de Sistema

- ***Instrucción***: Instala Miniconda en tu sistema Windows.
- ***Visuals***: Descarga [Miniconda Oficial](https://docs.anaconda.com/free/miniconda/miniconda-install/).
- ***Comprobación***: Abre la terminal Anaconda Prompt y verifica:
  ```powershell
  conda --version
  ```

[←Index](#index)

## 2 Creación del Entorno Conda

- ***Instrucción***: Crea el entorno aislado con todas las dependencias necesarias.
- ***Pasos***:
  1. Sitúate en la raíz del proyecto `SOFT_new`:
     ```powershell
     cd ../SOFT_new
     ```
  2. Crea el entorno virtual desde la receta precompilada:
     ```powershell
     conda env create -f environment.yml
     ```
  3. Activa el entorno (`sentinel2`):
     ```powershell
     conda activate sentinel2
     ```
- ***File References***:
  - Archivo de entorno: [environment.yml](../SOFT_new/environment.yml)

[←Index](#index)

## 3 Configuración Inicial

- ***Instrucción***: Define el periodo temporal, las órbitas y tus credenciales de descarga antes de ejecutar la aplicación.
- ***Pasos***:
  1. Edita el archivo de entorno y rellena tu usuario/contraseña de Copernicus.
  2. Edita la configuración JSON para indicar las fechas de inicio/fin y órbitas a procesar.
- ***File References***:
  - Configura variables secretas en [.env](../SOFT_new/.env)
  - Configura el rango temporal en [pipeline.json](../SOFT_new/pipeline.json)

[←Index](#index)

## 4 Las 5 Etapas del Pipeline

- ***Instrucción***: Comprende el flujo interno automático del orquestador una vez lo pones en marcha. El sistema sigue estrictamente este ciclo cerrado por cada segmento.

### ¿Qué es Sen2Cor?
Sen2Cor es un software científico de la Agencia Espacial Europea (ESA) integrado en nuestra aplicación (`Sen2Cor-02.12.03-win64`). Su misión principal es la **Corrección Atmosférica**.
Los satélites toman las fotos desde el espacio (Nivel L1C), y por tanto la imagen está "sucia" con neblina, aerosoles, partículas y vapor de agua. Sen2Cor procesa píxel a píxel, elimina todos estos gases y nos devuelve la imagen "limpia" (Nivel L2A) como si la hubiéramos tomado a ras de suelo (Bottom-Of-Atmosphere, BOA). Además, detecta automáticamente nubes, sombras y cuerpos de agua, emitiendo una máscara matemática llamada SCL (Scene Classification Layer).

### 4.1 Etapa 1: Rastreo y Descarga (L1C)
- El cliente conecta vía OData con Copernicus DataSpace.
- Identifica los gránulos de Nivel 1C (L1C) que intersectan la órbita/fecha, filtra solo el *Baseline* más reciente, lo descarga en paquetes `.zip` y verifica su integridad estructural mediante firmas MD5.

### 4.2 Etapa 2: Mosaico Crudo y Máscaras
- **Descompresión**: Los ZIPs se extraen en la carpeta de trabajo, dejando al descubierto los paquetes originales de la ESA (Carpetas L1C terminadas en `.SAFE`).
- **Mosaico**: Lee las bandas L1C, les aplica su factor de calibración radiométrica y genera un mosaico `.btf` continuo recortado a los límites de la zona mediante GDAL.
- **Máscara**: Extrae la banda B04, aplica dilatación/erosión por OpenCV y genera una máscara vectorial (`_mask.gpkg`) de limpieza geométrica.

### 4.3 Etapa 3: Motor Atmosférico Plano (NO-DEM)
- Llama al ejecutable binario de **Sen2Cor** (`L2A_Process.bat`) pasándole como argumento directamente la ruta a la carpeta cruda `.SAFE` recién extraída. 
- **Parámetros**: No se le inyecta ningún Modelo Digital de Elevaciones. Por tanto, Sen2Cor asume que todo el terreno es llano (Corrección Plana).
- **Salida**: Tras un par de horas de cálculo pesado, Sen2Cor escupe una nueva carpeta al lado llamada `S2A_MSIL2A_[...].SAFE`. 
- **Aislamiento**: Nuestro código de Python la detecta inmediatamente, le repara los metadatos XML, y le inyecta la etiqueta `_NODEM.SAFE` al nombre de la carpeta para blindarla de cara al futuro.

### 4.4 Etapa 4: Motor Atmosférico Topográfico (DEMCAT)
- **Segunda Invocación**: Vuelve a llamar a `L2A_Process.bat` de nuevo sobre la **misma** carpeta `.SAFE` inicial del satélite (la cruda L1C).
- **Parámetros**: Esta vez se le pasa un comando especial de inyección: `--GIP_L2A configs\gipp\L2A_GIPP_DEMCAT.xml`. Este archivo instruye a Sen2Cor a conectarse y descargar nuestro Modelo Digital del Terreno de Cataluña (DEMCAT). Ahora sí corregirá las sombras proyectadas por las montañas según el ángulo exacto del sol.
- **Salida y Aislamiento**: Sen2Cor vuelve a cocinar una nueva imagen, escupiendo otra carpeta `S2A_MSIL2A_[...].SAFE`. Nuestro código la detecta y la aísla rebautizándola con la etiqueta final `_DEMCAT.SAFE`.
- ***File References***:
  - Archivo GIPP inyectado: [L2A_GIPP_DEMCAT.xml](../SOFT_new/configs/gipp/L2A_GIPP_DEMCAT.xml)

### 4.5 Etapa 5: Mosaicos Finales y Productos Derivados
- **Herramienta**: Todo el trabajo de fusión se realiza internamente a través de librerías nativas de **GDAL** (Geospatial Data Abstraction Library) mediante Python, utilizando `gdal.BuildVRT` para alinear los gránulos virtualmente y `gdal.Translate` para unirlos y comprimirlos físicamente en formato BigTIFF (`.btf`).
- **L2A Normales**: El código rastrea y agrupa solo las carpetas aisladas como `_NODEM.SAFE` y ensambla el mosaico definitivo de 10 bandas.
- **L2A DEMCAT**: El código busca de forma independiente las carpetas `_DEMCAT.SAFE` y ensambla el mosaico topográfico paralelo.
- **SCL y NDVI**: GDAL extrae la capa de nubes (SCL) de Sen2Cor (que originalmente está a 20 metros), la remuestrea a 10 metros mediante un algoritmo estricto de "vecino más próximo" (para no corromper los códigos numéricos de clasificación), y calcula los índices NDVI para ambas variantes. Finalmente genera las miniaturas RGB (QuickLooks).

[←Index](#index)

## 5 Ejecución en Producción

- ***Instrucción***: Dispara el procesamiento general del pipeline desatendido.
- ***Pasos***:
  1. Con tu entorno activado, usa el archivo batch rápido o ejecuta directamente en consola:
     ```powershell
     python src\s2_process\main.py
     ```
  2. *(Nota: El propio código de Python se encarga de inyectar automáticamente la ruta de trabajo, por lo que no es necesario indicar `set PYTHONPATH` externamente).*
- ***File References***:
  - Atajo rápido: [run_pipeline.bat](../SOFT_new/run_pipeline.bat)
  - Orquestador principal: [main.py](../SOFT_new/src/s2_process/main.py)

[←Index](#index)
