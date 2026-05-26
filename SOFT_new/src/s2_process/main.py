# -*- coding: utf-8 -*-
"""
Orquestador secuencial principal del pipeline S2-PROCESS (SOFT).
Implementa un bucle batch por rango de fechas descargando imágenes L1C completas,
aplicando máscaras, Sen2Cor (NO-DEM y DEM-CAT), mosaicos L1C y L2A,
capas SCL, QuickLooks y NDVI, sobrescribiendo de forma segura.
"""

import os
import sys
import glob
import shutil
import zipfile
import logging
import argparse
from datetime import datetime, timedelta

# Asegurar que el directorio 'src' esté en el PYTHONPATH para evitar ModuleNotFoundError
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s2_process.config import PipelineConfig
from s2_process.utils.logger import setup_logger
from s2_process.download.dataspace_client import CopernicusDataspaceClient
from s2_process.processing import mask_generator
from s2_process.processing import cog_builder
from s2_process.processing import sen2cor_wrapper
from s2_process.processing import l2a_10b_mosaic
from s2_process.processing import scl_extractor
from s2_process.processing import ndvi_calculator
from s2_process.processing import quicklook_generator
from s2_process.utils import sen2cor_patch
from s2_process.utils.console_ui import PipelineConsoleUI

def parse_args():
    parser = argparse.ArgumentParser(description="SOFT Sentinel-2 Process Pipeline Batch Orchestrator")
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "pipeline.json"),
        help="Ruta al archivo pipeline.json de configuración"
    )
    return parser.parse_args()

def get_date_list(start_date_str, end_date_str):
    """Genera una lista de cadenas YYYY-MM-DD entre start y end inclusive."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    date_list = []
    curr = start
    while curr <= end:
        date_list.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)
    return date_list

def clean_safe_directories(directory, prefix=""):
    """Busca y elimina carpetas .SAFE en un directorio, opcionalmente filtrando por prefijo (ej. L1C)."""
    search_pattern = f"*{prefix}*.SAFE" if prefix else "*.SAFE"
    safe_dirs = glob.glob(os.path.join(directory, search_pattern))
    for s_dir in safe_dirs:
        logging.info(f"Limpiando directorio temporal .SAFE: {s_dir}")
        shutil.rmtree(s_dir, ignore_errors=True)

def compress_safe_to_zip(directory, prefix="", suffix=""):
    """Busca carpetas .SAFE, las empaqueta en .zip y borra la carpeta original para replicar el output legacy."""
    search_pattern = f"*{prefix}*.SAFE" if prefix else "*.SAFE"
    safe_dirs = glob.glob(os.path.join(directory, search_pattern))
    for s_dir in safe_dirs:
        # Extraer el nombre base sin la extensión .SAFE
        base_name = os.path.basename(s_dir)
        if base_name.endswith(".SAFE"):
            base_name = base_name[:-5]
        
        zip_filename = f"{base_name}{suffix}"
        zip_path = os.path.join(directory, zip_filename)
        
        logging.info(f"Empaquetando resultado a: {zip_path}.zip ...")
        shutil.make_archive(zip_path, 'zip', s_dir)
        logging.info(f"Borrando original: {s_dir}")
        shutil.rmtree(s_dir, ignore_errors=True)

def process_segment(date_str, orbit, config, client, ui=None):
    """Procesa de forma lineal y secuencial un segmento (combinación de fecha y órbita)."""
    segment_name = f"{date_str}_{orbit}"
    compact_date = date_str.replace("-", "")
    
    # 1. Adaptar rutas de Linux/Docker a Windows local de forma inteligente
    working_folder = config.working_folder
    if not working_folder or "/workspace/" in working_folder:
        working_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output", "segments")
    
    segment_dir = os.path.join(working_folder, segment_name)
    zip_dir = os.path.join(segment_dir, "ZIP")
    
    logging.info(f"============================================================")
    logging.info(f"INICIANDO PROCESAMIENTO DEL SEGMENTO: {segment_name}")
    logging.info(f"Directorio de trabajo: {segment_dir}")
    logging.info(f"============================================================")
    if ui:
        ui.display_header(segment_name)
    
    # 2. Buscar productos en Copernicus DataSpace
    poly_search = config.poly_search
    products = client.search_products(orbit, date_str, poly_search)
    if not products:
        logging.info(f"No se encontraron productos Sentinel-2 MSIL1C en Copernicus para {date_str} y órbita {orbit}. Saltando segmento.")
        return True
        
    # Filtrar última baseline
    if config.only_last_baseline:
        products = client.filter_latest_baseline(products)
        
    # Verificar si tenemos gránulos para procesar
    if not products:
        logging.info("No hay gránulos válidos tras filtrar la baseline. Saltando segmento.")
        return True
        
    # Crear directorios
    os.makedirs(segment_dir, exist_ok=True)
    os.makedirs(zip_dir, exist_ok=True)
    
    # ------------------------------------------------------------
    # ETAPA 1: Descarga de Imágenes L1C
    # ------------------------------------------------------------
    stage_msg = "ETAPA 1: Descargando gránulos L1C en formato .zip"
    if ui: ui.update_stage(stage_msg, 1)
    else: logging.info(f">>> {stage_msg}")
    downloaded_zips = []
    for p in products:
        name = p.get('Name', '')
        zip_name = name.replace(".SAFE", ".zip") if name.endswith(".SAFE") else f"{name}.zip"
        # Los ZIP se guardan en la raíz del segmento para igualar la salida de ejemplo
        dest_zip_path = os.path.join(segment_dir, zip_name)
        
        # Extraer hash MD5 esperado
        checksums = p.get('Checksum', [])
        expected_md5 = None
        if checksums and isinstance(checksums, list):
            expected_md5 = checksums[0].get('Value')
        elif isinstance(checksums, dict):
            expected_md5 = checksums.get('Value')
            
        success = client.download_product(p['Id'], dest_zip_path, expected_md5)
        if not success:
            logging.error(f"Error crítico al descargar el gránulo: {name}. Se aborta el segmento.")
            return False
        downloaded_zips.append(dest_zip_path)
        
    logging.info("Descargas completadas correctamente.")
    
    # Deducir satélite (S2A o S2B) a partir del primer zip descargado
    sat_prefix = "S2X"
    if downloaded_zips:
        first_zip = os.path.basename(downloaded_zips[0])
        if first_zip.startswith("S2A") or first_zip.startswith("S2B") or first_zip.startswith("S2C"):
            sat_prefix = first_zip[:3]
            
    logging.info(f"Satélite detectado para el segmento: {sat_prefix}")
    
    # ------------------------------------------------------------
    # ETAPA 2: Máscaras de nubes y COG L1C (Opcional)
    # ------------------------------------------------------------
    stage_msg = "ETAPA 2: Descomprimiendo gránulos L1C y generando máscaras de nubes"
    if ui: ui.update_stage(stage_msg, 2)
    else: logging.info(f">>> {stage_msg}")
    
    # Siempre limpiar SAFE anteriores para partir de un estado limpio
    # clean_safe_directories(segment_dir) # DESACTIVADO POR DEBUG
    
    # Descomprimir ZIPs
    for z_path in downloaded_zips:
        logging.info(f"Descomprimiendo: {z_path}...")
        try:
            with zipfile.ZipFile(z_path, 'r') as zip_ref:
                zip_ref.extractall(segment_dir)
        except Exception as e:
            logging.error(f"Error al descomprimir {z_path}: {e}")
            return False
            
    # Generar máscaras de nubes (GPKG, TIF y SHP)
    try:
        mask_generator.generate_l1c_cloud_masks(segment_dir)
    except Exception as e:
        logging.error(f"Error crítico al generar máscaras de nubes L1C: {e}")
        return False
        
    # Obtener límites UTM de la órbita actual
    limits_utm = config.limits_utm.get(orbit)
    if not limits_utm:
        logging.error(f"Límites UTM no configurados para la órbita: {orbit} en pipeline.json")
        return False
        
    # Formatear límites geográficos para GDAL [xmin, ymin, xmax, ymax]
    limits_gdal = [limits_utm[0], limits_utm[3], limits_utm[1], limits_utm[2]]
    utm_zone = config.per_orbit_zone_utm.get(orbit, "T31")
    
    # Construcción de COG L1C (si está activada la opción)
    if config.product_l1c_generation:
        logging.info("Generación de mosaico L1C 4-bandas activada...")
        
        # Construcción de COG L1C (si está activada la opción)
        nom_escena_l1c = f"{sat_prefix}_L1C_{orbit}_{compact_date}"
        try:
            cog_builder.build_l1c_4band_cog(segment_dir, nom_escena_l1c, limits_gdal, utm_zone)
        except Exception as e:
            logging.error(f"Error en la construcción del mosaico L1C: {e}")
            # Continuar de todos modos con L2A
            
    # ------------------------------------------------------------
    # ETAPA 3: Corrección Atmosférica (Sen2Cor) sin DEM
    # ------------------------------------------------------------
    stage_msg = "ETAPA 3: Ejecutando Sen2Cor sin relieve (NO-DEM)"
    if ui: ui.update_stage(stage_msg, 3)
    else: logging.info(f">>> {stage_msg}")
    
    # Buscar carpetas L1C
    l1c_dirs = glob.glob(os.path.join(segment_dir, "*L1C*.SAFE"))
    if not l1c_dirs:
        logging.error("No se encontraron carpetas gránulo L1C .SAFE para procesar Sen2Cor.")
        return False
        
    # Aplicar parche de Baseline 05.11 a los L1C antes de Sen2Cor
    sen2cor_patch.apply_patch_l1c(segment_dir)
        
    for l1c_d in l1c_dirs:
        logging.info(f"Procesando con Sen2Cor NO-DEM el gránulo: {os.path.basename(l1c_d)}")
        if ui: ui.start_subtask("Sen2Cor NO-DEM", total=100.0)
        
        # IMPORTANTE: gipp_path=None fuerza el uso de la configuración legacy. variant="NO-DEM" no añade sufijo.
        success = sen2cor_wrapper.run_sen2cor(
            config.sen2cor_bin, 
            l1c_d, 
            gipp_path=None,
            resolution=10, 
            variant="NO-DEM",
            progress_callback=ui.update_subtask_progress if ui else None
        )
        
        if ui: ui.complete_subtask()
        if not success:
            logging.error(f"Fallo crítico en Sen2Cor NO-DEM para {os.path.basename(l1c_d)}.")
            return False
            
    # Aplicar parche de Baseline a los L2A NO-DEM generados
    sen2cor_patch.apply_patch_l2a(segment_dir)
    
    # NOTA: NO borramos los L1C descomprimidos, el usuario ha solicitado preservar los archivos intermedios.
    
    # ------------------------------------------------------------
    # ETAPA 4: Corrección Atmosférica con Relieve (DEM-CAT)
    # ------------------------------------------------------------
    stage_msg = "ETAPA 4: Ejecutando Sen2Cor DEM-CAT (con relieve topográfico)"
    if ui: ui.update_stage(stage_msg, 4)
    else: logging.info(f">>> {stage_msg}")
    
    # Usamos los mismos l1c_dirs ya que no los hemos borrado
    for l1c_d in l1c_dirs:
        logging.info(f"Procesando con Sen2Cor DEM-CAT el gránulo: {os.path.basename(l1c_d)}")
        if ui: ui.start_subtask("Sen2Cor DEM-CAT", total=100.0)
        
        # IMPORTANTE: Se inyecta expresamente la ruta del gipp_demcat y la variant DEMCAT
        success = sen2cor_wrapper.run_sen2cor(
            config.sen2cor_bin, 
            l1c_d, 
            gipp_path=config.l2a_gipp_demcat, 
            resolution=10, 
            variant="DEMCAT",
            progress_callback=ui.update_subtask_progress if ui else None
        )
        
        if ui: ui.complete_subtask()
        if not success:
            logging.error(f"Fallo crítico en Sen2Cor DEM-CAT para {os.path.basename(l1c_d)}.")
            return False
            
    # Aplicar parche de Baseline a los L2A DEMCAT
    sen2cor_patch.apply_patch_l2a(segment_dir)
            
    # ------------------------------------------------------------
    # ETAPA 5: Ensamblaje de Mosaicos GDAL (NO-DEM y DEMCAT)
    # ------------------------------------------------------------
    stage_msg = "ETAPA 5: Ensamblando Mosaicos L2A, SCL, NDVI y QuickLooks"
    if ui: ui.update_stage(stage_msg, 5)
    else: logging.info(f">>> {stage_msg}")
    
    nom_escena_l2a = f"{sat_prefix}_L2A_{orbit}_{compact_date}"
    nom_escena_scl = f"{sat_prefix}_SCL_{orbit}_{compact_date}"
    
    safe_dirs_all = glob.glob(os.path.join(segment_dir, "S2*_MSIL2A_*.SAFE"))
    safe_dirs_demcat = [d for d in safe_dirs_all if d.endswith("_DEMCAT.SAFE")]
    safe_dirs_nodem = [d for d in safe_dirs_all if not d.endswith("_DEMCAT.SAFE")]
    
    # 5.1 MOSAICO NO-DEM
    if safe_dirs_nodem:
        logging.info("Ensamblando Mosaico L2A NO-DEM...")
        try:
            mosaic_10b_path = os.path.join(segment_dir, f"{nom_escena_l2a}.btf")
            l2a_10b_mosaic.build_l2a_10band_mosaic(segment_dir, nom_escena_l2a, limits_gdal, utm_zone, config.allowed_inner_zeros_l2a, is_demcat=False)
            
            scl_path = os.path.join(segment_dir, f"{nom_escena_scl}.tif")
            scl_extractor.build_l2a_scl_mosaic(segment_dir, nom_escena_scl, limits_gdal, utm_zone, is_demcat=False)
            
            ndvi_path = os.path.join(segment_dir, f"{sat_prefix}_NDVI_{orbit}_{compact_date}.tif")
            ndvi_calculator.calculate_l2a_ndvi(mosaic_10b_path, ndvi_path)
            
            # QuickLooks
            os.makedirs(os.path.join(segment_dir, "QuickLook"), exist_ok=True)
            rgb_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a}_RGB_8b.tif")
            rgbi_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a}_RGBI_16b.tif")
            quicklook_generator.generate_quicklook_8b(mosaic_10b_path, rgb_path)
            quicklook_generator.generate_quicklook_16b(mosaic_10b_path, rgbi_path)
            
        except Exception as e:
            logging.error(f"Error ensamblando mosaico NO-DEM: {e}")
            return False
            
    # 5.2 MOSAICO DEMCAT
    if safe_dirs_demcat:
        nom_escena_l2a_dem = f"{nom_escena_l2a}_DEMCAT"
        nom_escena_scl_dem = f"{nom_escena_scl}_DEMCAT"
        logging.info("Ensamblando Mosaico L2A DEMCAT...")
        try:
            mosaic_10b_dem_path = os.path.join(segment_dir, f"{nom_escena_l2a_dem}.btf")
            l2a_10b_mosaic.build_l2a_10band_mosaic(segment_dir, nom_escena_l2a_dem, limits_gdal, utm_zone, config.allowed_inner_zeros_l2a, is_demcat=True)
            
            scl_dem_path = os.path.join(segment_dir, f"{nom_escena_scl_dem}.tif")
            scl_extractor.build_l2a_scl_mosaic(segment_dir, nom_escena_scl_dem, limits_gdal, utm_zone, is_demcat=True)
            
            ndvi_dem_path = os.path.join(segment_dir, f"{sat_prefix}_NDVI_{orbit}_{compact_date}_DEMCAT.tif")
            ndvi_calculator.calculate_l2a_ndvi(mosaic_10b_dem_path, ndvi_dem_path)
            
            # QuickLooks
            os.makedirs(os.path.join(segment_dir, "QuickLook"), exist_ok=True)
            rgb_dem_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a_dem}_RGB_8b.tif")
            rgbi_dem_path = os.path.join(segment_dir, "QuickLook", f"{nom_escena_l2a_dem}_RGBI_16b.tif")
            quicklook_generator.generate_quicklook_8b(mosaic_10b_dem_path, rgb_dem_path)
            quicklook_generator.generate_quicklook_16b(mosaic_10b_dem_path, rgbi_dem_path)
            
        except Exception as e:
            logging.error(f"Error ensamblando mosaico DEMCAT: {e}")
            return False
            
    # ------------------------------------------------------------
    # ETAPA 6: Fin del Procesamiento
    # ------------------------------------------------------------
    # El usuario solicitó mantener todos los ficheros intermedios.
    # Se han desactivado `compress_safe_to_zip` y `clean_safe_directories`.
    logging.info("Omitiendo limpieza de ficheros .SAFE por solicitud del usuario.")
    
    logging.info(f"============================================================")
    logging.info(f"SEGMENTO COMPLETADO CON ÉXITO: {segment_name}")
    logging.info(f"============================================================")
    return True

def main():
    args = parse_args()
    
    # 1. Cargar archivo de configuración
    if not os.path.isfile(args.config):
        print(f"Error: No se encontró el archivo de configuración en: {args.config}")
        sys.exit(1)
        
    config = PipelineConfig(args.config)
    
    # 2. Configurar logger de sesión actual
    working_folder = config.working_folder
    if not working_folder or "/workspace/" in working_folder:
        working_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")
    else:
        # Si config.working_folder apunta a output/segments, el log va en el padre (output)
        working_folder = os.path.dirname(working_folder)
        
    log_filepath = setup_logger(working_folder, config.date_range_start, config.date_range_end)
    
    # 3. Inicializar el cliente Copernicus DataSpace
    username = config.get_credential("CDSE_USERNAME")
    password = config.get_credential("CDSE_PASSWORD")
    
    if not username or not password:
        logging.error("No se encontraron credenciales de CDSE_USERNAME o CDSE_PASSWORD en el archivo .env o en el entorno.")
        sys.exit(1)
        
    client = CopernicusDataspaceClient(
        download_url=config.api_download_url,
        auth_url=config.api_auth_url,
        username=username,
        password=password
    )
    
    # 4. Generar lista de fechas
    dates = get_date_list(config.date_range_start, config.date_range_end)
    orbits = config.orbits
    
    logging.info(f"Total de fechas a verificar: {len(dates)} ({config.date_range_start} a {config.date_range_end})")
    logging.info(f"Órbitas configuradas: {orbits}")
    
    success_count = 0
    fail_count = 0
    
    ui = PipelineConsoleUI()
    ui.start_pipeline()
    
    try:
        # Bucle secuencial y lineal por fechas y órbitas
        for date_str in dates:
            for orbit in orbits:
                try:
                    success = process_segment(date_str, orbit, config, client, ui=ui)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                        logging.error(f"Fallo en el procesamiento del segmento {date_str}_{orbit}")
                except Exception as e:
                    fail_count += 1
                    logging.exception(f"Error inesperado al procesar el segmento {date_str}_{orbit}: {e}")
    finally:
        ui.stop_pipeline()
                
    logging.info(f"============================================================")
    logging.info(f"PROCESAMIENTO BATCH CONCLUIDO")
    logging.info(f"Segmentos procesados con éxito: {success_count}")
    logging.info(f"Segmentos fallidos: {fail_count}")
    logging.info(f"Archivo de log registrado en: {log_filepath}")
    logging.info(f"============================================================")

if __name__ == "__main__":
    main()
