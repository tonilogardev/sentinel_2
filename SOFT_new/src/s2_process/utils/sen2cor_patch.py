# -*- coding: utf-8 -*-
import os
import glob
import logging

def _replace_line_in_file(filepath, line_num, new_line):
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        if len(lines) >= line_num:
            # Check if it's already patched to avoid double patching
            if new_line.strip() not in lines[line_num - 1]:
                lines[line_num - 1] = new_line
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                return True
    except Exception as e:
        logging.warning(f"No se pudo parchear {filepath}: {e}")
    return False

def apply_patch_l1c(segment_dir):
    """
    Parchea los XML MTD_TL y MTD_DS de los L1C descargados para que Sen2Cor
    no colapse con el schema moderno de la Baseline 05.11 (posterior a julio 2024).
    """
    safe_dirs = glob.glob(os.path.join(segment_dir, "*L1C*.SAFE"))
    patched_count = 0
    for s_dir in safe_dirs:
        # Patch GRANULE MTD_TL.xml
        granule_base = os.path.join(s_dir, "GRANULE")
        if os.path.isdir(granule_base):
            for g_name in os.listdir(granule_base):
                mtd_tl_path = os.path.join(granule_base, g_name, "MTD_TL.xml")
                if os.path.isfile(mtd_tl_path):
                    if _replace_line_in_file(
                        mtd_tl_path, 
                        line_num=2, 
                        new_line='<n1:Level-1C_Tile_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd">\n'
                    ):
                        patched_count += 1
                        
        # Patch DATASTRIP MTD_DS.xml
        ds_base = os.path.join(s_dir, "DATASTRIP")
        if os.path.isdir(ds_base):
            for ds_name in os.listdir(ds_base):
                mtd_ds_path = os.path.join(ds_base, ds_name, "MTD_DS.xml")
                if os.path.isfile(mtd_ds_path):
                    _replace_line_in_file(
                        mtd_ds_path, 
                        line_num=2, 
                        new_line='<n1:Level-1C_DataStrip_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd">\n'
                    )
    if patched_count > 0:
        logging.info(f"Parche Baseline 05.11 aplicado a {patched_count} gránulos L1C.")

def apply_patch_l2a(segment_dir):
    """
    Parchea los XML MTD_TL y MTD_DS de los L2A generados.
    """
    safe_dirs = glob.glob(os.path.join(segment_dir, "*L2A*.SAFE"))
    patched_count = 0
    for s_dir in safe_dirs:
        # Patch GRANULE MTD_TL.xml
        granule_base = os.path.join(s_dir, "GRANULE")
        if os.path.isdir(granule_base):
            for g_name in os.listdir(granule_base):
                mtd_tl_path = os.path.join(granule_base, g_name, "MTD_TL.xml")
                if os.path.isfile(mtd_tl_path):
                    if _replace_line_in_file(
                        mtd_tl_path, 
                        line_num=2, 
                        new_line='<n1:Level-2A_Tile_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd">\n'
                    ):
                        patched_count += 1
                        
        # Patch DATASTRIP MTD_DS.xml
        ds_base = os.path.join(s_dir, "DATASTRIP")
        if os.path.isdir(ds_base):
            for ds_name in os.listdir(ds_base):
                mtd_ds_path = os.path.join(ds_base, ds_name, "MTD_DS.xml")
                if os.path.isfile(mtd_ds_path):
                    _replace_line_in_file(
                        mtd_ds_path, 
                        line_num=2, 
                        new_line='<n1:Level-2A_DataStrip_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd">\n'
                    )
    if patched_count > 0:
        logging.info(f"Parche Baseline 05.11 aplicado a {patched_count} gránulos L2A.")
