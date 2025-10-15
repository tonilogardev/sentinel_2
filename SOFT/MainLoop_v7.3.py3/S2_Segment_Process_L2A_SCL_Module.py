# -*- coding: utf-8 -*-
"""
Created on Thu Mar 9 12:23:34 2017

@author: v.pala
"""

import os
import fnmatch
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
#    os.remove(granule_ID+".rf.xml")

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

def S2_Segment_Process_L2A_SCL(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject):
    
    try:
        GSD_bandes = [20]
        NOM_bandes = ['SCL']
    
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L2A*.SAFE')   
        os.chdir(dir_in)
    
        for nom_dir in granule_list:
    
    #       CONVERTIR UN GRÁNUL EM UN .RF AMB LA UNIÓ DE TOTES LES BANDES
            print ("\n",nom_dir)
    
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA\\R10m")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)

            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            for i_banda in range(len(NOM_bandes)):       
            
                if (GSD_bandes[i_banda]==10):
    
    #               CONVERTIR UNA BANDA EN UN .RF
                    file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R10m\\"+file_root+"_"+NOM_bandes[i_banda]+"_10m.jp2"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"                    
                    os.system("echo n   > input.dat\n")
                    os.system("echo "+file_in+"  >>  input.dat\n")
                    os.system("echo "+file_out+"  >>  input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImage2RF.exe < input.dat\n")
                    os.remove("input.dat")
    
                else:                    
    #               CONVERTIR UNA BANDA EN UN .RF          
                    file_in  = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\R20m\\"+file_root+"_"+NOM_bandes[i_banda]+"_20m.jp2"
                    file_tmp  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+"_20m.rf"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"


                    os.system("echo n   > input.dat\n")
                    os.system("echo "+file_in+"  >>  input.dat\n")
                    os.system("echo "+file_tmp+"  >>  input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImage2RF.exe < input.dat\n")
     
                    os.system("echo 0   > input.dat\n")
                    os.system("echo n   >> input.dat\n")
                    os.system("echo l   >> input.dat\n")
                    os.system("echo "+file_tmp+"  >>  input.dat\n")
                    os.system("echo 10   >> input.dat\n")
                    os.system("echo 10   >> input.dat\n")
                    os.system("echo "+file_out+"  >>  input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageResize.exe < input.dat\n")
                
                    os.remove(file_tmp)
                    os.remove(file_tmp+'.xml')
                    os.remove("input.dat")
     
                i_banda += 1    
                print ("\t",i_banda)
    
            os.remove(granule_ID+"_SCL.rf.XML")
            os.system("rename "+granule_ID+"_SCL.rf "+granule_ID+".rf")
    
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
            
        os.system(Soft_Geoproces+"\ICCImageCollage\exe\ICCImageCollage.exe -lfllista.txt -ol3 -ml"+limits+" "+nom_escena+".tif\n")
        os.remove("llista.txt")
    
        os.chdir(dir_in)
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
        
        if S2_utis.tiff2cog(Soft_GeoprocesGDAL, dir_in, nom_escena, "tif")!=0:
            print('\n\nError converting SCL to cog file!\n')

        return 0
    except:
        return 1
    