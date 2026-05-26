#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
SCRIPT AISLADO 03: ENSAMBLAJE DE MOSAICOS Y PRODUCTOS DERIVADOS (L2A, SCL, NDVI)
=============================================================================

Este script encapsula las Etapas 4 y 5 del pipeline original 'SOFT'.
Su propósito es leer los gránulos `.SAFE` generados por Sen2Cor y construir 
los grandes mosaicos consolidados usando GDAL, así como extraer las máscaras
e índices vegetativos.

[PRERREQUISITOS]
1. Directorio de trabajo con estructura válida (ej. `K:\t\2026-05-01_R051`).
2. Gránulos L2A (`.SAFE`) ya generados por Sen2Cor (mediante el Script 01 o 02).
3. Entorno Conda con librerías GDAL nativas habilitadas.

[PECULIARIDADES TÉCNICAS INYECTADAS]
- Sin compresión LZW en mosaico L2A 10b: Debido al límite estructural de 4.29 GB
  en los TIFF clásicos (32-bit offset), GDAL abortará si se comprimen 10 bandas de 
  alta entropía. Este script asume que la capa GDAL ha deshabilitado LZW/PREDICTOR
  en el módulo `l2a_10b_mosaic.py`.
- Detección Dinámica de Órbita: Parsea el nombre del directorio para deducir 
  la fecha, la órbita y por consiguiente los límites UTM (bounding box) desde `pipeline.json`.
- Integración Multi-Variable: Calcula independientemente el Mosaico 10-bandas,
  la máscara Scene Classification (SCL) a 10m y el Índice de Vegetación (NDVI).

[OUTPUT]
- `S2A_L2A_[RXXX]_[FECHA].btf` (o con sufijo DEMCAT)
- `S2A_SCL_[RXXX]_[FECHA].tif` (o con sufijo DEMCAT)
- `S2A_NDVI_[RXXX]_[FECHA].tif` (o con sufijo DEMCAT)
- Carpetas de Quicklooks RGB/RGBI.
"""

import sys
import os
import glob
import logging
import argparse
from datetime import datetime

# Añadir la ruta raíz del paquete src al path para resolver importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s2_process.config import PipelineConfig
from s2_process.utils.logger import setup_logger
from s2_process.processing import l2a_10b_mosaic
from s2_process.processing import scl_extractor
from s2_process.processing import ndvi_calculator
from s2_process.processing import quicklook_generator

def main():
    """
    Función principal de orquestación del Script 03.
    Flujo de ejecución:
      1. Parseo de argumentos (--segment_dir y --config).
      2. Configuración del logger aislado.
      3. Deducción de parámetros (órbita, fecha, bounding box UTM) a partir
         del nombre del directorio.
      4. Verificación de existencia de gránulos L2A procesados en modo NO-DEM.
      5. Invocación de `build_l2a_10band_mosaic` para fusionar las 10 bandas.
      6. Invocación de `extract_scl` para re-muestrear y fusionar máscara SCL.
      7. Invocación de `calculate_ndvi`.
      8. Generación de QuickLooks para validación visual.
    """
    parser = argparse.ArgumentParser(description="Script Aislado 03: Ensamblaje de Mosaicos e Índices")
    parser.add_argument(
        "--segment_dir",
        type=str,
        required=True,
        help="Directorio de trabajo que contiene las carpetas L2A .SAFE procesadas (ej: K:\\t\\2026-05-01_R051)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pipeline.json"),
        help="Ruta opcional al pipeline.json"
    )
    args = parser.parse_args()

    segment_dir = args.segment_dir
    if not os.path.isdir(segment_dir):
        print(f"ERROR: El directorio de segmento no existe: {segment_dir}")
        sys.exit(1)

    setup_logger(os.path.dirname(segment_dir), "SCRIPT_03", "MOSAICS")
    logging.info("=== INICIANDO SCRIPT 03: ENSAMBLAJE DE MOSAICOS Y PRODUCTOS ===")

    config = PipelineConfig(args.config)
    
    # Extraer variables del nombre de la carpeta (ej: 2026-05-01_R051)
    folder_name = os.path.basename(os.path.normpath(segment_dir))
    parts = folder_name.split('_')
    if len(parts) >= 2:
        date_str = parts[0]
        orbit = parts[1]
    else:
        logging.error("No se pudo deducir fecha y órbita del nombre de la carpeta.")
        sys.exit(1)

    compact_date = date_str.replace("-", "")
    
    limits_utm = config.limits_utm.get(orbit)
    if not limits_utm:
        logging.error(f"Límites UTM no configurados para la órbita: {orbit}")
        sys.exit(1)
        
    limits_gdal = [limits_utm[0], limits_utm[3], limits_utm[1], limits_utm[2]]
    utm_zone = config.per_orbit_zone_utm.get(orbit, "T31")

    # Mosaico L2A NO-DEM (El clásico)
    nom_escena_l2a = f"S2A_L2A_{orbit}_{compact_date}"
    nom_escena_scl = f"S2A_SCL_{orbit}_{compact_date}"
    
    # Separar carpetas por variante
    safe_dirs_all = glob.glob(os.path.join(segment_dir, "S2*_MSIL2A_*.SAFE"))
    safe_dirs_demcat = [d for d in safe_dirs_all if d.endswith("_DEMCAT.SAFE")]
    safe_dirs_nodem = [d for d in safe_dirs_all if not d.endswith("_DEMCAT.SAFE")]
    
    if safe_dirs_nodem:
        logging.info("Iniciando Mosaico L2A NO-DEM...")
        try:
            mosaic_10b_path = os.path.join(segment_dir, f"{nom_escena_l2a}.btf")
            l2a_10b_mosaic.build_l2a_10band_mosaic(
                segment_dir, nom_escena_l2a, limits_gdal, utm_zone, config.allowed_inner_zeros_l2a, is_demcat=False
            )
            logging.info("Mosaico L2A NO-DEM finalizado con éxito.")
            
            # Generar SCL y NDVI basados en el NO-DEM
            logging.info("Generando máscara SCL y NDVI (NO-DEM)...")
            scl_path = os.path.join(segment_dir, f"{nom_escena_scl}.tif")
            scl_extractor.build_l2a_scl_mosaic(segment_dir, nom_escena_scl, limits_gdal, utm_zone, is_demcat=False)
            
            ndvi_path = os.path.join(segment_dir, f"S2A_NDVI_{orbit}_{compact_date}.tif")
            ndvi_calculator.calculate_l2a_ndvi(mosaic_10b_path, ndvi_path)
            
            # Generar QuickLooks
            logging.info("Generando QuickLooks...")
            os.makedirs(os.path.join(segment_dir, "QuickLook"), exist_ok=True)
            rgb_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a}_RGB_8b.tif")
            rgbi_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a}_RGBI_16b.tif")
            quicklook_generator.generate_quicklook_8b(mosaic_10b_path, rgb_path)
            quicklook_generator.generate_quicklook_16b(mosaic_10b_path, rgbi_path)
            
        except Exception as e:
            logging.error(f"Error ensamblando mosaico NO-DEM: {e}")
    else:
        logging.info("Omitiendo Mosaico NO-DEM (no se hallaron carpetas .SAFE normales).")

    # Mosaico L2A DEMCAT
    if safe_dirs_demcat:
        nom_escena_l2a_dem = f"{nom_escena_l2a}_DEMCAT"
        nom_escena_scl_dem = f"{nom_escena_scl}_DEMCAT"
        logging.info("Iniciando Mosaico L2A DEMCAT...")
        try:
            mosaic_10b_dem_path = os.path.join(segment_dir, f"{nom_escena_l2a_dem}.btf")
            l2a_10b_mosaic.build_l2a_10band_mosaic(
                segment_dir, nom_escena_l2a_dem, limits_gdal, utm_zone, config.allowed_inner_zeros_l2a, is_demcat=True
            )
            logging.info("Mosaico L2A DEMCAT finalizado con éxito.")
            
            logging.info("Generando máscara SCL y NDVI (DEMCAT)...")
            scl_dem_path = os.path.join(segment_dir, f"{nom_escena_scl_dem}.tif")
            scl_extractor.build_l2a_scl_mosaic(segment_dir, nom_escena_scl_dem, limits_gdal, utm_zone, is_demcat=True)
            
            ndvi_dem_path = os.path.join(segment_dir, f"S2A_NDVI_{orbit}_{compact_date}_DEMCAT.tif")
            ndvi_calculator.calculate_l2a_ndvi(mosaic_10b_dem_path, ndvi_dem_path)
            
            # Generar QuickLooks
            logging.info("Generando QuickLooks DEMCAT...")
            os.makedirs(os.path.join(segment_dir, "QuickLook"), exist_ok=True)
            rgb_dem_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a_dem}_RGB_8b.tif")
            rgbi_dem_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a_dem}_RGBI_16b.tif")
            quicklook_generator.generate_quicklook_8b(mosaic_10b_dem_path, rgb_dem_path)
            quicklook_generator.generate_quicklook_16b(mosaic_10b_dem_path, rgbi_dem_path)
            
        except Exception as e:
            logging.error(f"Error ensamblando mosaico DEMCAT: {e}")
    else:
        logging.info("Omitiendo Mosaico DEMCAT (no se hallaron carpetas _DEMCAT.SAFE).")
        
    logging.info("=== SCRIPT 03 COMPLETADO CON ÉXITO ===")

if __name__ == "__main__":
    main()
