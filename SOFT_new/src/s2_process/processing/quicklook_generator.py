# -*- coding: utf-8 -*-
"""
Módulo para la generación de QuickLooks a partir del mosaico de 10 bandas L2A.
Genera:
- QuickLook RGB de 8 bits comprimido en JPEG (calidad 75), escalando por 0.1 y evitando ceros falsos.
- QuickLook RGBI de 16 bits (bandas B04, B03, B02, B08) en COG comprimido en LZW.
"""

import os
import logging
import numpy as np
from osgeo import gdal
from s2_process.utils.gdal_helpers import run_translate

def generate_quicklook_8b(mosaic_10b_path, output_rgb_8b_path):
    """
    Genera un QuickLook de 8 bits RGB (B04, B03, B02):
    - Multiplica los valores por 0.1 (factor de stretch).
    - Evita que los valores válidos mayores a 0 se conviertan en 0 (reservado para NoData).
    - Guarda en formato COG con compresión JPEG (calidad 75) y fotometría YCBCR.
    """
    logging.info(f"Generando QuickLook RGB de 8 bits desde: {mosaic_10b_path}")
    
    ds = gdal.Open(mosaic_10b_path, gdal.GA_ReadOnly)
    if not ds:
        raise RuntimeError(f"No se pudo abrir el mosaico multibanda L2A: {mosaic_10b_path}")
        
    width = ds.RasterXSize
    height = ds.RasterYSize
    projection = ds.GetProjection()
    geotransform = ds.GetGeoTransform()
    
    # En nuestro mosaico de 10 bandas:
    # B02 es banda 1, B03 es banda 2, B04 es banda 3
    # Leemos en orden R, G, B -> Banda 3 (B04), Banda 2 (B03), Banda 1 (B02)
    b_r_src = ds.GetRasterBand(3).ReadAsArray()
    b_g_src = ds.GetRasterBand(2).ReadAsArray()
    b_b_src = ds.GetRasterBand(1).ReadAsArray()
    ds = None # Cerrar para liberar
    
    # Crear arrays de salida
    rgb_8b = []
    for orig_band in [b_r_src, b_g_src, b_b_src]:
        # Copiar como float para operar
        data_f = orig_band.astype(np.float32)
        
        # Máscara de datos válidos (original > 0)
        valid_mask = orig_band > 0
        
        # Aplicar factor de escala 0.1 (stretch)
        scaled = data_f * 0.1
        
        # Corregir bug histórico: si era original > 0 pero al escalar da <= 0, forzar a 1
        scaled[valid_mask & (scaled <= 0)] = 1.0
        
        # Redondear y clip a Byte
        byte_band = np.clip(np.round(scaled), 0, 255).astype(np.uint8)
        
        # Asegurar NoData = 0 estricto
        byte_band[~valid_mask] = 0
        
        rgb_8b.append(byte_band)
        
    # Escribir en un TIFF temporal de 3 bandas
    temp_ql_tif = output_rgb_8b_path.replace(".tif", "_temp.tif")
    os.makedirs(os.path.dirname(temp_ql_tif), exist_ok=True)
    
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(temp_ql_tif, width, height, 3, gdal.GDT_Byte)
    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(geotransform)
    
    for idx, byte_band in enumerate(rgb_8b):
        out_band = out_ds.GetRasterBand(idx + 1)
        out_band.WriteArray(byte_band)
        out_band.SetNoDataValue(0)
        
    out_band = None
    out_ds = None
    
    # Convertir a COG con compresión JPEG calidad 75 y fotometría YCBCR
    logging.info(f"Escribiendo COG de QuickLook RGB 8b en: {output_rgb_8b_path}")
    opts_cog = {
        "format": "COG",
        "noData": 0,
        "creationOptions": [
            "COMPRESS=JPEG",
            "QUALITY=75",
            "PHOTOMETRIC=YCBCR",
            "BIGTIFF=YES",
            "OVERVIEWS=IGNORE_EXISTING"
        ]
    }
    
    run_translate(temp_ql_tif, output_rgb_8b_path, options_dict=opts_cog)
    
    # Limpiar archivo temporal
    if os.path.exists(temp_ql_tif):
        os.remove(temp_ql_tif)
        
    logging.info(f"QuickLook RGB de 8 bits generado con éxito: {output_rgb_8b_path}")
    return True

def generate_quicklook_16b(mosaic_10b_path, output_rgbi_16b_path):
    """
    Genera un QuickLook de 16 bits RGBI (B04, B03, B02, B08):
    - Selecciona las bandas 3, 2, 1, 7 del mosaico multibanda L2A.
    - Guarda en formato COG con compresión LZW y predictor estándar.
    """
    logging.info(f"Generando QuickLook RGBI de 16 bits desde: {mosaic_10b_path}")
    
    # Opciones de gdal.Translate para extraer bandas y convertirlas a COG directamente
    opts_cog = {
        "format": "COG",
        "outputType": gdal.GDT_UInt16,
        "bandList": [3, 2, 1, 7], # B04, B03, B02, B08
        "noData": 0,
        "creationOptions": [
            "COMPRESS=LZW",
            "PREDICTOR=STANDARD",
            "BIGTIFF=YES",
            "OVERVIEWS=IGNORE_EXISTING"
        ]
    }
    
    run_translate(mosaic_10b_path, output_rgbi_16b_path, options_dict=opts_cog)
    logging.info(f"QuickLook RGBI de 16 bits generado con éxito: {output_rgbi_16b_path}")
    return True
