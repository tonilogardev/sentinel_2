# -*- coding: utf-8 -*-
"""
Created on Thu Jul 25 13:30:03 2024

El parxe s'ha d'aplicar als productes de la baseline 05.11, és a dir, productes a partir del 23 de juliol de 2024.
Quan hi hagi una nova versió sen2cor que admeti aaquests productes es podrà eliminar el parxe

@author: v.pala
"""

import os
import fnmatch
import fileinput


def S2_Parxe1(dir_in):
    
    try:

        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
    
        for nom_dir in granule_list:
    
            os.chdir(nom_dir+r"\GRANULE")
            granule_name = os.listdir(".")[0]
            
            for line in fileinput.input(granule_name+"\\MTD_TL.xml", inplace=True):
                if fileinput.filelineno()==2:
                    line = r'<n1:Level-1C_Tile_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Tile_Metadata.xsd">'+"\n"
                print('{}'.format(line), end='')   

            os.chdir(dir_in)
            os.chdir(nom_dir+r"\DATASTRIP")
            granule_name = os.listdir(".")[0]
            
            for line in fileinput.input(granule_name+"\\MTD_DS.xml", inplace=True):
                if fileinput.filelineno()==2:
                    line = r'<n1:Level-1C_DataStrip_ID xmlns:n1="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-14.sentinel2.eo.esa.int/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.02.00/scripts/../../../schemas/14.08.02/PSD/S2_PDI_Level-1C_Datastrip_Metadata.xsd">'+"\n"
                print('{}'.format(line), end='')   
            os.chdir(dir_in)


        return 0
    except:
        return 1



def S2_Parxe2(dir_in):
    
    try:

        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L2A*.SAFE')   
    
        for nom_dir in granule_list:
    
            os.chdir(nom_dir+r"\GRANULE")
            granule_name = os.listdir(".")[0]
            
            for line in fileinput.input(granule_name+"\\MTD_TL.xml", inplace=True):
                if fileinput.filelineno()==2:
                    line = r'<n1:Level-2A_Tile_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_TILE_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Tile_Metadata.xsd">'+"\n"
                print('{}'.format(line), end='')   

            os.chdir(dir_in)
            os.chdir(nom_dir+r"\DATASTRIP")
            granule_name = os.listdir(".")[0]
            
            for line in fileinput.input(granule_name+"\\MTD_DS.xml", inplace=True):
                if fileinput.filelineno()==2:
                    line = r'<n1:Level-2A_DataStrip_ID xmlns:n1="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://psd-15.sentinel2.eo.esa.int/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd /dpc/app/s2ipf/FORMAT_METADATA_DS_L1C/06.03.00/scripts/../../../schemas/15.00.00/PSD/S2_PDI_Level-2A_Datastrip_Metadata.xsd">'+"\n"
                print('{}'.format(line), end='')   
            os.chdir(dir_in)


        return 0
    except:
        return 1


 
#dir_in = r"I:\Disc_I\S2_Proves\Baseline_5.11\PROVA_PARXE"

#S2_Parxe1(dir_in)
#S2_Parxe2(dir_in)
