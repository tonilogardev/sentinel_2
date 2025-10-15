# -*- coding: utf-8 -*-
"""
Created on Thu Mar 9 12:23:34 2017

@author: v.pala
"""

import os
import fnmatch
import S2_offset_gain
import S2_utis

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



def S2_Segment_Process_L2A_10B(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject):

    try:
        if (os.path.isfile(nom_escena+".btf")):
           print ("\n","Found previous version of "+nom_escena+".btf"+". Nothing to do")
           return 0
        
        GSD_bandes = [10,10,10,20,20,20,10,20,20,20]
        NOM_bandes = ['B02','B03','B04','B05','B06','B07','B08','B8A','B11','B12']
    
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

                if (GSD_bandes[i_banda]==10):
    
                    file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R10m\\"+file_root+"_"+NOM_bandes[i_banda]+"_10m.jp2"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".tif"

                    os.system("echo "+file_in+"  >>  input.dat\n")
                    os.system("echo "+str(offset_f)+","+str(gain_f)+" >>  input.dat\n")
                    os.system("echo 1.,0. >>  input.dat\n")
                    os.system("echo 3 >>  input.dat\n")
                    os.system("echo "+file_out+"  >>  input.dat\n")
                    os.system("echo ' ' >> input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe < input.dat\n")
                    os.remove("input.dat")
    
                else:

                    file_in  = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R20m\\"+file_root+"_"+NOM_bandes[i_banda]+"_20m.jp2"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".tif"
    
                    os.system("echo "+file_in+"  >>  input.dat\n")
                    os.system("echo "+str(offset_f)+","+str(gain_f)+" >>  input.dat\n")
                    os.system("echo 1.,0. >>  input.dat\n")
                    os.system("echo 3 >>  input.dat\n")
                    os.system("echo "+file_out+"  >>  input.dat\n")
                    os.system("echo ' ' >> input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe < input.dat\n")
                    os.remove("input.dat")

            list_bands = dir_in+"\\"+granule_ID+".txt"
            bands_vrt = dir_in+"\\"+granule_ID+".vrt"
            for i_banda in range(len(NOM_bandes)):       
                file_in = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".tif"
                os.system("echo "+file_in+"  >>  "+list_bands+"\n")
            
            options=" -separate -tr 10 10 -r bilinear -srcnodata 0 -vrtnodata 0 -tap "+bands_vrt+" -input_file_list "+list_bands
            os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt.bat "+ options)
            os.remove(list_bands)
##          Generacio imatge raster
            options=" -a_nodata 0 -co BIGTIFF=YES -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 "+bands_vrt+" "+dir_in+"\\"+granule_ID+".tif"
            os.system(Soft_GeoprocesGDAL+"\gdal_translate.bat "+options)
            os.remove(bands_vrt)
            for i_banda in range(len(NOM_bandes)):       
                file_in = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".tif"
                os.remove(file_in)
                os.remove(file_in+".xml") 
           
    #   FEM EL COLLAGE DE TOTS ELS GRÀNULS
        
        list_granules = dir_in+"\\"+nom_escena+".txt"
        granules_vrt = dir_in+"\\"+nom_escena+".vrt"
        os.chdir(dir_in)
        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            if (granule_ID[4:7] == UTM_Zone_to_reproject):
                options=" -i -b 1 -b 2 -b 3 -b 4 -b 5 -b 6 -b 7 -b 8 -b 9 -b 10 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -l footprint "+".\\MASK\\"+granule_ID[4:]+"_mask.gpkg"+" "+dir_in+"\\"+granule_ID+".tif"
                os.system(Soft_GeoprocesGDAL+"\gdal_rasterize.bat "+options)
            else:
                os.rename(dir_in+"\\"+granule_ID+".tif",dir_in+"\\"+granule_ID+"_zone30.tif")
                options=" -i -b 1 -b 2 -b 3 -b 4 -b 5 -b 6 -b 7 -b 8 -b 9 -b 10 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -burn 0 -l footprint "+".\\MASK\\"+granule_ID[4:]+"_mask.gpkg"+" "+dir_in+"\\"+granule_ID+"_zone30.tif"
                os.system(Soft_GeoprocesGDAL+"\gdal_rasterize.bat "+options)                
                options=" -t_srs EPSG:32631 -srcnodata 0 -dstnodata 0 -r cubic -tap -tr 10 10"
                files =" "+dir_in+"\\"+granule_ID+"_zone30.tif"+" "+dir_in+"\\"+granule_ID+".tif"
                os.system(Soft_GeoprocesGDAL+"\gdalwarp.bat "+options+files)
                os.remove(dir_in+"\\"+granule_ID+"_zone30.tif")
            os.system("echo "+dir_in+"\\"+granule_ID+".tif"+" >>  "+list_granules+"\n")
        options="-te "+limits+" -tr 10 10 -r bilinear -srcnodata 0 -vrtnodata 0 -tap "+granules_vrt+" -input_file_list "+list_granules   
        os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt.bat "+ options)
        os.remove(list_granules)
        options="-of COG -a_nodata 0 -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES -co RESAMPLING=NEAREST "
 ##       ​options=r" -of COG -a_nodata 0 -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES -co RESAMPLING=NEAREST "
        os.system(Soft_GeoprocesGDAL+"\gdal_translate.bat "+ options +" "+ granules_vrt +" "+nom_escena+".btf")
        os.remove(granules_vrt)
    
##        for nom_dir in granule_list:
##            os.chdir(nom_dir+"\GRANULE")
##            granule_name = os.listdir(".")[0]
##            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
##            file_root = bands_10m_jpg[0][0:22]
##            os.chdir(dir_in)
##      
##            granule_ID = granule_name[0:10]+granule_name[18:34]
##
##            if (granule_ID[4:7] != UTM_Zone_to_reproject):
##                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf")
##                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf.xml")
##            else:
##                os.remove(granule_ID+".rf")
##                os.remove(granule_ID+".rf.xml")
##        
##
##        if S2_utis.tiff2cog(Soft_GeoprocesGDAL, dir_in, nom_escena, "btf")!=0:
##            print('\n\nError converting .btf to cog file!\n')

        
        return 0
    except:
        return 1