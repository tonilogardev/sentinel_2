# -*- coding: utf-8 -*-
"""
Created on Tue Apr 16 17:04:06 2024

@author: v.pala
"""

import os
        


def tiff2cog(Soft_GeoprocesGDAL, name_file_in, name_file_out):

    try:
   
        os.environ['GDAL_DATA'] = Soft_GeoprocesGDAL+r"\gdal-data"
        os.environ['PROJ_LIB']  = Soft_GeoprocesGDAL+r"\proj7\share"      
        os.system("echo "+name_file_in+" > input_list.txt\n")
        os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt  -input_file_list input_list.txt  out.vrt\n")
        os.system(Soft_GeoprocesGDAL+"\gdal_translate -of cog out.vrt -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES "+name_file_out+"\n")
        os.remove("input_list.txt")
        os.remove("out.vrt")       
        return 0
    except:
        return 1




Soft_GeoprocesGDAL = "//icgc.local/aplicacions/produccio/dfapplications/gdal321_apps"
name_file_in = input("Path complert de l'arxiu d'entrada: ")
name_file_out = input("Path complert de l'arxiu cog de sortida: ")

tiff2cog(Soft_GeoprocesGDAL, name_file_in, name_file_out)
    