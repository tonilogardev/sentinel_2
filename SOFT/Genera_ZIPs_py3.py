# -*- coding: utf-8 -*-
"""
Created on 2021-07-12

@author: v.pala


Aquest programa descomprimeix un ZIP de cintoteca OT_SENTINEL2 que conté els productes L1C (.SAFE) per una escena
i construeix una carpeta ZIP tal com queda quan es descarreguen aquest producgtes del Copernicus Open Access Hub

"""

import os
import zipfile
import sys
import fnmatch
import shutil




def zipdir(path, ziph):   
    empty_dirs = []  
    for root, dirs, files in os.walk(path):  
        empty_dirs.extend([dir for dir in dirs if os.listdir(os.path.join(root, dir)) == []])  
        for file in files:  
            ziph.write(os.path.join(root, file))  

        for dir in empty_dirs:  
            zif = zipfile.ZipInfo(os.path.join(root, dir) + "/")  
            ziph.writestr(zif, "")  
        empty_dirs = []  



def unzip_granules(source_file_path, destination_dir, output_folder):
    with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
        zip_ref.extractall(destination_dir)
    return


                                    
#********************************************************************************* 
#   GENERACIÓ DE LA IMATGE DE 4 BANDES PER EL PRODUCTE SEN2
#********************************************************************************* 

 
#   UNZIP TOTS ELS PRODUCTES (GRÀNULS) l1C


#rootPath = r"//sfpcotprod01/Disc_I/DARP_S2/Prova"
rootPath = input("Path folder where ZIP file is [ex: \\sfpcotprod01\Disc_I\DARP_S2\Prova ]: ")
if not os.path.isdir(rootPath+"/ZIP"):
    os.mkdir(rootPath+"/ZIP")
extractiondir = rootPath+"/ZIP"

                 
files_dir = os.listdir(rootPath)            
for filename in fnmatch.filter(files_dir, '*.zip'):
                 
    pos=filename.find('.zip') 
    output_folder = filename[:pos]
    unzip_granules(rootPath+"\\"+filename, extractiondir, output_folder)


    #   ZIP TOTS ELS PRODUCTES (GRÀNULS *.SAFE) l1C

    try:
        os.chdir(extractiondir)
        file_SAFE=os.listdir(extractiondir)            
        for nom_file in fnmatch.filter(file_SAFE, '*.SAFE'):
            if (nom_file[0:10]=="S2A_MSIL1C" or nom_file[0:10]=="S2B_MSIL1C"):
                #   L1c product is zipped
                try:
                    pos2=nom_file.find('.SAFE') 
                    zipf = zipfile.ZipFile(nom_file[0:pos2]+'.zip', 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
                    zipdir(nom_file+'/', zipf)
                    shutil.rmtree(nom_file)
                    zipf.close()                        
                except:                          
                    print("Error when zipping L1C product!\n")
                    print("")
                    sys.stdout.flush()
                    break
    except:
        print('Error when zipping the L1c products!\n')
        print ("")
        sys.stdout.flush()
