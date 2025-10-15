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



def S2_Segment_Process_L1C_4B(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject):

    try:
        print('\n\nExecuting S2_Segment_Process_L1C_4B\n')
        if (os.path.isfile(nom_escena+".btf")):
           print ("\n","Found previous version of "+nom_escena+".btf"+". Nothing to do")
           return 0
        
        GSD_bandes = [10,10,10,10]
        NOM_bandes = ['B02','B03','B04','B08']
    
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
        os.chdir(dir_in)
    
        for nom_dir in granule_list:
    
    #       CONVERTIR UN GRÁNUL EM UN .RF AMB LA UNIÓ DE TOTES LES BANDES
            print ("\n",nom_dir)
    
            gain = S2_offset_gain.search_gain("L1C", dir_in+"\\"+nom_dir)
            if (gain==-9999):
                print("WARNING: Missing metadata for the band gain. Gain=10000!")
                gain = 10000

            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]
    
            for i_banda in range(len(NOM_bandes)):       
            
    #           CONVERTIR UNA BANDA EN UN .RF aplicant el offset i el gain
    #           TOAi = 10000*OFFi/GAIN + 10000*DNi/GAIN

                offset = S2_offset_gain.search_offset("L1C", dir_in+"\\"+nom_dir, i_banda+1)
                if (offset==-9999):
                    print("WARNING: Missing metadata for the band offset. Offset=0!")
                    offset = 0

                offset_f = 10000.*float(offset)/float(gain)
                gain_f = 10000./float(gain)

                if (GSD_bandes[i_banda]==10):
    
                    file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+file_root+"_"+NOM_bandes[i_banda]+".jp2"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"

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
                    file_tmp  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+"_20m.rf"
                    file_out  = dir_in+"\\"+granule_ID+"_"+NOM_bandes[i_banda]+".rf"
    
                    os.system("echo "+file_in+"  >>  input.dat\n")
                    os.system("echo "+str(offset_f)+","+str(gain_f)+" >>  input.dat\n")
                    os.system("echo 1.,0. >>  input.dat\n")
                    os.system("echo 3 >>  input.dat\n")
                    os.system("echo "+file_tmp+"  >>  input.dat\n")
                    os.system("echo ' ' >> input.dat\n")
                    os.system(Soft_Geoproces+"\ICCImageAnalisys\exe\ICCBandCombination.exe < input.dat\n")
                    os.remove("input.dat")

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
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA")
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
    
        os.system(Soft_Geoproces+"\ICCImageCollage\exe\ICCImageCollage.exe -lfllista.txt -ol3 -ml"+limits+" "+nom_escena+".btf\n")
        os.remove("llista.txt")
         
    
        for nom_dir in granule_list:
            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_10m_jpg = os.listdir(granule_name+"\\IMG_DATA")
            file_root = bands_10m_jpg[0][0:22]
            os.chdir(dir_in)
      
            granule_ID = granule_name[0:10]+granule_name[18:34]

            if (granule_ID[4:7] != UTM_Zone_to_reproject):
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf")
                os.remove(granule_ID+"_FUS"+UTM_Zone_to_reproject[1:]+"_net.rf.xml")
            else:
                os.remove(granule_ID+".rf")
                os.remove(granule_ID+".rf.xml")
        

        if S2_utis.tiff2cog(Soft_GeoprocesGDAL, dir_in, nom_escena, "btf")!=0:
            print('\n\nError converting .btf to cog file!\n')

        
        return 0
    except:
        return 1