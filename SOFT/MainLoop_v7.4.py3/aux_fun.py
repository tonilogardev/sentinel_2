import os
# import glob
# from typing import List, Any
from osgeo import gdal, gdalconst, osr, ogr
import numpy as np
from scipy import signal
import xml.etree.ElementTree as ET
import time
import sys
import pkg_resources
import cv2 as cv
import geopandas as gpd

import rasterio as rio
import rasterio.mask
from shapely.geometry import shape
import geopandas as gpd

installed = {pkg.key for pkg in pkg_resources.working_set}
try:
    import spectral as sp
except:
    os.system('pip install spectral')
try:
    import cupy as cp
    GPULib_flag=True
    from cupyx.scipy.signal import convolve2d
except:
    GPULib_flag=False
    #print('PY-CUDA not installed so GPU processed not used')
import shapely
try:
    shapely.speedups.disable()
except:
    print('Shapely version {} has not speedups module...'.format(shapely.__version__))
    
# if 'tifffile' in installed:
#     TF_flag=True
#     from tifffile import TiffFile as TF
# else:
#     TF_flag=False
    
gdal.SetConfigOption('GDAL_VRT_ENABLE_PYTHON', 'YES')

MAX_float = 2 ** 31 - 1
MIN_float = -2 ** 31 - 1

GDAL2NP_CONVERSION = {1: "int8", 2: "uint16", 3: "int16", 4: "uint32", 5: "int32", 6: "float32", 7: "float64",
                      10: "complex64", 11: "complex128"}
NP2GDAL_CONVERSION = {"int8": 1, "uint16": 2, "int16": 3, "uint32": 4, "int32": 5, "float32": 6, "float64": 7,
                      "complex64": 10, "complex128": 11}

# INTERP_ALGORITHMs = {'near': gdal.GRA_NearestNeighbour, 'bilinear':gdal.GRA_Bilinear, 'cubic': gdal.GRA_Cubic, 'cubicspline':gdal.GRA_CubicSpline,  'lanczos':gdal.GRA_Lanczos , 'average': gdal.GRA_Average,\
#              'mode': gdal.GRA_Mode, 'max': gdal.GRA_Max, 'min': gdal.GRA_Min, 'med': gdal.GRA_Med, 'q1': gdal.GRA_Q1 , 'q3': gdal.GRA_Q3}#, 'sum':gdal.GRA_SUM}
INTERP_ALGORITHMs = ['nearest', 'bilinear', 'cubic', 'cubicspline', 'lanczos', 'average', 'mode']


#def vrt2tif(vrt_in_f, tif_out_f):
#    gdal.Translate(tif_out_f, vrt_in_f, format='gtiff')

def dem_ortho2ellip_h_bat(input_f, output_f, geoid_f, datum='WGS84'):
    # Define the source and target spatial reference systems
    #src_srs = ' -src_srs +proj=longlat +datum={} +no_defs +geoidgrids={}'.format(datum, geoid_f)
    #dst_srs = ' -dst_srs +proj=longlat +datum={} +no_defs'.format(datum)

    src_srs = ' -s_srs "+proj=longlat +datum={} +no_defs +geoidgrids={}"'.format(datum, geoid_f)
    dst_srs = ' -t_srs "+proj=longlat +datum={} +no_defs"'.format(datum)

    cmd_str = r"\\icgc.local\aplicacions\produccio\DFApplications\gdal321_apps\gdalwarp.bat " +     src_srs  + dst_srs+ " {} {}".format(input_f, output_f)

    print(cmd_str)
    os.system(cmd_str)

def warp_vrt_reproj(img_in_f, vrt_out_f, im_res, out_fuse,  mosaic_limits_list):

    te_str = ' '.join([str(_) for _ in mosaic_limits_list])
    cmd_str = r'\\icgc.local\aplicacions\produccio\DFApplications\gdal321_apps\gdalwarp.bat -tap -tr {} {} -t_srs EPSG:{} -of VRT -te {} {} {} '.format(
        im_res, im_res, out_fuse, te_str, img_in_f, vrt_out_f)

    print('  GDAL reprojection instruction : {}'.format(cmd_str))
    os.system(cmd_str)



def dem_ortho2ellip_h(input_f, output_f, geoid_f, datum='WGS84'):
    # Define the source and target spatial reference systems
    src_srs = '+proj=longlat +datum={} +no_defs +geoidgrids={}'.format(datum, geoid_f)
    dst_srs = '+proj=longlat +datum={} +no_defs'.format(datum)

    # Perform the warp operation
    ds = gdal.Warp(output_f, input_f, srcSRS=src_srs, dstSRS=dst_srs)
    ds = None



def image_change_epsg(img_in_f, img_out_f, epsg_out, xres=None, yres=None, gdal_outputType=6):

    target_srs = 'EPSG:'+str(epsg_out)
    resampling_method = 'bilinear'

    creationOptions = {'dstSRS': target_srs, 'resampleAlg': resampling_method, 'format': 'GTiff'}
    if xres is not None:
        creationOptions['xRes'] = xres
    if yres is not None:
        creationOptions['yRes'] = yres

    creationOptions['outputType'] = gdal_outputType

    ds = gdal.Warp(img_out_f, img_in_f, **creationOptions)
    ds = None


def get_img_subset_from_gpkg(img_f, gpkg_f):
    gpdWs2 = gpd.read_file(gpkg_f)
    sh_obj = [gpdWs2['geometry'][0]]

    with rio.open(img_f) as src:
        out_image, out_transform = rio.mask.mask(src, sh_obj, crop=True)
        # out_meta = src.meta

    data_tmp = []
    for ind in range(out_image.shape[0]):
        data_tmp.append(np.squeeze(out_image[ind, :, :]))

    return data_tmp


def apply_mask(img_in_f, msk_f, img_out_f=None):
    img_info =  get_im_info(img_in_f)
    if img_out_f is None:
        img_out_f = img_in_f[:-4] + '_masked.tif'
    msk = read_image(msk_f, band_vec=[0])
    out_h = image_output_gen(img_out_f,  img_info['Nlines'], img_info['Ncolumns'], img_info['Nbands'], img_info['gdal_datatype'],
                                                  DriverName='GTiff', geotransform_info=img_info['im_geotransformation'],
                                                  src_proj_info=img_info['im_geoprojection'])
    for i_band in range(img_info['Nbands']):
        band = read_image(img_in_f)*msk
        write_im_band(out_h, band, i_band+1)

    out_h = None

def vrt2tif_bat(vrt_f, out_f,scale_vec = None):
    
    if scale_vec is None:
        scale_str = ''
    else:
        scale_str = ' -scale {} {} {} {} '.format(*scale_vec)

    cmd_str = r"\\icgc.local\aplicacions\produccio\DFApplications\gdal321_apps\gdal_translate.bat " \
              r"-of COG -ot UInt16 -co RESAMPLING=NEAREST -a_nodata 0 -co NUM_THREADS=ALL_CPUS -co BIGTIFF=YES -co COMPRESS=LZW {} {} {}" \
             .format(scale_str, vrt_f, out_f)

    print(cmd_str)
    os.system(cmd_str)

def vrt2tif(vrt_f, out_f, scale_fact= None, format=None):
    if scale_fact is None and format is None:
        ds = gdal.Open(vrt_f)
        ds = gdal.Translate(out_f, ds, creationOptions=['COMPRESS=LZW'])
        ds = None

    else:
        vrt_info  = get_im_info(vrt_f,  unpack_im_descr=False)
        out_h = image_output_gen(out_f, vrt_info['Nlines'], vrt_info['Ncolumns'], 1, NP2GDAL_CONVERSION[format],
                                                  DriverName='GTiff', geotransform_info=vrt_info['im_geotransformation'],
                                                  src_proj_info=vrt_info['im_geoprojection'],
                                                  interleave='PIXEL', compression_flag=True,
                                                  im_description='Multiplicative Factor applied to image = {}'.format(scale_fact))
        im_tmp = read_image(vrt_f)*scale_fact
        write_im_band(out_h, im_tmp, 1)
        out_h = None


def overview_gen(image_file, ext_flag=True, ov_list=[2, 4, 8, 16, 32, 64, 128, 256, 512], method = 'NEAREST'):
    if ext_flag:
        img_h = open_image(image_file)
    else:
        img_h = open_image(image_file, 'a')
    gdal.SetConfigOption('COMPRESS_OVERVIEW', 'DEFLATE')
    img_h.BuildOverviews(method, ov_list, gdal.TermProgress_nocb)
    img_h = None


def geojson2gpkg(geojson_dict: dict, epsg_in: int, epsg_out: int, out_f=None, buffer=0):
    gdf = gpd.GeoDataFrame([1], columns=['ID'], geometry=[geojson2shpobj(geojson_dict, buffer=buffer)], crs='EPSG:'+str(epsg_in)).to_crs('EPSG:'+str(epsg_out))
    if out_f is not None:
        gdf.to_file(out_f, driver='GPKG')
    return gdf


def geojson2msk(geojson_dict: dict, epsg_in: int, epsg_out: int, out_f: str, x_res: float, y_res: float, buffer=0):

    gpkg_tmp_f = out_f[:-4]+'.gpkg'
    gdf = geojson2gpkg(geojson_dict, epsg_in, epsg_out, out_f=gpkg_tmp_f, buffer=buffer)
    bbox = {'xmin': float(round(gdf.bounds['minx'][0])), 'xmax': float(round(gdf.bounds['maxx'][0])),
            'ymin': float(round(gdf.bounds['miny'][0])), 'ymax': float(round(gdf.bounds['maxy'][0]))}

    shp2raster_gen(gpkg_tmp_f, out_f, bbox=bbox, xRes=x_res, yRes=y_res, srs=epsg_out)


def geojson2wkt(geojson_dict):
    polygon_wkt = geojson2shpobj(geojson_dict).wkt
    return polygon_wkt


def geojson2shpobj(geojson_dict, buffer=0):
    
    if buffer == 0:
        polygon_shpobj = shape(geojson_dict)
    else:
        res = sorted(geojson_dict['coordinates'][0][:-1], key=lambda x: (x[0], x[1]))
        corner_dict = {'DL': res[0], 'DR': res[1], 'UL': res[2], 'UR': res[3]}
        corner_dict_buffered = {'DL': [corner_dict['DL'][0] - buffer, corner_dict['DL'][1] - buffer],
                                'DR': [corner_dict['DR'][0] + buffer, corner_dict['DL'][1] - buffer],
                                'UL': [corner_dict['UL'][0] - buffer, corner_dict['UL'][1] + buffer],
                                'UR': [corner_dict['UR'][0] + buffer, corner_dict['UR'][1] + buffer]}
        geojson_buffered_dict = {'type': 'Polygon',
                                 'coordinates': [[corner_dict_buffered['UL'],
                                                  corner_dict_buffered['UR'],
                                                  corner_dict_buffered['DR'],
                                                  corner_dict_buffered['DL'],
                                                  corner_dict_buffered['UL']]]}
        print('      * Polygon being dilated by {}'.format(buffer))
        polygon_shpobj = shape(geojson_buffered_dict)
        #polygon_shpobj = polygon_shpobj.buffer(buffer, join_style=2)
    return polygon_shpobj


def geojson2bbox(geojson_dict):
    polygon_bounds = shape(geojson_dict).bounds
    bbox_dict = {'lon_min': polygon_bounds[0],
                 'lon_max': polygon_bounds[2],
                 'lat_min': polygon_bounds[1],
                 'lat_max': polygon_bounds[3]}
    return bbox_dict

def shp2raster_gen(shp_file, raster_outfile, bbox, xRes, yRes, srs):

    shp = ogr.Open(shp_file)
    lyr = shp.GetLayer()
    src_proj = osr.SpatialReference()
    src_proj.ImportFromEPSG(int(srs))

    size = (int((bbox['xmax'] - bbox['xmin']) / xRes), int((bbox['ymax'] - bbox['ymin']) / yRes))
    #src_geo = (bbox['xmin'], (bbox['xmax'] - bbox['xmin']) / size[0], 0.0, bbox['ymax'], 0.0,  (bbox['ymin'] - bbox['ymax']) / size[0])
    src_geo = (bbox['xmin'], xRes, 0.0, bbox['ymax'], 0.0, -yRes)

    dst_ds = gdal.GetDriverByName('GTiff').Create(raster_outfile, size[0], size[1], 1, gdal.GDT_Byte, ['NBITS=1', 'COMPRESS=LZW'])
    dst_ds.SetGeoTransform(src_geo)
    dst_ds.SetProjection(src_proj.ExportToWkt())
    gdal.RasterizeLayer(dst_ds, [1], lyr, burn_values=[255])  # ,options = options)
    dst_ds = None


def getS2image_metadata(image_file, format='ZIP'):
    if format =='ZIP':
        import zipfile

        zf = zipfile.ZipFile(image_file, 'r')

        for name in zf.namelist():
            if name.endswith('/MTD_MSIL1C.xml') or name.endswith('/MTD_MSIL2A.xml'):
                ptr_str = name[-6:-4]
                f = zf.open(name)
                # here you do your magic with [f] : parsing, etc.
                # this will print out file contents
                tree_xml = ET.fromstring(f.read())
                break
    elif format =='SAFE':
        if os.path.basename(image_file).endswith('MTD_MSIL1C.xml') or os.path.basename(image_file).endswith('MTD_MSIL2A.xml'):
            ptr_str = os.path.basename(image_file)[-6:-4]
            with open(image_file,'r') as f:
                tree_xml = ET.fromstring(f.read())

    tmp_dict = tree_xml.attrib
    for _ in tmp_dict:
        Name_space = '{' + tmp_dict[_] + '}'

    #Name_space = '{https://psd-14.sentinel2.eo.esa.int/PSD/User_Product_Level-'+ptr_str+'.xsd}'
    General_Info = Name_space+'General_Info/'
    Geometric_Info = Name_space+'Geometric_Info/'
    Image_Characteristics = General_Info+'Product_Image_Characteristics/'
    Quality_Indicators = Name_space+'Quality_Indicators_Info/'
    physical_gains = Image_Characteristics+'PHYSICAL_GAINS'

    xml_path = {'START_TIME':       General_Info+'Product_Info/PRODUCT_START_TIME',
                   'STOP_TIME':        General_Info + 'Product_Info/PRODUCT_STOP_TIME',
                   'PRODUCT_URI':      General_Info + 'Product_Info/PRODUCT_URI',
                   'PROCESSING_LEVEL': General_Info + 'Product_Info/PROCESSING_LEVEL',
                   'PRODUCT_TYPE':     General_Info + 'Product_Info/PRODUCT_TYPE',
                   'GENERATION_TIME':  General_Info + 'Product_Info/GENERATION_TIME',
                   'SPACECRAFT_NAME':  General_Info + 'Product_Info/Datatake/SPACECRAFT_NAME',
                   'ORBIT_NUMBER':     General_Info +'Product_Info/Datatake/SENSING_ORBIT_NUMBER',
                   'ORBIT_DIRECTION':  General_Info +'Product_Info/Datatake/SENSING_ORBIT_DIRECTION',
                   'FOOTPRINT':        Geometric_Info+'Product_Footprint/Product_Footprint/Global_Footprint/EXT_POS_LIST',
                   'IRRADIANCE' :     Image_Characteristics + '/Reflectance_Conversion/Solar_Irradiance_List/SOLAR_IRRADIANCE',
                   'SPECTRAL'  :      Image_Characteristics + '/Spectral_Information_List/Spectral_Information'}

    S2_info = { key: tree_xml.find(xml_path[key]).text for key in xml_path.keys() if tree_xml.find(xml_path[key]) is not None}

    if ptr_str.upper() == '1C':
        nbands = 13
        S2_info['U']= tree_xml.find(Image_Characteristics + 'Reflectance_Conversion/U').text
        try:
            S2_info['QVALUE']= tree_xml.find(Image_Characteristics + 'Reflectance_Conversion/QUANTIFICATION_VALUE').text
        except:
            S2_info['QVALUE']='10000'
        xml_path['OFFSET'] = Image_Characteristics + '/Radiometric_Offset_List/RADIO_ADD_OFFSET'
        S2_info['OFFSET']= tree_xml.find(Image_Characteristics + '/Radiometric_Offset_List/RADIO_ADD_OFFSET').text
        S2_info['CLOUD_COVERAGE'] = tree_xml.find( Quality_Indicators + 'Cloud_Coverage_Assessment').text
        S2_info['SNOW_COVERAGE']  = tree_xml.find(Quality_Indicators + 'Snow_Coverage_Assessment').text
        S2_info['RADIOM_CALIB'] = {'U': S2_info['U'],
                               'QVALUE': S2_info['QVALUE'],
                               'irr': {'B' + "{:02d}".format(key + 1): tree_xml.find(
                                   xml_path['IRRADIANCE'] + '[@bandId=' + '"{}"]'.format(key)).text for key in
                                       range(nbands)},
                               'spectral': {'B' + "{:02d}".format(key + 1): tree_xml.find(
                                   xml_path['SPECTRAL'] + '[@bandId=' + '"{}"]/Spectral_Response/VALUES'.format(
                                       key)).text for key in range(nbands)},
                               'phys_gains': {'B' + "{:02d}".format(key + 1): tree_xml.find(
                                       physical_gains + '[@bandId=' + '"{}"]'.format(key)).text for key in
                                                  range(nbands)}}
    elif ptr_str.upper() == '2A':
        nbands = 10
        xml_path['OFFSET'] = Image_Characteristics + '/BOA_ADD_OFFSET_VALUES_LIST/BOA_ADD_OFFSET'
        try:
            S2_info['BOA_QUANT_VALUE'] = tree_xml.find(Image_Characteristics + '/QUANTIFICATION_VALUES_LIST/BOA_QUANTIFICATION_VALUE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('BOA_QUANT_VALUE'))
            S2_info['BOA_QUANT_VALUE'] = None

        try:
            S2_info['AOT_QUANT_VALUE'] = tree_xml.find(Image_Characteristics + '/QUANTIFICATION_VALUES_LIST/AOT_QUANTIFICATION_VALUE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('AOT_QUANT_VALUE'))
            S2_info['AOT_QUANT_VALUE'] = None

        try:
            S2_info['WVP_QUANT_VALUE'] = tree_xml.find(Image_Characteristics + '/QUANTIFICATION_VALUES_LIST/WVP_QUANTIFICATION_VALUE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('WVP_QUANT_VALUE'))
            S2_info['WVP_QUANT_VALUE'] = None

        try:
            S2_info['OFFSET'] = tree_xml.find(Image_Characteristics + '/BOA_ADD_OFFSET_VALUES_LIST/BOA_ADD_OFFSET').text
        except:
            print('Parameter {} not found! None value substituted...'.format('OFFSET'))
            S2_info['OFFSET'] = None

        try:
            S2_info['CLOUDY_PIXEL_OVER_LAND_PERCENTAGE'] = tree_xml.find(
                Quality_Indicators + '/Image_Content_QI/CLOUDY_PIXEL_OVER_LAND_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('CLOUDY_PIXEL_OVER_LAND_PERCENTAGE'))
            S2_info['CLOUDY_PIXEL_OVER_LAND_PERCENTAGE'] = tree_xml.find(
                Quality_Indicators + '/Cloud_Coverage_Assessment').text
        try:
            S2_info['NODATA_PIXEL_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/NODATA_PIXEL_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('NODATA_PIXEL_PERCENTAGE'))
            S2_info['NODATA_PIXEL_PERCENTAGE'] = None
        try:
            S2_info['SATURATED_DEFECTIVE_PIXEL_PERCENTAGE']= tree_xml.find(Quality_Indicators + '/Image_Content_QI/SATURATED_DEFECTIVE_PIXEL_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('SATURATED_DEFECTIVE_PIXEL_PERCENTAGE'))
            S2_info['SATURATED_DEFECTIVE_PIXEL_PERCENTAGE'] = None

        try:
            S2_info['DARK_FEATURES_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/DARK_FEATURES_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('DARK_FEATURES_PERCENTAGE'))
            S2_info['DARK_FEATURES_PERCENTAGE'] = None

        try:
            S2_info['CLOUD_SHADOW_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/CLOUD_SHADOW_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('CLOUD_SHADOW_PERCENTAGE'))
            S2_info['CLOUD_SHADOW_PERCENTAGE'] = None

        try:
            S2_info['VEGETATION_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/VEGETATION_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('VEGETATION_PERCENTAGE'))
            S2_info['VEGETATION_PERCENTAGE'] = None

        try:
            S2_info['NOT_VEGETATED_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/NOT_VEGETATED_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('NOT_VEGETATED_PERCENTAGE'))
            S2_info['NOT_VEGETATED_PERCENTAGE'] = None

        try:
            S2_info['WATER_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/WATER_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('WATER_PERCENTAGE'))
            S2_info['WATER_PERCENTAGE'] = None

        try:
            S2_info['UNCLASSIFIED_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/UNCLASSIFIED_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('UNCLASSIFIED_PERCENTAGE'))
            S2_info['UNCLASSIFIED_PERCENTAGE'] = None

        try:
            S2_info['MEDIUM_PROBA_CLOUDS_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/MEDIUM_PROBA_CLOUDS_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('MEDIUM_PROBA_CLOUDS_PERCENTAGE'))
            S2_info['MEDIUM_PROBA_CLOUDS_PERCENTAGE'] = None

        try:
            S2_info['HIGH_PROBA_CLOUDS_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/HIGH_PROBA_CLOUDS_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('HIGH_PROBA_CLOUDS_PERCENTAGE'))
            S2_info['HIGH_PROBA_CLOUDS_PERCENTAGE'] = None

        try:
            S2_info['THIN_CIRRUS_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/THIN_CIRRUS_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('THIN_CIRRUS_PERCENTAGE'))
            S2_info['THIN_CIRRUS_PERCENTAGE'] = None

        try:
            S2_info['SNOW_ICE_PERCENTAGE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/SNOW_ICE_PERCENTAGE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('SNOW_ICE_PERCENTAGE'))
            S2_info['SNOW_ICE_PERCENTAGE'] = None

        try:
            S2_info['RADIATIVE_TRANSFER_ACCURACY'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/RADIATIVE_TRANSFER_ACCURACY').text
        except:
            print('Parameter {} not found! None value substituted...'.format('RADIATIVE_TRANSFER_ACCURACY'))
            S2_info['RADIATIVE_TRANSFER_ACCURACY'] = None

        try:
            S2_info['WATER_VAPOUR_RETRIEVAL_ACCURACY'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/WATER_VAPOUR_RETRIEVAL_ACCURACY').text
        except:
            print('Parameter {} not found! None value substituted...'.format('WATER_VAPOUR_RETRIEVAL_ACCURACY'))
            S2_info['WATER_VAPOUR_RETRIEVAL_ACCURACY'] = None

        try:
            S2_info['AOT_RETRIEVAL_ACCURACY'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/AOT_RETRIEVAL_ACCURACY').text
        except:
            print('Parameter {} not found! None value substituted...'.format('AOT_RETRIEVAL_ACCURACY'))
            S2_info['AOT_RETRIEVAL_ACCURACY'] = None

        try:
            S2_info['AOT_RETRIEVAL_METHOD'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/AOT_RETRIEVAL_METHOD').text
        except:
            print('Parameter {} not found! None value substituted...'.format('AOT_RETRIEVAL_METHOD'))
            S2_info['AOT_RETRIEVAL_METHOD'] = None

        try:
            S2_info['GRANULE_MEAN_AOT'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/GRANULE_MEAN_AOT').text
        except:
            print('Parameter {} not found! None value substituted...'.format('GRANULE_MEAN_AOT'))
            S2_info['GRANULE_MEAN_AOT'] = None

        try:
            S2_info['GRANULE_MEAN_WV'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/GRANULE_MEAN_WV').text
        except:
            print('Parameter {} not found! None value substituted...'.format('GRANULE_MEAN_WV'))
            S2_info['GRANULE_MEAN_WV'] = None

        try:
            S2_info['OZONE_SOURCE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/OZONE_SOURCE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('OZONE_SOURCE'))
            S2_info['OZONE_SOURCE'] = None

        try:
            S2_info['OZONE_VALUE'] = tree_xml.find(Quality_Indicators + '/Image_Content_QI/OZONE_VALUE').text
        except:
            print('Parameter {} not found! None value substituted...'.format('OZONE_VALUE'))
            S2_info['OZONE_VALUE'] = None

        try:
            S2_info['RADIOM_CALIB'] = {'irr': {'B' + "{:02d}".format(key + 1): tree_xml.find(
                                            xml_path['IRRADIANCE'] + '[@bandId=' + '"{}"]'.format(key)).text for key in range(nbands)},
                                  'spectral': {'B' + "{:02d}".format(key + 1): tree_xml.find(
                                            xml_path['SPECTRAL'] + '[@bandId=' + '"{}"]/Spectral_Response/VALUES'.format(key)).text for key in range(nbands)},
                                  'phys_gains': {'B' + "{:02d}".format(key + 1): tree_xml.find(physical_gains + '[@bandId=' + '"{}"]'.format(key)).text for key in range(nbands)}}
        except:
            S2_info['RADIOM_CALIB'] = {}

    offset_check = S2_info['OFFSET']

    if offset_check is None:
        S2_info['RADIOM_CALIB']['ADD_OFFSET'] = {'B' + "{:02d}".format(key + 1): 0 for key in range(nbands)}
    else:
        S2_info['RADIOM_CALIB']['ADD_OFFSET'] = {'B' + "{:02d}".format(key + 1): tree_xml.find(xml_path['OFFSET']+'[@band_id=' + '"{}"]'.format(key)).text for key in range(nbands)}

    return S2_info


def getS2image_info(image_file, res = 10, format='ZIP'):

    if res ==10:
        dset_ind=0
    elif res == 20:
        dset_ind = 1
    elif res==60:
        dset_ind = 2
    else:
        print('Incorrect resolution parameter. Possible options are 10,20 or 60.')
        return 1

    hh = gdal.Open(image_file)
    im_info = get_im_info(hh.GetSubDatasets()[dset_ind][0], unpack_im_descr=False)
    hh = None
    return im_info


def img_dilation(img_in_f, img_out_f, kernel_win, img_info=None):

    if isinstance(img_in_f, str):
        img_info = get_im_info(img_in_f, unpack_im_descr=False)
        img = (read_image(img_in_f)>0).astype(np.uint8)
    else:
        img =  img_in_f.astype(np.uint8)

    kernel = np.ones(kernel_win, np.uint8)
    img_dilation = cv.dilate(img, kernel, iterations=1)

    if img_info is not None:

        out_h = image_output_gen(img_out_f, img_info['Nlines'], img_info['Ncolumns'], 1,img_info['gdal_datatype'],
                                 gdal.GDT_Byte, geotransform_info=img_info['im_geotransformation'],
                                 src_proj_info=img_info['im_geoprojection'],binary_mask=True)
        write_im_band(out_h, img_dilation, 1)
        out_h = None
    else:
        return img_dilation


def apply_fun2image_subsets(img_in, input_fun, fun_parms_list, fun_parms_dict, Nmax_el=2740000, over_elem=100):

    block_list, split_dim, blockjoin_list = split_img_into_nonull_blocks(img_in, Nmax_el=Nmax_el, over_elem=over_elem)

    N_blocks = len(block_list)
    data_out = np.zeros(img_in.shape, dtype=np.single)

    for ind, block in enumerate(block_list):
        progress = float(ind+1) / float(N_blocks)
        sys.stdout.write("\r%s: [%s] %.1f%%" % ('     - Processing ', ('#' * int(progress * 50)).ljust(50), progress * 100))
        out_tmp = input_fun(img_in[block['lin_ini']: block['lin_end'],  block['col_ini']:  block['col_end']], *fun_parms_list, **fun_parms_dict)

        data_out[blockjoin_list[ind]['abs_ind']['lin_ini']: blockjoin_list[ind]['abs_ind']['lin_end'],
                 blockjoin_list[ind]['abs_ind']['col_ini']: blockjoin_list[ind]['abs_ind']['col_end']] = \
         out_tmp[blockjoin_list[ind]['rel_ind']['lin_ini']: blockjoin_list[ind]['rel_ind']['lin_end'],
                 blockjoin_list[ind]['rel_ind']['col_ini']: blockjoin_list[ind]['rel_ind']['col_end']]

    return data_out


def bresenham(x1, y1, x2, y2):
    # https://www.mathworks.com/matlabcentral/fileexchange/28190-bresenham-optimized-for-matlab
    import numpy as np

    x1 = round(x1)
    x2 = round(x2)
    y1 = round(y1)
    y2 = round(y2)
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    steep = abs(dy) > abs(dx)

    if steep:
        dy, dx = dx, dy

    if dy == 0:
        q = np.zeros((dx + 1, 1))
    else:
        q = np.hstack([np.zeros((1,)),
                       np.diff(np.mod(np.arange(np.floor(dx / 2), -dy * (dx + 1) + np.floor(dx / 2), -dy), dx)) >= 0])

    if steep:
        if y1 <= y2:
            y = np.arange(y1, y2 + 1)
        else:
            y = np.arange(y1, y2 - 1, -1)

        if x1 <= x2:
            x = x1 + np.cumsum(q)
        else:
            x = x1 - np.cumsum(q)
    else:
        if x1 <= x2:
            x = np.arange(x1, x2 + 1)
        else:
            x = np.arange(x1, x2 - 1, -1)

        if y1 <= y2:
            y = y1 + np.cumsum(q)
        else:
            y = y1 - np.cumsum(q)

    return [x.astype(np.uint32), y.astype(np.uint32)]


def surfnorm(x_vec, y_vec, zz, eps=1e-12):
    xx, yy = np.meshgrid(x_vec, y_vec)

    stencil1 = np.expand_dims(np.array([1, 0, -1]) / 2, axis=0)
    stencil2 = np.expand_dims(np.array([1, 0, -1]) / 2, axis=1)

    xx = np.vstack([np.expand_dims(3 * xx[0, :] - 3 * xx[1, :] + xx[2, :], axis=0), \
                    xx, \
                    np.expand_dims(3 * xx[-1, :] - 3 * xx[-2, :] + xx[-3, :], axis=0)])

    xx = np.hstack([np.expand_dims(3 * xx[:, 0] - 3 * xx[:, 1] + xx[:, 2], axis=1), \
                    xx, \
                    np.expand_dims(3 * xx[:, -1] - 3 * xx[:, -2] + xx[:, -3], axis=1)])

    yy = np.vstack([np.expand_dims(3 * yy[0, :] - 3 * yy[1, :] + yy[2, :], axis=0), \
                    yy, \
                    np.expand_dims(3 * yy[-1, :] - 3 * yy[-2, :] + yy[-3, :], axis=0)])

    yy = np.hstack([np.expand_dims(3 * yy[:, 0] - 3 * yy[:, 1] + yy[:, 2], axis=1), \
                    yy, \
                    np.expand_dims(3 * yy[:, -1] - 3 * yy[:, -2] + yy[:, -3], axis=1)])

    zz = np.vstack([np.expand_dims(3 * zz[0, :] - 3 * zz[1, :] + zz[2, :], axis=0), \
                    zz, \
                    np.expand_dims(3 * zz[-1, :] - 3 * zz[-2, :] + zz[-3, :], axis=0)])

    zz = np.hstack([np.expand_dims(3 * zz[:, 0] - 3 * zz[:, 1] + zz[:, 2], axis=1), \
                    zz, \
                    np.expand_dims(3 * zz[:, -1] - 3 * zz[:, -2] + zz[:, -3], axis=1)])

    ax = signal.convolve2d(xx, stencil1)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]
    ay = signal.convolve2d(yy, stencil1)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]
    az = signal.convolve2d(zz, stencil1)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]

    bx = signal.convolve2d(xx, stencil2)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]
    by = signal.convolve2d(yy, stencil2)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]
    bz = signal.convolve2d(zz, stencil2)[1:y_vec.shape[0] + 1, 1:x_vec.shape[0] + 1]

    # Perform cross product to get normals
    nx = -(ay * bz - az * by)
    ny = -(az * bx - ax * bz)
    nz = -(ax * by - ay * bx)

    mag = np.sqrt(nx * nx + ny * ny + nz * nz)
    mag[mag == 0] = eps

    nxout = nx / mag
    nyout = ny / mag
    nzout = nz / mag

    return nxout, nyout, nzout


def norm2cosbeta(nx, ny, nz, sun_z_deg, sun_a_deg):
    sun_z = sun_z_deg * np.pi / 180
    sun_a = sun_a_deg * np.pi / 180

    xy2 = np.square(nx) + np.square(ny)
    # zn = np.arctan2(np.sqrt(xy2), nzout) # for elevation angle defined from Z-axis down
    phi_n = np.arctan2(nz, np.sqrt(xy2))  # for elevation angle defined from XY-plane up
    theta_n = np.arctan2(ny, nx)

    cosBeta = np.cos(sun_z) * np.cos(theta_n) + \
              (np.sin(sun_z) * np.sin(theta_n)) * np.cos(sun_a - phi_n)

    return cosBeta


def hdr_info_retrieval(img_f):
    sp.settings.envi_support_nonlowercase_params = True
    metadata_dict = sp.io.envi.open(img_f.replace('.dat', '.hdr')).metadata
    metadata_dict['Wavelength'] = [str(round(float(_), 2)) for _ in metadata_dict['Wavelength']]
    metadata_dict['calibration gain file'] = os.path.basename(metadata_dict['calibration gain file'])
    metadata_dict['LUT file'] = os.path.basename(metadata_dict['LUT file'])
    metadata_dict['raw image file'] = os.path.basename(metadata_dict['raw image file'])
    metadata_dict['dark current image file'] = os.path.basename(metadata_dict['dark current image file'])

    str_info = str(metadata_dict)

    return str_info


def geocoding_process(img_f, geom_f, out_dir=None, output_f=None, im_description_str=None):
    rad_info = get_im_info(img_f, unpack_im_descr=False)
    geo_info = get_im_info(geom_f, unpack_im_descr=False)

    im_line = read_image(geom_f, 0)
    im_col = read_image(geom_f, 1)

    if im_description_str is None:
        im_description_str = hdr_info_retrieval(img_f)

    if output_f is None:
        if out_dir is None:
            out_dir = os.path.dirname(img_f)
        output_f = os.path.join(out_dir, os.path.basename(img_f).replace('_radiance.dat', '_radiance_GEO.tif'))

    img_out_h = image_output_gen(output_f,
                                 geo_info['Nlines'],
                                 geo_info['Ncolumns'],
                                 rad_info['Nbands'],
                                 rad_info['gdal_datatype'],
                                 geotransform_info=geo_info['im_geotransformation'],
                                 src_proj_info=geo_info['im_geoprojection'],
                                 interleave='BAND',
                                 compression_flag=True,
                                 im_description=im_description_str)

    # Temporary image
    im_geo = np.zeros((im_line.shape))

    # Geocoded Image Valid pixels
    II_geo = np.where(im_line > 0)

    # Line and colum index vector of Not-geocoded image corresponding to geocoded image
    II_l = np.round(im_line[II_geo]).astype(np.uint32) - 1
    II_c = np.round(im_col[II_geo]).astype(np.uint32) - 1

    t00 = time.time()
    for i_band in range(rad_info['Nbands']):
        print('Band : {}'.format(i_band))
        band = read_image(img_f, i_band)
        im_geo[II_geo] = band[(II_c, II_l)]
        write_im_band(img_out_h, im_geo, i_band + 1)

    close_im(img_out_h)
    img_out_h = None

    print('\nTotal time [secs] : {}'.format(np.round(time.time() - t00)))

def image2ground(gt, col, row):
    """ Transforma un punt de coordenades imatge a coordenades terra aplicant
        els paràmetres de georeferenciació de la imatge (gdal.GeoTransform).
        Sistema de coordenades imatge GDAL (orígen 0,0 a la cantonada top left)
        Arguments:
            gt: tupla tipus gdal.GeoTransform
            col, row: coordenades imatge (columna, fila)
        Retorna:
            x, y: coordenades terra
    """
    x = gt[0] + col*gt[1] + row*gt[2]
    y = gt[3] + col*gt[4] + row*gt[5]
    return (x, y)


def ground2image(gt, x, y):
    """ Transforma un punt de coordenades terra a coordenades imatge aplicant
        els paràmetres de georeferenciació de la imatge (gdal.GeoTransform).
        Sistema de coordenades imatge GDAL (orígen 0,0 a la cantonada top left)
        Arguments:
            gt: tupla tipus gdal.GeoTransform
            x, y: coordenades terra
        Retorna:
            col, row: coordenades imatge (columna, fila)
    """
    col = (x*gt[5] - y*gt[2] + gt[2]*gt[3] - gt[0]*gt[5]) / float(gt[1]*gt[5] - gt[2]*gt[4])
    row = (x*gt[4] - y*gt[1] + gt[1]*gt[3] - gt[0]*gt[4]) / float(gt[2]*gt[4] - gt[1]*gt[5])
    return (col, row)


def ground2window(gt, ul_x, ul_y, lr_x, lr_y):
    """ Projecta una finestra de coordenades terra sobre una imatge aplicant
        els paràmetres de georeferenciació de la imatge (gdal.GeoTransform).
        Sistema de coordenades imatge GDAL (orígen 0,0 a la cantonada top left)
        Arguments:
            gt: tupla tipus gdal.GeoTransform (ul_x, gsd_x, 0, ul_y, 0, gsd_y)
            ul_x, ul_y: coordenades terra de la cantonada superior esquerra
            lr_x, lr_y: coordenades terra de la cantonada inferior dreta
        Retorna:
            ul_col, ul_row, num_cols, num_rows: paràmetres per gdal.ReadAsArray
    """
    ul_col, ul_row = ground2image(gt, ul_x, ul_y)
    lr_col, lr_row = ground2image(gt, lr_x, lr_y)
    num_cols = lr_col - ul_col + 1
    num_rows = lr_row - ul_row + 1
    return (ul_col, ul_row, num_cols, num_rows)


def surfnorm(x_vec,y_vec,zz, eps =1e-12):
    
    xx, yy = np.meshgrid(x_vec, y_vec)

    stencil1 =np.expand_dims(np.array([1,0,-1])/2, axis=0)
    stencil2 =np.expand_dims(np.array([1,0,-1])/2, axis=1)
    
    xx= np.vstack([np.expand_dims(3*xx[0,:]-3*xx[1,:]+xx[2,:],axis=0),\
                xx,\
                np.expand_dims(3*xx[-1,:]-3*xx[-2,:]+xx[-3,:],axis=0)]) 
    
    
    xx= np.hstack([np.expand_dims(3*xx[:,0]-3*xx[:,1]+xx[:,2],axis=1),\
                xx,\
                np.expand_dims(3*xx[:,-1]-3*xx[:,-2]+xx[:,-3],axis=1)]) 
    
    
    yy= np.vstack([np.expand_dims(3*yy[0,:]-3*yy[1,:]+yy[2,:],axis=0),\
                yy,\
                np.expand_dims(3*yy[-1,:]-3*yy[-2,:]+yy[-3,:],axis=0)]) 
    
    
    yy= np.hstack([np.expand_dims(3*yy[:,0]-3*yy[:,1]+yy[:,2],axis=1),\
                yy,\
                np.expand_dims(3*yy[:,-1]-3*yy[:,-2]+yy[:,-3],axis=1)]) 
        
        
        
    zz= np.vstack([np.expand_dims(3*zz[0,:]-3*zz[1,:]+zz[2,:],axis=0),\
                zz,\
                np.expand_dims(3*zz[-1,:]-3*zz[-2,:]+zz[-3,:],axis=0)]) 
    
    
    zz= np.hstack([np.expand_dims(3*zz[:,0]-3*zz[:,1]+zz[:,2],axis=1),\
                zz,\
                np.expand_dims(3*zz[:,-1]-3*zz[:,-2]+zz[:,-3],axis=1)]) 
       
              
    ax = signal.convolve2d(xx,stencil1)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    ay = signal.convolve2d(yy,stencil1)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    az = signal.convolve2d(zz,stencil1)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    
    bx = signal.convolve2d(xx,stencil2)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    by = signal.convolve2d(yy,stencil2)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    bz = signal.convolve2d(zz,stencil2)[1:y_vec.shape[0]+1,1:x_vec.shape[0]+1]
    
    
    # Perform cross product to get normals
    nx = -(ay*bz - az*by)
    ny = -(az*bx - ax*bz)
    nz = -(ax*by - ay*bx)
    
    
    mag = np.sqrt(nx*nx+ny*ny+nz*nz)
    mag[mag==0]=eps
    
    nxout = nx/mag
    nyout = ny/mag
    nzout = nz/mag

    return nxout, nyout, nzout


def norm2cosbeta(nx,ny,nz,sun_z_deg,sun_a_deg):
    
    sun_z=sun_z_deg*np.pi/180
    sun_a=sun_a_deg*np.pi/180
    
    xy2 = np.square(nx)+np.square(ny)
    #zn = np.arctan2(np.sqrt(xy2), nzout) # for elevation angle defined from Z-axis down
    phi_n = np.arctan2(nz,np.sqrt(xy2)) # for elevation angle defined from XY-plane up
    theta_n = np.arctan2(ny, nx)

    cosBeta =  np.cos(sun_z)*np.cos(theta_n)+\
               (np.sin(sun_z)*np.sin(theta_n))*np.cos(sun_a-phi_n)

    return cosBeta


def hdr_info_retrieval(img_f):

    sp.settings.envi_support_nonlowercase_params = True
    metadata_dict = sp.io.envi.open(img_f.replace('.dat','.hdr')).metadata
    metadata_dict['Wavelength']=[str(round(float(_),2)) for _ in metadata_dict['Wavelength']]
    metadata_dict['calibration gain file']=os.path.basename(metadata_dict['calibration gain file'])
    metadata_dict['LUT file']=os.path.basename(metadata_dict['LUT file'])
    metadata_dict['raw image file']=os.path.basename(metadata_dict['raw image file'])
    metadata_dict['dark current image file']=os.path.basename(metadata_dict['dark current image file'])
    
    str_info = str(metadata_dict)
    
    return str_info


def geocoding_process(img_f,geom_f, out_dir = None, output_f = None, im_description_str = None):

    rad_info = get_im_info(img_f, unpack_im_descr=False)
    geo_info = get_im_info(geom_f, unpack_im_descr=False)
    
    im_line = read_image(geom_f,0)
    im_col  = read_image(geom_f,1)
    
    if im_description_str is None:
         im_description_str = hdr_info_retrieval(img_f)
         
    if output_f is None:
        if out_dir is None:
            out_dir = os.path.dirname(img_f)
        output_f = os.path.join(out_dir,os.path.basename(img_f).replace('_radiance.dat','_radiance_GEO.tif'))    
    
    img_out_h = image_output_gen(output_f,
                                geo_info['Nlines'],  
                                geo_info['Ncolumns'], 
                                rad_info['Nbands'], 
                                rad_info['gdal_datatype'], 
                                geotransform_info = geo_info['im_geotransformation'],
                                src_proj_info     = geo_info['im_geoprojection'],
                                interleave        = 'BAND',
                                compression_flag  = True,
                                im_description    = im_description_str)
    
    # Temporary image
    im_geo = np.zeros((im_line.shape))
    
    # Geocoded Image Valid pixels
    II_geo = np.where(im_line>0)
    
    # Line and colum index vector of Not-geocoded image corresponding to geocoded image
    II_l   = np.round(im_line[II_geo]).astype(np.uint32)-1
    II_c   = np.round(im_col[II_geo]).astype(np.uint32)-1
    
    t00 = time.time()
    for i_band in range(rad_info['Nbands']):
        
        print('Band : {}'.format(i_band))
        band = read_image(img_f,i_band)
        im_geo[II_geo]=band[(II_c,II_l)]
        write_im_band(img_out_h, im_geo, i_band+1)
    
    
    close_im(img_out_h)    
    img_out_h= None
    
    print('\nTotal time [secs] : {}'.format(np.round(time.time() - t00)))


def vector_rasterize(shp, img_info, img_out_f,attr,NoData_value=0, qgis_path=None):
    mb_v = ogr.Open(shp)
    mb_l = mb_v.GetLayer()

    out_h = image_output_gen(img_out_f, img_info['Nlines'], img_info['Ncolumns'], 1,
                             NP2GDAL_CONVERSION['float32'], geotransform_info=img_info['im_geotransformation'],
                             src_proj_info=img_info['im_geoprojection'])
    band = out_h.GetRasterBand(1)
    band.SetNoDataValue(NoData_value)
    band.FlushCache()
    gdal.RasterizeLayer(out_h, [1], mb_l, options=["ATTRIBUTE=" + attr])
    out_h = None

    """if qgis_path is None:
        mb_v = ogr.Open(shp)
        mb_l = mb_v.GetLayer()

        out_h = image_output_gen(img_out_f, img_info['Nlines'], img_info['Ncolumns'],1,
                                 NP2GDAL_CONVERSION['float32'], geotransform_info=img_info['im_geotransformation'],
                                 src_proj_info=img_info['im_geoprojection'])
        band = out_h.GetRasterBand(1)
        band.SetNoDataValue(NoData_value)
        band.FlushCache()
        gdal.RasterizeLayer(out_h, [1], mb_l,  options=["ATTRIBUTE="+attr])
        out_h = None
    else:
        str_cmd = os.path.basename(qgis_path) + ' -l {} -a {} -tr {} {} -a_nodata 0 -te {} {} {} {} -ot Float32 -of GTiff {} {}'.format(
            os.path.basename(shp).split('.')[0],
            'Norm',
            img_info['dx'],
            img_info['dx'],  img_info['xmin'], img_info['ymin'], img_info['xmax'], img_info['ymax'], shp, img_out_f)"""

    """gdal.Rasterize(mb_v,out_h,
    xRes =  img_info['dx'], yRes =  img_info['dx'],
    outputBounds = [img_info['xmin'], img_info['ymin'], img_info['xmax'], img_info['ymax']],
    noData = NoData_value,
    outputType = gdal.GDT_Float32,
    allTouched = True)


    out_h = None
"""


def open_image(image_file, mode='r'):
    """
    Function opening an image (in reading -default- or appending mode) and returning a gdal handle-object to it.

    Args:
        image_file [str]: fullname of the image-file to be opened
        mode       [str]: mode defining how to open the image (r=ReadOnly, a=Append)

    Returns:
        src_ds     [obj] : Gdal-handle object
    """
    if mode.lower() == 'r':
        im_access = gdalconst.GA_ReadOnly
    elif mode.lower() == 'a':
        im_access = gdalconst.GA_Update

    # Open a set of images using GDAL and return a list of handles to them
    if not os.path.isfile(image_file) and not image_file.startswith('SENTINEL2_'):
        raise UserWarning("Image not found: {}".format(image_file))
        src_ds = None
    else:
        src_ds = gdal.Open(image_file, im_access)
        if not src_ds:
            raise UserWarning("GDAL cannot open the image : {}".format(image_file))

    return src_ds


def get_im_info(image_f, unpack_im_descr=False):
    """
     Function retrieving image main information  (SIZE) and Geoinformation using GDAL APIs

     Args:
         image_file [str]: fullname of the image-file to be opened

     Returns:
         im_info    [dict] : Image info in dictionary format
     """
    image_h = open_image(image_f)

    im_geoprojection = image_h.GetProjection()
    im_geotransform = image_h.GetGeoTransform()

    im_info = {'Nlines': image_h.RasterYSize,
               'Ncolumns': image_h.RasterXSize,
               'Nbands': image_h.RasterCount,
               'x0': im_geotransform[0],
               'dx': im_geotransform[1],
               'y0': im_geotransform[3],
               'dy': im_geotransform[5],
               'gdal_datatype': image_h.GetRasterBand(1).DataType,
               'numpy_datatype': GDAL2NP_CONVERSION[image_h.GetRasterBand(1).DataType]}

    if im_geoprojection == '':
        im_info['geoinfo_flag'] = False
    else:
        im_info['geoinfo_flag'] = True
        im_info['im_geotransformation'] = image_h.GetGeoTransform()
        im_info['im_geoprojection'] = image_h.GetProjection()
        proj = osr.SpatialReference(wkt=image_h.GetProjection())
        im_info['EPSG_code'] = int(proj.GetAttrValue('AUTHORITY', 1))
        im_info['xmin'] = im_info['x0']
        im_info['xmax'] = im_info['x0'] + (im_info['Ncolumns']) * im_info['dx']
        im_info['ymin'] = im_info['y0'] + (im_info['Nlines']) * im_info['dy']
        im_info['ymax'] = im_info['y0']
        im_info['bbox'] = {key: im_info[key] for key in ['xmin', 'ymin', 'xmax', 'ymax']}
        im_info['wkt'] = bbox2wkt(im_info['bbox'])
        if im_info['EPSG_code'] != '4326':
            im_info['wkt_geo'], im_info['center_geo'] = bbox2wkt_utm2geo(im_info['bbox'], im_info['EPSG_code'])
            
        if unpack_im_descr:
            if 'TIFFTAG_IMAGEDESCRIPTION' in image_h.GetMetadata().keys():
                str_info = image_h.GetMetadata()['TIFFTAG_IMAGEDESCRIPTION'].split('\n')
    
                if 'TIFFTAG_SOFTWARE' in image_h.GetMetadata().keys():
                # This condition takes into account header written by Ramon's code, which is slighlty differetn form python
                # libraries dealing with ENVI header file. Otherwise, in order to avoid this, the .hdr of Radiance file should be always provided
                    str_info_out=[]
                    for ind in range(len(str_info)):
                        line=str_info[ind]
                        if len(line)>0:
                            if line[-1]=='{' :
                                #key_tmp=line.split(' = ')[0]
                                tmp=[line]
                            elif line[-1]=='}' and not '{' in line:
                                tmp.append(line)
                                str_info_out.append(''.join(tmp))
                            elif not '=' in line:
                                tmp.append(line)
                            else:
                                str_info_out.append(line)
                    try:
                        a, b = zip(
                            *(s.split(" = ") for s in str_info_out if ' = ' in s))
                    except:
                        a, b = zip(
                         *(s.split("=") for s in [_ for _ in image_h.GetMetadata()['TIFFTAG_IMAGEDESCRIPTION'].split(';')][:-2]))
                else:
                    try:
                        a, b = zip(*(s.split(" = ") for s in str_info if ' = ' in s))
                    except :
                        im_info['imagedescription'] = image_h.GetMetadata()['TIFFTAG_IMAGEDESCRIPTION']
                        return im_info
                    
                im_info['imagedescription'] = {k: v for k, v in zip(a, b)}
            else:
                im_info['imagedescription'] = image_h.GetMetadata()['TIFFTAG_IMAGEDESCRIPTION']

        # if 'TIFFTAG_IMAGEDESCRIPTION' in image_h.GetMetadata().keys():
        #     a, b = zip(
        #         *(s.split("=") for s in [_ for _ in image_h.GetMetadata()['TIFFTAG_IMAGEDESCRIPTION'].split(';')][:-2]))
        #     im_info['imagedescription'] = {k: v for k, v in zip(a, b)}

        # image_h = None
        # if TF_flag:
        #     TIFFTAG_GDAL_METADATA = {}
        #     temp_tiff=TF(image_f).pages[0].tags
            
        #     if 42112 in temp_tiff.keys():
                
        #         gdal_info= temp_tiff[42112].value.split('\n')
                
        #         for ind in range(len(gdal_info)):
        #             line=gdal_info[ind]
                
        #             if line[-1]=='{' and not '}' in line:
        #                 key_tmp=line.split('=')[0]
        #                 tmp=[]
        #             elif line[-1]=='}' and not '{' in line:
        #                 TIFFTAG_GDAL_METADATA[key_tmp]='['+''.join(tmp) +']'
        #                 del key_tmp, tmp
        #             elif not '=' in line:
        #                 tmp.append(line)
        #             else:
        #                 TIFFTAG_GDAL_METADATA[line.split('=')[0]]=line.split('=')[1]
            
            
        #     im_info['TIFFTAG_GDAL_METADATA']=TIFFTAG_GDAL_METADATA

    return im_info


def create_vrt_file(vrt_f, image_list, im_resolution=None,
                    im_outputBounds=None,
                    im_xRes=None, im_yRes=None,
                    im_targetAlignedPixels=None,
                    im_separate=None,
                    im_bandList=None,
                    im_addAlpha=None,
                    im_resampleAlg=None,
                    im_outputSRS=None,
                    im_allowProjectionDifference=None,
                    im_srcNodata=None,
                    im_VRTNodata=0,
                    im_hideNodata=None):
    """
     Function generating GDAL Virtual Raster Image. This is thought for reading image subsets and apply interpolation step to a desired spatial resolution at once.

     Args:
         vrt_f       [str]: output virtual file
         image_list [list]: list of image to be used as input for the virtual file construction
         list of VRTBuild params....
     Returns:
         out    [str] : Output of BuildVRT function
     """

    options_vec = gdal.BuildVRTOptions(resolution=im_resolution, outputBounds=im_outputBounds, xRes=im_xRes,
                                       yRes=im_yRes, targetAlignedPixels=im_targetAlignedPixels, separate=im_separate,
                                       bandList=im_bandList, addAlpha=im_addAlpha, resampleAlg=im_resampleAlg,
                                       outputSRS=im_outputSRS, allowProjectionDifference=im_allowProjectionDifference,
                                       srcNodata=im_srcNodata, VRTNodata=im_VRTNodata, hideNodata=im_hideNodata)

    out = gdal.BuildVRT(vrt_f, image_list, options=options_vec)
    if out is not None:
        out.FlushCache()
        out = None

    return out


def add_BIAS2vrt(vrt_f, offset, band_type=2):
    # NP2GDAL_CONVERSION = {"int8": 1, "uint16": 2, "int16": 3, "uint32": 4, "int32": 5, "float32": 6, "float64": 7,
    #                      "complex64": 10, "complex128": 11}

    with open(vrt_f) as f:
        xml_str = f.read()
    xml_str = xml_str.replace('<SimpleSource', '<ComplexSource')
    xml_str = xml_str.replace('</SimpleSource>', '</ComplexSource>')
    if band_type == 2:
        xml_str = xml_str.replace('<VRTRasterBand dataType="UInt16" band="1">',
                                  '  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">')
        xml_str = xml_str.replace('</VRTRasterBand>\n  <VRTRasterBand dataType="UInt16" band="2">\n', '')
        dtype_out = "'UInt16'" 
    elif band_type == 6:
        xml_str = xml_str.replace('<VRTRasterBand dataType="Float32" band="1">',
                                  '  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">')
        xml_str = xml_str.replace('</VRTRasterBand>\n  <VRTRasterBand dataType="Float32" band="2">\n', '')
        dtype_out = "'Float32'" 

    xml_str = xml_str.replace('<NoDataValue>0</NoDataValue>', '')

    os.remove(vrt_f)
    vrt_func = 'np.array(in_ar[0],dtype=float) -'.format(offset)

    xml_str = xml_str.replace('</VRTRasterBand>\n</VRTDataset>\n', """   <PixelFunctionLanguage>Python</PixelFunctionLanguage>
        <PixelFunctionType>pyfun</PixelFunctionType>
        <PixelFunctionCode>
          <![CDATA[
    import numpy as np
    def pyfun(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize,
                       raster_ysize, buf_radius, gt, **kwargs):
        """ + vrt_func + """, dtype = XXX, out = out_ar )
    ]]>
        </PixelFunctionCode>
      </VRTRasterBand>
    </VRTDataset>""").replace('XXX',dtype_out)

    with open(vrt_f, 'w') as f:
        f.write(xml_str)

    xml_str = None


def add_VI2vrt(vrt_f, index_fun,band_type = 2):
    #NP2GDAL_CONVERSION = {"int8": 1, "uint16": 2, "int16": 3, "uint32": 4, "int32": 5, "float32": 6, "float64": 7,
    #                      "complex64": 10, "complex128": 11}

    with open(vrt_f) as f:
        xml_str = f.read()
    xml_str = xml_str.replace('<SimpleSource', '<ComplexSource')
    xml_str = xml_str.replace('</SimpleSource>', '</ComplexSource>')
    if band_type == 2:
        xml_str = xml_str.replace('<VRTRasterBand dataType="UInt16" band="1">',
                                  '  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">')
        xml_str = xml_str.replace('</VRTRasterBand>\n  <VRTRasterBand dataType="UInt16" band="2">\n', '')

    elif band_type == 6:
        xml_str = xml_str.replace('<VRTRasterBand dataType="Float32" band="1">',
                                  '  <VRTRasterBand dataType="Float32" band="1" subClass="VRTDerivedRasterBand">')
        xml_str = xml_str.replace('</VRTRasterBand>\n  <VRTRasterBand dataType="Float32" band="2">\n', '')

    xml_str = xml_str.replace('<NoDataValue>0</NoDataValue>', '')

    os.remove(vrt_f)
    if index_fun.upper() == 'NDVI':
        vrt_func = 'np.divide( np.subtract(np.array(in_ar[1],dtype=float),np.array(in_ar[0],dtype=float)) , np.sum(np.array(in_ar,dtype=float),axis = 0)'
    elif index_fun.upper() == 'RVI':
        vrt_func = 'np.divide(np.multiply(np.array(4.0,dtype=float),np.array(in_ar[0],dtype=float)) , np.sum(np.array(in_ar,dtype=float),axis = 0)'
    elif index_fun.upper() == 'RATIO':
        vrt_func = 'np.divide(np.array(in_ar[0],dtype=float) , np.array(in_ar[1],dtype=float)'
    elif index_fun.upper() == 'OFFSET':
        vrt_func = 'np.array(in_ar[0],dtype=float) - 1000'
        
    xml_str = xml_str.replace('</VRTRasterBand>\n</VRTDataset>\n', """   <PixelFunctionLanguage>Python</PixelFunctionLanguage>
        <PixelFunctionType>pyfun</PixelFunctionType>
        <PixelFunctionCode>
          <![CDATA[
    import numpy as np
    def pyfun(in_ar, out_ar, xoff, yoff, xsize, ysize, raster_xsize,
                       raster_ysize, buf_radius, gt, **kwargs):
        """ + vrt_func + """, dtype = 'Float32', out = out_ar )
    ]]>
        </PixelFunctionCode>
      </VRTRasterBand>
    </VRTDataset>""")

    with open(vrt_f, 'w') as f:
        f.write(xml_str)

    xml_str = None

def create_img_subset(input_f, output_f,xRes,yRes,bbox,resampleAlg='nearest'):

    ds_in = open_image(input_f)
    bbox_list = [bbox['xmin'], bbox['ymax'], bbox['xmax'], bbox['ymin']]
    options = gdal.TranslateOptions(xRes=xRes, yRes=yRes, projWin=bbox_list,resampleAlg=resampleAlg, metadataOptions=['-co NBITS=1'])

    out_ds =  gdal.Translate(output_f,ds_in,options=options)
    out_ds = None




def create_vrt_subset(vrt_f, image_list, bbox, im_xRes, im_yRes, im_resampAlg, separate=True, im_VRTNodata=0, im_srcNodata=0):

    """
        Function creating GDAL Virtual Raster Image form input image list and region-to-crop extension (in the same reference as the output)

        Args:
            vrt_f       [str]: output virtual file
            image_list [list]: list of image to be used as input for the virtual file construction
            bbox_coord [dict]: dictionary of COORDINATES of the bounding box to crop
                            (# bbox = {minx: value, miny: value, maxx: value, maxy: value})
            im_xRes    [float]: Image resolution along X-direction
            im_yRes    [float]: Image resolution along Y-direction
            im_resampleAlg [GDAL opt] : interpolation function for image downscaling/upscaling
                            Resampling method to use. Available methods are:
                                near: nearest neighbour resampling (default, fastest algorithm, worst interpolation quality).
                                bilinear: bilinear resampling.
                                cubic: cubic resampling.
                                cubicspline: cubic spline resampling.
                                lanczos: Lanczos windowed sinc resampling.
                                average: average resampling, computes the weighted average of all non-NODATA contributing pixels.
                                mode: mode resampling, selects the value which appears most often of all the sampled points.
                                max: maximum resampling, selects the maximum value from all non-NODATA contributing pixels.
                                min: minimum resampling, selects the minimum value from all non-NODATA contributing pixels.
                                med: median resampling, selects the median value of all non-NODATA contributing pixels.
                                q1: first quartile resampling, selects the first quartile value of all non-NODATA contributing pixels.
                                q3: third quartile resampling, selects the third quartile value of all non-NODATA contributing pixels.
                                sum: compute the weighted sum of all non-NODATA contributing pixels (since GDAL 3.1)
        Returns:
            out    [str] : Output of BuildVRT function
    """
    if im_resampAlg in INTERP_ALGORITHMs:

        bbox_list = [bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']]
        if isinstance(image_list, str) or  isinstance(image_list, list) and len(image_list)==1:
            separate=False
        out = create_vrt_file(vrt_f, image_list, im_outputBounds=bbox_list,
                              im_xRes=im_xRes, im_yRes=im_yRes,
                              im_resampleAlg=im_resampAlg, im_separate=separate, im_VRTNodata=im_VRTNodata,im_srcNodata=im_srcNodata )
        if out is not None:
            out.FlushCache()

    else:
        print('Interpolation method required not available. Available methods:')
        print(list(INTERP_ALGORITHMs.keys()))
        out = -1

    return out


def get_image_EPSG_code(image_f):
    image_h = open_image(image_f)
    proj = osr.SpatialReference(wkt=image_h.GetProjection())
    EPSG_code = proj.GetAttrValue('AUTHORITY', 1)

    return EPSG_code


def read_image(image_f, band_vec=None):
    """
        Function to read a whole image
        Args:
            image_f  [str]: input image to be read
            band_ind [list] : list of 0-based indexes of bands to be read. If None, all the bands are read
        Returns:
            data  [narray]: whole image in np.array format
    """
    image_h = open_image(image_f)
    data_type = image_h.GetRasterBand(1).DataType

    if band_vec is None:
        band_vec = range(image_h.RasterCount)
        Nbands = image_h.RasterCount
    elif isinstance(band_vec, np.number) or isinstance(band_vec, int):
        band_vec = [int(band_vec)]
        Nbands = len(band_vec)
    else:
        Nbands = len(band_vec)

    data = np.zeros([image_h.RasterYSize, image_h.RasterXSize, Nbands], GDAL2NP_CONVERSION[data_type])
    band_cnt = 0
    for i_band in band_vec:
        data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray()
        band_cnt += 1

    image_h = None

    if Nbands == 1:
        data = np.squeeze(data)

    return data

def read_pixel_by_lincol(image_f, col,lin, band_ind=None):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f     [str]: input image to be read
            bbox_coord [dict]: dictionary of COORDINATES of the bounding box to crop
                            (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
            band_ind [list] : list of 0-based indexes of bands to be read. If None, all the bands are read

        Returns:
            data     [narray]: whole image in np.array format
    """
    im_info = get_im_info(image_f, unpack_im_descr=False)

    if band_ind is None:
        band_ind = list(range(im_info['Nbands']))
        Nbands = im_info['Nbands']

    elif isinstance(band_ind, np.number) or isinstance(band_ind, int):
        band_ind = [int(band_ind)]
        Nbands = len(band_ind)

    data = np.zeros([1, 1, Nbands], GDAL2NP_CONVERSION[im_info['gdal_datatype']])

    band_cnt = 0
    image_h = open_image(image_f)
    for i_band in band_ind:
        data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray(round(col), round(lin),1, 1)
        band_cnt += 1

        if Nbands == 1:
            data = np.squeeze(data)
    image_h = None

    return data

def read_pixel_by_coordinates(image_f, xp,yp, band_ind=None):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f     [str]: input image to be read
            bbox_coord [dict]: dictionary of COORDINATES of the bounding box to crop
                            (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
            band_ind [list] : list of 0-based indexes of bands to be read. If None, all the bands are read

        Returns:
            data     [narray]: whole image in np.array format
    """
    im_info = get_im_info(image_f, unpack_im_descr=False)

    if band_ind is None:
        band_ind = list(range(im_info['Nbands']))
        Nbands = im_info['Nbands']

    elif isinstance(band_ind, np.number) or isinstance(band_ind, int):
        band_ind = [int(band_ind)]
        Nbands = len(band_ind)

    x_vec = np.arange(im_info['xmin'], im_info['xmax'], im_info['dx'])
    if im_info['dy'] > 0:
        y_start = im_info['ymin']
        y_stop = im_info['ymax']
    else:
        y_start = im_info['ymax']
        y_stop = im_info['ymin']

    y_vec = np.arange(y_start, y_stop, im_info['dy'])

    ind_x = np.argmin(np.abs(x_vec - xp))
    ind_y = np.argmin(np.abs(y_vec - yp))

    if all((ind_x.size, ind_y.size)):
        data = np.zeros([ind_y.size, ind_x.size, Nbands], GDAL2NP_CONVERSION[im_info['gdal_datatype']])

        band_cnt = 0
        image_h = open_image(image_f)
        for i_band in band_ind:
            data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray(int(np.min(ind_x)), int(np.min(ind_y)),
                                                                                 ind_x.size, ind_y.size)
            band_cnt += 1

        image_h = None

        if Nbands == 1:
            data = np.squeeze(data)
    else:
        data = None

    return data
    
def get_index_subset_by_coordinates(image_f, bbox_coord):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f     [str]: input image to be read
            bbox_coord [dict]: dictionary of COORDINATES of the bounding box to crop
                            (# bbox = {minx: value, miny: value, maxx: value, maxy: value})
            band_ind [list] : list of 0-based indexes of bands to be read. If None, all the bands are read

        Returns:
            data     [narray]: whole image in np.array format
    """
    im_info = get_im_info(image_f, unpack_im_descr = False)
    x_vec = np.arange(im_info['xmin'], im_info['xmax'], im_info['dx'])
    if im_info['dy'] > 0:
        y_start = im_info['ymin']
        y_stop = im_info['ymax']
    else:
        y_start = im_info['ymax']
        y_stop = im_info['ymin']

    y_vec = np.arange(y_start, y_stop, im_info['dy'])

    ind_x = np.argwhere((x_vec >= bbox_coord['xmin']) & (x_vec <= bbox_coord['xmax']))
    ind_y = np.argwhere((y_vec >= bbox_coord['ymin']) & (y_vec <= bbox_coord['ymax']))


    ind_info = {'x0':int(np.min(ind_x)),'y0': int(np.min(ind_y)),'xsize':ind_x.size,'ysize':ind_y.size}

    return ind_info


def get_point_lc_index(image_f, coord_list):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f     [str]: input image to be read
            coord_list  [list]: list of points coordinates lists in (Lon, lat) or (XUTM, YUTM) order

        Returns:
            lc_list   [list]: list of points' line-column index
    """
    im_info = get_im_info(image_f, unpack_im_descr=False)

    if not isinstance(coord_list[0], list):
        coord_list = [coord_list]
        single_point_flag = True
    else:
        single_point_flag = False

    x_vec = np.arange(im_info['xmin'], im_info['xmax'], im_info['dx'])
    if im_info['dy'] > 0:
        y_start = im_info['ymin']
        y_stop = im_info['ymax']
    else:
        y_start = im_info['ymax']
        y_stop = im_info['ymin']

    y_vec = np.arange(y_start, y_stop, im_info['dy'])

    cl_list = []
    for point in coord_list:
        ind_x = np.argmin(np.abs(x_vec - point[1]))
        ind_y = np.argmin(np.abs(y_vec - point[0]))
        cl_list.append([ind_x, ind_y])

    if single_point_flag:
        cl_list = cl_list[0]
    return cl_list

def read_img_subset_by_coordinates(image_f, bbox_coord, band_ind=None):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f     [str]: input image to be read
            bbox_coord [dict]: dictionary of COORDINATES of the bounding box to crop
                            (# bbox = {minx: value, miny: value, maxx: value, maxy: value})
            band_ind [list] : list of 0-based indexes of bands to be read. If None, all the bands are read

        Returns:
            data     [narray]: whole image in np.array format
    """
    im_info = get_im_info(image_f, unpack_im_descr = False)

    if band_ind is None:
        band_ind = list(range(im_info['Nbands']))
        Nbands = im_info['Nbands']

    elif isinstance(band_ind, np.number) or isinstance(band_ind, int):
        band_ind = [int(band_ind)]
        Nbands = len(band_ind)

    x_vec = np.arange(im_info['xmin'], im_info['xmax'], im_info['dx'])
    if im_info['dy'] > 0:
        y_start = im_info['ymin']
        y_stop = im_info['ymax']
    else:
        y_start = im_info['ymax']
        y_stop = im_info['ymin']

    y_vec = np.arange(y_start, y_stop, im_info['dy'])

    ind_x = np.argwhere((x_vec >= bbox_coord['xmin']) & (x_vec <= bbox_coord['xmax']))
    ind_y = np.argwhere((y_vec >= bbox_coord['ymin']) & (y_vec <= bbox_coord['ymax']))

    if all((ind_x.size, ind_y.size)):
        data = np.zeros([ind_y.size, ind_x.size, Nbands], GDAL2NP_CONVERSION[im_info['gdal_datatype']])

        band_cnt = 0
        image_h = open_image(image_f)
        for i_band in band_ind:
            data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray(int(np.min(ind_x)), int(np.min(ind_y)),
                                                                                 ind_x.size, ind_y.size)
            band_cnt += 1

        image_h = None

        if Nbands == 1:
            data = np.squeeze(data)

    else:
        data = None

    return data


def read_img_subset_by_indexes(image_f, bbox_ind, band_ind=None):
    """
        Function to read a subset of input image defining the coordinates bounding box
        Args:
            image_f  [str]: input image to be read
            bbox_ind [dict]: dictionary of INDEXES of the bounding box to crop
                            (# bbox = {col_start: value, line_start: value, col_stop: value, line_stop: value})
        Returns:
            data  [narray]: whole image in np.array format
    """

    im_info = get_im_info(image_f, unpack_im_descr=False)

    if band_ind is None:
        band_ind = list(range(im_info['Nbands']))
        Nbands = im_info['Nbands']
    elif isinstance(band_ind, np.number) or isinstance(band_ind, int):
        band_ind = [int(band_ind)]
        Nbands = len(band_ind)
    else:
        Nbands = len(band_ind)

    nl_sub = bbox_ind['line_stop'] - bbox_ind['line_start'] + 1
    nc_sub = bbox_ind['col_stop'] - bbox_ind['col_start'] + 1
    data = np.zeros([nl_sub, nc_sub, Nbands], GDAL2NP_CONVERSION[im_info['gdal_datatype']])

    image_h = open_image(image_f)

    band_cnt = 0
    for i_band in band_ind:
        """if Nbands == 1:
            data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray(bbox_ind['col_start'],
                                                                               bbox_ind['line_start'], nc_sub, nl_sub)

        else:"""

        data[:, :, band_cnt] = image_h.GetRasterBand(i_band + 1).ReadAsArray(bbox_ind['col_start'],
                                                                               bbox_ind['line_start'], nc_sub, nl_sub)
        band_cnt += 1

    image_h = None

    if Nbands == 1:
        data = np.squeeze(data)

    return data


def get_epsg_transform(inputEPSG, outputEPSG):
    ssrc = osr.SpatialReference()
    ssrc.ImportFromEPSG(inputEPSG)  # the output must be 0 instead of 6
    tsrs = osr.SpatialReference()
    tsrs.ImportFromEPSG(outputEPSG)  # the output must be 0 instead of 6

    # create coordinate transformation
    transform = osr.CoordinateTransformation(ssrc, tsrs)
    return transform


def utm2geo_transf(utm_EPSG):
    transform = get_epsg_transform(utm_EPSG, 4326)
    return transform


def geo2utm_transf(utm_EPSG):
    transform = get_epsg_transform(4326, utm_EPSG)
    return transform


def bbox2wkt(bbox):
    wkt_str = 'POLYGON (( ' + str(bbox['xmin']) + ' ' + str(bbox['ymax']) + ',' + str(bbox['xmax']) + ' ' + str(
        bbox['ymax']) + ',' + str(bbox['xmax']) + ' ' + str(bbox['ymin']) + ',' + str(bbox['xmin']) + \
              ' ' + str(bbox['ymin']) + str(bbox['xmin']) + ' ' + str(bbox['ymax']) + '))'

    return wkt_str


def bbox2wkt_utm2geo(bbox_in, utm_EPSG):
    transform = utm2geo_transf(utm_EPSG)

    UL_corner = transform.TransformPoint(bbox_in['xmin'], bbox_in['ymax'], 0.0)
    DR_corner = transform.TransformPoint(bbox_in['xmax'], bbox_in['ymin'], 0.0)

    #bbox = {'Lon_min': UL_corner[0], 'Lat_min': DR_corner[1], 'Lon_max': DR_corner[0], 'Lat_max': UL_corner[1]}
    bbox = {'Lon_min': UL_corner[1], 'Lat_min': DR_corner[0], 'Lon_max': DR_corner[1], 'Lat_max': UL_corner[0]}

    geo_center = {'lon_mean' : (bbox['Lon_max']+bbox['Lon_min'])/2,
                  'lat_mean' : (bbox['Lat_max'] + bbox['Lat_min']) / 2}

    wkt_str = 'POLYGON (( ' + str(bbox['Lon_min']) + ' ' + str(bbox['Lat_max']) + ',' + str(
        bbox['Lon_max']) + ' ' + str(bbox['Lat_max']) + ',' + str(bbox['Lon_max']) + ' ' + str(bbox['Lat_min']) + \
              ',' + str(bbox['Lon_min']) + ' ' + str(bbox['Lat_min']) + str(bbox['Lon_min']) + ' ' + str(
        bbox['Lat_max']) + '))'

    return wkt_str, geo_center


def bbox2wkt_geo2utm(bbox_in, utm_EPSG):
    transform = geo2utm_transf(utm_EPSG)

    UL_corner = transform.TransformPoint(bbox_in['Lon_min'], bbox_in['Lat_max'], 0.0)
    DR_corner = transform.TransformPoint(bbox_in['Lon_max'], bbox_in['Lat_min'], 0.0)

    bbox = {'xmin': UL_corner[0], 'ymin': DR_corner[1], 'xmax': DR_corner[0], 'ymax': UL_corner[1]}

    wkt_str = 'POLYGON (( ' + str(bbox['xmin']) + ' ' + str(bbox['ymax']) + ',' + str(bbox['xmax']) + ' ' + str(
        bbox['ymax']) + ',' + str(bbox['xmax']) + ' ' + str(bbox['ymin']) + ',' + str(bbox['xmin']) + \
              ' ' + str(bbox['ymin']) + str(bbox['xmin']) + ' ' + str(bbox['ymax']) + '))'


def retrieve_singleband_reflectance(data_band, Lg1, Lg2, Lo1, Lo2, valid_ind=None, p1=0.05, p2=0.6,
                                    rad_conv_param=1 / 1e3, adj_win=3):
    if valid_ind is None:  # Non-valid radiance pixels are expected to be geocorrected with -9999.0 value
        valid_ind = np.where(data_band > 0)

    # Retrieved reflectance matrix is initialized
    #p = np.zeros(data_band.shape, dtype=float)
    p = np.full(data_band.shape, -0.9999, dtype=float)

    Lg1 = Lg1[valid_ind]
    Lg2 = Lg2[valid_ind]
    Lo1 = Lo1[valid_ind]
    Lo2 = Lo2[valid_ind]

    S0 = (Lg1 * p2 - Lg2 * p1) / (p1 * p2 * (Lg1 - Lg2))
    A0 = Lg1 * (1 - p1 * S0) / p1

    M11 = p1 / (1 - p1 * S0)
    M12 = 1
    M21 = p2 / (1 - p2 * S0)
    M22 = 1

    X01 = Lo1
    X02 = Lo2

    La = (X02 * M11 - M21 * X01) / (M11 * M22 - M12 * M21)
    B = (X01 - M12 * La) / M11

    core = np.full((2 * adj_win + 1, 2 * adj_win + 1), 1 / (2 * adj_win + 1) ** 2)
    Le = signal.convolve2d(data_band * rad_conv_param, core, mode='same')
    pe = (Le[valid_ind] - La) / (A0 + B + S0 * (Le[valid_ind] - La))
    p[valid_ind] = ((data_band[valid_ind] * rad_conv_param - La) * (1 - pe * S0) - pe * B) / A0

    return p


def split_img_into_nonull_blocks(img_in, Nmax_el=2740000, over_elem=100):

    cost_shape = img_in.shape

    Ind_max = np.argmax(cost_shape)
    Ind_min = np.argmin(cost_shape)

    print('          - Input IMAGE dimension Lin/Col : ({},{})'.format(cost_shape[0], cost_shape[1]))
    print('          - Maximum # of pixels per block : {}'.format(Nmax_el))
    split_dim = 'Y' if Ind_max == 0 else 'X'

    # Test Block
    img_ref = img_in > 0

    cnt_tmp = 0
    ind_ini = 0
    ind_end = None
    block_list = []
    step = int(over_elem / 2)

    for ind_search in range(cost_shape[Ind_max]):

        if split_dim == 'Y':
            cnt_tmp += np.where(img_ref[ind_search, :])[0].size
        else:
            cnt_tmp += np.where(img_ref[:, ind_search])[0].size
        if cnt_tmp < Nmax_el:
            continue
        else:
            ind_end = ind_search

            if ind_ini > step:
                ind_ini -= step

            if ind_end + step <= cost_shape[Ind_max]:
                ind_ini_new = ind_end - step
                ind_end += step
            elif cost_shape[Ind_max] - ind_end < step:

                ind_end = cost_shape[Ind_max]
                ind_ini_new = None

            if split_dim == 'Y':
                nd_subset = np.where(img_ref[ind_ini:ind_end, :])
                lin_off = ind_ini
                col_off = 0
            else:
                nd_subset = np.where(img_ref[:, ind_ini:ind_end])
                lin_off = 0
                col_off = ind_ini

            lin_ini = nd_subset[0].min()
            lin_end = nd_subset[0].max()
            col_ini = nd_subset[1].min()
            col_end = nd_subset[1].max()

            block_list.append({'lin_ini': lin_off + lin_ini,
                               'lin_end': lin_off + lin_end,
                               'col_ini': col_off + col_ini,
                               'col_end': col_off + col_end})
            if ind_ini_new is None:
                break
            else:
                ind_ini = ind_ini_new
                ind_end = None
                cnt_tmp = 0

    if split_dim == 'Y':
        if block_list[-1]['lin_end'] < cost_shape[Ind_max]:
            block_list[-1]['lin_end'] = cost_shape[Ind_max]
    else:
        if block_list[-1]['col_end'] < cost_shape[Ind_max]:
            block_list[-1]['col_end'] = cost_shape[Ind_max]

    N_blocks = len(block_list)
    print('          - Input IMAGE divided along {} dimension into {} blocks with {} overlapping pixels...'
          .format(split_dim, N_blocks, over_elem))

    blockjoin_list = []
    for ind, block in enumerate(block_list):
        lin_ini = block['lin_ini']
        lin_end = block['lin_end']
        col_ini = block['col_ini']
        col_end = block['col_end']

        if split_dim == 'X':
            dx = step
            dy = 0
        else:
            dx = 0
            dy = step

        if ind == 0:
            if dx == 0:
                out_lin_ini = lin_ini
                out_lin_end = lin_end - dy
                out_col_ini = col_ini
                out_col_end = col_end
                subout_lin_ini = 0
                subout_lin_end = (lin_end - lin_ini) - dy
                subout_col_ini = 0
                subout_col_end = (col_end - col_ini)
            else:
                out_lin_ini = lin_ini
                out_lin_end = lin_end
                out_col_ini = col_ini
                out_col_end = col_end - dx
                subout_lin_ini = 0
                subout_lin_end = lin_end - lin_ini
                subout_col_ini = 0
                subout_col_end = (col_end - col_ini)-dx
        elif ind == N_blocks-1:
            if dx == 0:
                out_lin_ini = lin_ini + dy
                out_lin_end = lin_end
                out_col_ini = col_ini
                out_col_end = col_end
                subout_lin_ini = dy
                subout_lin_end = (lin_end - lin_ini)
                subout_col_ini = 0
                subout_col_end = (col_end - col_ini)
            else:
                out_lin_ini = lin_ini
                out_lin_end = lin_end
                out_col_ini = col_ini + dx
                out_col_end = col_end
                subout_lin_ini = 0
                subout_lin_end = (lin_end - lin_ini)
                subout_col_ini = dx
                subout_col_end = (col_end - col_ini)

        else:
            if dx == 0:
                out_lin_ini = lin_ini + dy
                out_lin_end = lin_end - dy
                out_col_ini = col_ini
                out_col_end = col_end
                subout_lin_ini = dy
                subout_lin_end = (lin_end - lin_ini) - dy
                subout_col_ini = 0
                subout_col_end = (col_end - col_ini)
            else:
                out_lin_ini = lin_ini
                out_lin_end = lin_end
                out_col_ini = col_ini + dx
                out_col_end = col_end - dx
                subout_lin_ini = 0
                subout_lin_end = (lin_end - lin_ini)
                subout_col_ini = dx
                subout_col_end = (col_end - col_ini) - dx

        blockjoin_list.append({'abs_ind': {'lin_ini': out_lin_ini,
                                           'lin_end': out_lin_end,
                                           'col_ini': out_col_ini,
                                           'col_end': out_col_end},
                               'rel_ind': {'lin_ini': subout_lin_ini,
                                           'lin_end': subout_lin_end,
                                           'col_ini': subout_col_ini,
                                           'col_end': subout_col_end}})
    return block_list, split_dim, blockjoin_list


def lowpass_fir_split(data_in, adj_win, filt_mode='S', over_elem=100):
    """
    
    :param data_in: Image 2 filter
    :param adj_win: 2D filter size
    :param filt_mode: S:Spectral FFT, D: Convolution 
    :return: 
    """
    print('     * Low-pass 2D filtering....')
    core_ones = np.full((2 * adj_win + 1, 2 * adj_win + 1), 1)
    #data_in_ma = np.ma.array(data_in, mask=data_in == 0)

    block_list, split_dim, blockjoin_list = split_img_into_nonull_blocks(data_in, over_elem=over_elem)
    step = int(over_elem / 2)

    N_blocks = len(block_list)
    data_filt = np.zeros(data_in.shape, dtype=np.single)

    for ind, block in enumerate(block_list):
        progress = float(ind+1) / float(N_blocks)
        sys.stdout.write("\r%s: [%s] %.1f%%" % ('     - Processing ', ('#' * int(progress * 50)).ljust(50), progress * 100))
        #print('         - Part {} of {} : [{}:{},{}:{}]'.format(ind + 1, N_blocks, block['lin_ini'], block['lin_end'],
        #                                                        block['col_ini'], block['col_end']))
        lin_ini = block['lin_ini']
        lin_end = block['lin_end']
        col_ini = block['col_ini']
        col_end = block['col_end']

        S_tmp = data_in[lin_ini: lin_end, col_ini: col_end]
        if filt_mode =='D':
            data_filt_num = signal.convolve2d(S_tmp, core_ones, mode='same')
            data_filt_den = signal.convolve2d((S_tmp > 0).astype(np.uint16), core_ones, mode='same')
        else:
            data_filt_num = signal.fftconvolve(S_tmp, core_ones, mode='same')
            data_filt_den = np.round(signal.fftconvolve((S_tmp > 0).astype(np.single), core_ones, mode='same'))

        data_filt_tmp = np.zeros(data_filt_num.shape, dtype=np.single)
        ind_valid = np.where(data_filt_den)
        data_filt_tmp[ind_valid] = data_filt_num[ind_valid] / data_filt_den[ind_valid]

        data_filt[blockjoin_list[ind]['abs_ind']['lin_ini']: blockjoin_list[ind]['abs_ind']['lin_end'],
                  blockjoin_list[ind]['abs_ind']['col_ini']: blockjoin_list[ind]['abs_ind']['col_end']] = \
            data_filt_tmp[blockjoin_list[ind]['rel_ind']['lin_ini']: blockjoin_list[ind]['rel_ind']['lin_end'],
                  blockjoin_list[ind]['rel_ind']['col_ini']: blockjoin_list[ind]['rel_ind']['col_end']]

        """if split_dim == 'X':
            dx = step
            dy = 0
        else:
            dx = 0
            dy = step

        if ind == 0:
            data_filt[lin_ini: lin_end-dy, col_ini: col_end-dx] = data_filt_tmp[:-dy,:] if dx == 0 else data_filt_tmp[:,:-dx]
        elif ind == N_blocks-1:
            data_filt[lin_ini+dy: lin_end, col_ini+dx: col_end] = data_filt_tmp[dy:, :] if dx == 0 else data_filt_tmp[:, dx:]
        else:
            data_filt[lin_ini+dy: lin_end-dy, col_ini+dx: col_end-dx] = data_filt_tmp[dy:-dy, :] if dx == 0 else data_filt_tmp[:, dx:-dx]"""
    print('\n')

    return data_filt


def erode_binary_msk(data_in, kernel_size):

    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    msk = cv.erode(data_in.astype(np.uint8), kernel)

    return msk

def lowpass_fir(data_in, adj_win):
    print('Low-pass 2D filtering....')
    core_ones = np.full((2 * adj_win + 1, 2 * adj_win + 1), 1)

    print('Numerator being calculated...')
    data_filt_num = signal.convolve2d(data_in, core_ones, mode='same')
    print('Denominator being calculated...')
    data_filt_den = signal.convolve2d((data_in>0).astype(np.uint16), core_ones, mode='same')

    #data_filt_num = signal.fftconvolve(data_in, core_ones, mode='same')
    #data_filt_den = np.round(signal.fftconvolve((data_in > 0).astype(np.float32), core_ones, mode='same'))
    data_filt = np.zeros(data_filt_num.shape, dtype=float)
    ind_valid = np.where(data_filt_den)
    data_filt[ind_valid] = data_filt_num[ind_valid] / data_filt_den[ind_valid]

    #data_filt[(np.isnan(data_filt)) | np.isinf(data_filt)] = 0
    #data_filt[data_in == 0] = 0

    # core = np.full((2 * adj_win + 1, 2 * adj_win + 1), 1 / (2 * adj_win + 1) ** 2)
    # data_filt = signal.convolve2d(data, core, mode='same')

    return data_filt


def retrieve_boa2toa_atm_params(Lg1, Lg2, Lo1, Lo2, p1=0.05, p2=0.6):

    S0 = (Lg1 * p2 - Lg2 * p1) / (p1 * p2 * (Lg1 - Lg2))
    A0 = Lg1 * (1 - p1 * S0) / p1

    M11 = p1 / (1 - p1 * S0)
    M12 = 1
    M21 = p2 / (1 - p2 * S0)
    M22 = 1

    X01 = Lo1
    X02 = Lo2

    La = (X02 * M11 - M21 * X01) / (M11 * M22 - M12 * M21)
    B = (X01 - M12 * La) / M11

    info_dict = {'S0': S0, 'A0': A0, 'La': La, 'B': B}

    return info_dict


def retrieve_singleband_reflectance_opt(data_band, Lg1, Lg2, Lo1, Lo2, valid_ind=None, p1=0.05, p2=0.6,
                                    rad_conv_param=1 / 1e3, adj_win=3, offset=0, Le=None, im_shape=None):
    if valid_ind is None:  # Non-valid radiance pixels are expected to be geocorrected with -9999.0 value
        valid_ind = np.where(data_band > 0)

    # Retrieved reflectance matrix is initialized
    #p = np.zeros(data_band.shape, dtype=float)
    if im_shape is not None:
        p = np.full(im_shape, -0.9999, dtype=np.single)
    else:
        p = np.zeros(data_band.shape, dtype=np.single)

    S0 = (Lg1 * p2 - Lg2 * p1) / (p1 * p2 * (Lg1 - Lg2))
    A0 = Lg1 * (1 - p1 * S0) / p1

    M11 = p1 / (1 - p1 * S0)
    M12 = 1
    M21 = p2 / (1 - p2 * S0)
    M22 = 1

    X01 = Lo1
    X02 = Lo2

    La = (X02 * M11 - M21 * X01) / (M11 * M22 - M12 * M21)
    B = (X01 - M12 * La) / M11

    #core = np.full((2 * adj_win + 1, 2 * adj_win + 1), 1 / (2 * adj_win + 1) ** 2)
    #Le = signal.convolve2d(data_band * rad_conv_param, core, mode='same')
    #Le_in = (data_band * rad_conv_param +offset).astype(float)

    if rad_conv_param != 1:
        data_band = data_band* rad_conv_param+offset
    if Le is None:
        Le = lowpass_fir_split(data_band, adj_win)[valid_ind]
    else:
        Le = Le*rad_conv_param+offset

    if data_band.ndim == 2:
        data_band = data_band[valid_ind]

    pe = (Le - La) / (A0 + B + S0 * (Le - La))
    p[valid_ind] = ((data_band - La) * (1 - pe * S0) - pe * B) / A0

    return p


def retrieve_singleband_reflectance_GPU(data_band, Lg1, Lg2, Lo1, Lo2, valid_ind=None, p1=0.05, p2=0.6,
                                    rad_conv_param=1 / 1e3, adj_win=3):
    if valid_ind is None:  # Non-valid radiance pixels are expected to be geocorrected with -9999.0 value
        valid_ind = np.where(data_band > 0)

    # Retrieved reflectance matrix is initialized
    #p = np.zeros(data_band.shape, dtype=float)
    #p = cp.zeros(data_band.shape, dtype=float)
    p = cp.full(data_band.shape, -9999.0,  dtype=float)

    Lg1 = cp.asarray(Lg1[valid_ind])
    Lg2 = cp.asarray(Lg2[valid_ind])
    Lo1 = cp.asarray(Lo1[valid_ind])
    Lo2 = cp.asarray(Lo2[valid_ind])
    p1  = cp.asarray(p1)
    p2  = cp.asarray(p2)
    data_band = cp.asarray(data_band)
    
    S0 = (Lg1 * p2 - Lg2 * p1) / (p1 * p2 * (Lg1 - Lg2))
    A0 = Lg1 * (1 - p1 * S0) / p1

    M11 = p1 / (1 - p1 * S0)
    M12 = cp.asarray(1.0)
    M21 = p2 / (1 - p2 * S0)
    M22 = cp.asarray(1.0)

    X01 = Lo1
    X02 = Lo2

    La = (X02 * M11 - M21 * X01) / (M11 * M22 - M12 * M21)
    B = (X01 - M12 * La) / M11

    core = cp.full((2 * adj_win + 1, 2 * adj_win + 1), 1 / (2 * adj_win + 1) ** 2)
    #Le = signal.convolve2d(data_band * rad_conv_param, core, mode='same')
    Le = convolve2d(data_band * rad_conv_param, core, mode='same')
    pe = (Le[valid_ind] - La) / (A0 + B + S0 * (Le[valid_ind] - La))
    p[valid_ind] = ((data_band[valid_ind] * rad_conv_param - La) * (1 - pe * S0) - pe * B) / A0
    p[p<0]=0
    p_out=  p.get()
    return p_out


def image_value2ind(image_in, value_vec, block_line=3000, dtype='uint16'):
    nl, nc = image_in.shape
    ind_vec = np.arange(np.floor(nl / block_line).astype(dtype) + 1)*block_line
    if ind_vec[-1]<nl:
        ind_vec = np.append(ind_vec, nl)

    image_in_ind = np.zeros(image_in.shape, dtype=dtype)

    for ind_block in range(ind_vec.size-1):
        print('     -Block {} of {} being processed....'.format(ind_block+1, ind_vec.size-1))
        sub_im = image_in[ind_vec[ind_block]:ind_vec[ind_block+1],  : ]
        sub_ind = np.zeros(sub_im.shape, dtype=dtype)
        for ind, value in enumerate(value_vec):
            sub_ind[np.where(sub_im == value)] = ind
        image_in_ind[ind_vec[ind_block]:ind_vec[ind_block+1],  : ] = sub_ind
        del sub_ind, sub_im
        #image_in_ind[valid_pix][np.where(image_in[valid_pix] == value)] = ind

    return image_in_ind


def write_IMAGEDESCRITPION_TAG(image_h,str_info):
    
    image_h.SetMetadata({'TIFFTAG_IMAGEDESCRIPTION': str_info})


def image_output_gen(output_f, num_rows, num_cols, num_bands, data_type, DriverName='GTiff', geotransform_info=None,
                     src_proj_info=None, interleave='PIXEL', compression_flag=True, im_description=None,
                     binary_mask=False, bigtiff_flag=True):
    option_list = ['PHOTOMETRIC=MINISBLACK', 'INTERLEAVE=' + interleave.upper()]
    if compression_flag:
        option_list.append('COMPRESS=LZW')
    if bigtiff_flag:
        option_list.append('BIGTIFF=YES')
    if binary_mask:
        option_list.append('NBITS=1')

    if DriverName == 'cog':
        DriverName = 'GTiff'
        option_list.append('COPY_SRC_OVERVIEWS=YES')
    dst_ds = gdal.GetDriverByName(DriverName).Create(output_f, num_cols, num_rows, num_bands, data_type,
                                                     options=option_list)

    gdal.SetConfigOption("COMPRESS_OVERVIEW", "DEFLATE")

    if geotransform_info is not None:
        dst_ds.SetGeoTransform(geotransform_info)
    if src_proj_info is not None:
        dst_ds.SetProjection(src_proj_info)
    if im_description is not None:
        dst_ds.SetMetadata({'TIFFTAG_IMAGEDESCRIPTION':im_description})

    return dst_ds


def write_im_band(image_h, band, band_ind, overviews_flag=False, method='NEAREST', size_vec=[2, 4, 8, 16, 32, 64, 128, 256]):
    image_h.GetRasterBand(band_ind).WriteArray(band)
    if overviews_flag:
        image_h.GetRasterBand(band_ind).BuildOverviews(method, size_vec)
    image_h.FlushCache()


def write_im_reference(image_h, geotransform_info, src_proj_info):
    image_h.SetGeoTransform(geotransform_info)
    image_h.SetProjection(src_proj_info)


def close_im(image_h):
    image_h = None


def write_im_subset_by_indexes(image_h,data,block_info, band_axis = 2):
    
    for i_band in range(data.shape[band_axis]):
        if band_axis==0:
            data_tmp = data[i_band,:,:]
        elif band_axis==2:
            data_tmp = data[:,:,i_band]
        
        image_h.GetRasterBand(i_band+1).WriteArray(data_tmp,block_info[1],block_info[0])
        image_h.FlushCache()

