import sys
sys.path.insert(0, r'\\sfpcotdev01\PCTODEV01_F\SOFTDEV\NEWSPACE_EXE\MENUT_PROCESS')

import S2lib
import glob
import os
import aux_fun as af
import argparse
import time
import json


fus_epsg_dict = {'T31' : 32631, 'T30' : 32630}

def bbox_erosion(bbox_in, buffer_erosion):

    bbox_out = {'xmin': bbox_in['xmin']+buffer_erosion,
                'xmax': bbox_in['xmax']-buffer_erosion,
                'ymin': bbox_in['ymin']+buffer_erosion,
                'ymax': bbox_in['ymax']-buffer_erosion}

    return bbox_out


class s2_mosaic():
    def __init__(self, dir_data, band_ID_vec, img_res, out_vrt_f, bbox=None, fuse=None, overview_flag=False, del_vrt_flag=False, prm_json_f=r'.\S2_Catalunya.json', msk_ref_band='B04', buffer_erosion=None, res_out=10):
        self.dir_data = dir_data
        self.band_ID_vec = band_ID_vec
        self.img_res = img_res
        self.out_vrt_f = out_vrt_f
        self.bbox = bbox
        self.fuse = fuse
        self.overview_flag = overview_flag
        self.del_vrt_flag = del_vrt_flag
        self.prm_json_f = prm_json_f
        self.msk_ref_band = msk_ref_band
        self.buffer_erosion = buffer_erosion
        self.res_out = res_out
        self.mosaic_out_dict = {}
        self.mask_out_dict = {}

    def set_output_dir(self):
        if self.out_vrt_f is None:
            self.out_dir = None
        else:
            print(' A specific output file name has been specified. Then, the folder is assumed to contain only SAFE (or .ZIP) files from the same FUSE. Therwise, specify the --fuse parameter to avoid overwriting output VRT')
            self.out_dir = os.path.dirname(self.out_vrt_f)

    def set_bbox(self):
        if self.bbox is None:
            self.img_info = {'bbox': {'xmin': None, 'xmax': None, 'ymin': None, 'ymax': None}, 'dx': self.img_res}
        else:
            self.img_info = {'bbox': self.bbox}

    def get_processing_info(self):
        with open(self.prm_json_f) as json_file:
            self.proc_info = json.load(json_file)


    def get_capture_info(self):
        safe_list = glob.glob(os.path.join(self.dir_data, '*.SAFE.zip')) + glob.glob(os.path.join(self.dir_data, '*.SAFE'))
        if len(safe_list) == 0:
            safe_list = glob.glob(os.path.join(self.dir_data, '*.zip'))

        self.capture_root_name = list(set(['_'.join(os.path.basename(_).split('_')[:5]) for _ in safe_list]))[0]
        self.fuse_vec = list(set([os.path.basename(_).split('_')[5][:3] for _ in safe_list]))


    def get_mosaic_limits(self):
        mosaic_limits = [float(__) for __ in [self.proc_info['limitsUTM'][_].split(',') for _ in self.proc_info['limitsUTM'] if
                                              _ in self.capture_root_name][0]]
        self.mosaic_limits_dict = {'xmin': mosaic_limits[0], 'xmax': mosaic_limits[1],
                              'ymax': mosaic_limits[2], 'ymin': mosaic_limits[3]}

    def preprocess_safe(self):

        for ind_fuse, fuse_val in enumerate(self.fuse_vec):
            safe_list = glob.glob(os.path.join(self.dir_data, '*{}*.SAFE.zip'.format(fuse_val))) + \
                        glob.glob(os.path.join(self.dir_data, '*{}*.SAFE'.format(fuse_val)))
            if len(safe_list) == 0:
                safe_list = glob.glob(os.path.join(self.dir_data, '*{}*.zip'.format(fuse_val)))
            print('')
            print('Input images found:')
            print('\n'.join(safe_list))
            print('')
            if self.out_dir is None:
                self.out_dir = os.path.dirname(safe_list[0])

            prefix = 'Ref_'

            if self.out_vrt_f is None:
                mosaic_vrt_f = os.path.join(self.out_dir, prefix + 'Mosaic_FUSE_{}.vrt'.format(fuse_val))
            else:
                mosaic_vrt_f = self.out_vrt_f
            mask_vrt_f = os.path.join(self.out_dir, prefix + 'Mask_FUSE_{}.vrt'.format(fuse_val))

            print(' Output mosaic: {}'.format(mosaic_vrt_f))

            if self.buffer_erosion is None:
                npix_buffer = 51
                self.buffer_erosion = npix_buffer * self.res_out
            else:
                self.npix_buffer = round(self.buffer_erosion / self.res_out)

            if not os.path.exists(mosaic_vrt_f):
                print('Processing.....')
                safe_h_list = [S2lib.S2image(_) for _ in safe_list]

                img_dict = {}
                msk_dict = {}
                for safe_ind, safe_h in enumerate(safe_h_list):
                    print(' - Input image : {}'.format(safe_h.img_root_name))
                    root_name = os.path.basename(safe_list[safe_ind]).split('.SAFE')[0]

                    img_dict[root_name] = os.path.join(self.out_dir, root_name + '.vrt')
                    safe_h.extract_real_bands(self.band_ID_vec, out_image_f=img_dict[root_name], res_out=self.img_info['dx'],
                                              bbox_dict=bbox_erosion(safe_h.img_info['10']['bbox'], self.buffer_erosion))
                    if self.overview_flag:
                        print('    * Overviews being created...')
                        af.overview_gen(img_dict[root_name])
                    if safe_h.producttype == 'L2A':
                        msk_dict[root_name] = safe_h.footprint_dict[self.msk_ref_band]
                    else:
                        msk_dict[root_name] = None
                    img_dict[root_name] = os.path.join(self.out_dir, root_name + '.vrt')
                safe_h_list = [None for _ in safe_h_list]
                del safe_h_list

                if self.fuse is not None and fuse_val == self.fuse:
                    mosaic_limits_vrt = [self.mosaic_limits_dict['xmin'],
                                         self.mosaic_limits_dict['ymin'],
                                         self.mosaic_limits_dict['xmax'],
                                         self.mosaic_limits_dict['ymax']]
                else:
                    mosaic_limits_vrt = None

                af.create_vrt_file(mosaic_vrt_f, [img_dict[root_name] for root_name in img_dict],
                                   im_xRes=self.img_info['dx'],
                                   im_yRes=self.img_info['dx'],
                                   im_resampleAlg='nearest',
                                   im_separate=False,
                                   im_srcNodata=0,
                                   im_outputBounds=mosaic_limits_vrt,
                                   im_targetAlignedPixels=True)
                print('\n   * Output mosaic created successfully!')

                af.create_vrt_file(mask_vrt_f, [msk_dict[root_name] for root_name in msk_dict],
                                   im_xRes=self.img_info['dx'],
                                   im_yRes=self.img_info['dx'],
                                   im_resampleAlg='nearest',
                                   im_separate=False,
                                   im_srcNodata=0,
                                   im_outputBounds=mosaic_limits_vrt,
                                   im_targetAlignedPixels=True)
                print('\n   * Output Mosaic Mask created successfully!')
            else:
                print('\n   * Output mosaic already exists!')

            if self.fuse is not None and not fuse_val == self.fuse:
                print('     * Tile being reprojected : {}'.format(mosaic_vrt_f))
                mosaic_fus_reproj_vrt = mosaic_vrt_f.replace(fuse_val, fuse_val + '_reprojected')
                mask_fus_reproj_vrt = mask_vrt_f.replace(fuse_val, fuse_val + '_reprojected')

                mosaic_limits_vrt = [self.mosaic_limits_dict['xmin'],
                                     self.mosaic_limits_dict['ymin'],
                                     self.mosaic_limits_dict['xmax'],
                                     self.mosaic_limits_dict['ymax']]
                if not os.path.exists(mosaic_fus_reproj_vrt):
                    af.warp_vrt_reproj(mosaic_vrt_f, mosaic_fus_reproj_vrt, self.img_info['dx'], fus_epsg_dict[self.fuse],
                                       mosaic_limits_vrt)

                if not os.path.exists(mask_fus_reproj_vrt):
                    af.warp_vrt_reproj(mask_vrt_f, mask_fus_reproj_vrt, self.img_info['dx'], fus_epsg_dict[self.fuse],
                                       mosaic_limits_vrt)

                self.mosaic_out_dict[fuse_val] = mosaic_fus_reproj_vrt
                self.mask_out_dict[fuse_val] = mask_fus_reproj_vrt

            else:
                self.mosaic_out_dict[fuse_val] = mosaic_vrt_f
                self.mask_out_dict[fuse_val] = mask_vrt_f


    def mosaic_gen(self):

        self.s2_mosaic_vrt = os.path.join(self.out_dir, self.capture_root_name + '_Mosaic_FUSE_{}.vrt'.format(self.fuse))
        self.s2_mosaoc_msk_vrt = os.path.join(self.out_dir, self.capture_root_name + '_Mask_FUSE_{}.vrt'.format(self.fuse))
        self.s2_mosaic_tif = os.path.join(self.out_dir, self.capture_root_name + '_Mosaic_FUSE_{}.tif'.format(self.fuse))
        self.s2_mosaic_msk_tif = os.path.join(self.out_dir, self.capture_root_name + '_Mask_FUSE_{}.tif'.format(self.fuse))
        self.s2_mosaic_temp_tif = os.path.join(self.out_dir, self.capture_root_name + '_Mosaic_FUSE_{}_temp.tif'.format(self.fuse))

        if not os.path.exists(self.s2_mosaic_vrt):
            print('     * Image list to be mosaicked : {}'.format(
                [os.path.basename(self.mosaic_out_dict[_]) for _ in self.mosaic_out_dict]))
            af.create_vrt_file(self.s2_mosaic_vrt, [self.mosaic_out_dict[_] for _ in self.mosaic_out_dict], im_separate=False,
                               im_outputBounds=self.bbox)

        if not os.path.exists(self.s2_mosaoc_msk_vrt):
            print('     * Image list to be mosaicked : {}'.format(
                [os.path.basename(self.mask_out_dict[_]) for _ in self.mask_out_dict]))
            af.create_vrt_file(self.s2_mosaoc_msk_vrt, [self.mask_out_dict[_] for _ in self.mask_out_dict], im_separate=False,
                               im_outputBounds=self.bbox)

        if not os.path.exists(self.s2_mosaic_msk_tif):
            af.vrt2tif_bat(self.s2_mosaoc_msk_vrt, self.s2_mosaic_msk_tif)

        t0 = time.time()
        print(' VRT to TIF conversion...')
        if not os.path.exists(self.s2_mosaic_tif):
            mosaic_info = af.get_im_info(self.s2_mosaic_vrt)
            t00 = time.time()
            print('  Mosaic mask being eroded to avoid Sen2cor artifacts along borders...')
            msk = af.erode_binary_msk(af.read_image(self.s2_mosaic_msk_tif) > 0, self.npix_buffer)
            print('     * Processing time [secs] : {}'.format(round(time.time() - t00)))

            print('  Input value <= 1000 are set to 1001 to avoid Mosaic NoData after ESA Bias removal...')
            t00 = time.time()
            out_h = af.image_output_gen(self.s2_mosaic_temp_tif, mosaic_info['Nlines'], mosaic_info['Ncolumns'],
                                        mosaic_info['Nbands'],
                                        mosaic_info['gdal_datatype'],
                                        geotransform_info=mosaic_info['im_geotransformation'],
                                        src_proj_info=mosaic_info['im_geoprojection'], interleave='BAND')

            for i_band in range(int(mosaic_info['Nbands'])):
                print(f'Band being processed for ESA  offset removal : {i_band}')
                img = af.read_image(self.s2_mosaic_vrt, band_vec=[i_band])
                img[img <= 1000] = 1001
                img = img * msk
                af.write_im_band(out_h, img, i_band + 1)

            out_h = None
            print('     * Processing time [secs] : {}'.format(round(time.time() - t00)))
            print('Mosaic COG generation...')
            t00 = time.time()
            af.vrt2tif_bat(self.s2_mosaic_temp_tif, self.s2_mosaic_tif, scale_vec=[1000, 11000, 0, 10000])
            print('     * Processing time [secs] : {}'.format(round(time.time() - t00)))

            print('     * OVERALL Processing time [secs] : {}'.format(round(time.time() - t0)))

        print('\nTotal time for conversion [secs] : {}'.format(round(time.time() - t0)))

    def delete_tmp_info(self):

        if os.path.exists(self.s2_mosaic_tif):
            if os.path.exists(self.s2_mosaic_temp_tif):
                os.remove(self.s2_mosaic_temp_tif)
            if self.del_vrt_flag:
                vrt_list = glob.glob(os.path.join(self.out_dir, '*.vrt'))
                for _ in vrt_list:
                    print(' VTR being removed : {}'.format(_))
                    os.remove(_)


def main_proc(dir_data, band_ID_vec, img_res, out_vrt_f, bbox=None, fuse=None, overview_flag=False, del_vrt_flag=False, prm_json_f=r'.\S2_Catalunya.json', msk_ref_band='B04', buffer_erosion=None, res_out=10):

    s2m = s2_mosaic(dir_data, band_ID_vec, img_res, out_vrt_f, bbox, fuse, overview_flag, del_vrt_flag, prm_json_f, msk_ref_band, buffer_erosion, res_out)
    s2m.set_output_dir()
    s2m.set_bbox()
    s2m.get_processing_info()
    s2m.get_capture_info()
    s2m.get_mosaic_limits()
    s2m.preprocess_safe()
    s2m.mosaic_gen()
    s2m.delete_tmp_info()


def parse_args():
    argparser = argparse.ArgumentParser(
        description="Perfoms VRT mosaicking of S2 .SAFE or .ZIP tile list contained within an input folder of the bands and at the spatial resolution (optionally)  specified by user")
    # Mandatory arguments
    argparser.add_argument('dir_data', type=str, help=r"Folder containing S2 images")
    # Optional arguments
    argparser.add_argument('--bands', type=str,
                           help=r"String defineing the band to be mosaicked. Default ('B02,B03,B04,B05,B06,B07,B08')",
                           default='B02,B03,B04,B05,B06,B07,B08,B8A,B11,B12')
    argparser.add_argument('--img_res', type=float, help="SPatial resolution of the output VRT file (Default: 5.0 [m])",
                           default=10)
    argparser.add_argument('--bbox', type=str,
                           help="boundix box defining the AOI as a string separated by commas : Ex xmin,xmax,ymin,ymax (default='0')",
                           default='0')
    argparser.add_argument('--fuse', type=str,
                           help="Tile Fuse to be selected in the Sentinel2 nomenclature (ex. T31) (No filter corresponds to default option ='0')",
                           default='T31')
    argparser.add_argument('--overview_flag', type=int, help="Flag (0/1) to generate overviews to speed up final VRT loading (Default=0)", default='0')
    argparser.add_argument('--out_vrt_f', type=str, help="Output VRT file (Default: '0', corresponding to  generic refix MOSAIC followed by the FUSE within the input data folder)", default='0')
    argparser.add_argument('--del_vrt_flag', type=int, help="Delete temporary VRT files [0/1] (Default = 1)", default=1)


    return argparser.parse_args()


if __name__ == '__main__':

    args = parse_args()

    args.bands = args.bands.split(',')

    if args.out_vrt_f == '0':
        args.out_vrt_f = None

    if args.fuse == '0':
        args.fuse = None

    if args.bbox == '0':
        args.bbox = None
    else:
        bbox_list = args.bbox.split(',')
        args.bbox = {'xmin': bbox_list[0], 'xmax': bbox_list[1], 'ymin': bbox_list[2], 'ymax': bbox_list[3]}

    main_proc(args.dir_data, args.bands, args.img_res, args.out_vrt_f, args.bbox, args.fuse, args.overview_flag, args.del_vrt_flag)




