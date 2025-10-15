
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 16:02:21 2022

@author: v.pala
"""

import os


def search_offset(product_type, rootPath, iband):

#    NOM_bandes = ['B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12']
    llista_bandes_metadades = ['1','2','3','4','5','6','7','8','11','12']

    if (product_type=="L1C"):
        text2search = '<RADIO_ADD_OFFSET band_id='
    elif (product_type=="L2A"):
        text2search = '<BOA_ADD_OFFSET band_id='
    else:
        return -9999
    
    tmp_dir = rootPath+"/DATASTRIP"
    
    subdir=os.listdir(tmp_dir)[0]
            
    metadata_file = open(tmp_dir+"/"+subdir+"/MTD_DS.xml","r")
    
    found = False
    
    for line in metadata_file:
        if (text2search in line):
            if (line.find('_id="'+llista_bandes_metadades[iband-1])!=-1):
                found = True
                break
    metadata_file.close()
    
    if (found):
        pos_ini = line.find('>')
        pos_fin = line.find('</')
        return line[pos_ini+1:pos_fin]
    else:
        return -9999
        


def search_gain(product_type, rootPath):

    if (product_type=="L1C"):
        text2search = '<QUANTIFICATION_VALUE'
    elif (product_type=="L2A"):
        text2search = 'BOA_QUANTIFICATION_VALUE'
    else:
        return -9999

    tmp_dir = rootPath+"/DATASTRIP"
    
    subdir=os.listdir(tmp_dir)[0]
            
    metadata_file = open(tmp_dir+"/"+subdir+"/MTD_DS.xml","r")
    
    found = False
    
    for line in metadata_file:
        if (text2search in line):
            found = True
            break

    metadata_file.close()

    if (found):
        pos_ini = line.find('>')
        pos_fin = line.find('</')
        return line[pos_ini+1:pos_fin]
    else:
        return -9999
