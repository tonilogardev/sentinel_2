# -*- coding: utf-8 -*-
"""
Módulo para leer y parsear los valores de gain (quantification) y offset radiométrico
del archivo de metadatos MTD_DS.xml dentro del directorio del gránulo.
"""

import os
import xml.etree.ElementTree as ET
import logging

BAND_NAME_TO_ID = {
    'B01': '0', 'B02': '1', 'B03': '2', 'B04': '3',
    'B05': '4', 'B06': '5', 'B07': '6', 'B08': '7',
    'B8A': '8', 'B09': '9', 'B10': '10', 'B11': '11', 'B12': '12'
}

def _get_mtd_ds_filepath(granule_safe_path):
    """
    Localiza de forma robusta el archivo MTD_DS.xml dentro de la carpeta DATASTRIP del gránulo.
    """
    datastrip_dir = os.path.join(granule_safe_path, "DATASTRIP")
    if not os.path.isdir(datastrip_dir):
        return None
        
    subdirs = os.listdir(datastrip_dir)
    if not subdirs:
        return None
        
    metadata_path = os.path.join(datastrip_dir, subdirs[0], "MTD_DS.xml")
    if os.path.isfile(metadata_path):
        return metadata_path
        
    return None

def get_gain(product_type, granule_safe_path):
    """
    Retorna el valor de cuantización (gain) del metadato del producto.
    product_type: 'L1C' o 'L2A'
    """
    metadata_file = _get_mtd_ds_filepath(granule_safe_path)
    if not metadata_file:
        logging.warning(f"No se encontró MTD_DS.xml en {granule_safe_path}. Se usará gain por defecto 10000.")
        return 10000.0

    tag_to_search = "QUANTIFICATION_VALUE" if product_type.upper() == "L1C" else "BOA_QUANTIFICATION_VALUE"
    
    try:
        tree = ET.parse(metadata_file)
        root = tree.getroot()
        
        # Buscar el tag en el XML de forma recursiva
        for elem in root.iter():
            if tag_to_search in elem.tag:
                val = float(elem.text.strip())
                return val
                
        logging.warning(f"No se encontró la etiqueta <{tag_to_search}> en {metadata_file}. Se asume gain = 10000.")
        return 10000.0
    except Exception as e:
        logging.error(f"Error al parsear el gain en {metadata_file}: {e}")
        return 10000.0

def get_offset(product_type, granule_safe_path, band_name_or_id):
    """
    Retorna el offset radiométrico de una banda espectral específica.
    band_name_or_id: puede ser el nombre de la banda (ej: 'B02') o el band_id de la ESA (ej: '1')
    """
    metadata_file = _get_mtd_ds_filepath(granule_safe_path)
    if not metadata_file:
        logging.warning(f"No se encontró MTD_DS.xml en {granule_safe_path}. Se usará offset por defecto 0.")
        return 0.0

    # Obtener el ID de la banda de la ESA
    band_id = BAND_NAME_TO_ID.get(band_name_or_id, str(band_name_or_id))
    tag_to_search = "RADIO_ADD_OFFSET" if product_type.upper() == "L1C" else "BOA_ADD_OFFSET"
    
    try:
        tree = ET.parse(metadata_file)
        root = tree.getroot()
        
        for elem in root.iter():
            if tag_to_search in elem.tag:
                if elem.attrib.get("band_id") == band_id:
                    return float(elem.text.strip())
                    
        # Búsqueda fallback heredada si no encuentra por band_id exacto (ej. si el XML es antiguo o modificado)
        logging.warning(f"No se encontró offset para band_id={band_id} en {metadata_file}. Se asume offset = 0.")
        return 0.0
    except Exception as e:
        logging.error(f"Error al parsear el offset de banda {band_name_or_id} en {metadata_file}: {e}")
        return 0.0
