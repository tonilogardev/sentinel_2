#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
SCRIPT AISLADO 02: SEN2COR DEM-CAT (CORRECCIÓN ATMOSFÉRICA CON RELIEVE)
=============================================================================

Este script encapsula la Etapa 6 del pipeline original 'SOFT'.
Su propósito es reprocesar los gránulos L1C (Top of Atmosphere) a través 
del motor Sen2Cor (ESA) para generar un segundo juego de niveles L2A, 
pero esta vez inyectando un Modelo Digital de Elevaciones (DEM) de 
alta resolución para aplicar la corrección de iluminación topográfica.

[PRERREQUISITOS]
1. Directorio de trabajo con gránulos L1C. El script extraerá archivos `.zip`
   si las carpetas `.SAFE` no existen.
2. Motor Sen2Cor instalado y referenciado en `pipeline.json` (sen2cor_bin).
3. Configuración del GIPP customizado con las rutas relativas al DEM apuntando
   al archivo `L2A_GIPP_DEMCAT.xml` (referenciado en `pipeline.json` como `l2a_gipp_demcat`).

[PECULIARIDADES TÉCNICAS INYECTADAS]
- Parche Baseline 05.11: Pre y post-procesado para evitar el error de 
  esquema PSD-14/15 de la ESA en sistemas Windows.
- Parámetro gipp_path: SE FUERZA a cargar el XML de configuración `L2A_GIPP_DEMCAT.xml`
  que contiene la activación estricta del DEM (`<DEM_Directory>`).
- Variant "DEMCAT": Esta variante añadirá un sufijo a los gránulos L2A generados
  (ej. `S2A_MSIL2A_..._DEMCAT.SAFE`) para no sobrescribir la pasada NO-DEM.

[OUTPUT]
Múltiples carpetas `.SAFE` de nivel L2A en el mismo directorio de trabajo,
identificables por el sufijo añadido `_DEMCAT`.
"""

import sys
import os
import glob
import logging
import argparse
import zipfile

# Añadir la ruta raíz del paquete src al path para resolver importaciones
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s2_process.config import PipelineConfig
from s2_process.utils.logger import setup_logger
from s2_process.processing import sen2cor_wrapper
from s2_process.utils import sen2cor_patch

def main():
    """
    Función principal de orquestación del Script 02.
    Flujo de ejecución:
      1. Parseo de argumentos (--segment_dir y --config).
      2. Configuración del logger aislado.
      3. Extracción proactiva de archivos ZIP L1C si no hay SAFEs.
      4. Aplicación del parche de esquema ESA Baseline 05.11 (L1C).
      5. Invocación de `run_sen2cor` para cada gránulo L1C inyectando 
         la ruta del GIPP customizado y la variante "DEMCAT".
      6. Aplicación del parche de esquema ESA Baseline 05.11 (L2A).
    """
    parser = argparse.ArgumentParser(description="Script Aislado 02: Sen2Cor DEMCAT (Con Relieve)")
    parser.add_argument(
        "--segment_dir",
        type=str,
        required=True,
        help="Directorio de trabajo que contiene las carpetas L1C .SAFE (ej: K:\\t\\2026-05-01_R051)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pipeline.json"),
        help="Ruta opcional al pipeline.json (por defecto busca en el raíz del proyecto)"
    )
    args = parser.parse_args()

    segment_dir = args.segment_dir
    if not os.path.isdir(segment_dir):
        print(f"ERROR: El directorio de segmento no existe: {segment_dir}")
        sys.exit(1)

    setup_logger(os.path.dirname(segment_dir), "SCRIPT_02", "DEMCAT")
    logging.info(f"=== INICIANDO SCRIPT 02: SEN2COR CON RELIEVE (DEMCAT) ===")
    logging.info(f"Directorio de segmento: {segment_dir}")

    config = PipelineConfig(args.config)
    
    # Buscar carpetas L1C
    l1c_dirs = glob.glob(os.path.join(segment_dir, "*L1C*.SAFE"))
    if not l1c_dirs:
        logging.info("No se encontraron carpetas L1C .SAFE. Buscando archivos .zip para extraer...")
        l1c_zips = glob.glob(os.path.join(segment_dir, "*L1C*.zip"))
        if not l1c_zips:
            logging.error("No se encontraron ni carpetas .SAFE ni archivos .zip de L1C para procesar.")
            sys.exit(1)
        for z_path in l1c_zips:
            logging.info(f"Descomprimiendo: {os.path.basename(z_path)}...")
            try:
                with zipfile.ZipFile(z_path, 'r') as zip_ref:
                    zip_ref.extractall(segment_dir)
            except Exception as e:
                logging.error(f"Error al descomprimir {z_path}: {e}")
                sys.exit(1)
        # Refrescar lista
        l1c_dirs = glob.glob(os.path.join(segment_dir, "*L1C*.SAFE"))
        
    logging.info(f"Encontrados {len(l1c_dirs)} gránulos L1C. Aplicando parche Baseline 05.11...")
    sen2cor_patch.apply_patch_l1c(segment_dir)
    
    for l1c_d in l1c_dirs:
        logging.info(f"Procesando con Sen2Cor DEMCAT: {os.path.basename(l1c_d)}")
        
        # PARTICULARIDADES DE LA CORRECCIÓN DEM:
        # Se inyecta expresamente el config.l2a_gipp_demcat y la variante "DEMCAT"
        success = sen2cor_wrapper.run_sen2cor(
            config.sen2cor_bin, 
            l1c_d, 
            gipp_path=config.l2a_gipp_demcat, 
            resolution=10, 
            variant="DEMCAT",
            progress_callback=None
        )
        
        if not success:
            logging.error(f"Fallo crítico en Sen2Cor DEMCAT para {os.path.basename(l1c_d)}.")
            sys.exit(1)
            
    logging.info("Aplicando parche Baseline 05.11 a los productos L2A DEMCAT generados...")
    sen2cor_patch.apply_patch_l2a(segment_dir)
    
    logging.info("=== SCRIPT 02 COMPLETADO CON ÉXITO ===")

if __name__ == "__main__":
    main()
