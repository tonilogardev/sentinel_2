# -*- coding: utf-8 -*-
"""
Módulo para el cálculo del NDVI en formato Byte [0-200] optimizado,
donde 0 es NoData, y cualquier valor 0 matemático real es forzado a 1 para preservar NoData.
Fórmula idéntica a la del pipeline de la ICC: NDVI_Byte = (200.0 * B08) / (B08 + B04).
"""

import os
import logging
import numpy as np
from osgeo import gdal
from s2_process.utils.gdal_helpers import run_translate

def calculate_l2a_ndvi(mosaic_10b_path, output_ndvi_path):
    """
    Calcula el NDVI a partir del mosaico de 10 bandas L2A (normalmente DEMCAT):
    - B04 (Banda 3)
    - B08 (Banda 7)
    Genera un COG TIFF de 8 bits (Byte) en output_ndvi_path.
    """
    logging.info(f"Iniciando cálculo de NDVI desde: {mosaic_10b_path}")
    
    ds = gdal.Open(mosaic_10b_path, gdal.GA_ReadOnly)
    if not ds:
        raise RuntimeError(f"No se pudo abrir el mosaico multibanda L2A: {mosaic_10b_path}")
        
    width = ds.RasterXSize
    height = ds.RasterYSize
    projection = ds.GetProjection()
    geotransform = ds.GetGeoTransform()
    
    # B04 es la banda 3, B08 es la banda 7 en nuestro mosaico de 10 bandas
    b04_band = ds.GetRasterBand(3)
    b08_band = ds.GetRasterBand(7)
    
    b04 = b04_band.ReadAsArray().astype(np.float32)
    b08 = b08_band.ReadAsArray().astype(np.float32)
    ds = None # Cerrar el dataset de entrada para liberar recursos
    
    # Calcular el denominador
    denom = b08 + b04
    
    # Píxeles válidos: donde ambas bandas son mayores que 0 (evitando NoData de bordes) y denom > 0
    valid_mask = (b04 > 0) & (b08 > 0) & (denom > 0)
    
    ndvi = np.zeros_like(b04, dtype=np.float32)
    
    # Aplicar la fórmula optimizada (200 * B08) / (B08 + B04)
    # que equivale matemáticamente a: 100 * (B08 - B04)/(B08 + B04) + 100
    ndvi[valid_mask] = (200.0 * b08[valid_mask]) / denom[valid_mask]
    
    # Forzar cualquier 0 real/matemático dentro de la máscara a 1 para diferenciar de NoData (0)
    zero_indices = valid_mask & (ndvi <= 0)
    ndvi[zero_indices] = 1.0
    
    # Redondear y clip a Byte [0, 255], forzando NoData a 0
    ndvi_byte = np.clip(np.round(ndvi), 0, 255).astype(np.uint8)
    ndvi_byte[~valid_mask] = 0
    
    # Guardar a un archivo temporal TIFF
    temp_ndvi_tif = output_ndvi_path.replace(".tif", "_temp.tif")
    driver = gdal.GetDriverByName("GTiff")
    out_ds = driver.Create(temp_ndvi_tif, width, height, 1, gdal.GDT_Byte)
    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(geotransform)
    
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(ndvi_byte)
    out_band.SetNoDataValue(0)
    out_band = None
    out_ds = None
    
    # Convertir a COG definitivo
    logging.info(f"Escribiendo COG de NDVI en: {output_ndvi_path}")
    opts_cog = {
        "format": "COG",
        "noData": 0,
        "creationOptions": ["COMPRESS=LZW", "BIGTIFF=YES"]
    }
    run_translate(temp_ndvi_tif, output_ndvi_path, options_dict=opts_cog)
    
    # Limpiar archivo temporal
    if os.path.exists(temp_ndvi_tif):
        os.remove(temp_ndvi_tif)
        
    logging.info(f"NDVI calculado y guardado con éxito: {output_ndvi_path}")
    return True
