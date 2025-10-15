# -*- coding: utf-8 -*-
"""
Created on Thu Mar 9 12:23:34 2017

@author: v.pala
"""

import os
import fnmatch
import S2_offset_gain

def reprojecta(dir_out, granule_ID, Soft_Geoproces, UTM_Zone_to_reproject):
    os.system("echo 1 >input_mask.dat\n")
    os.system("echo "+granule_ID+".rf >>input_mask.dat\n")
    os.system("echo .\\MASK\\"+granule_ID[4:]+"_mask.tif >>input_mask.dat\n")
    os.system("echo.>>input_mask.dat\n")
    os.system("echo 2 >> input_mask.dat\n")
    os.system("echo s >> input_mask.dat\n")
    os.system("echo "+granule_ID+"_net.rf >>input_mask.dat\n")
    os.system("echo.>>input_mask.dat\n")
    os.system(Soft_Geoproces+"\ICCImageCollage\exe\ICCImageCollage.exe <input_mask.dat")
    os.remove("input_mask.dat")
    os.remove(granule_ID+".rf")
    os.remove(granule_ID+".rf.xml")

    os.system("echo "+granule_ID+"_net.rf > input_reproject.dat\n")
    os.system("echo 2 >> input_reproject.dat\n")
    os.system("echo 700 >> input_reproject.dat\n")
    os.system("echo 1001001 >> input_reproject.dat\n")
    os.system("echo "+UTM_Zone_to_reproject[1:]+" >> input_reproject.dat\n")
    os.system("echo 0 >> input_reproject.dat\n")
    os.system("echo.>> input_reproject.dat\n")
    os.system("echo.>> input_reproject.dat\n")
    os.system("echo.>> input_reproject.dat\n")
    os.system("echo.>> input_reproject.dat\n")
    os.system("echo "+granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf >> input_reproject.dat\n")
    os.system("echo.>> input_reproject.dat\n")
    os.system("echo 2 >> input_reproject.dat\n")
    os.system("echo 0 >> input_reproject.dat\n")
    os.system("echo n >> input_reproject.dat\n")
    os.system(Soft_Geoproces+"\ICCImageOperationsGeoCorrection\exe\ICCImageGeoTransformation.exe <input_reproject.dat\n")
    os.remove("input_reproject.dat")
    os.remove(granule_ID+"_net.rf")
    os.remove(granule_ID+"_net.rf.xml")



def S2_Segment_Process_NDVI(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject):

    try:
        NOM_bandes = ['B04','B08']
    
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L2A*.SAFE')   
        os.chdir(dir_in)
    
        for nom_dir in granule_list:
    
    #       CONVERTIR UN GRÁNUL EM UN .RF AMB LA UNIÓ DE TOTES LES BANDES
            print ("\n",nom_dir)
    
            gain = S2_offset_gain.search_gain("L2A", dir_in+"\\"+nom_dir)
            if (gain==-9999):
                print("WARNING: Missing metadata for the band gain. Gain=10000!")
                gain = 10000

            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            for i_banda in range(len(NOM_bandes)):       
            
    #           CONVERTIR UNA BANDA EN UN .RF aplicant el offset i el gain
    #           TOAi = 10000*OFFi/GAIN + 10000*DNi/GAIN

                offset = S2_offset_gain.search_offset("L2A", dir_in+"\\"+nom_dir, i_banda+1)
                if (offset==-9999):
                    print("WARNING: Missing metadata for the band offset. Offset=0!")
                    offset = 0

                offset_f = 10000.*float(offset)/float(gain)
                gain_f = 10000./float(gain)

    
                file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R10m\\"+file_root+"_"+NOM_bandes[i_banda]+"_10m.jp2"
                file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"

                os.system("echo "+file_in+"  >>  input.dat\n")
                os.system("echo "+str(offset_f)+","+str(gain_f)+" >>  input.dat\n")
                os.system("echo 1.,0. >>  input.dat\n")
                os.system("echo 3 >>  input.dat\n")
                os.system("echo "+file_out+"  >>  input.dat\n")
                os.system("echo ' ' >> input.dat\n")
                os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe < input.dat\n")
                os.remove("input.dat")
         
                i_banda += 1    
                print ("\t",i_banda)
    
            os.system("echo "+str(len(NOM_bandes))+" > input.dat\n")
            os.system("echo n >> input.dat\n")
            os.system("echo n >> input.dat\n")
    
            for i_banda in range(len(NOM_bandes)):       
                file_in = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"
                os.system("echo "+file_in+"  >>  input.dat\n")
                         
            os.system("echo n >> input.dat\n")
            file_out = dir_in+"\\"+granule_ID+".rf"
            os.system("echo "+file_out+"  >>  input.dat\n")
            os.system("echo ' ' >> input.dat\n")
            os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageChannelsUnion.exe < input.dat\n")
            os.remove("input.dat")
       
    
            for i_banda in range(len(NOM_bandes)):       
    
               file = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"
           
               os.remove(file)
               os.remove(file+'.xml')
           
    #   FEM EL COLLAGE DE TOTS ELS GRÀNULS
    
        os.chdir(dir_in)
        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            if (granule_ID[4:7] == UTM_Zone_to_reproject):
                file_in = granule_ID+".rf"
                os.system("echo "+file_in+" >> llista.txt\n")
                os.system("echo .\\MASK\\"+granule_ID[4:]+"_mask.tif"+" >> llista.txt\n")
            else:
                reprojecta(dir_in, granule_ID, Soft_Geoproces, UTM_Zone_to_reproject)
                os.system("echo "+granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf >> llista.txt\n")
    
        os.system(Soft_Geoproces+"\ICCImageCollage\exe\ICCImageCollage.exe -lfllista.txt -ol3 -ml"+limits+" "+nom_escena+"_B-Index.btf\n")
        os.remove("llista.txt")
        os.remove(nom_escena+"_B-Index.btf.xml" )
         
        os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe -coefN0.,0.,200 -coefD0.,1.,1. -opt3 "+nom_escena+"_B-Index.btf "+nom_escena+"_NDVI16.tif\n")
        os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe -b8 -dtuint -ca0.0 -cf1.0 -svnull0 "+nom_escena+"_NDVI16.tif "+nom_escena+"_NDVI.tif\n")
        os.remove(nom_escena+"_NDVI16.tif" )
        os.remove(nom_escena+"_NDVI16.tif.xml" )
#        os.remove(nom_escena+"_NDVI.tif.xml" )

    
        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]

            if (granule_ID[4:7] != UTM_Zone_to_reproject):
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf")
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf.xml")
            else:
                os.remove(granule_ID+".rf")
                os.remove(granule_ID+".rf.xml")
        

##        os.environ['GDAL_DATA'] = Soft_GeoprocesGDAL+r"\gdal-data"
##        os.environ['PROJ_LIB']  = Soft_GeoprocesGDAL+r"\proj7\share"      
##        os.system("echo "+nom_escena+"_NDVI.tif > input_list.txt\n")
##        os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt  -input_file_list input_list.txt  out.vrt\n")
##        os.system(Soft_GeoprocesGDAL+"\gdal_translate -of cog out.vrt -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES "+nom_escena+"_NDVI_cog.tif\n")
        nom_in = nom_escena+"_NDVI.tif"
        nom_out = nom_escena+"_NDVI_cog.tif
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_params=" -of COG -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES -co OVERVIEWS=IGNORE_EXISTING "
        command = gdal_translate_exe + gdal_params + nom_in + " " + nom_out
        os.system(command)
##        os.remove(nom_escena+"_NDVI.tif")
        os.remove(nom_in)
##        os.remove("input_list.txt")
##        os.remove("out.vrt")
##        os.system("rename "+nom_escena+"_NDVI_cog.tif "+nom_escena+"_NDVI.tif")
        os.system("rename "+nom_in+" "+nom_out)
        
        return 0
    except:
        return 1