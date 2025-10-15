import os

def tiff2cog(Soft_GeoprocesGDAL, dir_file, name_file, extension):

    try:
        os.chdir(dir_file)
    
        os.environ['GDAL_DATA'] = Soft_GeoprocesGDAL+r"\gdal-data"
        os.environ['PROJ_LIB']  = Soft_GeoprocesGDAL+r"\proj7\share"      
        os.system("echo "+name_file+"."+extension+" > input_list.txt\n")
        os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt  -input_file_list input_list.txt  out.vrt\n")
        os.system(Soft_GeoprocesGDAL+"\gdal_translate -of cog out.vrt -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES "+name_file+"_cog."+extension+"\n")
        os.remove(name_file+"."+extension)
        os.remove("input_list.txt")
        os.remove("out.vrt")
        os.system("rename "+name_file+"_cog."+extension+" "+name_file+"."+extension)
        
        return 0

    except:
        return 1
