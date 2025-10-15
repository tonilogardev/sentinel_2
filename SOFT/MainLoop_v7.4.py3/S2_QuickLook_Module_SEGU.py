# -*- coding: utf-8 -*-
"""
Created on Thu Jun 28 13:24:42 2018

@author: v.pala
"""

import os
import sys

def QuickLook_Generation(dir_in, dir_out, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL):

    try:
        os.chdir(dir_in)
        nom_in=os.path.join(dir_in,nom_escena+".btf")
 ##       nom_in = nom_escena+".btf"
    
        nom_out_tmp="S2_RGB_8b_"+nom_escena[-8:]+nom_escena[-14:-9]+".tif"
        nom_out=os.path.join(dir_out,nom_out_tmp)
##        nom_out = "S2_RGB_8b_"+nom_escena[-8:]+nom_escena[-14:-9]+".tif"
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_params=" -ot byte -a_nodata 0 -b 3 -b 2 -b 1 -co COMPRESS=JPEG -co QUALITY=75 -of COG -scale 0 1 0 0.1 -co BIGTIFF=YES -co OVERVIEWS=IGNORE_EXISTING "
        command = gdal_translate_exe + gdal_params + nom_in + " " + nom_out
##        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b8 -wc3,2,1 -dtuint -ca0 -cf0.1 -svnull0 -qf75 -o0 "+nom_in+" "+dir_out+"\\"+nom_out+"\n")
        os.system(command)
        try:
##            os.remove(dir_out+"\\"+nom_out+".xml")
            os.remove(nom_out+".aux.xml")
        except:
##            print(dir_out+"\\"+nom_out+".xml  cannot be removed!\n")
            print(nom_out+".aux.xml  cannot be removed!\n")
            sys.stdout.flush()
    
        nom_out_tmp = "S2_RGBI_16b_"+nom_escena[-8:]+nom_escena[-14:-9]+".btf"
        nom_out=os.path.join(dir_out,nom_out_tmp)
        gdal_params=" -ot UInt16 -a_nodata 0 -b 3 -b 2 -b 1 -b 7 -co COMPRESS=LZW -co PREDICTOR=STANDARD -of COG -co BIGTIFF=YES -co OVERVIEWS=IGNORE_EXISTING "
        command = gdal_translate_exe + gdal_params + nom_in + " " + nom_out
##        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b16 -wc3,2,1,7 -svnull0 -LZW -o0 "+nom_in+" "+dir_out+"\\"+nom_out+"\n")
        os.system(command)

        try:
##            os.remove(dir_out+"\\"+nom_out+".xml")
            if (os.path.isfile(nom_out+".aux.xml")):      
               os.remove(nom_out+".aux.xml")
        except:
##            print(dir_out+"\\"+nom_out+".xml  cannot be removed!\n")
            print(nom_out+".aux.xml  cannot be removed!\n")
            sys.stdout.flush()
               
        sys.stdout.flush()
        return 0
    except:
        return 1