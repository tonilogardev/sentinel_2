import os

def tiff2cog(Soft_GeoprocesGDAL, dir_file, name_file, extension):

    try:
        os.chdir(dir_file)
    
##        os.environ['GDAL_DATA'] = Soft_GeoprocesGDAL+r"\gdal-data"
##        os.environ['PROJ_LIB']  = Soft_GeoprocesGDAL+r"\proj7\share"      
##        os.system("echo "+name_file+"."+extension+" > input_list.txt\n")
##        os.system(Soft_GeoprocesGDAL+"\gdalbuildvrt.bat  -input_file_list input_list.txt  out.vrt\n")
##        os.system(Soft_GeoprocesGDAL+"\gdal_translate.bat -of cog out.vrt -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES "+name_file+"_cog."+extension+"\n")
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_params=" -of cog -a_nodata 0 -co COMPRESS=LZW -co PREDICTOR=STANDARD -co BIGTIFF=YES "
        command = gdal_translate_exe + gdal_params + name_file+"."+extension+" "+name_file+"_cog."+extension
        os.system(command)
        if (os.path.isfile(name_file+"_cog."+extension+".aux.xml")):
          os.remove(name_file+"_cog."+extension+".aux.xml")
        os.remove(name_file+"."+extension)
##        os.remove("input_list.txt")
##        os.remove("out.vrt")
##        os.system("rename "+name_file+"_cog."+extension+" "+name_file+"."+extension)
        os.rename(name_file+"_cog."+extension,name_file+"."+extension)
        
        return 0

    except:
        return 1

def tiff2cog_QL_8b(Soft_GeoprocesGDAL, name_in, name_out):

    try:
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_params=" -ot byte -a_nodata 0 -b 3 -b 2 -b 1 -co COMPRESS=JPEG -co QUALITY=75 -of COG -scale 0 1 0 0.1 -co BIGTIFF=YES -co OVERVIEWS=IGNORE_EXISTING "
        command = gdal_translate_exe + gdal_params + name_in + " " + name_out
        os.system(command)
        if (os.path.isfile(name_out+".aux.xml")):
          os.remove(name_out+".aux.xml")
        
        return 0

    except:
        return 1

def tiff2cog_QL_16b(Soft_GeoprocesGDAL, name_in, name_out):

    try:
        gdal_translate_exe=os.path.join(Soft_GeoprocesGDAL,"gdal_translate.bat")
        gdal_params=gdal_params=" -ot UInt16 -a_nodata 0 -b 3 -b 2 -b 1 -b 7 -co COMPRESS=LZW -co PREDICTOR=STANDARD -of COG -co BIGTIFF=YES -co OVERVIEWS=IGNORE_EXISTING "
        command = gdal_translate_exe + gdal_params + name_in + " " + name_out
        os.system(command)
        if (os.path.isfile(name_out+".aux.xml")):
          os.remove(name_out+".aux.xml")
        
        return 0

    except:
        return 1