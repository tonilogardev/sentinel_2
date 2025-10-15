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


def S2_MaskGeneration_L1C(dir_in, nom_escena, limits, Soft_GeoprocesGDAL):
    try:
        dir_mask=os.path.join(dir_in,"MASK")
##        print ("\n dir_mask : "+dir_mask)
        os.mkdir(dir_mask)

##        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')
        
        mosaic_T31_list = os.path.join(dir_mask,nom_escena+"_T31_mask.txt")
        mosaic_T31_vrt = os.path.join(dir_mask,nom_escena+"_T31_mask.vrt")
        mosaic_T30_list = os.path.join(dir_mask,nom_escena+"_T30_mask.txt")
        mosaic_T30_vrt = os.path.join(dir_mask,nom_escena+"_T30_mask.vrt")
        mosaic_T30_reprojected_vrt = os.path.join(dir_mask,nom_escena+"_T30_reprojected_mask.vrt")
        mosaic_T30_reprojected_tif = os.path.join(dir_mask,nom_escena+"_T30_reprojected_mask.tif")
        mosaic_mask_tif = os.path.join(dir_mask,nom_escena+"_mask.tif")
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_footprint_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_footprint.bat")
        gdalbuildvrt_exe=os.path.join(Soft_GeoprocesGDAL,"gdalbuildvrt.bat")
        gdalwarp_exe=os.path.join(Soft_GeoprocesGDAL,"gdalwarp.bat")
        
        for nom_dir in granule_list:
    
            granule_name = os.listdir(dir_in+"\\"+nom_dir+"\\GRANULE")[0]
            bands_jpg = os.listdir(dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA")
     
            file_root = bands_jpg[0][0:22]
            granule_ID = granule_name[4:10]+granule_name[18:34]

            file_in   = dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+file_root+"_B04.jp2"
            file_out_1b  = dir_mask+"\\"+granule_ID+"_B04_1b.tif"
            file_out_1b_tfw  = dir_mask+"\\"+granule_ID+"_B04_1b.tfw"
            
            gdal_params=" -of Gtiff -ot Byte -a_nodata 0 -co NBITS=1 -co PHOTOMETRIC=MINISBLACK -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO -co TFW=YES "
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
            
            gdal_params=" -of Gtiff -ot Byte -a_nodata 0 -co NBITS=1 -co PHOTOMETRIC=MINISBLACK -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO -a_srs EPSG:"+epsg+" "
            command = gdal_translate_exe + gdal_params + file_out_eroded_full+" "+file_dest_full
            os.system(command)
            if (os.path.isfile(file_dest_full+".aux.xml")):
               os.remove(file_dest_full+".aux.xml")

            os.remove(file_out_eroded_full)
            os.remove(file_out_eroded_full_tfw)

##            file_gpkg_full = dir_mask+"\\"+granule_ID+"_mask.gpkg"
            
##            gdal_params = " -srcnodata 0 -t_srs EPSG:"+epsg+" "
##            command = gdal_footprint_exe + gdal_params + file_dest_full+" "+file_gpkg_full
##            os.system(command)
##            if (os.path.isfile(file_gpkg_full+".aux.xml")):
##               os.remove(file_gpkg_full+".aux.xml")
            
            index=granule_ID.find("T31")
            if(index!=-1):
               os.system("echo "+file_dest_full+" >>"+mosaic_T31_list)
            else:
               os.system("echo "+file_dest_full+" >>"+mosaic_T30_list)
               
        if (os.path.isfile(mosaic_T30_list)):
           
           options=" -tr 10 10 -r bilinear -srcnodata 0 -vrtnodata 0 -tap "+mosaic_T30_vrt+" -input_file_list "+mosaic_T30_list
           os.system(gdalbuildvrt_exe+options)

           options=" -t_srs EPSG:32631 -srcnodata 0 -dstnodata 0 -r cubic -tap -tr 10 10 "+mosaic_T30_vrt+" "+mosaic_T30_reprojected_vrt
           os.system(gdalwarp_exe+options)
           
           options=" -of Gtiff -ot Byte -a_nodata 0 -co NBITS=1 -co PHOTOMETRIC=MINISBLACK -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO "
           os.system(gdal_translate_exe+options+mosaic_T30_reprojected_vrt+" "+mosaic_T30_reprojected_tif)
           
           os.system("echo "+mosaic_T30_reprojected_tif+" >>"+mosaic_T31_list)
 
##        options=" -tr 10 10 -te "+limits+" -r bilinear -srcnodata 0 -vrtnodata 0 -tap "+mosaic_T31_vrt+" -input_file_list "+mosaic_T31_list
        options= " -te "+limits+"-r nearest -srcnodata 0 -vrtnodata 0 "+mosaic_T31_vrt+" -input_file_list "+mosaic_T31_list
        os.system(gdalbuildvrt_exe+options)
           
        options=" -of Gtiff -ot Byte -a_nodata 0 -co NBITS=1 -co PHOTOMETRIC=MINISBLACK -co TILED=YES -co BLOCKXSIZE=1024 -co BLOCKYSIZE=1024 -co INTERLEAVE=BAND -co BIGTIFF=NO "
        os.system(gdal_translate_exe+options+mosaic_T31_vrt+" "+mosaic_mask_tif)
        return 0
    except:
        return 1

    