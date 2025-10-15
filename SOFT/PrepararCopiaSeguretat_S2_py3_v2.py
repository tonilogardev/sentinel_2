# -*- coding: utf-8 -*-
"""

Programa per copiar a l'espai de backup les dades Sentinel-2 descarregades
i generades durant un mes determinat.


Created on Thu Dec 14 12:19:21 2017

@author: v.pala
"""

import os, fnmatch

#any_mes = "201712"
any_mes = input("Year and month to be copied (ex: 201712): ")

#directory_in  = 'W:\\DARP_S2'
directory_in  = '\\\\sfpcotprod01\\Disc_I\\S2_CAT_NDVI_Download'

#directory_out = 'K:\\TMP'
directory_out = '\\\\icgc.local\\dades\\pcot_storage\\Backup_S2'

#
# Aquesta rutina genera la lllista de tots els arxius que segueixen un 
# patró (wildcard) i que estan en algun dels directoris que penjen d'un
# directory arrel donat.
#
def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


os.system("mkdir "+directory_out+"\\S2_"+any_mes)
 
os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\BTF")
for filename in find_files(directory_in, 'S2*L2A*'+any_mes+'??.btf'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\BTF")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\BTF_DEMCAT")
for filename in find_files(directory_in, 'S2*L2A*'+any_mes+'??_DEMCAT.btf'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\BTF_DEMCAT")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\L1C")
for filename in find_files(directory_in, 'S2*MSIL1C*'+any_mes+'*.zip'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\L1C")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\L2A")
for filename in find_files(directory_in, 'S2*MSIL2A*'+any_mes+'?????????.zip'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\L2A")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\L2A_DEMCAT")
for filename in find_files(directory_in, 'S2*MSIL2A*'+any_mes+'*_DEMCAT.zip'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\L2A_DEMCAT")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\NDVI")
for filename in find_files(directory_in, 'S2*L2A*'+any_mes+'*_NDVI.tif'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\NDVI")
    print (filename)

os.system("mkdir "+directory_out+"\\S2_"+any_mes+"\\SCL")
for filename in find_files(directory_in, 'S2*SCL*'+any_mes+'*.tif'):
    os.system("copy "+filename+" "+directory_out+"\\S2_"+any_mes+"\\SCL")
    print (filename)
