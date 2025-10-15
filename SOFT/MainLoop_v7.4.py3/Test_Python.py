# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 14:26:02 2018

@author: v.pala
"""

#
# ****  A la versió 4.0 es va afegir el procés L2A grànul a grànul, evitant aixóGRANULES LIST
# ****  el problema que es apareix amb la versió 2.5.5 de sen2cor que no funciona
# ****  bé quan la imatge té dos "datatake" (dos segments).
# ****
# ****  A la versió 4.1, a més, també es fa el procés grànul a grànul per la generació
# ****  del producte L1C de 4 bandes i la generació de MASK, enlloc d'atacar el 
# ****  producte combinat que es generava abans i que tenia tots els granuls al
# ****  subfolder GRANULE, amb el seu XML modificat (aquest procés ja no és necessari).
#
# ****  A la versió 4.2 es fa un dilation absns dels 50 erosion per tal d'evitar el problema
# ****  d'alguns pixels amb no-data dins la imatge L1C.
# ****  També s'ha modificat el codi per generar els dos ZIPs que cont tots els productes
# ****  L1C i L2A per tal de que no desapareixi el subfolder buït AUX_DATA.
# ****  També es passa a crida la versió 2.8.0 de sen2cor.
#
# **** A la versió 4.3 s'automatitza la descàrrega de productes OFFLINE (dins el modul download)
# **** A la versió 4.4 s'utilitza sen2cor_2.9.0 que corregeix un problema de la versió 2.8 per les nous tile refinats L1C
# **** A la versió 4.4 també es corregeix el problema per de fer UNZIP aparegut a la imatge 2021-04-20
# **** A la versió 4.5 posem totes les dades de customització en un fitxer JSON. Es generalitza l'ús de qualsevol zona UTM
# **** A la versió 5.0 el programa s'adapta a la Baseline 4.00, que requereix sen2cor 2.10 i que implementa gain=10000 i offset=-1000.
# **** A la versió 5.1 el programa s'adapta a la Baseline 4.00, que requereix sen2cor 2.10 i llegeix el gain i offset de les metadades.
# **** A la versió 5.2 s'implementa la generació de COG TIF (amb programari GDAL) per la imatge de 10 bandes i el SCL.
# **** A la versió 6.0 s'adapta el programari a la nova api de dataspace.copernicus
# **** A la versió 6.1 s'implementa un mecanisme per esperar quan es detecta que manca un datastrip
# **** A la versió 6.2 s'elimina la possibilitat d'enviar un email que havia deixat d'estar operativa per canvis a gmail i
# ****                 s'introdueix el JSON com a paràmetre quan s'executa el programa
# **** A la versió 6.3 s'eliminen els arxius dins la carpeta ZIP (excepte granulelist.txt)
# **** A la versió 7.0 s'inclou la generació de segments NDVI a partir de la correcció atmosfèrica amb topografia descrita amb DEM-CAT
# **** A la versió 7.1 hi ha la opció a descarregar només la darrera BASELINE per els productes que estan en diferents BASELINES
# **** A la versió 7.2 en el cas de descarregar només la darrera baseline, s'eliminen els possibles duplicats (mateixa foorprint) (ex: T31TDG de 20220820; two-datatake 20220709, two baseline 20180801)
# ****                 en aquesta versió també es genera la imatge L2A de 10 bandes amb la correcció topogràfica a partir de la qual es calcula el NDVI
# ****                 en aquesta versió també s'implementa la verificació amb checksum de la correcte descàrrega dels arxius. Els arxius antic no tenen checksum.
# **** A la versió 7.3 s'activa en la segona etapa la opció de generar un .RF L1C amb les 4 bandes de 10 metres.
 
import time
import subprocess
from datetime import datetime
from datetime import timedelta
import urllib
import urllib.request
import urllib.parse
import os
import openpyxl
import socket
import zipfile
import sys
import shutil
import fnmatch
import json
import S2_Parxes_BL_05_11 # PARXE
import os.path


import S2_Segment_Granules_Download_Modules as S2_Download
import S2_MaskGeneration_L1C_Module_TestPere as S2_Mask
import S2_Segment_Process_L1C_4B_Module as  S2_L1C_4B
import S2_Segment_Process_L2A_10B_Module_TestPere_v2 as S2_L2A_10B
import S2_Segment_Process_L2A_SCL_Module as S2_L2A_SCL
import S2_QuickLook_Module as S2_QL
import S2_Segment_Process_NDVI as S2_NDVI
import S2_utis

#----------------------------------------------------------------------------------------------------------
# MAIN
#----------------------------------------------------------------------------------------------------------

# Cal entrar el JSON com a paràmetre en l'execució. Per exemple es següent: 
#json_name = r'I:\Disc_I\S2_CAT_NDVI_Download\SOFT\MainLoop_v7.1.py3\S2_Catalunya.json'


dir_in=r"I:\Disc_I\S2_CAT_NDVI_Download\2025-05-16_R051"
##dir_in=r"I:\Disc_I\S2_CAT_NDVI_Download\2024-10-18_R008"
Path_L2A_ORTHO="\\\\ortofoto1\\Public_D\\Pere_Test\\SOFT\\####Sen2Cor-02.11.00-win64\\L2A_Process_NO-DEM_mod.bat"
QuickLook_dir=r"Z:\Sentinel-2"
Soft_Geoproces="\\\\icgc.local\\aplicacions\\produccio\\DFApplications"
Soft_GeoprocesGDAL="\\\\icgc.local\\aplicacions\\produccio\\DFApplications\\gdal381_apps"
os.chdir(dir_in)
nom_escena="S2A_SCL_R051_20250516"
limits='"240000 467500 4780000 4480000"'
UTM_Zone_to_reproject="T31"
S2_L2A_SCL.S2_Segment_Process_L2A_SCL(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)
## resultat_QuickLook_Generation = S2_QL.QuickLook_Generation(dir_in, QuickLook_dir, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL)         
##resultat_mask = S2_Mask.S2_MaskGeneration_L1C(dir_in, nom_escena, limits, Soft_GeoprocesGDAL)
sys.exit()
