# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 09:00:00 2025

Aquest programa per una data donada intenta baixar les imatges trobades S2
per generar mosaic Quicklook de catalunya a partir d'imatges L2A 
@author: p.rios
"""

import time
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
import os.path
import glob
from dataspace_lib import eoData
from os.path import join




#import S2_Segment_Granules_Download_Modules as S2_Download

def unzip_granule(source_file_path, destination_dir, output_folder):
    with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
        zip_ref.extractall(destination_dir)
    return

def S2_Segment_Process_L2A_QL_AND_SCL(dir_in, nom_escena, Soft_Geoproces_GDAL, limits, UTM_Zone_to_reproject):

    filename_rgb=nom_escena.replace("XXX","RGB")
    filename_scl=filename_rgb.replace("RGB","SCL")
    input_TCI_dat=os.path.join(dir_in,"input_TCI.dat")
    input_SCL_dat=os.path.join(dir_in,"input_SCL.dat")
    try:
        if (os.path.isfile(os.path.join(dir_in,filename_rgb+".tif"))):
           print ("\n","Found previous version of "+filename_rgb+".tif"+". Nothing to do")
           return 0
        if (os.path.isfile(os.path.join(dir_in,filename_scl+".tif"))):
           print ("\n","Found previous version of "+filename_scl+".tif"+". Nothing to do")
           return 0
          
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L2A*.SAFE')   
        os.chdir(dir_in)
    
        for nom_dir in granule_list:
    
    #       CONVERTIR UN GRÁNUL EM UN .RF AMB LA UNIÓ DE TOTES LES BANDES
            print ("\n",nom_dir)
            
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_20m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R20m")
            file_root = bands_20m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]
   
            file_in_tci   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R10m\\"+file_root+"_"+"TCI"+"_10m.jp2"
            file_in_scl   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R20m\\"+file_root+"_"+"SCL"+"_20m.jp2"
   #         file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"
            index = granule_name.find('L2A_T31')
            if index==0:
               os.system("echo "+file_in_tci+"  >>  "+input_TCI_dat+" \n")
               os.system("echo "+file_in_scl+"  >>  "+input_SCL_dat+" \n")
            else:
               file_in_tci_f31=os.path.splitext(os.path.split(file_in_tci)[1])[0]+"_F31.vrt"
               file_in_scl_f31=os.path.splitext(os.path.split(file_in_scl)[1])[0]+"_F31.vrt"
               gdal_warp_exe=os.path.join(Soft_Geoproces_GDAL,"gdalwarp.bat")
               gdal_params=" -t_srs EPSG:32631 -srcnodata 0 -dstnodata 0 -r cubic -tap -tr 10 10 "
               command = gdal_warp_exe + gdal_params + file_in_tci+" "+file_in_tci_f31
               os.system(command)
               if (os.path.isfile(file_in_tci_f31+".aux.xml")):
                 os.remove(file_in_tci_f31+".aux.xml")
               os.system("echo "+file_in_tci_f31+"  >>  "+input_TCI_dat+" \n")
               gdal_params=" -t_srs EPSG:32631 -srcnodata 0 -dstnodata 0 -r cubic -tap -tr 20 20 "
               command = gdal_warp_exe + gdal_params + file_in_scl+" "+file_in_scl_f31
               os.system(command)
               if (os.path.isfile(file_in_scl_f31+".aux.xml")):
                 os.remove(file_in_scl_f31+".aux.xml")
               os.system("echo "+file_in_scl_f31+"  >>  "+input_SCL_dat+" \n")
               
        limits_split = limits.split(",")
        limits_gdal_order = limits_split[0]+" "+limits_split[3]+" "+limits_split[1]+" "+limits_split[2]
        gdal_buildvrt_exe=os.path.join(Soft_Geoproces_GDAL,"gdalbuildvrt.bat")
        gdal_params=" -te "+limits_gdal_order+" -input_file_list "
        command = gdal_buildvrt_exe + gdal_params + input_TCI_dat +" "+filename_rgb+".vrt"
        os.system(command)
        if (os.path.isfile(filename_rgb+".vrt"+".aux.xml")):
           os.remove(filename_rgb+".vrt"+".aux.xml")
        command = gdal_buildvrt_exe + gdal_params + input_SCL_dat +" "+filename_scl+".vrt"
        os.system(command)
        if (os.path.isfile(filename_scl+".vrt"+".aux.xml")):
           os.remove(filename_scl+".vrt"+".aux.xml")
               
        gdal_warp_exe=os.path.join(Soft_Geoproces_GDAL,"gdalwarp.bat")
        gdal_params=" -t_srs EPSG:32631 -srcnodata 0 -dstnodata 0 -r near -tap -tr 10 10 "
        command = gdal_warp_exe + gdal_params + filename_scl+".vrt"+" "+filename_scl+"_10m.vrt"
        os.system(command)
        if (os.path.isfile(filename_scl+"_10m.vrt"+".aux.xml")):
           os.remove(filename_scl+"_10m.vrt"+".aux.xml")
 #       os.remove(filename_scl+".vrt")
 #       os.rename(filename_scl+"_10m.vrt",filename_scl+".vrt")
            
                   
        gdal_translate_exe=os.path.join(Soft_Geoproces_GDAL,"gdal_translate.bat")
        gdal_params=" -a_nodata 0 -co COMPRESS=JPEG -co JPEG_QUALITY=75 -of GTiff -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 -co INTERLEAVE=PIXEL -co BIGTIFF=NO "
        command = gdal_translate_exe + gdal_params + filename_rgb+".vrt"+" "+filename_rgb+".tif"
        os.system(command)
        if (os.path.isfile(filename_rgb+".tif"+".aux.xml")):
           os.remove(filename_rgb+".tif"+".aux.xml")
        gdal_params=" -a_nodata 0 -co COMPRESS=DEFLATE -co PREDICTOR=2 -co ZLEVEL=9 -of GTiff -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 -co INTERLEAVE=PIXEL -co BIGTIFF=NO "
        command = gdal_translate_exe + gdal_params + filename_scl+"_10m.vrt"+" "+filename_scl+".tif"
        os.system(command)
        if (os.path.isfile(filename_scl+".tif"+".aux.xml")):
           os.remove(filename_scl+".tif"+".aux.xml")
        os.remove(filename_rgb+".vrt")
        os.remove(filename_scl+".vrt")
        os.remove(filename_scl+"_10m.vrt")
        for f in glob.glob("*.vrt"):
            os.remove(f)
        os.remove(input_TCI_dat)
        os.remove(input_SCL_dat)
        for f in glob.glob("*.SAFE"):
            shutil.rmtree(f)      
        shutil.rmtree("ZIP")         
        return 0
    except:
        return 1
     
out_dir_root = input("Directori arrel de treball (def: I:\S2_QuickLooks\QuickLooks_2017): ")
if not  out_dir_root:
   out_dir_root = r"I:\S2_QuickLooks\QuickLooks_2017"
   
any_mes_dia = input("Any mes i dia de proces (ex: 20171201): ")
extractiondate=any_mes_dia[0:4]+"-"+any_mes_dia[4:6]+"-"+any_mes_dia[6:8]
wkt_polygon = 'POLYGON ((0.1873941083836813 40.46212014624089,3.6319312482049257 40.46212014624089,3.6319312482049257 42.91398496782941,0.1873941083836813 42.91398496782941,0.1873941083836813 40.46212014624089))'

#out_dir = join(out_dir_root, '2017-01-16_R051')

granules_list_R051 =["T30TYN",
                     "T31TBE",
                     "T31TBF",
                     "T31TBG",
                     "T31TCE",
                     "T31TCF",
                     "T31TCG",
                     "T31TCH",
                     "T31TDF",
                     "T31TDG",
                     "T31TDH"]
granules_list_R008 =[ "T31TBE",
			"T31TCE",
			"T31TCF",
			"T31TCG",
			"T31TCH",
			"T31TDE",
			"T31TDF",
			"T31TDG",
			"T31TDH",
			"T31TEE",
			"T31TEF",
			"T31TEG",
			"T31TEH"]

eodata = eoData()

kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
 #            'contains_str':"T31TDE",
             'relorbnum': '08',
             'sensing_date_start': extractiondate,
             'sensing_date_stop': extractiondate,
             'top': 100,
             'expand': True}
eodata.search(**kwarg)
rorbit="R0XX"
if len(eodata.data_dict)>=1:
   rorbit="R008"
else:
   kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
 #            'contains_str':"T30TYN",
             'relorbnum': '51',
             'sensing_date_start': extractiondate,
             'sensing_date_stop': extractiondate,
             'top': 100,
             'expand': True}
   eodata.search(**kwarg)
   if len(eodata.data_dict)>=1:
      rorbit="R051"
   else:
      print ("\n",r"No s'han trobat cap granule per aquesta data. Res a fer")
      sys.exit()
      
extractiondir=any_mes_dia[0:4]+"-"+any_mes_dia[4:6]+"-"+any_mes_dia[6:8]+"_"+rorbit
out_dir = join(out_dir_root, extractiondir)
if not os.path.isdir(out_dir):
   os.mkdir(out_dir)
out_dir = join(out_dir, 'ZIP')
if not os.path.isdir(out_dir):
   os.mkdir(out_dir)
         
if rorbit =="R008":
   for granules in granules_list_R008:
      kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
             'contains_str': granules,
             'relorbnum': '08',
             'sensing_date_start': extractiondate,
             'sensing_date_stop': extractiondate,
             'top': 100,
             'expand': True}
      eodata.search(**kwarg)
      eodata.get_access_token()
      eodata.download(out_dir=out_dir, nmax_flux=4)
elif rorbit == "R051":
  for granules in granules_list_R051:
      kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
             'contains_str': granules,
             'relorbnum': '51',
             'sensing_date_start': extractiondate,
             'sensing_date_stop': extractiondate,
             'top': 100,
             'expand': True}
      eodata.search(**kwarg)
      eodata.get_access_token()
      eodata.download(out_dir=out_dir, nmax_flux=4)
else:
    kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
             #'contains_str': '31TCG',
             #'relorbnum': '51',
             'sensing_date_start': extractiondate,
             'sensing_date_stop': extractiondate,
             'top': 100,
             'expand': True}
    eodata.search(**kwarg)
    data_dict2 = dict()
    print(len(eodata.data_dict))
    for ind, key in enumerate(eodata.data_dict):
       print (ind)
       print (key)
       print(eodata.data_dict[key]['Name'])
       data_dict2[key]=eodata.data_dict[key]
       print(len(data_dict2))
    for ind, key in enumerate(data_dict2):
       print (ind)
       print (key)
       print(data_dict2[key]['Name'])
    eodata.get_access_token()
    eodata.download(out_dir=out_dir, nmax_flux=4)
     
#Soft_Geoproces="\\\\icgc.local\\aplicacions\\produccio\\DFApplications"
Soft_GeoprocesGDAL="\\\\icgc.local\\aplicacions\\produccio\\DFApplications\\gdal381_apps"
rootPath=out_dir_root
#extractiondir = r"2017-01-16_R051"
workingdir=os.path.join(rootPath,extractiondir)
#nom_escena="S2_XXX_8b_20170116_R051"
#nom_escena="S2_XXX_8b_"+any_mes_dia+"_R0"+orbit
UTM_Zone_to_reproject="T31"
limits_R051="240000,467500,4780000,4480000"
limits_R008="300000,540000,4780000,4480000"

zipPath = os.path.join(workingdir,"ZIP")
pattern = '*.zip'

os.chdir(workingdir)

#S2_Segment_Process_L2A_QL_AND_SCL(workingdir, nom_escena, Soft_GeoprocesGDAL, limits_R008, UTM_Zone_to_reproject)
first=True
#rorbit="R0XX"
for root, dirs, files in os.walk(zipPath):
   for filename in fnmatch.filter(files, pattern):
       pos=filename.find('.zip')
       output_folder = filename[:pos]
       if first==True:
#          rorbit=filename[33:38]
          nom_escena= filename[:3]+"_XXX_8b_"+any_mes_dia+"_"+rorbit
          first=False
       if not os.path.isdir(output_folder+".SAFE"):
          unzip_granule(zipPath+"\\"+filename, workingdir, output_folder)        

#Generacio mosaic per generar imatge QL
if rorbit =='R008':
   S2_Segment_Process_L2A_QL_AND_SCL(workingdir, nom_escena, Soft_GeoprocesGDAL, limits_R008, UTM_Zone_to_reproject)
else:
   S2_Segment_Process_L2A_QL_AND_SCL(workingdir, nom_escena, Soft_GeoprocesGDAL, limits_R051, UTM_Zone_to_reproject)

os.chdir(out_dir_root)  
for f in glob.glob(os.path.join(workingdir,"*.tif")):
    filename = os.path.split(f)[1]
    filenameout = os.path.join(out_dir_root,filename)
    shutil.move(f,filenameout)
shutil.rmtree(workingdir)
