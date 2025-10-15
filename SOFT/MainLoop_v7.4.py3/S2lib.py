# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import os
import subprocess as sp
import aux_fun as af
from osgeo import gdal
import zipfile as zf
import re
import shutil
import numpy as np
import glob
import math

degToRad = math.pi / 180

s2_band_dict = {
    'L1C': {'real': ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B10', 'B11', 'B12'],
            'virtual': ['view_azimuth_B1', 'view_azimuth_B2', 'view_azimuth_B3', 'view_azimuth_B4', 'view_azimuth_B5',
                        'view_azimuth_B6', 'view_azimuth_B7', 'view_azimuth_B8', 'view_azimuth_B9', 'view_azimuth_B10',
                        'view_azimuth_B11', 'view_azimuth_B12', 'view_azimuth_mean', 'view_zenith_B1', 'view_zenith_B2',
                        'view_zenith_B3', 'view_zenith_B4', 'view_zenith_B5', 'view_zenith_B6', 'view_zenith_B7',
                        'view_zenith_B8', 'view_zenith_B9', 'view_zenith_B10', 'view_zenith_B11', 'view_zenith_B12',
                        'view_zenith_mean', 'sun_azimuth', 'sun_zenith', 'B_snow_and_ice_areas', 'B_opaque_clouds',
                        'B_cirrus_clouds']},

    'L2A': {'real': ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B11', 'B12', 'AOT', 'TCI',
                     'WVP', 'SCL'],
            'virtual': ['aod550', 'z', 'bcaod550', 'omaod550', 'ssaod550', 'suaod550', 'aod469', 'aod670', 'aod865',
                        'aod1240', 'tco3', 'tcwv', 'msl', 'r', '10u', '10v',
                        'view_azimuth_B1', 'view_azimuth_B2', 'view_azimuth_B3', 'view_azimuth_B4', 'view_azimuth_B5',
                        'view_azimuth_B6', 'view_azimuth_B7', 'view_azimuth_B8', 'view_azimuth_B9', 'view_azimuth_B10',
                        'view_azimuth_B11', 'view_azimuth_B12', 'view_azimuth_mean', 'view_zenith_B1', 'view_zenith_B2',
                        'view_zenith_B3', 'view_zenith_B4', 'view_zenith_B5', 'view_zenith_B6', 'view_zenith_B7',
                        'view_zenith_B8', 'view_zenith_B9', 'view_zenith_B10', 'view_zenith_B11', 'view_zenith_B12',
                        'view_zenith_mean', 'sun_azimuth', 'sun_zenith']}}

s2_band_ind_dict = {'B01': {'subset_ind': 2, 'ind_in': 1, 'res': 60},
                    'B02': {'subset_ind': 0, 'ind_in': 3, 'res': 10},
                    'B03': {'subset_ind': 0, 'ind_in': 2, 'res': 10},
                    'B04': {'subset_ind': 0, 'ind_in': 1, 'res': 10},
                    'B05': {'subset_ind': 1, 'ind_in': 1, 'res': 20},
                    'B06': {'subset_ind': 1, 'ind_in': 2, 'res': 20},
                    'B07': {'subset_ind': 1, 'ind_in': 3, 'res': 20},
                    'B08': {'subset_ind': 0, 'ind_in': 4, 'res': 10},
                    'B8A': {'subset_ind': 1, 'ind_in': 4, 'res': 20},
                    'B09': {'subset_ind': 2, 'ind_in': 2, 'res': 20},
                    'B10': {'subset_ind': 2, 'ind_in': 3, 'res': 60},
                    'B11': {'subset_ind': 1, 'ind_in': 5, 'res': 20},
                    'B12': {'subset_ind': 1, 'ind_in': 6, 'res': 20}}


def image_storage(data, scl_image_msk, out_dir, out_f_flag, format_input, image_f,ref_info,  suffix):
    data = data.astype(np.float32) * scl_image_msk

    if out_f_flag:
        if format_input == 'ZIP':
            out_f = os.path.join(out_dir, os.path.basename(image_f).split('.')[0] + '_'+suffix+'.TIF')
        elif format_input == 'SAFE':
            out_f = os.path.join(out_dir, os.path.basename(image_f.split('.SAFE')[0]) + '_'+suffix+'.TIF')

        out_h = af.image_output_gen(out_f, num_rows=ref_info['Nlines'], num_cols=ref_info['Ncolumns'], num_bands=1,
                                    data_type=af.NP2GDAL_CONVERSION['float32'],
                                    geotransform_info=ref_info['im_geotransformation'],
                                    src_proj_info=ref_info['im_geoprojection'])
        af.write_im_band(out_h, data, 1)
        out_h = None
        out = out_f
    else:
        out = data
    return out


def filelist_gen(path_str):
    filelist = []
    for root, dirs, files in os.walk(path_str):
        for file in files:
            # append the file name to the list
            filelist.append(os.path.join(root, file))
    return filelist


def is_contained(bbox_image, bbox_subset):
    if bbox_subset is not None:
        flag_dict = {'xmin': bbox_subset['xmin'] >= bbox_image['xmin'],
                     'ymin': bbox_subset['ymin'] >= bbox_image['ymin'],
                     'xmax': bbox_subset['xmax'] <= bbox_image['xmax'],
                     'ymax': bbox_subset['ymax'] <= bbox_image['ymax']}

        cond_vec = [flag_dict[_] for _ in flag_dict.keys()]

        if all(cond_vec):
            print("Provided Bounding Box fully contained within image's footprint")
        elif not any(cond_vec):
            print("Provided Bounding Box outside image's footprint")
            bbox_subset = {_: None for _ in bbox_subset.keys()}
        else:
            print(
                "Provided Bounding Box PARTIALLY contained within image's footprint. Cropped bounding box dictionary "
                "is returned")
            for key in bbox_image.keys():
                if not flag_dict[key]:
                    bbox_subset[key] = bbox_image[key]
    return bbox_subset


class S2image:
    """
    Class managing Sentinel2 (S2) L1C and L2A imagery
    :param : img_f : Absolute path of S2 file (.SAFE or ZIP format)
    :param : bbox_dict : dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
    :param : gpt_exe_f : absolute path to GPT.EXE available when ESA SNAP SW is installed. The GPT.EXE is used for
                        extraction of VIRTUAL bands, but this dependence should be avoided in future versions of S2Lib
    """
    def __init__(self, img_f, bbox_dict=None, gpt_exe_f=r"C:\Program Files\snap\bin\gpt.exe"):
        if os.path.basename(img_f).lower().endswith('.zip'):
            assert os.path.exists(img_f), 'Input S2 zipped file not found!'
            self.format = 'ZIP'
            self.img_root_name = os.path.basename(img_f).split('.')[0]
            self.footprint_dict = None
        elif os.path.basename(img_f).lower().endswith('.safe'):
            assert os.path.isdir(img_f), 'Input S2 SAFE file not found!'
            self.format = 'SAFE'
            self.img_root_name = os.path.basename(img_f).split('.SAFE')[0]
            self.xml2mod = glob.glob(os.path.join(img_f,'GRANULE','*','MTD_TL.xml'))[0]
            if os.path.exists(os.path.join(img_f, 'MTD_MSIL1C.xml')):
                img_f = os.path.join(img_f, 'MTD_MSIL1C.xml')
            elif os.path.exists(os.path.join(img_f, 'MTD_MSIL2A.xml')):
                img_f = os.path.join(img_f, 'MTD_MSIL2A.xml')

            self.footprint_dict = {os.path.basename(_).split('.jp2')[0].split('_')[-1]: _
                                   for _ in glob.glob(os.path.join(os.path.dirname(img_f), 'GRANULE', '*', 'QI_DATA', 'MSK_DETFOO_B*.jp2'))}

        assert os.path.exists(gpt_exe_f), 'GPT.exe file at the provided path ({}) not found'.format(gpt_exe_f)

        self.image_f = img_f
        self.gpt_exe_f = gpt_exe_f

        self.img_info = {'10': af.getS2image_info(img_f, res=10), '20': af.getS2image_info(img_f, res=20)}
        self.metadata = af.getS2image_metadata(img_f, format=self.format)
        try:
            if self.metadata['PROCESSING_LEVEL'] == 'Level-1C':
                self.producttype = 'L1C'
            elif self.metadata['PROCESSING_LEVEL'] == 'Level-2A':
                self.producttype = 'L2A'
            else:
                if '_MSIL2A_' in os.path.basename(img_f):
                    self.producttype = 'L2A'
                elif '_MSIL1C_' in os.path.basename(img_f):
                    self.producttype = 'L1C'
        except:
            print('Image processing level unknown. Producttype param not defined')
        self.bbox_dict = is_contained(self.img_info['10']['bbox'], bbox_dict)

    def set_boundingbox(self,  bbox_dict):
        self.bbox_dict = is_contained(self.img_info['10']['bbox'], bbox_dict)

    def read_band(self, band_id, res_out=None, im_resampleAlg=None, bbox_dict=None):
        if band_id in s2_band_dict[self.producttype]['real']:
            """if self.format == 'SAFE':
                prefix = os.path.basename(self.image_f.split('.SAFE')[0]) + '_'
            else:
                prefix = os.path.basename(self.image_f).replace('.zip', '_')"""
            tmp_f = os.path.join(os.getcwd(), self.img_root_name + 'temp.vrt')
            self.extract_real_bands([band_id], out_image_f=tmp_f, res_out=res_out, im_resampleAlg=im_resampleAlg,
                                    bbox_dict=bbox_dict)
        elif band_id in s2_band_dict[self.producttype]['virtual']:
            tmp_f = self.extract_virtual_bands([band_id], out_dir=os.getcwd(), res_out=res_out,
                                               im_resampleAlg=im_resampleAlg, bbox_dict=bbox_dict)
        else:
            print('Band not in REAL or VIRTUAL bands list. Check it...')
            return -1
        if isinstance(tmp_f, str):
            data = af.read_image(tmp_f)
            data_info = af.get_im_info(tmp_f, unpack_im_descr=False)
            os.remove(tmp_f)
        elif isinstance(tmp_f, list) and len(tmp_f) == 1:
            tmp_f = tmp_f[0]
            data = af.read_image(tmp_f)
            data_info = af.get_im_info(tmp_f, unpack_im_descr=False)
            os.remove(tmp_f)
        else:
            data = {}
            for temp in tmp_f:
                data[os.path.basename(temp)] = af.read_image(temp)
                os.remove(temp)

        return data

    def get_ref2rad_fact(self,  band_id):
        """
        This function retrieve radiance information corresponding to SINGLE band from L1C product and return the array with data or the
        link to the TIF file storing the new info, depending of user's settings.

        :param band_id: S2 L1C REAL band to be converted into radiance (Ex. 'BO2')
        :param geo_info_flag: If set to True, output image geoinformation is returned too, along with the data or path
                        to TIF file.
        :return:
                band 2D-array (if out_f and dir_out set to None) or link to TIF output
                output geoinformation (If geo_info_flag set to True)
        """
        assert self.producttype == 'L1C', 'Radiance retrieval can only be performed over L1C imagery'

        sun_zenith = self.read_band('sun_zenith')
        scale = 1 / (0.001 * 1000)
        fact = float(self.metadata['RADIOM_CALIB']['ADD_OFFSET'][band_id]) * np.cos(sun_zenith * degToRad) * float(self.metadata['RADIOM_CALIB']['irr'][band_id]) / (np.pi * (1 / float(self.metadata['RADIOM_CALIB']['U'])))

        return fact, scale

    def read_radiance(self, band_id, out_f=None, out_dir=None, res_out=None, im_resampleAlg=None, bbox_dict=None, geo_info_flag=False, overviews_flag=False):
        """
        This function retrieve radiance information corresponding to SINGLE band from L1C product and return the array with data or the
        link to the TIF file storing the new info, depending of user's settings.

        :param band_id: S2 L1C REAL band to be converted into radiance (Ex. 'BO2')
        :param out_f: Output file name, if radiance is to be exported to TIF file (Def. None)
        :param out_dir: Output directory name, if radiance is to be exported to TIF file (Def. None). It is considered
                        if out_f is None, and the name is obtained from L1C file adding "band_id"+_RAD.tif suffix.
        :param res_out: Output image spatial resolution(Def. None). If None, the nominal band_id spatial resolution is used
        :param im_resampleAlg:  Spatial resampling strategy (Def. nearest) - See GDAL interpolation methods
        :param bbox_dict: dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
        :param geo_info_flag: If set to True, output image geoinformation is returned too, along with the data or path
                        to TIF file.
        :return:
                band 2D-array (if out_f and dir_out set to None) or link to TIF output
                output geoinformation (If geo_info_flag set to True)
        """
        assert self.producttype == 'L1C', 'Radiance retrieval can only be performed over L1C imagery'

        if bbox_dict is None:
            bbox_dict = self.bbox_dict
            
        if isinstance(band_id, list):
            band_id_vec = band_id.copy()
        else:
            band_id_vec = [band_id]

        out_tmp_f = None
        if out_f is not None:
            out_tmp_f = out_f
            output_data = out_tmp_f

        else:
            if out_dir is not None:
                out_tmp_f = os.path.join(out_dir, self.img_root_name + '_' + band_id + '_RAD.tif')
                output_data = out_tmp_f
            else:
                output_data = []

        if out_tmp_f is None or not os.path.exists(out_tmp_f):
            for seq_ind, band_id in enumerate(band_id_vec):
                print('Band being processed : {}'.format(band_id))

                if band_id in s2_band_dict[self.producttype]['real']:
                    """if self.format == 'SAFE':
                        prefix = os.path.basename(self.image_f.split('.SAFE')[0]) + '_'
                    else:
                        prefix = os.path.basename(self.image_f).replace('.zip', '_')"""
                    tmp_f = os.path.join(os.getcwd(), self.img_root_name + 'temp.vrt')
                    self.extract_real_bands([band_id], out_image_f=tmp_f, res_out=res_out, im_resampleAlg=im_resampleAlg,
                                            bbox_dict=bbox_dict)
                else:
                    print('Radiance conversion can only be performed over REAL and not VIRTUAL bands. Check it...')
                    return -1
                data_info = af.get_im_info(tmp_f, unpack_im_descr=False)
                if seq_ind == 0:
                    if out_tmp_f is not None:
                        im_out_h = af.image_output_gen(out_tmp_f, data_info['Nlines'], data_info['Ncolumns'],
                                                       len(band_id_vec),
                                                       af.NP2GDAL_CONVERSION['float32'],
                                                       geotransform_info=data_info['im_geotransformation'],
                                                       src_proj_info=data_info['im_geoprojection'], interleave='PIXEL',
                                                       im_description='Band List : {} [Unit] Radiance W/[m²sr µm]'.format(','.join(band_id_vec)))

                    sun_zenith = self.read_band('sun_zenith',  res_out=res_out, im_resampleAlg='bilinear', bbox_dict=data_info['bbox'])
                    scale = 1/(0.001*1000)

                data = scale*(af.read_image(tmp_f).astype(np.float32) + float(self.metadata['RADIOM_CALIB']['ADD_OFFSET'][band_id]))*\
                      np.cos(sun_zenith*degToRad) * float(self.metadata['RADIOM_CALIB']['irr'][band_id])/\
                      (np.pi * (1 / float(self.metadata['RADIOM_CALIB']['U'])))/1e4

                os.remove(tmp_f)
                data[data < 0] = 0

                if out_tmp_f is not None:
                    print('     * Band being stored...')
                    af.write_im_band(im_out_h, data, seq_ind+1, overviews_flag=overviews_flag)
                else:
                    output_data.append(data)
                del data

            im_out_h = None

        """if overviews_flag:
            print('External overviews being generated')
            af.overview_gen(out_tmp_f)"""

        if geo_info_flag:
            return output_data, data_info
        else:
            return output_data

    def read_reflectivity(self, band_id, out_f=None, out_dir=None, res_out=None, im_resampleAlg=None, bbox_dict=None, geo_info_flag=False):
        """
        This function retrieve reflectance information corresponding to SINGLE band from L1C or L2A product and return the array with data or the
        link to the TIF file storing the new info, depending of user's settings.

        :param band_id: S2 L1C REAL band to be converted into radiance (Ex. 'BO2')
        :param out_f: Output file name, if radiance is to be exported to TIF file (Def. None)
        :param out_dir: Output directory name, if radiance is to be exported to TIF file (Def. None). It is considered
                        if out_f is None, and the name is obtained from L1C file adding "band_id"+_RAD.tif suffix.
        :param res_out: Output image spatial resolution(Def. None). If None, the nominal band_id spatial resolution is used
        :param im_resampleAlg:  Spatial resampling strategy (Def. nearest) - See GDAL interpolation methods
        :param bbox_dict: dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
        :param geo_info_flag: If set to True, output image geoinformation is returned too, along with the data or path
                        to TIF file.
        :return:
                band 2D-array (if out_f and dir_out set to None) or link to TIF output
                output geoinformation (If geo_info_flag set to True)
        """
        if self.producttype == 'L1C':
            offset = float(self.metadata['RADIOM_CALIB']['ADD_OFFSET'][band_id])
            qvalue = float(self.metadata['QVALUE'])
        elif self.producttype == 'L2A':
            band_id_ind_dict = {'B02': 'B01', 'B03': 'B02', 'B04': 'B03', 'B05': 'B04', 'B06': 'B05', 'B07': 'B06',
                                'B08': 'B07', 'B8A': 'B08', 'B11': 'B09',
                                'B12': 'B10'}
            offset = float(self.metadata['RADIOM_CALIB']['ADD_OFFSET'][band_id_ind_dict[band_id]])
            qvalue = float(self.metadata['BOA_QUANT_VALUE'])

        if band_id in s2_band_dict[self.producttype]['real']:
            """if self.format == 'SAFE':
                prefix = os.path.basename(self.image_f.split('.SAFE')[0]) + '_'
            else:
                prefix = os.path.basename(self.image_f).replace('.zip', '_')"""
            tmp_f = os.path.join(os.getcwd(), self.img_root_name + 'temp.vrt')
            self.extract_real_bands([band_id], out_image_f=tmp_f, res_out=res_out, im_resampleAlg=im_resampleAlg,
                                    bbox_dict=bbox_dict)
        else:
            print('Radiance conversion can only be performed over REAL and not VIRTUAL bands. Check it...')
            return -1

        data = (af.read_image(tmp_f).astype(np.double) +offset)/qvalue
        data_info = af.get_im_info(tmp_f, unpack_im_descr=False)
        os.remove(tmp_f)

        out_tmp_f= None
        if out_f is not None:
            out_tmp_f = out_f
        elif out_dir is not None:
            """if self.format == 'SAFE':
                out_tmp_f = os.path.join(out_dir,
                                         os.path.basename(self.image_f.split('.SAFE')[0]) + '_' + band_id + '_REF.tif')
            else:
                out_tmp_f = os.path.join(out_dir, os.path.basename(self.image_f)
                                         .replace('.zip', '') + '_' + band_id + '_REF.tif')"""
            out_tmp_f = os.path.join(out_dir, self.img_root_name + '_' + band_id + '_REF.tif')

        if out_tmp_f is not None:
            im_out_h = af.image_output_gen(out_tmp_f, data_info['Nlines'], data_info['Ncolumns'],
                                           data_info['Nbands'],
                                           af.NP2GDAL_CONVERSION['float32'],
                                           geotransform_info=data_info['im_geotransformation'],
                                           src_proj_info=data_info['im_geoprojection'], interleave='PIXEL',
                                           im_description='Radiance W/[m²sr µm]')
            af.write_im_band(im_out_h, data, 1)
            im_out_h = None
            del data
            data = out_tmp_f

        if geo_info_flag:
            return data, data_info
        else:
            return data

    def real_band_list(self):
        """
        :return: List of REAL bands available withing S2-Capture
        """
        print('List of REAL bands available withing S2-Capture :')
        print('\n'.join(s2_band_dict[self.producttype]['real']))

    def virtual_band_list(self):
        """
        :return: List of VIRTUAL bands available withing S2-Capture :'
        """
        print('List of VIRTUAL bands available withing S2-Capture :')
        print('\n'.join(s2_band_dict[self.producttype]['virtual']))

    def extract_real_bands(self, band_id, out_image_f=None, res_out=None, im_resampleAlg=None, bbox_dict=None,
                           out_format='VRT'):
        """
        This function performs the extraction of a SINGLE or a LIST of REAL bands from S2 L1C or L2A image, and store
        the results in a VRT (Default) or TIF single/multiband file specified by "out_image_f" or named automatically
        from the S2 product with suffix "band_id", if a single band is defined, or "multiband", otherwise.

        :param band_id: str or list of str of bands to be extracted
        :param out_image_f: output file full-path
        :param res_out: Output image spatial resolution(Def. None). If None, the nominal band_id spatial resolution is
                        used, if band_id is a string; the highest spatial resolution of band list, otherwise.
        :param im_resampleAlg: Spatial resampling strategy (Def. nearest) - See GDAL interpolation methods
        :param bbox_dict:dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
        :param out_format: Output  file format (TIF or VRT). (Def. VRT)
        :return:
            link to TIF or VRT output file
        """
        if isinstance(band_id, str):
            band_id = [band_id]

        # For S2 L2A image, some real bands are not available through GDAL Sentinel2 Driver.
        # They are ['AOT', 'TCI', 'WVP', 'SCL'], their request must be managed as additional band tasks

        additional_bnd = []
        ref_vrt_band = ['AOT', 'TCI', 'WVP', 'SCL']
        for band_name in ref_vrt_band:
            if band_name in band_id:
                band_id.remove(band_name)
                additional_bnd.append(band_name)

        if len(additional_bnd) > 0:
            res_str = '_60m'
            additional_bnd_tmp = [_ + res_str for _ in additional_bnd]
            if self.format == 'ZIP':
                zz = zf.ZipFile(self.image_f)
                additional_bnd_list = ['/vsizip/' + self.image_f + '/' + f.filename
                                       for f in zz.filelist
                                       if any(re.findall(r'|'.join(additional_bnd_tmp), f.filename, re.IGNORECASE))]
            elif self.format == 'SAFE':
                additional_bnd_list = [f for f in filelist_gen(self.image_f.split('.SAFE')[0]+'.SAFE') if any(re.findall(r'|'.join(additional_bnd_tmp), f, re.IGNORECASE))]
            del additional_bnd_tmp
        else:
            additional_bnd_list = []

        for band_id_elem in band_id:
            assert band_id_elem in s2_band_dict[self.producttype]['real'], \
                'Band {} is virtual. Use get_virtual_band method.'.format(band_id_elem)

        if res_out is None:
            res_list = []
            for band_id_elem in band_id:
                res_list.append(s2_band_ind_dict[band_id_elem]['res'])
            res_list = list(set(res_list))
            res_out = min(res_list)
            print('No output spatial-resolution was set. Default value of {}m applied'.format(res_out))

        #not_vrt_out_flag = not os.path.basename(out_image_f).endswith('.vrt') if out_image_f is not None  else True
        not_vrt_out_flag = True if out_image_f is not None and not os.path.basename(out_image_f).lower().endswith('.vrt') or not out_format.upper() == 'VRT' else False

        n_out_bands = len(band_id)
        separate_flag = False if n_out_bands == 1 else True

        if out_image_f is None or not_vrt_out_flag:
            if n_out_bands == 1:
                suffix_str = '_' + band_id[0]
            elif n_out_bands == 0 and len(additional_bnd_list) == 1:
                suffix_str = '_' + additional_bnd[0]
            else:
                suffix_str = '_multiBand_'

            #out_vrt_f = os.path.join(os.path.dirname(self.image_f),
            #                         os.path.basename(self.image_f).split('.')[0] + suffix_str + '.vrt')

            out_dir = os.path.dirname(self.image_f.split('.SAFE')[0]) if self.format == 'SAFE' else os.path.dirname(self.image_f)
            out_vrt_f = os.path.join(out_dir, os.path.basename(self.image_f.split('.SAFE')[0]) + suffix_str + '.vrt') \
                if self.format == 'SAFE' else os.path.join(out_dir,
                                                           os.path.basename(self.image_f).replace('.zip',  suffix_str + '.vrt'))

        else:
            out_vrt_f = out_image_f
            out_dir = os.path.dirname(out_vrt_f)

        root_ds = gdal.Open(self.image_f)
        ds_list = root_ds.GetSubDatasets()

        tmp_vrt_list = []
        vrt_band_list = []
        vrt_ind_band_list = []
        vrt_ind_dataset_list = []
        vrt_res_list = []

        for band_id_elem in band_id:
            vrt_res_list.append(s2_band_ind_dict[band_id_elem]['res'])
            vrt_ind_dataset_list.append(s2_band_ind_dict[band_id_elem]['subset_ind'])
            vrt_ind_band_list.append(s2_band_ind_dict[band_id_elem]['ind_in'])
            vrt_band_list.append(ds_list[s2_band_ind_dict[band_id_elem]['subset_ind']][0])

        n_res_vec = len(set(vrt_res_list))
        if n_res_vec > 1:
            res_out = min(vrt_res_list)

        if bbox_dict is None:
            bbox_dict =  self.bbox_dict

        if bbox_dict is None:
            im_outputBounds = None
        else:
            im_outputBounds = [bbox_dict['xmin'], bbox_dict['ymin'], bbox_dict['xmax'], bbox_dict['ymax']]

        if n_out_bands == 1:
            out = af.create_vrt_file(out_vrt_f, vrt_band_list,
                                     im_xRes=res_out,
                                     im_yRes=res_out,
                                     im_bandList=[s2_band_ind_dict[band_id_elem]['ind_in']],
                                     im_resampleAlg=im_resampleAlg,
                                     im_outputBounds=im_outputBounds, im_targetAlignedPixels=True)
            out = None#out.FlushCache()
        else:

            for ind, band_id_elem in enumerate(band_id):
                suffix_str = '_' + band_id_elem
                tmp_vrt_list.append(os.path.join(out_dir, self.img_root_name + suffix_str + '_tmp.vrt'))

                out = af.create_vrt_file(tmp_vrt_list[-1], vrt_band_list[ind],
                                         im_xRes=res_out,
                                         im_yRes=res_out,
                                         im_resampleAlg=im_resampleAlg,
                                         im_bandList=[vrt_ind_band_list[ind]],
                                         im_outputBounds=im_outputBounds, im_targetAlignedPixels=True)

            for ind_add, add_band_f in enumerate(additional_bnd_list):
                suffix_str = '_' + additional_bnd[ind_add]
                tmp_vrt_list.append(os.path.join(out_dir, self.img_root_name + suffix_str + '_tmp.vrt'))

                out = af.create_vrt_file(tmp_vrt_list[-1], [add_band_f],
                                         im_xRes=res_out, im_yRes=res_out,
                                         im_resampleAlg=im_resampleAlg,
                                         im_outputBounds=im_outputBounds, im_targetAlignedPixels=True)
                if out is not None:
                    out.FlushCache()

            out = af.create_vrt_file(out_vrt_f, tmp_vrt_list, im_separate=separate_flag)
            if out is not None:
                out.FlushCache()

        root_ds = None

        if not not_vrt_out_flag and out_format.upper() == 'VRT':
            out_image_f = out_vrt_f
        else:
            creationOptions = ['PHOTOMETRIC=MINISBLACK', 'INTERLEAVE=BAND', 'COMPRESS=LZW', 'BIGTIFF=YES']
            translate_options = gdal.TranslateOptions(format='GTiff', creationOptions=creationOptions)

            if out_image_f is None:
                out_image_f = out_vrt_f.replace('.vrt', '.tif')
                print('Default output image: {}'.format(out_image_f))

            print('Output TIF file being generated...')
            gdal.Translate(out_image_f, out_vrt_f, options=translate_options)

            print('Temporary VRT files being deleted...')

            if len(tmp_vrt_list) > 0:
                for tmp_vrt in tmp_vrt_list:
                    if os.path.exists(tmp_vrt):
                        os.remove(tmp_vrt)
            if os.path.exists(out_vrt_f):
                os.remove(out_vrt_f)

        return out_image_f

    def extract_virtual_bands(self, band_id, out_dir=None, res_out=None, im_resampleAlg=None, bbox_dict=None):
        """
        This function performs the extraction of a SINGLE or a LIST of VIRTUAL bands from S2 L1C or L2A image, and store
        the results in a specific TIF file for each VIRTUAL band, naming it automatically
        from the S2 product with suffix "band_id".

        :param band_id: str or list of str of bands to be extracted
        :param out_dir: Output directory name, if radiance is to be exported to TIF file (Def. None). If it is None, the
                        directory of L1C filename is used, and the name is obtained using L1C filename as prefix.
        :param res_out: Output image spatial resolution(Def. None). If None, the nominal band_id spatial resolution is
                        used, if band_id is a string; the highest spatial resolution of band list, otherwise.
        :param im_resampleAlg: Spatial resampling strategy (Def. nearest) - See GDAL interpolation methods
        :param bbox_dict:dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
        :return:
            dictionary containing the VIRTUAL band names as keys and the link to output TIF files
        """
        # TODO : Add option to convert the bounding box to an EPSG 4296 wkt polygon and perform subset extraction using GPT

        if out_dir is not None:
            assert os.path.isdir(out_dir), 'Output directory does not exist!'

        if isinstance(band_id, str):
            band_id = [band_id]

        for band_id_elem in band_id:
            assert band_id_elem in s2_band_dict[self.producttype]['virtual'], 'Band {} not found. It might be either ' \
                        'real (Use "get_real_band" method instead) or not contained among S2 {} real/virtual products ' \
                         '(Use "real_band_list" and "virtual_band_list" methods to check).'.format(
                band_id_elem, self.producttype)

        if res_out is None:
            res_list = []
            for band_id_elem in band_id:
                res_list.append(s2_band_ind_dict[band_id_elem]['res'])
            res_list = list(set(res_list))
            res_out = min(res_list)
            print('No output spatial-resolution was set. Default value of {}m applied'.format(res_out))

        additional_bnd = []
        ref_vrt_band = ['B_snow_and_ice_areas', 'B_opaque_clouds', 'B_cirrus_clouds']
        for band_name in ref_vrt_band:
            if band_name in band_id:
                band_id.remove(band_name)
                additional_bnd.append(band_name)
        cd_old = os.getcwd()
        os.chdir(os.path.dirname(self.gpt_exe_f))

        if out_dir is None:
            out_dir = os.path.dirname(self.image_f.split('.SAFE')[0]) if self.format == 'SAFE' \
                 else os.path.dirname(self.image_f)

        out_f = os.path.join(out_dir, self.img_root_name + '.dim')

        out_add_f = os.path.join(out_dir, self.img_root_name + '_add.dim')

        cmd_str = 'gpt Subset  -SsourceProduct=' + self.image_f + ' -PsourceBands="' + ','.join(
            band_id) + '" -PsubSamplingX=1 -PsubSamplingY=1 -PcopyMetadata=true  -t ' + out_f
        sp.call(cmd_str)

        if len(additional_bnd) > 0:
            cmd_str = 'gpt Subset  -SsourceProduct=' + self.image_f + ' -PsourceBands="' + ','.join(
                additional_bnd) + '" -PsubSamplingX=1 -PsubSamplingY=1 -PcopyMetadata=true  -t ' + out_add_f
            sp.call(cmd_str)

        os.chdir(cd_old)
        out_f_list = []
        for dim_f in [out_f, out_add_f]:
            if os.path.exists(dim_f):
                    for band_name in band_id + additional_bnd:
                        envi_f = os.path.join(dim_f.replace('.dim', '.data'), band_name + '.img')
                        if os.path.exists(envi_f):
                            print('Output {} TIF file being generated...'.format(band_name))
                            """if self.format == 'SAFE':
                                out_tmp_f = os.path.join(out_dir, os.path.basename(self.image_f.split('.SAFE')[0]) + '_' + band_name + '.tif')
                            else:
                                out_tmp_f = os.path.join(out_dir, os.path.basename(self.image_f)
                                                         .replace('.zip', '') + '_' + band_name + '.tif')"""
                            out_tmp_f = os.path.join(out_dir, self.img_root_name + '_' + band_name + '.tif')



                            #out_vrt_tmp_f= out_tmp_f.replace('.tif','.vrt')
                            #af.create_vrt_subset(out_vrt_tmp_f,[envi_f],bbox= bbox_dict,im_xRes=res_out, im_yRes=res_out,im_resampAlg=im_resampleAlg)

                            translate_options_dict = {'format': 'GTiff'}
                            if im_resampleAlg is not None:
                                translate_options_dict['resampleAlg'] = im_resampleAlg
                            if res_out is not None:
                                translate_options_dict['xRes'] = res_out
                                translate_options_dict['yRes'] = res_out

                            if bbox_dict is None:
                                bbox_dict = self.bbox_dict

                            if bbox_dict is not None:
                                translate_options_dict['projWin'] = \
                                    [bbox_dict['xmin'], bbox_dict['ymax'], bbox_dict['xmax'], bbox_dict['ymin']]
                                #translate_options_dict['outputBounds'] = \
                                #    [bbox_dict['xmin'], bbox_dict['ymax'], bbox_dict['xmax'], bbox_dict['ymin']]

                            translate_options_dict['creationOptions'] = ['PHOTOMETRIC=MINISBLACK', 'INTERLEAVE=BAND',
                                                                         'COMPRESS=LZW', 'BIGTIFF=YES']

                            translate_options = gdal.TranslateOptions(**translate_options_dict)

                            gdal.Translate(out_tmp_f, envi_f, options=translate_options)
                            out_f_list.append(out_tmp_f)

        for dim_f in [out_f, out_add_f]:
            if os.path.exists(dim_f):
                os.remove(dim_f)
            data_f = dim_f.replace('.dim', '.data')
            if os.path.isdir(data_f):
                shutil.rmtree(data_f)

        return out_f_list

        
    def read_sclimage(self, res_out=20.0, scl_value_list =[4,5]):

        scl_image = self.read_band('SCL', res_out=res_out, bbox_dict=self.bbox_dict)
        scl_image_msk = np.zeros(scl_image.shape, dtype=np.bool)
        for scl_value in scl_value_list:
            scl_image_msk[scl_image == scl_value] = True
        return scl_image_msk

    def index_calc(self, vi_in,res_out=20, bbox_dict=None, out_f_flag=False, out_dir=None, scl_flag=True, scl_value_list =[4,5]):
        """

        :param vi_in: Vegetation index o LIST of vegetotion indexs be generated. See list below.
        :param res_out: Output image spatial resolution(Def. 20). If None, the nominal band_id spatial resolution is
                        used, if band_id is a string; the highest spatial resolution of band list, otherwise.
        :param bbox_dict: dictionary of COORDINATES of the bounding box to crop. (Def. None)
                          (# bbox = {'xmin': value, 'ymin': value, 'xmax': value, 'ymax': value})
        :param out_f_flag: flag activating output file generation. (Def. False)
        :param out_dir: Output directory name, if radiance is to be exported to TIF file (Def. None). If it is None, the
                        directory of L1C filename is used, and the name is obtained using L1C filename as prefix.
        :param scl_flag: flag activating the use of Sen2Cor classification to filter out undesired pixels
        :param scl_value_list: List of useful values of Sen2Cor classification to be kept in the image.
                                0 NO_DATA
                                1 SATURATED_OR_DEFECTIVE
                                2 CASTED_SHADOWS
                                3 CLOUD_SHADOWS
                                4 VEGETATION
                                5 NOT_VEGETATED
                                6 WATER
                                7 UNCLASSIFIED
                                8 CLOUD_MEDIUM_PROBABILITY
                                9 CLOUD_HIGH_PROBABILITY
                                10 THIN_CIRRUS
                                11 SNOW
        :return:
                dictionary containing the LIST of indexs as keys and the link to output TIF files or the index 2D-Array,
                depending on user's parameters setting

        LIST of available vegetation indexs:
            NDVI  : Normalize Difference Vegetation index
            GNDVI : Green Normalize Difference Vegetation index
            EVI   : Enhanced Vegetation Index
            EVI2  : Enhanced Vegetation Index 2
            CHLRE : Chorophyll red-Edge
            MCARI : Modified Chlorophyll Absorption in Reflectance Index
            NDMI  : normalized difference moisture index
            NDWI  : normalized difference water index
            SAVI  : soil adjusted vegetation index
        """


        index_band_dict = {'NDVI': ['B04', 'B08'],
                           'GNDVI': ['B03', 'B08'],
                           'EVI2': ['B04', 'B08'],
                           'EVI': ['B02', 'B04', 'B08'],
                           'CHLRE': ['B07', 'B05'],
                           'MCARI': ['B03', 'B04', 'B05'],
                           'MDMI': ['B08', 'B11'],
                           'NDWI': ['B03', 'B08'],
                           'SAVI': ['B04', 'B08']}

        if isinstance(vi_in, str):
            vi_in = list(vi_in)

        vi_tmp = []
        out_dict = {}
        for vi in vi_in:
            if out_f_flag:

                out_f = os.path.join(out_dir, self.img_root_name + '_' + vi + '.TIF')
                """if self.format == 'ZIP':
                    out_f = os.path.join(out_dir, os.path.basename(self.image_f).split('.')[0] + '_' + vi + '.TIF')
                elif self.format == 'SAFE':
                    out_f = os.path.join(out_dir,
                                         os.path.basename(self.image_f.split('.SAFE')[0]) + '_' + vi + '.TIF')"""
                if not os.path.exists(out_f):
                    vi_tmp.append(vi)
                else:
                    print('File {} already processed!'.format(os.path.basename(out_f)))
                    out_dict[vi] = out_f

        if out_f_flag is None or len(vi_tmp) > 0:

            band_vec = set([b for b1 in vi_in for b in index_band_dict[b1.upper()]])
            band_dict = {b: self.read_reflectivity(b, res_out=res_out, bbox_dict=self.bbox_dict, geo_info_flag=True)
                         for b in band_vec}
            ref_info = band_dict[list(band_dict.keys())[0]][1]
            scl_image_msk = self.read_sclimage(res_out=res_out, scl_value_list=scl_value_list) if scl_flag else True
            out_dict = {}
            for vi in vi_in:
                if vi.upper() == 'NDVI':
                    data = (band_dict['B08'][0] - band_dict['B04'][0]) / (band_dict['B08'][0] + band_dict['B04'][0])
                if vi.upper() == 'GNDVI':  # Green NDVI
                    data = (band_dict['B08'][0] - band_dict['B03'][0]) / (band_dict['B08'][0] + band_dict['B03'][0])
                elif vi.upper() == 'EVI':
                    data = 2.5 * (band_dict['B08'][0] - band_dict['B04'][0]) / (
                                (band_dict['B08'][0] + 6.0 * band_dict['B04'][0] - 7.5 * band_dict['B02'][0]) + 1.0)
                elif vi.upper() == 'EVI2':
                    data = 2.4 * (band_dict['B08'][0] - band_dict['B04'][0]) / (
                                band_dict['B08'][0] + band_dict['B04'][0] + 1.0)
                elif vi.upper() == 'CHLRE':  # Chlorophyll Red-Edge
                    data = np.power(band_dict['B07'][0] / band_dict['B05'][0], -1)
                elif vi.upper() == 'MCARI':  # Modified Chlorophyll Absorption in Reflectance Index
                    data = ((band_dict['B05'][0] - band_dict['B04'][0]) - 0.2 * (
                                band_dict['B05'][0] - band_dict['B03'][0])) * (
                                       band_dict['B05'][0] / band_dict['B04'][0])
                elif vi.upper() == 'NDMI':  # Normalized Difference Moisture Index(NDMI)
                    data = (band_dict['B08'][0] - band_dict['B11'][0]) / (band_dict['B08'][0] + band_dict['B11'][0])
                elif vi.upper() == 'NDWI':  # Normalized Difference Water Index
                    data = (band_dict['B03'][0] - band_dict['B08'][0]) / (band_dict['B08'][0] + band_dict['B03'][0])
                if vi.upper() == 'SAVI':  # Soil Adjusted Vegetation Index)
                    L = 0.428
                    data = (band_dict['B08'][0] - band_dict['B04'][0]) / (
                                band_dict['B08'][0] + band_dict['B04'][0] + L) * (1.0 + L)

                out_dict[vi] = image_storage(data, scl_image_msk, out_dir, out_f_flag, self.format, self.image_f,
                                             ref_info, vi)

        return out_dict

        """index_band_dict ={  'NDVI' :  ['B04', 'B08'],
                            'GNDVI':  ['B03', 'B08'],
                            'EVI2':   ['B04', 'B08'],
                            'EVI':    ['B02', 'B04', 'B08'],
                            'CHLRE':  ['B07', 'B05'],
                            'MCARI':  ['B03', 'B04', 'B05'],
                            'NDMI':   ['B08', 'B11'],
                            'NDWI':   ['B03', 'B08'],
                            'SAVI':   ['B04', 'B08']}

        if isinstance(vi_in, str):
            vi_in = [vi_in]

        band_vec = set([b for b1 in vi_in for b in index_band_dict[b1.upper()]])
        band_dict ={b: self.read_reflectivity(b, res_out=res_out, bbox_dict=self.bbox_dict, geo_info_flag=True) for b in band_vec}
        ref_info = band_dict[list(band_dict.keys())[0]][1]
        scl_image_msk = self.read_sclimage(res_out=res_out, scl_value_list=scl_value_list) if scl_flag else True
        out_dict={}
        for vi in vi_in:
            if vi.upper() == 'NDVI':
                data = (band_dict['B08'][0] - band_dict['B04'][0]) / (band_dict['B08'][0] + band_dict['B04'][0])
            if vi.upper() == 'GNDVI':  # Green NDVI
                data = (band_dict['B08'][0] - band_dict['B03'][0]) / (band_dict['B08'][0] + band_dict['B03'][0])
            elif vi.upper() == 'EVI':
                data = 2.5 * (band_dict['B08'][0] - band_dict['B04'][0]) / ((band_dict['B08'][0] + 6.0 * band_dict['B04'][0] - 7.5 * band_dict['B02'][0]) + 1.0)
            elif vi.upper() == 'EVI2':
                data = 2.4 * (band_dict['B08'][0] - band_dict['B04'][0]) / (band_dict['B08'][0] + band_dict['B04'][0] + 1.0)
            elif vi.upper() == 'CHLRE':  # Chlorophyll Red-Edge
                data = np.power(band_dict['B07'][0] / band_dict['B05'][0], -1)
            elif vi.upper() == 'MCARI':  # Modified Chlorophyll Absorption in Reflectance Index
                data = ((band_dict['B05'][0] - band_dict['B04'][0]) - 0.2 * (band_dict['B05'][0] - band_dict['B03'][0])) * (band_dict['B05'][0] / band_dict['B04'][0])
            elif vi.upper() == 'NDMI':  # Normalized Difference Moisture Index(NDMI)
                data = (band_dict['B08'][0] - band_dict['B11'][0]) / (band_dict['B08'][0] + band_dict['B11'][0])
            elif vi.upper() == 'NDWI':  # Normalized Difference Water Index
                data = (band_dict['B03'][0] - band_dict['B08'][0]) / (band_dict['B08'][0] + band_dict['B03'][0])
            if vi.upper() == 'SAVI':  # Soil Adjusted Vegetation Index)
                L = 0.428
                data = (band_dict['B08'][0] - band_dict['B04'][0]) / (band_dict['B08'][0] + band_dict['B04'][0] + L) * (1.0 + L)

            out_dict[vi] = image_storage(data, scl_image_msk, out_dir, out_f_flag, self.format, self.image_f, ref_info, vi)

        return out_dict
"""