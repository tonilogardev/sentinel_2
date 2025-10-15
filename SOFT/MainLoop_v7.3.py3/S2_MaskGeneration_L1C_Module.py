# -*- coding: utf-8 -*-
"""
Created on Thu Mar 9 12:23:34 2017

@author: v.pala
"""

import os
import cv2
import numpy as np
import fnmatch


def S2_MaskGeneration_L1C(dir_in, Soft_Geoproces):
    
    try:
        os.mkdir(dir_in+"/MASK")
        dir_mask = dir_in+"/MASK"

        os.chdir(dir_in)
        granule_list=fnmatch.filter(os.listdir(dir_in),'*L1C*.SAFE')   
    
        for nom_dir in granule_list:
    
            print ("\n",nom_dir)

            os.chdir(nom_dir+"\GRANULE")
            granule_name = os.listdir(".")[0]
            bands_jpg = os.listdir(granule_name+"\\IMG_DATA")
            os.chdir(dir_in)
     
            file_root = bands_jpg[0][0:22]
            granule_ID = granule_name[4:10]+granule_name[18:34]

            file_in   = nom_dir+"\\GRANULE\\"+granule_name+"\\IMG_DATA\\"+file_root+"_B04.jp2"
            file_out  = dir_mask+"\\"+granule_ID+"_B04.rf"
    
            os.system("echo n   > input.dat\n")
            os.system("echo "+file_in+"  >>  input.dat\n")
            os.system("echo "+file_out+"  >>  input.dat\n")
            os.chdir(dir_in)
            os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImage2RF.exe < input.dat\n")
     
            os.remove("input.dat")     
     
            file_out_1b  = dir_mask+"\\"+granule_ID+"_B04_1b.tif"
            os.system("echo "+file_out+" > input.dat\n")
            os.system("echo 1 >> input.dat\n")
            os.system("echo uint >> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo 0 >> input.dat\n")
            os.system("echo 1 >> input.dat\n")
            os.system("echo 0 >> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo 1024>> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo "+file_out_1b+" >> input.dat\n")
            os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe < input.dat\n")
            os.remove("input.dat")
    
            os.remove(file_out)
            os.remove(file_out+'.xml')
    
    
            os.chdir(dir_mask)
            file_orig = granule_ID+"_B04_1b.tif"
            file_dest = granule_ID+"_mask.tif"
            os.system("rename "+file_orig+" "+file_dest) 
            os.system("rename "+file_orig+".xml "+file_dest+".xml") 
    
       
            file_out_eroded = granule_ID+"_mask_eroded.tif"
            img = cv2.imread(file_dest,0)
            kernel = np.ones((3,3),np.uint8)
            dilation = cv2.dilate(img,kernel,iterations = 1)            
            erosion_val = 51
            erosion = cv2.erode(dilation, kernel,iterations = erosion_val)
            erosion[0:erosion_val,:]=0
            erosion[-erosion_val:,:]=0
            erosion[:,0:erosion_val]=0
            erosion[:,-erosion_val:]=0
        
            cv2.imwrite(file_out_eroded, erosion)
            os.system("rename "+file_dest+".xml "+file_out_eroded+".xml")
            os.remove(file_dest)
            
        
            file_out_eroded_1b = dir_mask+"\\"+granule_ID+"_mask_eroded_1b.tif"
            os.system("echo "+file_out_eroded+" > input.dat\n")
            os.system("echo 1 >> input.dat\n")
            os.system("echo uint >> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo 0 >> input.dat\n")
            os.system("echo 1 >> input.dat\n")
            os.system("echo 0 >> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo.>> input.dat\n")
            os.system("echo "+file_out_eroded_1b+" >> input.dat\n")
            os.system(Soft_Geoproces+"\ICCImageOperations\exe\ICCImageDataTypeChange.exe < input.dat\n")
            os.remove(file_out_eroded)
            os.remove(file_out_eroded+'.xml')
            os.remove('input.dat')
     
            os.system("rename "+granule_ID+"_mask_eroded_1b.tif"+" "+file_dest) 
            os.remove(file_out_eroded_1b+".xml ")
            
            os.chdir(dir_in)
            
        return 0
    except:
        return 1

    