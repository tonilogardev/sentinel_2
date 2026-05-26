# Generación de L2A Sin DEM (Corrección Atmosférica Base)

Este documento detalla el procedimiento validado, estandarizado y seguro para la generación de productos Sentinel-2 Nivel 2A (L2A) **sin** corrección de relieve topográfico (NO-DEM) en el entorno Windows nativo. 

> [!IMPORTANT]
> Esta configuración ha sido validada exhaustivamente frente al pipeline "Legacy" original de la ICGC (Linux/Docker). Genera una radiancia/reflectancia (BOA) matemáticamente idéntica, solucionando los problemas de cuelgues de memoria y corrupción de metadatos introducidos por la *Baseline 05.11*. Debe guardarse "como oro en paño" y aplicarse ininterrumpidamente en entornos de producción.

---

## 1. Archivos Clave del Proceso

El flujo de ejecución recae sobre el orquestador principal refactorizado, apoyado por módulos dedicados:

1. **`src/s2_process/main.py`**: El orquestador general (`process_segment()`). Gestiona el bucle de las etapas secuenciales.
2. **`src/s2_process/processing/sen2cor_wrapper.py`**: El lanzador seguro de subprocess para aislar Sen2Cor y capturar sus logs de Windows.
3. **`src/s2_process/utils/sen2cor_patch.py`**: Inyector pre/post procesamiento que falsea y revierte la Baseline 05.11 a 05.09 para engañar a los XSD rígidos del motor `L2A_Process.bat`.

---

## 2. Parámetros Críticos (El Secreto de la Estabilidad)

La clave del éxito para reproducir el L2A normal radica en la correcta invocación del *wrapper* dentro de `main.py` (ETAPA 3).

```python
success = sen2cor_wrapper.run_sen2cor(
    config.sen2cor_bin, 
    l1c_d, 
    gipp_path=None, # CRÍTICO: Debe ser None
    resolution=10, 
    variant="NO-DEM", # CRÍTICO: Etiqueta semántica y control de logs
    progress_callback=ui.update_subtask_progress if ui else None
)
```

### ¿Por qué `gipp_path=None`?
Sen2Cor es un motor muy sensible a las sobreescrituras de configuración. Al pasar `gipp_path=None`, forzamos al Wrapper de Python a invocar `L2A_Process.bat` **sin** el flag `--GIP_L2A`. 
Al no recibir GIPP externos, Sen2Cor utiliza automáticamente sus tablas de parámetros L2A incrustadas en su propio código fuente (las que trae la instalación por defecto). Esto garantiza que no intente cargar modelos de relieve ni algoritmos DEM (DEMCAT), reproduciendo fielmente el procesado atmosférico base.

---

## 3. Secuencia Lógica Completa (Etapa 3 del Pipeline)

Para que el proceso nunca falle, el orquestador ejecuta estos 4 pasos en orden estricto antes de intentar el mosaico:

1. **Localización de L1C**: Glob busca las carpetas nativas `.SAFE` recién descomprimidas de la Etapa 1.
2. **Parche Previo (L1C)**: Se ejecuta `sen2cor_patch.apply_patch_l1c(segment_dir)`. Esto entra a las carpetas L1C y altera el `MTD_MSIL1C.xml`, rebajando su versión para evitar el `Syntax Error` nativo de Sen2Cor 2.12 en Windows.
3. **Ejecución Aisalda de Sen2Cor**: Se llama a `run_sen2cor` gránulo a gránulo (loop iterativo). El wrapper redirige `STDOUT` a la consola UI pero aísla la memoria, evitando memory leaks en Python.
4. **Parche Posterior (L2A)**: Se ejecuta `sen2cor_patch.apply_patch_l2a(segment_dir)`. Esto escanea las nuevas carpetas L2A generadas por Sen2Cor y les devuelve su metadato legal "Baseline 05.11" para que librerías externas (como Rasterio, Snap o GDAL) no rechacen el producto en un futuro.

---

## 4. Preservación del Flujo Continuo

En la iteración final y modular del código:
* **No se borran las carpetas L1C originales** tras finalizar el NO-DEM. Estas mismas carpetas `.SAFE` (ya extraídas) servirán como input inmediato para la Etapa 4 (Sen2Cor DEM-CAT), ahorrando horas de re-extracción de zips y lecturas en disco.
* **Tolerancia a Fallos**: Si un gránulo específico falla (por nubes corruptas, etc.), el iterador lanza un `False`, pero Sen2Cor no crashea la memoria de Python, por lo que el log principal queda íntegro.

> **Ubicación del Código Principal**: 
> Puedes revisar la inyección exacta en `f:\Disc_F\Orto_S2_CAT\antonio\open_code_project\SOFT_new\src\s2_process\main.py` -> Busca el comentario `# ETAPA 3: Corrección Atmosférica (Sen2Cor) sin DEM`.
