# -*- coding: utf-8 -*-
"""
Módulo wrapper para la llamada robusta al binario Sen2Cor (L2A_Process),
aplicación del parche de metadatos XML para Baseline 05.11+ y control del subprocess.
"""

import os
import re
import fnmatch
import logging
import subprocess
import time

def apply_l1c_xml_patch(granule_safe_path):
    """
    Parche L1C (Parxe1): Modifica MTD_TL.xml y MTD_DS.xml en gránulos L1C 
    para forzar compatibilidad con PSD-14 y evitar que Sen2Cor colapse.
    """
    logging.info(f"Aplicando parche XML L1C para Baseline 05.11+ en {granule_safe_path}")
    
    # 1. Parche MTD_TL.xml
    granule_dir = os.path.join(granule_safe_path, "GRANULE")
    if os.path.isdir(granule_dir):
        subdirs = os.listdir(granule_dir)
        if subdirs:
            mtd_tl_path = os.path.join(granule_dir, subdirs[0], "MTD_TL.xml")
            if os.path.isfile(mtd_tl_path):
                _modify_xml_line2(
                    mtd_tl_path,
                    r'<n1:Level-1C_Tile_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd">'
                )
                
    # 2. Parche MTD_DS.xml
    datastrip_dir = os.path.join(granule_safe_path, "DATASTRIP")
    if os.path.isdir(datastrip_dir):
        subdirs = os.listdir(datastrip_dir)
        if subdirs:
            mtd_ds_path = os.path.join(datastrip_dir, subdirs[0], "MTD_DS.xml")
            if os.path.isfile(mtd_ds_path):
                _modify_xml_line2(
                    mtd_ds_path,
                    r'<n1:Level-1C_DataStrip_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd">'
                )

def apply_l2a_xml_patch(granule_safe_path):
    """
    Parche L2A (Parxe2): Modifica MTD_TL.xml y MTD_DS.xml en gránulos L2A
    para forzar compatibilidad con PSD-15.
    """
    logging.info(f"Aplicando parche XML L2A para Baseline 05.11+ en {granule_safe_path}")
    
    # 1. Parche MTD_TL.xml
    granule_dir = os.path.join(granule_safe_path, "GRANULE")
    if os.path.isdir(granule_dir):
        subdirs = os.listdir(granule_dir)
        if subdirs:
            mtd_tl_path = os.path.join(granule_dir, subdirs[0], "MTD_TL.xml")
            if os.path.isfile(mtd_tl_path):
                _modify_xml_line2(
                    mtd_tl_path,
                    r'<n1:Level-2A_Tile_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd">'
                )
                
    # 2. Parche MTD_DS.xml
    datastrip_dir = os.path.join(granule_safe_path, "DATASTRIP")
    if os.path.isdir(datastrip_dir):
        subdirs = os.listdir(datastrip_dir)
        if subdirs:
            mtd_ds_path = os.path.join(datastrip_dir, subdirs[0], "MTD_DS.xml")
            if os.path.isfile(mtd_ds_path):
                _modify_xml_line2(
                    mtd_ds_path,
                    r'<n1:Level-2A_DataStrip_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd">'
                )

def _modify_xml_line2(filepath, replacement_content):
    """Auxiliar para reemplazar exactamente la línea 2 de un archivo de metadatos."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if len(lines) >= 2:
            lines[1] = replacement_content + "\n"
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception as e:
        logging.error(f"Error al escribir parche en metadato {filepath}: {e}")
        raise

def resolve_sen2cor_bin(configured_bin, variant="NO-DEM"):
    """
    Resuelve la ruta al ejecutable de Sen2Cor de forma inteligente.
    Si estamos en Windows y la ruta configurada apunta a Linux (/opt/),
    busca automáticamente los archivos .bat locales en la cintoteca de SOFT_new/.
    """
    if os.name == 'nt':
        # Si la ruta es de Linux o no existe localmente
        if "/opt/" in configured_bin or not os.path.exists(configured_bin):
            # Buscar en SOFT_new/
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            soft_sen2cor = os.path.join(base_dir, "Sen2Cor-02.12.03-win64")
            
            # Nombre de variante esperada: 'NO-DEM' o 'DEM-CAT'
            clean_variant = "NO-DEM" if "NO_DEM" in variant.upper() or "NO-DEM" in variant.upper() else "DEM-CAT"
            bat_name = f"L2A_Process_{clean_variant}.bat"
            local_bat = os.path.join(soft_sen2cor, bat_name)
            if os.path.isfile(local_bat):
                logging.info(f"Resolución automática de Sen2Cor para Windows: detectado {local_bat}")
                return local_bat
                
            # Fallback 2.11 (opcional, por si también se copia)
            soft_sen2cor_211 = os.path.join(base_dir, "Sen2Cor-02.11.00-win64")
            local_bat_211 = os.path.join(soft_sen2cor_211, bat_name)
            if os.path.isfile(local_bat_211):
                logging.info(f"Resolución automática de Sen2Cor para Windows (v2.11): detectado {local_bat_211}")
                return local_bat_211
                
    return configured_bin

def run_sen2cor(sen2cor_bin, granule_safe_path, gipp_path=None, resolution=10, variant="NO-DEM", progress_callback=None):
    """
    Ejecuta Sen2Cor sobre el gránulo L1C .SAFE especificado.
    Aplica automáticamente el parche XML L1C antes de la ejecución y el parche L2A después.
    """
    # 1. Resolver binario adaptándolo a Windows de forma inteligente
    resolved_bin = resolve_sen2cor_bin(sen2cor_bin, variant=variant)
    
    logging.info(f"Preparando ejecución de Sen2Cor para gránulo: {granule_safe_path}")
    
    # 2. Aplicar parche XML L1C previo
    try:
        apply_l1c_xml_patch(granule_safe_path)
    except Exception as e:
        logging.error(f"No se pudo aplicar el parche XML L1C previo a Sen2Cor: {e}")
        
    # 3. Construir comando Sen2Cor
    cmd = [resolved_bin, "--resolution", str(resolution)]
    if gipp_path and os.path.isfile(gipp_path):
        logging.info(f"Usando archivo GIPP personalizado: {gipp_path}")
        cmd.extend(["--GIP_L2A", gipp_path])
    else:
        logging.warning("No se especificó GIPP o el archivo no existe. Se usará la configuración por defecto de Sen2Cor.")
        
    cmd.append(granule_safe_path)
    
    logging.info(f"Comando a ejecutar: {' '.join(cmd)}")
    
    # 4. Lanzar subprocess
    start_time = time.time()
    try:
        # En Windows, para ejecutar .bat de forma segura se puede usar shell=True
        use_shell = os.name == 'nt' and resolved_bin.endswith('.bat')
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=use_shell
        )
        
        # Expresion regular para atrapar el progreso
        prog_regex = re.compile(r"Progress\[%\]:\s+([\d\.]+)")
        
        # Volcar output al logger en tiempo real
        for line in process.stdout:
            line_str = line.strip()
            if line_str:
                logging.info(f"[Sen2Cor] {line_str}")
                if progress_callback:
                    m = prog_regex.search(line_str)
                    if m:
                        try:
                            progress_callback(float(m.group(1)))
                        except ValueError:
                            pass
                
        process.wait()
        elapsed = time.time() - start_time
        
        if process.returncode != 0:
            logging.error(f"Sen2Cor finalizó con código de error {process.returncode} en {elapsed:.1f} segundos.")
            return False
            
        logging.info(f"Sen2Cor completó el procesamiento L2A con éxito en {elapsed:.1f} segundos.")
        
        # 5. Localizar el gránulo L2A generado en el mismo segmento y aplicar el parche L2A post-procesamiento
        segment_dir = os.path.dirname(granule_safe_path)
        l1c_name = os.path.basename(granule_safe_path)
        
        l2a_pattern = l1c_name.replace("MSIL1C", "MSIL2A")
        
        # Buscar gránulos L2A en el segmento
        l2a_candidates = fnmatch.filter(os.listdir(segment_dir), l2a_pattern)
        if l2a_candidates:
            l2a_safe_path = os.path.join(segment_dir, l2a_candidates[0])
            logging.info(f"Gránulo L2A generado localizado en: {l2a_safe_path}")
            apply_l2a_xml_patch(l2a_safe_path)
        else:
            logging.warning("No se pudo localizar el gránulo L2A generado en disco para aplicarle el parche L2A.")
            
        return True
    except Exception as e:
        logging.error(f"Error crítico al ejecutar Sen2Cor por subprocess: {e}")
        return False
