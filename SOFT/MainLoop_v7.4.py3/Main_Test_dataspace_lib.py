from dataspace_lib import eoData
from os.path import join


ex_ID = 'S2'
wkt_polygon = 'POLYGON ((0.1873941083836813 40.46212014624089,3.6319312482049257 40.46212014624089,3.6319312482049257 42.91398496782941,0.1873941083836813 42.91398496782941,0.1873941083836813 40.46212014624089))'
#out_dir_root = r'\\sfpcotprod01\Disc_I\S2_QuickLooks\QuickLooks_2017'
out_dir_root = r'E:\Test\Test_download_S2'
out_dir = join(out_dir_root, '2017-01-03_R008')
out_dir = join(out_dir, 'ZIP')


eodata = eoData()

if ex_ID == 'S1':
    kwarg = {'wkt_search': wkt_polygon,
             'collection': 'Sentinel-1',
             'productType': 'SLC',
             'orbit_direction': 'ASCENDING',
             'sensing_date_start': '2022-06-01',
             'sensing_date_stop': '2022-06-01',
             'sensor_mode': 'IW',
             'relorbnum': 132,
             'top': 100,
             'expand': True}

if ex_ID == 'S2':
    kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 100.00,
             'collection': 'Sentinel-2',
 #            'productType': 'S2MSI1C',
             'productType': 'S2MSI2A',
             #'orbit_direction': 'DESCENDING',
             #'contains_str': '31TCG',
             #'relorbnum': '51',
             'sensing_date_start': '2017-01-16',
             'sensing_date_stop': '2017-01-16',
             'top': 100,
             'expand': True}

if ex_ID == 'S3':
    kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 10.00,
             'collection': 'Sentinel-3',
             'productType': 'SY_2_SYN___',
             'orbit_direction': 'DESCENDING',
             'sensing_date_start': '2022-05-03',
             'sensing_date_stop': '2022-06-03',
             'top': 100,
             'expand': True}

if ex_ID == 'L8':
    kwarg = {'wkt_search': wkt_polygon,
             'cloud_cov': 70.00,
             'collection': 'Landsat8',
             'productType': 'LEVEL1T',
             'sensing_date_start': '2022-06-01',
             'sensing_date_stop': '2022-06-01',
             'top': 100,
             'expand': True}



eodata.search(**kwarg)

data_dict2 = dict()
print(len(eodata.data_dict))
for ind, key in enumerate(eodata.data_dict):
    print (ind)
    print(eodata.data_dict[key]['Name'])
    data_dict2[key]=eodata.data_dict[key]
print(len(data_dict2))
for ind, key in enumerate(data_dict2):
    print (ind)
    print(data_dict2[key]['Name'])
eodata.get_access_token()
eodata.download(out_dir=out_dir, nmax_flux=4)

