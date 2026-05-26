#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
SCRIPT AISLADO 01: SEN2COR NO-DEM (CORRECCIÓN ATMOSFÉRICA SIN RELIEVE)
=============================================================================

Este script encapsula de manera estanca la Etapa 3 del pipeline original 'SOFT'.
Su único propósito es tomar gránulos L1C (Top of Atmosphere) y procesarlos
uno por uno a través del motor Sen2Cor (ESA) para generar niveles L2A
(Bottom of Atmosphere), excluyendo expresamente el Modelo Digital de Elevaciones.

[PRERREQUISITOS]
1. Directorio de trabajo con estructura válida (ej. `K:\t\2026-05-01_R051`).
2. Existencia de gránulos L1C. El script soporta:
   - Carpetas `.SAFE` ya extraídas.
   - Archivos `.zip` originales de Copernicus (los extraerá automáticamente).
3. Motor Sen2Cor instalado y referenciado en `pipeline.json` (sen2cor_bin).

[PECULIARIDADES TÉCNICAS INYECTADAS]
- Parche Baseline 05.11: Se inyecta un pre-procesado (apply_patch_l1c) y post-procesado
  (apply_patch_l2a) para evitar el error de esquema (psd-14/15) en Windows.
- Parámetro gipp_path=None: Fuerza el uso del GIPP por defecto de Sen2Cor.
  Esto es VITAL para replicar el comportamiento radiométrico original de la
  cartografía legacy de la Generalitat.
- Variant "NO-DEM": Etiqueta los gránulos de salida para evitar colisiones con
  la futura pasada topográfica.

[OUTPUT]
Múltiples carpetas `.SAFE` de nivel L2A en el mismo directorio de trabajo.
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
    Función principal de orquestación del Script 01.
    Flujo de ejecución:
      1. Parseo de argumentos (--segment_dir y --config).
      2. Configuración del logger aislado.
      3. Verificación y extracción proactiva de archivos ZIP L1C si no hay SAFEs.
      4. Aplicación del parche de esquema ESA Baseline 05.11 (L1C).
      5. Invocación de `run_sen2cor` en bucle para cada gránulo L1C, forzando
         resolución 10m y parámetros GIPP genéricos.
      6. Aplicación del parche de esquema ESA Baseline 05.11 (L2A).
    """
    parser = argparse.ArgumentParser(description="Script Aislado 01: Sen2Cor NO-DEM (Baseline 05.11 compatible)")
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

    # Configurar logger aislado (escribirá en el directorio padre de segment_dir o en output/)
    setup_logger(os.path.dirname(segment_dir), "SCRIPT_01", "NODEM")
    logging.info(f"=== INICIANDO SCRIPT 01: SEN2COR NO-DEM ===")
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
        # Refrescar lista de carpetas
        l1c_dirs = glob.glob(os.path.join(segment_dir, "*L1C*.SAFE"))
        
    logging.info(f"Encontrados {len(l1c_dirs)} gránulos L1C. Aplicando parche Baseline 05.11...")
    
    # 1. APLICAR PARCHE PREVIO L1C
    # Imprescindible para evitar el crash de validación de esquemas PSD-14 y PSD-15 en Windows
    sen2cor_patch.apply_patch_l1c(segment_dir)
    
    # 2. EJECUTAR SEN2COR NO-DEM
    for l1c_d in l1c_dirs:
        logging.info(f"Procesando con Sen2Cor NO-DEM: {os.path.basename(l1c_d)}")
        
        # PARTICULARIDADES CLAVE QUE FUNCIONARON PARA REPLICAR `SOFT`:
        # - gipp_path = None -> Fuerza a usar el GIPP estándar de la ESA sin modelo digital.
        # - resolution = 10 -> Fuerzas a 10m.
        # - variant = "NO-DEM" -> Deja la nomenclatura en L2A sin apéndice.
        success = sen2cor_wrapper.run_sen2cor(
            config.sen2cor_bin, 
            l1c_d, 
            gipp_path=None, 
            resolution=10, 
            variant="NO-DEM",
            progress_callback=None
        )
        
        if not success:
            logging.error(f"Fallo crítico en Sen2Cor NO-DEM para {os.path.basename(l1c_d)}.")
            sys.exit(1)
            
    # 3. APLICAR PARCHE POSTERIOR L2A
    logging.info("Aplicando parche Baseline 05.11 a los productos L2A generados...")
    sen2cor_patch.apply_patch_l2a(segment_dir)
    
    logging.info("=== SCRIPT 01 COMPLETADO CON ÉXITO ===")

if __name__ == "__main__":
    main()
