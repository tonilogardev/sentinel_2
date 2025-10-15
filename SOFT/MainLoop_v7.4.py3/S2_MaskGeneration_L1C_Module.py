# -*- coding: utf-8 -*-
"""
Created on Thu Mar 9 12:23:34 2017

@author: v.pala
"""

import os
import subprocess
import cv2
import numpy as np
import fnmatch
import time
from osgeo import gdal,osr


def S2_MaskGeneration_L1C(dir_in, Soft_GeoprocesGDAL):
    try:
        dir_mask=os.path.join(dir_in,"MASK")
##        print ("\n dir_mask : "+dir_mask)
        os.mkdir(dir_mask)

##        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
    
        for nom_dir in granule_list:
    
            granule_name = os.listdir(dir_in+"\\"+nom_dir+"\\GRANULE")[0]
            bands_jpg = os.listdir(dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA")
     
            file_root = bands_jpg[0][0:22]
            granule_ID = granule_name[4:10]+granule_name[18:34]

            file_in   = dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+file_root+"_B04.jp2"
            file_out_1b  = dir_mask+"\\"+granule_ID+"_B04_1b.tif"
            file_out_1b_tfw  = dir_mask+"\\"+granule_ID+"_B04_1b.tfw"

            gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
            gdal_params=" -of Gtiff -ot Byte -co NBITS=1 -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO -co TFW=YES "
            command = gdal_translate_exe + gdal_params + file_in+" "+file_out_1b
            os.system(command)
            if (os.path.isfile(file_out_1b+".aux.xml")):
               os.remove(file_out_1b+".aux.xml")

            dataset = gdal.Open(file_out_1b, gdal.GA_ReadOnly)
            proj = osr.SpatialReference(wkt=dataset.GetProjection())
            epsg=proj.GetAttrValue('AUTHORITY',1)

            dataset=None
     
            file_orig_1b = dir_mask+"\\"+granule_ID+"_B04_1b.tif" 
       
            file_out_eroded_full = dir_mask+"\\"+granule_ID+"_B04_1b_eroded.tif"
            img = cv2.imread(file_orig_1b,0)
            kernel = np.ones((3,3),np.uint8)
            dilation = cv2.dilate(img,kernel,iterations = 1)            
            erosion_val = 51
            erosion = cv2.erode(dilation, kernel,iterations = erosion_val)
            erosion[0:erosion_val,:]=0
            erosion[-erosion_val:,:]=0
            erosion[:,0:erosion_val]=0
            erosion[:,-erosion_val:]=0
        
            cv2.imwrite(file_out_eroded_full, erosion)
            file_out_eroded_full_tfw = dir_mask+"\\"+granule_ID+"_B04_1b_eroded.tfw"
            os.rename(file_out_1b_tfw,file_out_eroded_full_tfw)
            os.remove(file_orig_1b)
            file_dest_full = dir_mask+"\\"+granule_ID+"_mask.tif"
            
            gdal_params=" -of Gtiff -ot Byte -co NBITS=1 -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO -a_srs EPSG:"+epsg+" "
            command = gdal_translate_exe + gdal_params + file_out_eroded_full+" "+file_dest_full
            os.system(command)
            if (os.path.isfile(file_dest_full+".aux.xml")):
               os.remove(file_dest_full+".aux.xml")

            os.remove(file_out_eroded_full)
            os.remove(file_out_eroded_full_tfw)

            file_gpkg_full = dir_mask+"\\"+granule_ID+"_mask.gpkg"
            gdal_footprint_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_footprint.bat")
            gdal_params = " -srcnodata 0 -t_srs EPSG:"+epsg+" "
            command = gdal_footprint_exe + gdal_params + file_dest_full+" "+file_gpkg_full
            os.system(command)
            if (os.path.isfile(file_gpkg_full+".aux.xml")):
               os.remove(file_gpkg_full+".aux.xml")
            
        return 0
    except:
        return 1

    