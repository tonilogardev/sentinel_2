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


def S2_MaskGeneration_L1C(dir_in, Soft_Geoproces):
    try:
        dir_mask=os.path.join(dir_in,"MASK")
##        print ("\n dir_mask : "+dir_mask)
        os.mkdir(dir_mask)

##        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
    
        for nom_dir in granule_list:
    
##            print ("\n nom dir :"+nom_dir)

##            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(dir_in+"\\"+nom_dir+"\\GRANULE")[0]
##            print ("\n granule_name : "+granule_name)
            bands_jpg = os.listdir(dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA")
##            os.chdir(dir_in)
     
            file_root = bands_jpg[0][0:22]
            granule_ID = granule_name[4:10]+granule_name[18:34]

            file_in   = dir_in+"\\"+ nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+file_root+"_B04.jp2"
##            print ("\n file_in : "+file_in)
            file_out  = dir_mask+"\\"+granule_ID+"_B04.rf"
##            print ("\n file_out : "+file_out)

            input_dat = dir_in+"\\"+"input.dat"
##            print ("\n input_dat : "+input_dat)
##            print ("\n Soft_Geoproces : "+Soft_Geoproces)
##            print ("\n dir_Image2RF : "+dir_Image2RF)
            subprocess.call("echo n   > " + input_dat+"\n",shell=True)
            subprocess.call("echo "+file_in+"  >> " + input_dat+"\n",shell=True)
            subprocess.call("echo "+file_out+"  >> " + input_dat+"\n",shell=True)
##            os.chdir(dir_in)
            dir_Image2RF = os.path.join(Soft_Geoproces,"ICCImageOperations\\exe\\ICCImage2RF.exe ")
##            print ("\n dir_Image2RF : "+dir_Image2RF)
            subprocess.call(dir_Image2RF +" < "+ input_dat+"\n",shell=True)
            os.remove(input_dat)     
     
            file_out_1b  = dir_mask+"\\"+granule_ID+"_B04_1b.tif"
            os.system("echo "+file_out+" > " + input_dat+"\n")
            os.system("echo 1 >> " + input_dat+"\n")
            os.system("echo uint >> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo 0 >> " + input_dat+"\n")
            os.system("echo 1 >> " + input_dat+"\n")
            os.system("echo 0 >> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo 1024>> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo "+file_out_1b+" >> " + input_dat+"\n")
            dir_ICCImageDataTypeChange = os.path.join(Soft_Geoproces,"ICCImageOperations\\exe\\ICCImageDataTypeChange.exe ")
            os.system(dir_ICCImageDataTypeChange+" < " + input_dat+"\n")
            os.remove(input_dat)
    
            os.remove(file_out)
            os.remove(file_out+'.xml')
    
    
##            os.chdir(dir_mask)
            file_orig = dir_mask+"\\"+granule_ID+"_B04_1b.tif"
            file_dest_full = dir_mask+"\\"+granule_ID+"_mask.tif"
            file_dest = granule_ID+"_mask.tif"
            os.rename(file_orig,file_dest_full) 
            os.rename(file_orig+".xml",file_dest_full+".xml") 
    
       
            file_out_eroded_full = dir_mask+"\\"+granule_ID+"_mask_eroded.tif"
            img = cv2.imread(file_dest_full,0)
            kernel = np.ones((3,3),np.uint8)
            dilation = cv2.dilate(img,kernel,iterations = 1)            
            erosion_val = 51
            erosion = cv2.erode(dilation, kernel,iterations = erosion_val)
            erosion[0:erosion_val,:]=0
            erosion[-erosion_val:,:]=0
            erosion[:,0:erosion_val]=0
            erosion[:,-erosion_val:]=0
        
            cv2.imwrite(file_out_eroded_full, erosion)
            file_out_eroded = granule_ID+"_mask_eroded.tif"
            os.rename(file_dest_full+".xml",file_out_eroded_full+".xml")
            os.remove(file_dest_full)
            
        
            file_out_eroded_1b = dir_mask+"\\"+granule_ID+"_mask_eroded_1b.tif"
            os.system("echo "+file_out_eroded_full+" > " + input_dat+"\n")
            os.system("echo 1 >> " + input_dat+"\n")
            os.system("echo uint >> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo 0 >> " + input_dat+"\n")
            os.system("echo 1 >> " + input_dat+"\n")
            os.system("echo 0 >> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo.>> " + input_dat+"\n")
            os.system("echo "+file_out_eroded_1b+" >> " + input_dat+"\n")
            os.system(dir_ICCImageDataTypeChange+" < " + input_dat+"\n")
            os.remove(file_out_eroded_full)
            os.remove(file_out_eroded_full+".xml")
            os.remove(input_dat)
     
            os.rename(file_out_eroded_1b,file_dest_full) 
            os.remove(file_out_eroded_1b+".xml")
            
##            os.chdir(dir_in)
            
        return 0
    except:
        return 1

    