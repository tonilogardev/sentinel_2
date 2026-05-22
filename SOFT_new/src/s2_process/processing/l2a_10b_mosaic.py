# -*- coding: utf-8 -*-
"""
Módulo para el procesamiento de bandas L2A (10 bandas espectrales a 10m),
aplicación de calibraciones radiométricas de metadatos, corrección de ceros interiores (AllowedInnerzerosproductL2A)
y mosaico a Cloud Optimized GeoTIFF (COG) BigTIFF en huso UTM de destino.
"""

import os
import fnmatch
import logging
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst
from s2_process.utils import offset_gain
from s2_process.utils.gdal_helpers import run_translate, run_warp, run_build_vrt

def build_l2a_10band_mosaic(segment_dir, nom_escena, limits_gdal, utm_zone_destination, allowed_inner_zeros_l2a, is_demcat=False):
    """
    Orquesta el procesamiento de bandas L2A de gránulos .SAFE:
    - B02, B03, B04, B08 (10m)
    - B05, B06, B07, B8A, B11, B12 (20m, remuestreados cúbicamente a 10m)
    Aplica calibración radiométrica por banda, limpia ceros interiores (AllowedInnerzerosproductL2A=NO) usando
    la máscara binaria de nubes/área, re-proyecta e integra los gránulos en un COG BigTIFF definitivo.
    """
    variant_name = "DEMCAT" if is_demcat else "L2A"
    logging.info(f"Iniciando construcción de Mosaico {variant_name} 10-Bandas para escena: {nom_escena}")
    
    NOM_bandes = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B11', 'B12']
    GSD_bandes = [10, 10, 10, 20, 20, 20, 10, 20, 20, 20]
    
    # 1. Buscar carpetas .SAFE de L2A en el segmento
    # Si es DEMCAT, buscará los directorios L2A que contengan DEMCAT en el nombre?
    # No, Sen2Cor genera directorios .SAFE estándar. Pero el orquestador principal
    # probablemente los organiza en carpetas temporales o el pipeline corre Sen2Cor y produce carpetas.
    # Buscaremos carpetas .SAFE
    granule_list = fnmatch.filter(os.listdir(segment_dir), '*L2A*.SAFE')
    if not granule_list:
        raise RuntimeError(f"No se encontraron gránulos L2A .SAFE en {segment_dir}")
        
    temp_granule_tiffs = []
    
    for nom_dir in granule_list:
        granule_safe_path = os.path.join(segment_dir, nom_dir)
        granule_dir = os.path.join(granule_safe_path, "GRANULE")
        
        if not os.path.exists(granule_dir):
            logging.error(f"Falta la carpeta GRANULE en {granule_safe_path}")
            continue
            
        granules = os.listdir(granule_dir)
        if not granules:
            continue
            
        granule_name = granules[0]
        img_data_dir = os.path.join(granule_dir, granule_name, "IMG_DATA")
        
        if not os.path.exists(img_data_dir):
            continue
            
        # Determinar el nombre base
        r10_dir = os.path.join(img_data_dir, "R10m")
        if not os.path.exists(r10_dir):
            logging.error(f"Falta el directorio R10m en {img_data_dir}")
            continue
            
        r10_files = os.listdir(r10_dir)
        b02_files = fnmatch.filter(r10_files, '*_B02_10m.jp2')
        if not b02_files:
            logging.error(f"No se encontró el archivo de banda B02 a 10m en {r10_dir}")
            continue
            
        file_root = b02_files[0][:-12] # Corta '_B02_10m.jp2'
        
        # ID compacto del gránulo
        granule_ID = granule_name[4:10] + "_" + granule_name[18:34]
        logging.info(f"Calibrando offset y gain de bandas L2A para gránulo: {granule_ID}")
        
        # Obtener gain general del gránulo
        gain = offset_gain.get_gain("L2A", granule_safe_path)
        gain_f = 10000.0 / gain
        
        # Leer el dataset de referencia de 10m para obtener geotransform, proyección y dimensiones
        ref_band_path = os.path.join(r10_dir, b02_files[0])
        ref_ds = gdal.Open(ref_band_path, gdal.GA_ReadOnly)
        if not ref_ds:
            raise RuntimeError(f"No se pudo abrir la banda de referencia L2A B02: {ref_band_path}")
            
        target_width = ref_ds.RasterXSize
        target_height = ref_ds.RasterYSize
        ref_projection = ref_ds.GetProjection()
        ref_geotransform = ref_ds.GetGeoTransform()
        ref_ds = None
        
        # Cargar la máscara binaria de nubes del gránulo
        mask_path = os.path.join(segment_dir, "MASK", f"{granule_ID}_mask.tif")
        mask_data = None
        if not allowed_inner_zeros_l2a:
            if os.path.isfile(mask_path):
                mask_ds = gdal.Open(mask_path, gdal.GA_ReadOnly)
                if mask_ds:
                    mask_data = mask_ds.GetRasterBand(1).ReadAsArray()
                    mask_ds = None
                else:
                    logging.warning(f"No se pudo abrir la máscara {mask_path} a pesar de que existe.")
            else:
                logging.warning(f"No se encontró la máscara {mask_path} necesaria para AllowedInnerzerosproductL2A=NO.")
                
        # Crear el TIFF multibanda temporal para el gránulo (10 bandas)
        temp_granule_tif = os.path.join(segment_dir, f"{granule_ID}_10B_{variant_name}_temp.tif")
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(temp_granule_tif, target_width, target_height, len(NOM_bandes), gdal.GDT_UInt16)
        out_ds.SetProjection(ref_projection)
        out_ds.SetGeoTransform(ref_geotransform)
        
        for i_banda, band_name in enumerate(NOM_bandes):
            gsd = GSD_bandes[i_banda]
            if gsd == 10:
                band_path = os.path.join(img_data_dir, "R10m", f"{file_root}_{band_name}_10m.jp2")
            else:
                band_path = os.path.join(img_data_dir, "R20m", f"{file_root}_{band_name}_20m.jp2")
                
            if not os.path.isfile(band_path):
                # Intentar buscar sin la extensión '_20m.jp2' por si varía
                logging.warning(f"Banda no encontrada en {band_path}, buscando patrón...")
                r_dir = "R10m" if gsd == 10 else "R20m"
                search_dir = os.path.join(img_data_dir, r_dir)
                candidates = fnmatch.filter(os.listdir(search_dir), f"*{band_name}*.jp2")
                if candidates:
                    band_path = os.path.join(search_dir, candidates[0])
                else:
                    raise FileNotFoundError(f"No se encontró el archivo jp2 para la banda L2A: {band_name} en {search_dir}")
                    
            # Leer offset de la banda espectral
            offset = offset_gain.get_offset("L2A", granule_safe_path, band_name)
            offset_f = 10000.0 * offset / gain
            
            logging.debug(f"Procesando {band_name} L2A -> offset: {offset}, gain: {gain}. Factores -> gain_f: {gain_f}, offset_f: {offset_f}")
            
            # Abrir y leer/resamplear con GDAL en una sola operación in-memory
            src_ds = gdal.Open(band_path, gdal.GA_ReadOnly)
            band = src_ds.GetRasterBand(1)
            
            # Resampling cúbico para 20m a 10m, lectura directa para 10m
            if gsd == 20:
                data = band.ReadAsArray(buf_xsize=target_width, buf_ysize=target_height, resample_alg=gdal.GRIORA_Cubic)
            else:
                data = band.ReadAsArray()
                
            # Calibración radiométrica
            calibrated = data.astype(np.float32) * gain_f + offset_f
            calibrated[calibrated < 0] = 0
            
            # Limpieza de ceros interiores si corresponde
            if not allowed_inner_zeros_l2a and mask_data is not None:
                # Píxeles válidos del gránulo con valor <= 0 se setean a 1
                zero_indices = (mask_data == 1) & (calibrated <= 0)
                calibrated[zero_indices] = 1.0
                
            # Seteo de NoData (0) para cualquier pixel que no esté en la máscara o donde el original sea 0
            if mask_data is not None:
                calibrated[mask_data == 0] = 0
            else:
                calibrated[data == 0] = 0
                
            # Conversión final a UInt16
            calibrated = np.clip(calibrated, 0, 65535).astype(np.uint16)
            
            # Escribir en la banda correspondiente del TIFF multibanda
            out_band = out_ds.GetRasterBand(i_banda + 1)
            out_band.WriteArray(calibrated)
            out_band.SetNoDataValue(0)
            
            # Liberar dataset de banda de origen
            src_ds = None
            
        # Cerrar el dataset multibanda del gránulo
        out_ds = None
        temp_granule_tiffs.append(temp_granule_tif)
        
    # 2. Recorte por máscara (cutline) y reproyección de huso UTM de los gránulos multibanda L2A
    cut_vrts = []
    utm_zone_dst_clean = utm_zone_destination.upper().replace("T", "") # Ej: "31"
    
    for file_in in temp_granule_tiffs:
        granule_filename = os.path.basename(file_in)
        # Corta '_10B_DEMCAT_temp.tif' o '_10B_L2A_temp.tif'
        granule_ID = granule_filename.split("_10B_")[0]
        
        file_mask = os.path.join(segment_dir, "MASK", f"{granule_ID}_mask.gpkg")
        file_in_cut = os.path.join(segment_dir, f"{granule_ID}_{variant_name}_cut.vrt")
        
        if not os.path.isfile(file_mask):
            raise RuntimeError(f"Falta la máscara GeoPackage requerida para recortar L2A: {file_mask}")
            
        src_zone = granule_ID[1:3] # "30" o "31"
        logging.info(f"Aplicando cutline a L2A {granule_ID}. Huso origen: UTM {src_zone}N, Destino: UTM {utm_zone_dst_clean}N")
        
        if src_zone == utm_zone_dst_clean:
            # Warp simple sin reproyección
            opts_warp = {
                "format": "VRT",
                "cutlineDSName": file_mask,
                "cropToCutline": True,
                "dstNodata": 0
            }
            run_warp(file_in, file_in_cut, options_dict=opts_warp)
        else:
            # Warp con reproyección cúbica
            opts_warp = {
                "format": "VRT",
                "cutlineDSName": file_mask,
                "cropToCutline": True,
                "xRes": 10.0,
                "yRes": 10.0,
                "targetAlignedPixels": True,
                "srcSRS": f"EPSG:326{src_zone}",
                "dstSRS": f"EPSG:326{utm_zone_dst_clean}",
                "dstNodata": 0,
                "resampleAlg": gdal.GRA_Cubic
            }
            run_warp(file_in, file_in_cut, options_dict=opts_warp)
            
        cut_vrts.append(file_in_cut)
        
    # 3. Construcción del VRT mosaico global recortado por los límites geográficos
    file_out_vrt_global = os.path.join(segment_dir, f"{nom_escena}_{variant_name}_mosaico.vrt")
    opts_vrt_global = {
        "VRTNodata": 0,
        "outputBounds": limits_gdal
    }
    run_build_vrt(cut_vrts, file_out_vrt_global, options_dict=opts_vrt_global)
    
    # 4. Traducir el mosaico general a formato COG BigTIFF definitivo
    # El nombre definitivo será algo como S2X_L2A_{orbit}_{compact}.btf
    file_out_cog = os.path.join(segment_dir, f"{nom_escena}.btf")
    logging.info(f"Escribiendo COG L2A 10-Bandas definitivo en: {file_out_cog}")
    
    opts_cog = {
        "format": "COG",
        "noData": 0,
        "creationOptions": ["COMPRESS=LZW", "PREDICTOR=STANDARD", "BIGTIFF=YES"]
    }
    run_translate(file_out_vrt_global, file_out_cog, options_dict=opts_cog)
    
    # 5. Limpieza de archivos temporales
    if os.path.exists(file_out_vrt_global):
        os.remove(file_out_vrt_global)
        
    for cv in cut_vrts:
        if os.path.exists(cv):
            os.remove(cv)
            
    for gt in temp_granule_tiffs:
        if os.path.exists(gt):
            os.remove(gt)
            
    logging.info(f"Mosaico COG L2A 10-Bandas completado exitosamente: {file_out_cog}")
    return True
