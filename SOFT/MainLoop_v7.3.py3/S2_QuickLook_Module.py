# -*- coding: utf-8 -*-
"""
Created on Thu Jun 28 13:24:42 2018

@author: v.pala
"""

import os
import sys

def QuickLook_Generation(dir_in, dir_out, nom_escena, Soft_Geoproces):

    try:
        os.chdir(dir_in)
    
        nom_in = nom_escena+".btf"
    
        nom_out = "S2_RGB_8b_"+nom_escena[-8:]+nom_escena[-14:-9]+".tif"
        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b8 -wc3,2,1 -dtuint -ca0 -cf0.1 -svnull0 -qf75 -o0 "+nom_in+" "+dir_out+nom_out+"\n")
    
        try:
            os.remove(dir_out+nom_out+".xml")
        except:
            print(dir_out+nom_out+".xml  cannot be removed!\n")
            sys.stdout.flush()
    
        nom_out = "S2_RGBI_16b_"+nom_escena[-8:]+nom_escena[-14:-9]+".btf"
        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b16 -wc3,2,1,7 -svnull0 -LZW -o0 "+nom_in+" "+dir_out+nom_out+"\n")
    
        try:
            os.remove(dir_out+nom_out+".xml")
        except:
            print(dir_out+nom_out+".xml  cannot be removed!\n")
            sys.stdout.flush()
               
        sys.stdout.flush()
        return 0
    except:
        return 1