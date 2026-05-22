# -*- coding: utf-8 -*-
"""
Módulo para el procesamiento y calibración de bandas L1C, corrección radiométrica
y construcción del mosaico COG 4-bandas con corrección del swap de bandas de GDAL.
"""

import os
import fnmatch
import logging
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst
from s2_process.utils import offset_gain
from s2_process.utils.gdal_helpers import run_translate, run_warp, run_build_vrt

def build_l1c_4band_cog(segment_dir, nom_escena, limits_gdal, utm_zone_destination):
    """
    Orquesta el procesamiento de bandas L1C (B02, B03, B04, B08) de gránulos .SAFE,
    aplica ganancia/offset radiométrico, recorta con cutline (máscara GPKG),
    reproyecta cúbicamente si es necesario y mosaica a un COG de 4 bandas definitivo.
    """
    logging.info(f"Iniciando construcción de COG L1C 4-Bandas para escena: {nom_escena}")
    
    # 1. Parámetros de banda L1C
    GSD_bandes = [10, 10, 10, 10]
    NOM_bandes = ['B02', 'B03', 'B04', 'B08']
    
    granule_list = fnmatch.filter(os.listdir(segment_dir), '*L1C*.SAFE')
    if not granule_list:
        raise RuntimeError(f"No se encontraron gránulos L1C .SAFE en {segment_dir}")
        
    temp_granule_tiffs = []
    
    # Procesar gránulo por gránulo
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
            
        bands_jpg = os.listdir(img_data_dir)
        # Nombre base del archivo jp2
        b02_files = fnmatch.filter(bands_jpg, '*_B02.jp2')
        if not b02_files:
            continue
            
        file_root = b02_files[0][:22]
        
        # ID compacto del gránulo
        granule_ID = granule_name[4:10] + "_" + granule_name[18:34]
        logging.info(f"Calibrando offset y gain de bandas 10m para gránulo: {granule_ID}")
        
        # Leer gain general del gránulo
        gain = offset_gain.get_gain("L1C", granule_safe_path)
        gain_f = 10000.0 / gain
        
        band_tifs = []
        
        # Calibrar y generar TIF temporal para cada una de las 4 bandas
        for i_banda, band_name in enumerate(NOM_bandes):
            band_filename = f"{file_root}_{band_name}.jp2"
            file_in = os.path.join(img_data_dir, band_filename)
            file_out = os.path.join(segment_dir, f"{granule_ID}_{band_name}.tif")
            
            if not os.path.isfile(file_in):
                raise RuntimeError(f"No se encontró el archivo de banda espectral: {file_in}")
                
            # Leer offset de la banda
            # El original pasaba index i_banda+1 y lo convertía. Le pasamos el nombre de la banda directamente.
            offset = offset_gain.get_offset("L1C", granule_safe_path, band_name)
            offset_f = 10000.0 * offset / gain
            
            logging.debug(f"Banda {band_name} -> offset: {offset}, gain: {gain}. Factores -> gain_f: {gain_f}, offset_f: {offset_f}")
            
            # Aplicar calibración matemática en memoria con Numpy (súper eficiente y libre de dependencias complejas)
            src_ds = gdal.Open(file_in, gdal.GA_ReadOnly)
            band = src_ds.GetRasterBand(1)
            data = band.ReadAsArray()
            
            # Calibración: TOAi = DN * gain_f + offset_f
            calibrated = data.astype(np.float32) * gain_f + offset_f
            calibrated[calibrated < 0] = 0
            calibrated = np.clip(calibrated, 0, 65535).astype(np.uint16)
            # Conservar NoData original
            calibrated[data == 0] = 0
            
            # Escribir a TIF temporal
            driver = gdal.GetDriverByName("GTiff")
            out_ds = driver.Create(file_out, src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_UInt16)
            out_ds.SetProjection(src_ds.GetProjection())
            out_ds.SetGeoTransform(src_ds.GetGeoTransform())
            out_band = out_ds.GetRasterBand(1)
            out_band.WriteArray(calibrated)
            out_band.SetNoDataValue(0)
            
            # Cerrar
            out_band = None
            out_ds = None
            src_ds = None
            
            band_tifs.append(file_out)
            
        # Crear VRT del gránulo agrupando las 4 bandas
        file_out_vrt = os.path.join(segment_dir, f"{granule_ID}.vrt")
        opts_vrt = {"separate": True, "srcNodata": 0, "VRTNodata": 0}
        run_build_vrt(band_tifs, file_out_vrt, options_dict=opts_vrt)
        
        # Traducir el VRT a un TIFF unificado de gránulo
        file_out_tif = os.path.join(segment_dir, f"{granule_ID}.tif")
        opts_trans = {
            "format": "GTiff",
            "noData": 0,
            "creationOptions": ["COMPRESS=LZW", "TILED=YES", "BIGTIFF=YES"]
        }
        run_translate(file_out_vrt, file_out_tif, options_dict=opts_trans)
        
        # Limpieza de archivos de bandas individuales y VRT temporal del gránulo
        if os.path.exists(file_out_vrt):
            os.remove(file_out_vrt)
        for t in band_tifs:
            if os.path.exists(t):
                os.remove(t)
                
        temp_granule_tiffs.append(file_out_tif)
        
    # 2. Recorte por máscara (cutline) y reproyección de huso UTM
    cut_vrts = []
    utm_zone_dst_clean = utm_zone_destination.upper().replace("T", "") # Ej: "31"
    
    for file_in in temp_granule_tiffs:
        granule_filename = os.path.basename(file_in)
        granule_ID = os.path.splitext(granule_filename)[0]
        
        file_mask = os.path.join(segment_dir, "MASK", f"{granule_ID}_mask.gpkg")
        file_in_cut = os.path.join(segment_dir, f"{granule_ID}_cut.vrt")
        
        if not os.path.isfile(file_mask):
            raise RuntimeError(f"Falta la máscara GeoPackage requerida para recortar L1C: {file_mask}")
            
        # Determinar zona UTM del gránulo. Tile empieza con "T31..." o "T30..."
        # El tile está en granule_ID, ej: T31TBE_20260401T112500 -> zone es "31"
        src_zone = granule_ID[1:3]
        
        logging.info(f"Aplicando cutline a {granule_ID}. Huso origen: UTM {src_zone}N, Destino: UTM {utm_zone_dst_clean}N")
        
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
            # Warp con reproyección
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
        
    # 3. Construcción del VRT mosaico global con los límites geográficos
    file_out_vrt_global = os.path.join(segment_dir, f"{nom_escena}.vrt")
    opts_vrt_global = {
        "VRTNodata": 0,
        "outputBounds": limits_gdal
    }
    run_build_vrt(cut_vrts, file_out_vrt_global, options_dict=opts_vrt_global)
    
    # 4. Traducir el mosaico general a formato COG definitivo
    file_out_cog = os.path.join(segment_dir, f"{nom_escena}.btf")
    logging.info(f"Escribiendo COG de 4 bandas definitivo en: {file_out_cog}")
    
    opts_cog = {
        "format": "COG",
        "noData": 0,
        "creationOptions": ["COMPRESS=LZW", "PREDICTOR=STANDARD", "BIGTIFF=YES"]
    }
    run_translate(file_out_vrt_global, file_out_cog, options_dict=opts_cog)
    
    # 5. Limpieza de todos los archivos de trabajo temporales (gránulos .tif y VRTs cortados)
    if os.path.exists(file_out_vrt_global):
        os.remove(file_out_vrt_global)
        
    for cv in cut_vrts:
        if os.path.exists(cv):
            os.remove(cv)
            
    for gt in temp_granule_tiffs:
        if os.path.exists(gt):
            os.remove(gt)
            
    logging.info(f"Mosaico COG L1C 4-Bandas completado exitosamente: {file_out_cog}")
    return True
