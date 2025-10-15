# -*- coding: utf-8 -*-
"""
Created on Thu Jun 28 13:24:42 2018

@author: v.pala
"""

import os
import sys
import S2_utis

def QuickLook_Generation(dir_in, dir_out, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL):

    try:
        os.chdir(dir_in)
        name_in=os.path.join(dir_in,nom_escena+".btf")
        name_out_tmp="S2_RGB_8b_"+nom_escena[-8:]+nom_escena[-14:-9]+".tif"
        name_out=os.path.join(dir_out,name_out_tmp)
##        if S2_utis.tiff2cog_QL_8b(Soft_GeoprocesGDAL, name_in, name_out)!=0:
##            print("\n\nError generating image QL 8b "+ name_out +" from "+name_in+"!\n")
##        Pere 151024 La versio actual podia genera 0 a la sortida a partir de valor diferents de 0 (NoData) es modifica i de moment es deixa al directori exe_VS2019
##        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b8 -wc3,2,1 -dtuint -ca0 -cf0.1 -svnull0 -qf75 -o0 "+nom_in+" "+nom_out+"\n")
        os.system(Soft_Geoproces+"\ICCImageOperations\exe_VS2019\ICCImageDataTypeChange.exe -b8 -wc3,2,1 -dtuint -ca0 -cf0.1 -svnull0 -qf75 -o0 "+name_in+" "+name_out+"\n")
    
        try:
            os.remove(name_out+".xml")
        except:
            print(name_out+".xml  cannot be removed!\n")
            sys.stdout.flush()

        name_out_tmp = "S2_RGBI_16b_"+nom_escena[-8:]+nom_escena[-14:-9]+".btf"
        name_out=os.path.join(dir_out,name_out_tmp)
        if S2_utis.tiff2cog_QL_16b(Soft_GeoprocesGDAL, name_in, name_out)!=0:
            print("\n\nError generating image QL 16b "+ name_out +" from "+name_in+ "!\n")

        return 0
    except:
        return 1