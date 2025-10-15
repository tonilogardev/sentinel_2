# -*- coding: utf-8 -*-
"""
Created on Wed Mar 22 19:01:54 2023

@author: l.pipia
"""

import urllib
import urllib.request as urllib2
from ssl import create_default_context
from certifi import where
from json import loads
import requests
import os
from threading import Thread
from threading import Semaphore
from datetime import datetime
from time import sleep
import subprocess as sb


datahub_user_dict = {'l.pipia' : {'userID': 'luca.pipia@icgc.cat',
                                  'userPSW': 'Tropuilde1976$'},
                     'f.perez' : {'userID': 'fernando.perez@icgc.cat',
                                  'userPSW': 'User2023$2023$'},
                     'p.rios' : {'userID': 'pere.rios@icgc.cat',
                                  'userPSW': 'User1234$#4321#$'}}


def check_size(im_f, size_th=1024 * 1024):
    file_stats = os.stat(im_f)
    return round(file_stats.st_size / (1024 * 1024)) > 0


def curl_call(access_token, uuid_element, out_f, max_calls=10):
    cmd_Str = 'curl --progress-bar -H "Authorization: Bearer ' + access_token + '" "https://catalogue.dataspace.copernicus.eu/odata/v1/Products(' + uuid_element + ')/$value" --location-trusted --output ' + out_f + ''
    #cmd_Str = 'curl -H "Authorization: Bearer ' + access_token + '" "https://catalogue.dataspace.copernicus.eu/odata/v1/Products(' + uuid_element + ')/$value" --location-trusted --output ' + out_f + ''

    cnd = True
    cnt = 0
    while cnd:
        #os.system(cmd_Str)
        result = sb.run(cmd_Str, stdout=sb.PIPE)#, capture_output=True)

        if check_size(out_f):
            print('Downloading {} successful!'.format(os.path.basename(out_f)))
            cnd = False
        else:
            print('{}  empty. Being deleted and downloaded again!'.format(os.path.basename(out_f)))
            os.remove(out_f)
            cnt += 1
            sleep(5)

            if cnt > max_calls:
                print('{} downloading aborted. Maximum numbers of attemps reached!'.format(os.path.basename(out_f)))
                cnd = False


def task(semaphore, access_token, uuid_element, out_f):
    with semaphore:
        curl_call(access_token, uuid_element, out_f)


num_attrib_str_gen = lambda x, y, op: "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq '{1}' and att/" \
                                  "OData.CSC.DoubleAttribute/Value {3} XXX_{2})"\
                                  .replace('{1}', x).replace('{2}', y).replace('{3}',op)
str_attrib_str_gen = lambda x, y, op: "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq '{1}' and att/" \
                                  "OData.CSC.StringAttribute/Value {3} 'XXX_{2}')"\
                                  .replace('{1}', x).replace('{2}', y).replace('{3}',op)

datasource_str_dict = {
    'safe_name': "Name ee 'XXX_safe_name",
    'contains_str': "contains(Name,'XXX_contains_str')",
    'sensing_date_start': "ContentDate/Start gt XXX_sensing_date_startT00:00:00.000Z",
    'sensing_date_stop': "ContentDate/End lt XXX_sensing_date_stopT23:59:59.000Z",
    'publication_date_start': "PublicationDate gt XXX_publication_date_startT00:00:00.000Z",
    'publication_date_stop': "PublicationDate lt XXX_publication_date_stopT23:59:59.000Z",
    'collection': "Collection/Name eq 'XXX_collection'",
    'wkt_search': "OData.CSC.Intersects(area=geography'SRID=4326;XXX_wkt_search')",
    'cloud_cov': num_attrib_str_gen('cloudCover', 'cloud_cov', 'lt'),
    'relativeOrbitNumber': num_attrib_str_gen('relativeOrbitNumber', 'relativeOrbitNumber', 'eq'),
    'productType': str_attrib_str_gen('productType', 'productType', 'eq'),
    'orbit_direction': str_attrib_str_gen('orbitDirection', 'orbit_direction', 'eq'),
    'sensor_mode': str_attrib_str_gen('operationalMode', 'sensor_mode', 'eq'),
    'top': "&$top=XXX_top",
    'expand': "&$expand=Attributes"}

collection_opt = ['Sentinel1', 'SENTINEL-1', 'Sentinel2', 'SENTINEL-2', 'Sentinel3', 'SENTINEL-3', 'Sentinel5P',
                  'SENTINEL-5P']

collection_split = {'SENTINEL-1': '.SAFE',
                    'SENTINEL-2': '.SAFE',
                    'SENTINEL-3': '.SEN3',
                    'SENTINEL-5P': '',
                    'LANDSAT-7': '',
                    'LANDSAT-8': ''}

collection_dict = {'Sentinel1': {'productType': ['SCL', 'GRD'],
                                 'platform': ['S1A', 'S1B'],
                                 'sensorMode': ['EW', 'IW', 'SM', 'WV'],
                                 'orbitDirection': ['ASCENDING', 'DESCENDING'],
                                 'polarisation': ["HH", "HV", "VH", "VV", "VV VH", "VH VV", "HH HV"],
                                 'instrument': 'SAR-C SAR'},
                   'Sentinel2': {'productType': ['S2MSI1C', 'S2MSI2A'],
                                 'platform': ['S2A', 'S2B'],
                                 'orbitDirection': ['DESCENDING'],
                                 'instrument': ['MSI']},
                   'Sentinel3': {'productType': ["OL_1_EFR___",
                                                 "OL_1_ERR___",
                                                 "SR_2_LAN___",
                                                 "SR_2_LAN_HY",
                                                 "SR_2_LAN_LY",
                                                 "SR_2_LAN_SI",
                                                 "OL_2_LFR___",
                                                 "OL_2_LRR___",
                                                 "SL_2_LST___",
                                                 "SL_1_RBT___",
                                                 "SL_2_AOD___",
                                                 "SL_2_FRP___",
                                                 "SR_1_SRA___",
                                                 "SR_1_SRA_A_",
                                                 "SR_1_SRA_BS",
                                                 "SY_2_SYN___",
                                                 "SY_2_V10___",
                                                 "SY_2_VG1___",
                                                 "SY_2_VGP___",
                                                 "SR_2_WAT___",
                                                 "SY_2_AOD___",
                                                 "OL_2_WFR___",
                                                 "OL_2_WRR___",
                                                 "SL_2_WST___"],
                                 'platform': ['S3A', 'S3B'],
                                 'orbitDirection': ['DESCENDING'],
                                 'instrument': ["OLCI", "SLSTR", "SRAL"]},
                   'Sentinel5P': {'productType': ["L1B_IR_SIR",
                                                  "L1B_IR_UVN",
                                                  "L1B_RA_BD1",
                                                  "L1B_RA_BD2",
                                                  "L1B_RA_BD3",
                                                  "L1B_RA_BD4",
                                                  "L1B_RA_BD5",
                                                  "L1B_RA_BD6",
                                                  "L1B_RA_BD7",
                                                  "L1B_RA_BD8",
                                                  "L2__AER_AI",
                                                  "L2__AER_LH",
                                                  "L2__CH4___",
                                                  "L2__CLOUD_",
                                                  "L2__CO____",
                                                  "L2__HCHO__",
                                                  "L2__NO2___",
                                                  "L2__NP_BD3",
                                                  "L2__NP_BD6",
                                                  "L2__NP_BD7",
                                                  "L2__O3____",
                                                  "L2__O3__PR",
                                                  "L2__O3_TCL",
                                                  "L2__SO2___",
                                                  "AUX_CTMANA",
                                                  "AUX_CTMFCT"],
                                  'platform': ['S5P'],
                                  'orbitDirection': ['DESCENDING'],
                                  'instrument': ['TROPOMI'],
                                  'sensorMode': ['RPRO', 'NRTI', 'OFFL']},
                   'Landsat7': {'productType': ['GTC_1P', 'L1G', 'L1GT', 'L1T'],
                                'platform': ["LANDSAT-7"],
                                'sensorMode': ['EW', 'IW', 'SM', 'WV'],
                                'instrument': ['ETM', 'ETM_BUMPER'],},
                   'Landsat8': {'productType': ['LEVEL1', 'LEVEL1GT', 'LEVEL1T', 'LEVEL1TP', 'LEVEL2', 'LEVEL2SP'],
                                'platform': ["LANDSAT-8"],
                                'instrument': ['OLI_TIRS'],
                                }
                   }


class eoData:

    def __init__(self, url="https://catalogue.dataspace.copernicus.eu/odata/v1/Products?",
                 url_token='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
                 userID=None,
                 userPSW=None):

        user_login = os.getlogin()
        if userID is not None and userPSW is not None:
            self.userID = userID
            self.userPSW =userPSW
        elif user_login in datahub_user_dict:
            print(' USER {} authorized for processing!'.format(user_login))
            self.userID = datahub_user_dict[user_login]['userID']
            self.userPSW = datahub_user_dict[user_login]['userPSW']
        else:
            print(' USER {} NOT authorized for processing!COpernicus DATASPACE credentials requiered!'.format(user_login))
            self.userID = input(' Input USERNAME :')
            self.userPSW = input(' Input USERPSW :')

        self.collection_dict = collection_dict
        self.url_root = url
        self.url_token = url_token

        self.url_filter = self.url_root + "$filter="
        self.data_dict = None
        self.token_dict = None


    def get_sensor_list(self):
        print('List of supported sensors:')
        print('\n'.join(list(collection_dict.keys())))

    def search(self, safe_name=None, contains_Str=None, sensing_date_start=None, sensing_date_stop=None,
               publication_date_start=None, publication_date_stop=None, collection=None, sensor_mode=None,
               wkt_search=None, contains_str = None,
               cloud_cov=None, productType=None, orbit_direction=None, top=None, expand=False, relorbnum=None):

        check = lambda x: x if isinstance(x, str) else str(x)

        opt_list = list()

        if sensing_date_start is not None and sensing_date_stop is not None:
            opt_list.append(
                datasource_str_dict['sensing_date_start'].replace('XXX_sensing_date_start', sensing_date_start))
            opt_list.append(
                datasource_str_dict['sensing_date_stop'].replace('XXX_sensing_date_stop', sensing_date_stop))

        if publication_date_start is not None and publication_date_stop is not None:
            opt_list.append(datasource_str_dict['publication_date_start'].replace('XXX_publication_date_start',
                                                                                  publication_date_start))
            opt_list.append(datasource_str_dict['publication_date_stop'].replace('XXX_publication_date_stop',
                                                                                 publication_date_stop))

        if safe_name is not None:
            opt_list.append(datasource_str_dict['safe_name'].replace('XXX_safe_name', safe_name))

        if contains_Str is not None:
            assert contains_Str in collection_opt, 'Collection Name not supported'
            opt_list.append(datasource_str_dict['contains_Str'].replace('XXX_contains_Str', contains_Str))

        if collection is not None:
            opt_list.append(datasource_str_dict['collection'].replace('XXX_collection', collection.upper()))

        if sensor_mode is not None:
            if collection.upper() == 'SENTINEL-1':
                opt_list.append(datasource_str_dict['sensor_mode'].replace('XXX_sensor_mode', sensor_mode))

        if wkt_search is not None:
            opt_list.append(datasource_str_dict['wkt_search'].replace('XXX_wkt_search', wkt_search))

        if contains_str is not None:
            opt_list.append(datasource_str_dict['contains_str'].replace('XXX_contains_str', contains_str))

        if cloud_cov is not None:
            opt_list.append(datasource_str_dict['cloud_cov'].replace('XXX_cloud_cov', check(cloud_cov)))

        if productType is not None:
            opt_list.append(datasource_str_dict['productType'].replace('XXX_productType', productType))

        if orbit_direction is not None:
            opt_list.append(datasource_str_dict['orbit_direction'].replace('XXX_orbit_direction', orbit_direction))

        if relorbnum is not None:
            opt_list.append(
                datasource_str_dict['relativeOrbitNumber'].replace('XXX_relativeOrbitNumber', check(relorbnum)))

        requestString = self.url_filter + ' and '.join(opt_list)

        if top is not None:
            requestString = requestString + datasource_str_dict['top'].replace('XXX_top', check(top))

        if expand:
            requestString = requestString + datasource_str_dict['expand']

        urlRequest = urllib.parse.quote(requestString, ':()[]/?=,&')

        # Perform the query
        page = urllib2.urlopen(urlRequest, context=create_default_context(cafile=where())).read()
        self.data_dict = {_['Name'].split(collection_split[collection.upper()])[0]: _ for _ in loads(page)['value']}

    def get_access_token(self):

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'password',
                'username': self.userID,
                'password': self.userPSW,
                'client_id': 'cdse-public'}

        response = requests.post(self.url_token, data=data, headers=headers)
        token_dict = loads(response.text)
        token_dict['t0'] = datetime.now()
        self.token_dict = token_dict

    def get_refresh_token(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'refresh_token',
                'refresh_token': self.token_dict['refresh_token'],
                'client_id': 'cdse-public'}

        response = requests.post(self.url_token, data=data, headers=headers)
        token_dict = loads(response.text)
        token_dict['t0'] = datetime.now()
        self.token_dict = token_dict

    def download(self, im_dict=None, nmax_flux=1, out_dir=None):

        if out_dir is None:
            out_dir = os.getcwd()
        else:
            if not os.path.isdir(out_dir):
                os.mkdir(out_dir)

        if im_dict is None:
            im_dict = self.data_dict

        token_access_th = self.token_dict['expires_in']
        toke_refresh_th = self.token_dict['refresh_expires_in']
        out_f_list = []
        semaphore = Semaphore(nmax_flux)
        dw_check = True
        process_vec = [False for _ in range(len(im_dict))]
        worker_list = []

        while dw_check:
            for ind, key in enumerate(im_dict):
                delta_sec = (datetime.now() - self.token_dict['t0']).seconds
                if token_access_th < delta_sec < toke_refresh_th:
                    self.get_refresh_token()
                elif delta_sec > toke_refresh_th:
                    self.get_access_token()
                out_f = os.path.join(out_dir, self.data_dict[key]['Name'].replace('.SAFE', '.zip'))
                out_f_list.append(out_f)

                if os.path.exists(out_f):
                    if check_size(out_f):
                        process_vec[ind] = True
                    else:
                        os.remove(out_f)
                else:
                    worker = Thread(target=task, args=(semaphore,
                                                       self.token_dict['access_token'], self.data_dict[key]['Id'],
                                                       out_f))
                    worker.start()
                    worker_list.append(worker)

            # We make sure all the threads are finished.
            for w in worker_list:
                w.join()

            if all(process_vec):
                dw_check = False

        out_f_list = [_ for _ in out_f_list if os.path.exists(_)]

        return out_f_list


