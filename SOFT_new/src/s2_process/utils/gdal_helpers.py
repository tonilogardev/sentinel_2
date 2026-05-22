# -*- coding: utf-8 -*-
"""
Módulo de utilidades y wrappers para operaciones con GDAL/OGR/OSR.
Proporciona llamadas nativas y controladas de Translate, Warp, BuildVRT y Polygonize.
"""

import os
import logging
from osgeo import gdal, ogr, osr, gdalconst

gdal.UseExceptions()

def get_raster_epsg(raster_path):
    """
    Obtiene el código EPSG de un archivo raster.
    Retorna la cadena 'EPSG:xxxx' o None.
    """
    try:
        ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
        if not ds:
            return None
        proj_wkt = ds.GetProjection()
        if not proj_wkt:
            ds = None
            return None
        srs = osr.SpatialReference(wkt=proj_wkt)
        srs.AutoIdentifyEPSG()
        epsg = srs.GetAttrValue('AUTHORITY', 1)
        ds = None
        if epsg:
            return f"EPSG:{epsg}"
        return None
    except Exception as e:
        logging.error(f"Error al obtener EPSG de {raster_path}: {e}")
        return None

def run_translate(src_path, dest_path, options_dict=None, **kwargs):
    """
    Wrapper seguro alrededor de gdal.Translate.
    Siempre sobrescribe si el archivo de destino existe.
    """
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)
            aux_xml = dest_path + ".aux.xml"
            if os.path.exists(aux_xml):
                os.remove(aux_xml)
                
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if options_dict:
            opts = gdal.TranslateOptions(**options_dict)
        else:
            opts = gdal.TranslateOptions(**kwargs)
            
        ds = gdal.Translate(dest_path, src_path, options=opts)
        ds = None  # Cerrar dataset
        
        # Eliminar aux.xml residual
        aux_xml = dest_path + ".aux.xml"
        if os.path.exists(aux_xml):
            try:
                os.remove(aux_xml)
            except Exception:
                pass
                
        return True
    except Exception as e:
        logging.error(f"Error en gdal.Translate de {src_path} a {dest_path}: {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise

def run_warp(src_paths, dest_path, options_dict=None, **kwargs):
    """
    Wrapper seguro alrededor de gdal.Warp.
    Siempre sobrescribe si el archivo de destino existe.
    """
    try:
        if os.path.exists(dest_path):
            os.remove(dest_path)
            aux_xml = dest_path + ".aux.xml"
            if os.path.exists(aux_xml):
                os.remove(aux_xml)
                
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if options_dict:
            opts = gdal.WarpOptions(**options_dict)
        else:
            opts = gdal.WarpOptions(**kwargs)
            
        ds = gdal.Warp(dest_path, src_paths, options=opts)
        ds = None  # Cerrar dataset
        
        # Eliminar aux.xml residual
        aux_xml = dest_path + ".aux.xml"
        if os.path.exists(aux_xml):
            try:
                os.remove(aux_xml)
            except Exception:
                pass
                
        return True
    except Exception as e:
        logging.error(f"Error en gdal.Warp a {dest_path}: {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise

def run_build_vrt(src_paths, dest_vrt_path, options_dict=None, **kwargs):
    """
    Wrapper seguro alrededor de gdal.BuildVRT.
    Siempre sobrescribe si el archivo VRT existe.
    """
    try:
        if os.path.exists(dest_vrt_path):
            os.remove(dest_vrt_path)
            
        os.makedirs(os.path.dirname(dest_vrt_path), exist_ok=True)
        
        if options_dict:
            opts = gdal.BuildVRTOptions(**options_dict)
        else:
            opts = gdal.BuildVRTOptions(**kwargs)
            
        vrt = gdal.BuildVRT(dest_vrt_path, src_paths, options=opts)
        vrt = None  # Cerrar dataset VRT
        return True
    except Exception as e:
        logging.error(f"Error en gdal.BuildVRT en {dest_vrt_path}: {e}")
        if os.path.exists(dest_vrt_path):
            try:
                os.remove(dest_vrt_path)
            except Exception:
                pass
        raise

def polygonize_raster(raster_path, vector_path, driver_name="GPKG", layer_name="polygons"):
    """
    Convierte una máscara raster en un archivo vectorial utilizando gdal.Polygonize.
    Soporta GPKG y ESRI Shapefile de forma segura y multiplataforma.
    """
    try:
        if os.path.exists(vector_path):
            # Para GPKG o Shapefile, usamos OGR para borrar
            drv = ogr.GetDriverByName(driver_name)
            if drv:
                drv.DeleteDataSource(vector_path)
            else:
                os.remove(vector_path)
        
        os.makedirs(os.path.dirname(vector_path), exist_ok=True)
        
        # Abrir raster
        src_ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
        if not src_ds:
            raise RuntimeError(f"No se pudo abrir el raster {raster_path} para vectorizar.")
            
        src_band = src_ds.GetRasterBand(1)
        
        # Obtener SRS
        proj_wkt = src_ds.GetProjection()
        srs = osr.SpatialReference()
        if proj_wkt:
            srs.ImportFromWkt(proj_wkt)
        else:
            srs = None
            
        # Crear dataset vectorial de salida
        drv = ogr.GetDriverByName(driver_name)
        if not drv:
            raise RuntimeError(f"Driver OGR '{driver_name}' no disponible.")
            
        out_ds = drv.CreateDataSource(vector_path)
        if not out_ds:
            raise RuntimeError(f"No se pudo crear el archivo vectorial {vector_path}")
            
        out_lyr = out_ds.CreateLayer(layer_name, srs=srs, geom_type=ogr.wkbPolygon)
        
        # Crear campo de atributo
        field_defn = ogr.FieldDefn("value", ogr.OFTInteger)
        out_lyr.CreateField(field_defn)
        field_index = out_lyr.GetLayerDefn().GetFieldIndex("value")
        
        # Usar la banda de máscara para NoData si procede
        mask_band = src_band.GetMaskBand()
        
        # Polygonize
        gdal.Polygonize(src_band, mask_band, out_lyr, field_index, [], callback=None)
        
        # Cerrar todo para forzar la escritura en disco
        out_lyr = None
        out_ds = None
        src_ds = None
        
        # Eliminar aux.xml residual
        aux_xml = vector_path + ".aux.xml"
        if os.path.exists(aux_xml):
            try:
                os.remove(aux_xml)
            except Exception:
                pass
                
        logging.info(f"Vectorización completada con éxito en: {vector_path}")
        return True
    except Exception as e:
        logging.error(f"Error al vectorizar {raster_path} en {vector_path}: {e}")
        if os.path.exists(vector_path):
            try:
                os.remove(vector_path)
            except Exception:
                pass
        raise
