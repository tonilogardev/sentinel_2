# -*- coding: utf-8 -*-
"""
Módulo para la generación de máscaras de nubes binarias L1C (poligonación, dilatación y erosión OpenCV).
Portado y optimizado desde S2_MaskGeneration_L1C_Module_new.py.
"""

import os
import fnmatch
import logging
import cv2
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst
from s2_process.utils.gdal_helpers import run_translate, get_raster_epsg, polygonize_raster

def generate_l1c_cloud_masks(segment_dir):
    """
    Genera las máscaras binarias de nubes para todos los gránulos L1C .SAFE en el directorio del segmento.
    Crea archivos .tif, .gpkg y .shp de máscara bajo la carpeta MASK/.
    Retorna True si tiene éxito, o levanta una excepción en caso de error.
    """
    logging.info(f"Iniciando generación de máscaras de nubes para el segmento: {segment_dir}")
    
    dir_mask = os.path.join(segment_dir, "MASK")
    os.makedirs(dir_mask, exist_ok=True)
    
    # Buscar carpetas .SAFE de L1C en el directorio del segmento
    granule_list = fnmatch.filter(os.listdir(segment_dir), '*L1C*.SAFE')
    if not granule_list:
        logging.warning(f"No se encontraron directorios L1C .SAFE en: {segment_dir}")
        return True
        
    for nom_dir in granule_list:
        safe_path = os.path.join(segment_dir, nom_dir)
        granule_dir = os.path.join(safe_path, "GRANULE")
        
        if not os.path.exists(granule_dir):
            logging.error(f"Estructura incorrecta, falta la carpeta GRANULE en {safe_path}")
            continue
            
        granules = os.listdir(granule_dir)
        if not granules:
            logging.error(f"No hay gránulos dentro de GRANULE en {safe_path}")
            continue
            
        granule_name = granules[0]
        img_data_dir = os.path.join(granule_dir, granule_name, "IMG_DATA")
        
        if not os.path.exists(img_data_dir):
            logging.error(f"No se encontró IMG_DATA en {img_data_dir}")
            continue
            
        bands_jpg = os.listdir(img_data_dir)
        # Buscar la banda B04 jp2
        b04_files = fnmatch.filter(bands_jpg, '*_B04.jp2')
        if not b04_files:
            logging.error(f"No se encontró el archivo de la banda B04 en {img_data_dir}")
            continue
            
        b04_filename = b04_files[0]
        file_root = b04_filename[:22]
        
        # ID compacto del gránulo (ej: T31TBE_20260401T112500)
        # En el original: granule_ID = granule_name[4:10] + granule_name[18:34]
        # Ej: T31TBE_20260401T112500
        granule_ID = granule_name[4:10] + "_" + granule_name[18:34]
        
        file_in = os.path.join(img_data_dir, b04_filename)
        file_out_1b = os.path.join(dir_mask, f"{granule_ID}_B04_1b.tif")
        file_out_1b_tfw = os.path.join(dir_mask, f"{granule_ID}_B04_1b.tfw")
        
        logging.info(f"Procesando máscara para gránulo {granule_ID} usando la banda B04: {b04_filename}")
        
        # 1. Translate a TIFF 1-bit temporal para conservar el TFW
        opts_1b = {
            "format": "GTiff",
            "outputType": gdalconst.GDT_Byte,
            "noData": 0,
            "creationOptions": ["NBITS=1", "TILED=YES", "BLOCKXSIZE=1024", "BLOCKYSIZE=1024", "INTERLEAVE=BAND", "BIGTIFF=NO", "TFW=YES"]
        }
        run_translate(file_in, file_out_1b, options_dict=opts_1b)
        
        # Obtener el EPSG del original
        epsg = get_raster_epsg(file_out_1b)
        if not epsg:
            logging.warning(f"No se pudo determinar el EPSG de {file_out_1b}. Se asumirá EPSG:32631 (UTM 31N) por defecto.")
            epsg = "EPSG:32631"
            
        # 2. Leer con OpenCV y aplicar dilatación (1) y erosión (51)
        img = cv2.imread(file_out_1b, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise RuntimeError(f"OpenCV no pudo leer el archivo TIFF binario temporal: {file_out_1b}")
            
        kernel = np.ones((3, 3), np.uint8)
        dilation = cv2.dilate(img, kernel, iterations=1)
        
        erosion_val = 51
        erosion = cv2.erode(dilation, kernel, iterations=erosion_val)
        
        # Limpiar los bordes con un grosor de 51 píxeles
        erosion[0:erosion_val, :] = 0
        erosion[-erosion_val:, :] = 0
        erosion[:, 0:erosion_val] = 0
        erosion[:, -erosion_val:] = 0
        
        # Escribir la imagen erosionada
        file_out_eroded_full = os.path.join(dir_mask, f"{granule_ID}_B04_1b_eroded.tif")
        cv2.imwrite(file_out_eroded_full, erosion)
        
        # Renombrar .tfw original al del erosionado temporal para conservar geotransform
        file_out_eroded_full_tfw = os.path.join(dir_mask, f"{granule_ID}_B04_1b_eroded.tfw")
        if os.path.exists(file_out_1b_tfw):
            if os.path.exists(file_out_eroded_full_tfw):
                os.remove(file_out_eroded_full_tfw)
            os.rename(file_out_1b_tfw, file_out_eroded_full_tfw)
            
        # Eliminar original 1b
        if os.path.exists(file_out_1b):
            os.remove(file_out_1b)
            
        # 3. Translate final para asignar SRS y generar el raster TIFF definitivo
        file_dest_full = os.path.join(dir_mask, f"{granule_ID}_mask.tif")
        opts_mask = {
            "format": "GTiff",
            "outputType": gdalconst.GDT_Byte,
            "outputSRS": epsg,
            "noData": 0,
            "creationOptions": ["NBITS=1", "TILED=YES", "BLOCKXSIZE=1024", "BLOCKYSIZE=1024", "INTERLEAVE=BAND", "BIGTIFF=NO"]
        }
        run_translate(file_out_eroded_full, file_dest_full, options_dict=opts_mask)
        
        # Limpiar temporales de erosión
        if os.path.exists(file_out_eroded_full):
            os.remove(file_out_eroded_full)
        if os.path.exists(file_out_eroded_full_tfw):
            os.remove(file_out_eroded_full_tfw)
            
        # 4. Vectorización a GeoPackage
        file_gpkg_full = os.path.join(dir_mask, f"{granule_ID}_mask.gpkg")
        polygonize_raster(file_dest_full, file_gpkg_full, driver_name="GPKG", layer_name="polygons")
        
        # 5. Vectorización a Shapefile (opcional, portado por compatibilidad heredada)
        file_shp_full = os.path.join(dir_mask, f"{granule_ID}_mask.shp")
        polygonize_raster(file_dest_full, file_shp_full, driver_name="ESRI Shapefile", layer_name="polygons")
        
        logging.info(f"Máscara creada con éxito para {granule_ID}: {file_dest_full} y {file_gpkg_full}")
        
    logging.info("Generación de máscaras de nubes L1C completada exitosamente.")
    return True
