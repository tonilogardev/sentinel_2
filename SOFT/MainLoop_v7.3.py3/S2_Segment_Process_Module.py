# -*- coding: utf-8 -*-
"""
Created on Thu Nov 24 12:23:34 2016

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


def S2_Segment_Process(dir_in, nom_escena, Soft_Geoproces, UTM_Zone_to_reproject):

    try:
        llista_bandes = [2,3,4,8]    

        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
        os.chdir(dir_in)


        for nom_dir in granule_list:
    
    #   CONVERTIR UN GRÁNUL EM UN .RF AMB LA UNIÓ DE TOTES LES BANDES
            print ("\n",nom_dir)

            gain = S2_offset_gain.search_gain("L1C", dir_in+"\\"+nom_dir)
            if (gain==-9999):
                print("Gain bands ERROR!")
                gain = 10000
                
                
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_jpg = os.listdir(granule_name+"\\IMG_DATA")
            os.chdir(dir_in)

            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            for i_jpg in llista_bandes: 
    
    #           CONVERTIR UNA BANDA EN UN .RF aplicant el offset i el gain
    #           TOAi = 10000*OFFi/GAIN + 10000*DNi/GAIN

                offset = S2_offset_gain.search_offset("L1C", dir_in+"\\"+nom_dir, i_jpg-1)
                if (offset==-9999):
                    print("Offset band ",i_jpg," ERROR!")
                    offset = 0

                offset_f = 10000.*float(offset)/float(gain)
                gain_f = 10000./float(gain)
 
                file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+bands_jpg[i_jpg-1]
                file_out  = dir_in+"\\"+granule_ID+"_B0"+str(i_jpg)+".rf"
    
                os.system("echo "+file_in+"  >>  input.dat\n")
                os.system("echo "+str(offset_f)+","+str(gain_f)+" >>  input.dat\n")
                os.system("echo 1.,0. >>  input.dat\n")
                os.system("echo 3 >>  input.dat\n")
                os.system("echo "+file_out+"  >>  input.dat\n")
                os.system("echo ' ' >> input.dat\n")
                os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe < input.dat\n")
                os.remove("input.dat")
    
    
            os.system("echo "+str(len(llista_bandes))+" > input.dat\n")
            os.system("echo n >> input.dat\n")
            os.system("echo n >> input.dat\n")
    
            for i_jpg in llista_bandes:
                file_in = dir_in+"\\"+granule_ID+"_B0"+str(i_jpg)+".rf"
                os.system("echo "+file_in+"  >>  input.dat\n")
    
            os.system("echo n >> input.dat\n")
            file_out=dir_in+"\\"+granule_ID+".rf"
            os.system("echo "+file_out+"  >>  input.dat\n")
            os.system("echo ' ' >> input.dat\n")
            os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageChannelsUnion.exe < input.dat\n")
            os.remove("input.dat")
       
            for i_jpg in llista_bandes:
                file = dir_in+"\\"+granule_ID+"_B0"+str(i_jpg)+".rf"
                os.remove(file)
                file = dir_in+"\\"+granule_ID+"_B0"+str(i_jpg)+".rf.xml"
                os.remove(file)
    
    
    #   FEM EL COLLAGE DE TOTS ELS GRÀNULS
    
        os.chdir(dir_in)
        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            os.chdir(dir_in)

            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            if (granule_ID[4:7] == UTM_Zone_to_reproject):
                file_in = granule_ID+".rf"
                os.system("echo "+file_in+" >> llista.txt\n")
                os.system("echo .\\MASK\\"+granule_ID[4:]+"_mask.tif"+" >> llista.txt\n")
            else:
                reprojecta(dir_in, granule_ID, Soft_Geoproces, UTM_Zone_to_reproject)
                os.system("echo "+granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf >> llista.txt\n")
            
        os.system(Soft_Geoproces+"\ICCImageCollage\exe\ICCImageCollage.exe -lfllista.txt -t64 -ol1 "+nom_escena+"_net.rf\n")
        os.remove("llista.txt")
    

        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]

            if (granule_ID[4:7] != UTM_Zone_to_reproject):
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf")
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf.xml")
            else:
                os.remove(granule_ID+".rf")
                os.remove(granule_ID+".rf.xml")
            
    
        os.remove(nom_escena+"_net.rf.xml")
        return 0
    except:
        return 1