# Generación de Nivel 2A con Corrección Topográfica (DEM-CAT)

Este documento describe la fase del pipeline encargada de aplicar el Modelo Digital de Elevaciones (DEM) de alta resolución de Cataluña (u otros modelos específicos) durante la corrección atmosférica de Sentinel-2 mediante Sen2Cor.

## 1. El concepto de Topographic Correction

Por defecto, Sen2Cor en su versión "plana" (Flat) no compensa las sombras generadas por el relieve montañoso (iluminación del terreno según el ángulo solar). 
Al activar la corrección topográfica, Sen2Cor utiliza un archivo DEM local para:
- Ajustar la reflectancia (*Bottom of Atmosphere*) en las laderas orientadas al sol o en sombra.
- Generar máscaras de relieve y sombras topográficas precisas.

## 2. Configuración en el Pipeline (GIPP)

Para forzar a Sen2Cor a utilizar un DEM, en lugar de alterar su instalación base, se utiliza un archivo GIPP (Ground Image Processing Parameters) inyectado dinámicamente.

- **Archivo GIPP Customizado:** `configs/gipp/L2A_GIPP_DEMCAT.xml`
- **Activación interna:** El XML define `<DEM_Terrain_Correction>TRUE</DEM_Terrain_Correction>` y apunta al subdirectorio donde reside la cartografía de elevaciones (`<DEM_Directory>DEM-CAT</DEM_Directory>`).

Esta configuración se enlaza en el archivo `pipeline.json`:
```json
"workspace": {
    "sen2cor": {
        "bin": "Sen2Cor-02.12.03-win64/L2A_Process.bat",
        "gippPath": "configs\\gipp\\L2A_GIPP_DEMCAT.xml"
    }
}
```

## 3. Ejecución del Procesado L2A (Script 02)

El procesamiento topográfico se abstrae a través del script `script_02_sen2cor_dem.py`. Este módulo lee el gránulo descargado y ejecuta Sen2Cor con parámetros específicos para diferenciar este procesado del clásico.

### Arquitectura de ejecución
1. **Comando interno:** El script llama al binario de Sen2Cor inyectando la flag `--GIP_L2A` para asegurar el uso del XML de terreno.
2. **Flag Variant:** El script añade un distintivo lógico (variante DEMCAT) para que las carpetas de salida se diferencien de las L2A normales.
3. **Renombrado Automático:** Una vez el motor `L2A_Process` termina, el script etiqueta el archivo resultante, garantizando que el sufijo `_DEMCAT.SAFE` aparezca en el nombre del gránulo procesado.
   *Ejemplo de salida:* `S2A_MSIL2A_20260501T104651_N9999_R051_T31TDG_20260526T130244_DEMCAT.SAFE`

## 4. Ensamblaje del Mosaico GDAL (Script 03)

El orquestador de GDAL (`script_03_mosaics_and_indices.py`) está programado para rastrear y organizar paralelamente las múltiples variantes de procesamiento. 

Al detectar la firma `_DEMCAT.SAFE` en los directorios de entrada, el script:
1. Extrae independientemente las bandas a 10m y 20m.
2. Construye un VRT exclusivo para los datos topográficos.
3. Exporta un archivo BigTIFF COG paralelo al estándar para permitir validaciones visuales sin sobreescribir los datos "planos".

**Archivos resultantes tras la etapa de mosaico:**
- `S2A_L2A_R051_20260501.btf` *(Procesado estándar, sin relieve)*
- `S2A_L2A_R051_20260501_DEMCAT.btf` *(Procesado topográfico, con relieve)*
- `S2A_SCL_R051_20260501_DEMCAT.tif` *(Máscara de clasificación adaptada a las sombras)*
- `S2A_NDVI_R051_20260501_DEMCAT.tif` *(Índice de Vegetación post-corrección de iluminación)*
