# -*- coding: utf-8 -*-
"""
Módulo para la extracción, remuestreo (a 10m) y mosaico de la capa SCL (Scene Classification Layer) L2A.
Usa interpolación por vecino más próximo para preservar las clases categóricas discretas de Sen2Cor.
"""

import os
import fnmatch
import logging
from osgeo import gdal, ogr, osr, gdalconst
from s2_process.utils.gdal_helpers import run_translate, run_warp, run_build_vrt

def build_l2a_scl_mosaic(segment_dir, nom_escena, limits_gdal, utm_zone_destination, is_demcat=False):
    """
    Orquesta el procesamiento de la Scene Classification Layer (SCL) de los gránulos L2A .SAFE:
    - Extrae la banda SCL de 20m.
    - La remuestrea a 10m por Vecino Más Próximo (GRIORA_NearestNeighbour).
    - Aplica la máscara de recorte (GPKG cutline) para limpiar bordes.
    - Reproyecta cúbicamente? ¡No, re-proyecta por vecino más próximo (GRA_NearestNeighbour) para preservar clases!
    - Mosaica los gránulos del segmento a un COG de 8 bits definitivo.
    """
    variant_name = "DEMCAT" if is_demcat else "L2A"
    logging.info(f"Iniciando extracción y mosaico de capa SCL {variant_name} para escena: {nom_escena}")
    
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
            
        # Localizar el SCL a 20m
        r20_dir = os.path.join(img_data_dir, "R20m")
        if not os.path.exists(r20_dir):
            logging.error(f"Falta el directorio R20m en {img_data_dir}")
            continue
            
        r20_files = os.listdir(r20_dir)
        scl_files = fnmatch.filter(r20_files, '*_SCL_20m.jp2')
        if not scl_files:
            # Buscar con patrón alternativo
            candidates = fnmatch.filter(os.listdir(r20_dir), '*SCL*.jp2')
            if candidates:
                scl_files = [candidates[0]]
            else:
                logging.error(f"No se encontró el archivo SCL en {r20_dir}")
                continue
                
        scl_filename = scl_files[0]
        file_root = scl_filename.split("_SCL_")[0]
        
        # ID compacto del gránulo
        granule_ID = granule_name[4:10] + "_" + granule_name[18:34]
        logging.info(f"Procesando SCL para gránulo: {granule_ID}")
        
        # Buscar la banda B02 a 10m para obtener las dimensiones objetivo (10m)
        r10_dir = os.path.join(img_data_dir, "R10m")
        if not os.path.exists(r10_dir):
            raise FileNotFoundError(f"Falta el directorio R10m necesario para leer dimensiones en {img_data_dir}")
            
        r10_files = os.listdir(r10_dir)
        b02_files = fnmatch.filter(r10_files, '*_B02_10m.jp2')
        if not b02_files:
            raise FileNotFoundError(f"No se encontró la banda de referencia B02 en {r10_dir}")
            
        ref_ds = gdal.Open(os.path.join(r10_dir, b02_files[0]), gdal.GA_ReadOnly)
        target_width = ref_ds.RasterXSize
        target_height = ref_ds.RasterYSize
        ref_projection = ref_ds.GetProjection()
        ref_geotransform = ref_ds.GetGeoTransform()
        ref_ds = None
        
        # Abrir el SCL origen y remuestrearlo a 10m por Vecino Más Próximo
        scl_path = os.path.join(r20_dir, scl_filename)
        src_ds = gdal.Open(scl_path, gdal.GA_ReadOnly)
        band = src_ds.GetRasterBand(1)
        
        # Lectura con remuestreo por vecino más próximo
        scl_10m_data = band.ReadAsArray(buf_xsize=target_width, buf_ysize=target_height, resample_alg=gdal.GRIORA_NearestNeighbour)
        src_ds = None
        
        # Aplicar la máscara binaria para limpiar bordes
        mask_path = os.path.join(segment_dir, "MASK", f"{granule_ID}_mask.tif")
        if os.path.isfile(mask_path):
            mask_ds = gdal.Open(mask_path, gdal.GA_ReadOnly)
            if mask_ds:
                mask_data = mask_ds.GetRasterBand(1).ReadAsArray()
                # Fuera de la máscara el valor SCL es 0 (NoData)
                scl_10m_data[mask_data == 0] = 0
                mask_ds = None
                
        # Escribir SCL remuestreado temporal
        temp_scl_tif = os.path.join(segment_dir, f"{granule_ID}_SCL_temp.tif")
        driver = gdal.GetDriverByName("GTiff")
        out_ds = driver.Create(temp_scl_tif, target_width, target_height, 1, gdal.GDT_Byte)
        out_ds.SetProjection(ref_projection)
        out_ds.SetGeoTransform(ref_geotransform)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(scl_10m_data)
        out_band.SetNoDataValue(0)
        out_band = None
        out_ds = None
        
        temp_granule_tiffs.append(temp_scl_tif)
        
    # 2. Recorte por cutline y reproyección a huso UTM de destino
    cut_vrts = []
    utm_zone_dst_clean = utm_zone_destination.upper().replace("T", "") # Ej: "31"
    
    for file_in in temp_granule_tiffs:
        granule_filename = os.path.basename(file_in)
        granule_ID = granule_filename.split("_SCL_")[0]
        
        file_mask = os.path.join(segment_dir, "MASK", f"{granule_ID}_mask.gpkg")
        file_in_cut = os.path.join(segment_dir, f"{granule_ID}_{variant_name}_SCL_cut.vrt")
        
        if not os.path.isfile(file_mask):
            raise RuntimeError(f"Falta la máscara GeoPackage requerida para recortar SCL: {file_mask}")
            
        src_zone = granule_ID[1:3] # "30" o "31"
        logging.info(f"Aplicando cutline a SCL {granule_ID}. Huso origen: UTM {src_zone}N, Destino: UTM {utm_zone_dst_clean}N")
        
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
            # Warp con reproyección por Vecino Más Próximo
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
                "resampleAlg": gdal.GRA_NearestNeighbour
            }
            run_warp(file_in, file_in_cut, options_dict=opts_warp)
            
        cut_vrts.append(file_in_cut)
        
    # 3. Mosaico global recortado por límites geográficos
    file_out_vrt_global = os.path.join(segment_dir, f"{nom_escena}_{variant_name}_SCL_mosaico.vrt")
    opts_vrt_global = {
        "VRTNodata": 0,
        "outputBounds": limits_gdal
    }
    run_build_vrt(cut_vrts, file_out_vrt_global, options_dict=opts_vrt_global)
    
    # 4. Traducir a formato COG definitivo
    file_out_cog = os.path.join(segment_dir, f"{nom_escena}.tif")
    logging.info(f"Escribiendo COG SCL definitivo en: {file_out_cog}")
    
    opts_cog = {
        "format": "COG",
        "noData": 0,
        "creationOptions": ["COMPRESS=LZW", "BIGTIFF=YES"]
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
            
    logging.info(f"Mosaico COG SCL completado exitosamente: {file_out_cog}")
    return True
