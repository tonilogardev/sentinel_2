# -*- coding: utf-8 -*-
"""
Created on Tue Jun 26 14:26:02 2018

@author: v.pala
"""

#
# ****  A la versió 4.0 es va afegir el procés L2A grànul a grànul, evitant aixóGRANULES LIST
# ****  el problema que es apareix amb la versió 2.5.5 de sen2cor que no funciona
# ****  bé quan la imatge té dos "datatake" (dos segments).
# ****
# ****  A la versió 4.1, a més, també es fa el procés grànul a grànul per la generació
# ****  del producte L1C de 4 bandes i la generació de MASK, enlloc d'atacar el 
# ****  producte combinat que es generava abans i que tenia tots els granuls al
# ****  subfolder GRANULE, amb el seu XML modificat (aquest procés ja no és necessari).
#
# ****  A la versió 4.2 es fa un dilation absns dels 50 erosion per tal d'evitar el problema
# ****  d'alguns pixels amb no-data dins la imatge L1C.
# ****  També s'ha modificat el codi per generar els dos ZIPs que cont tots els productes
# ****  L1C i L2A per tal de que no desapareixi el subfolder buït AUX_DATA.
# ****  També es passa a crida la versió 2.8.0 de sen2cor.
#
# **** A la versió 4.3 s'automatitza la descàrrega de productes OFFLINE (dins el modul download)
# **** A la versió 4.4 s'utilitza sen2cor_2.9.0 que corregeix un problema de la versió 2.8 per les nous tile refinats L1C
# **** A la versió 4.4 també es corregeix el problema per de fer UNZIP aparegut a la imatge 2021-04-20
# **** A la versió 4.5 posem totes les dades de customització en un fitxer JSON. Es generalitza l'ús de qualsevol zona UTM
# **** A la versió 5.0 el programa s'adapta a la Baseline 4.00, que requereix sen2cor 2.10 i que implementa gain=10000 i offset=-1000.
# **** A la versió 5.1 el programa s'adapta a la Baseline 4.00, que requereix sen2cor 2.10 i llegeix el gain i offset de les metadades.
# **** A la versió 5.2 s'implementa la generació de COG TIF (amb programari GDAL) per la imatge de 10 bandes i el SCL.
# **** A la versió 6.0 s'adapta el programari a la nova api de dataspace.copernicus
# **** A la versió 6.1 s'implementa un mecanisme per esperar quan es detecta que manca un datastrip
# **** A la versió 6.2 s'elimina la possibilitat d'enviar un email que havia deixat d'estar operativa per canvis a gmail i
# ****                 s'introdueix el JSON com a paràmetre quan s'executa el programa
# **** A la versió 6.3 s'eliminen els arxius dins la carpeta ZIP (excepte granulelist.txt)
# **** A la versió 7.0 s'inclou la generació de segments NDVI a partir de la correcció atmosfèrica amb topografia descrita amb DEM-CAT
# **** A la versió 7.1 hi ha la opció a descarregar només la darrera BASELINE per els productes que estan en diferents BASELINES
# **** A la versió 7.2 en el cas de descarregar només la darrera baseline, s'eliminen els possibles duplicats (mateixa foorprint) (ex: T31TDG de 20220820; two-datatake 20220709, two baseline 20180801)
# ****                 en aquesta versió també es genera la imatge L2A de 10 bandes amb la correcció topogràfica a partir de la qual es calcula el NDVI
# ****                 en aquesta versió també s'implementa la verificació amb checksum de la correcte descàrrega dels arxius. Els arxius antic no tenen checksum.
# **** A la versió 7.3 s'activa en la segona etapa la opció de generar un .RF L1C amb les 4 bandes de 10 metres.
# **** A la versió 7.4 es modifica el codi per generar els arxius tif-cog amb gdal_translate.
# ****                 s'activa el la opció de treballar amb el satel·lit 2C (en principi aquest subtitueix al 2A des del 21/01/2025.
 
import time
from datetime import datetime
from datetime import timedelta
import urllib
import urllib.request
import urllib.parse
import os
import openpyxl
import socket
import zipfile
import sys
import shutil
import fnmatch
import json
##import S2_Parxes_BL_05_11 # PARXE
import os.path


import S2_Segment_Granules_Download_Modules as S2_Download
import S2_MaskGeneration_L1C_Module as S2_Mask
##import S2_Segment_Process_Module as  S2_L1C_Process
import S2_Segment_Process_L1C_4B_Module as  S2_L1C_4B
import S2_Segment_Process_L2A_10B_Module as S2_L2A_10B
import S2_Segment_Process_L2A_SCL_Module as S2_L2A_SCL
import S2_QuickLook_Module as S2_QL
import S2_Segment_Process_NDVI as S2_NDVI




def SearchProducts(SearchDateString, Days_Increment, url, username, password):

    GranulesPerOrbit = params['granulesPerOrbit']

    #--------------------------------        
    # QUERY POlygon definition 
    #--------------------------------   
    poly_search = params['polySearch']



    #---------------------------------------        
    # Sentinel 2 : Request QUERY definition 
    #---------------------------------------    
   
    SearchDate = datetime.strptime(SearchDateString, '%Y-%m-%d')
    SearchDateEndString=(SearchDate+timedelta(days=Days_Increment-1)).strftime("%Y-%m-%d")     
    
#    urlrequest = urllib.parse.quote('https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start ge '+SearchDateString+'T00:00:00.000Z and ContentDate/Start le '+SearchDateEndString+'T23:59:59.999Z'+" and contains(Name,'MSIL1C') and contains(Name,'"+Segment_Orbit+"') and OData.CSC.Intersects(area=geography'SRID=4326;"+poly_search+"')",':()[]/?=,&')
    urlrequest = urllib.parse.quote(url+'odata/v1/Products?$top=500&$filter=ContentDate/Start ge '+SearchDateString+'T00:00:00.000Z and ContentDate/Start le '+SearchDateEndString+'T23:59:59.999Z'+" and contains(Name,'MSIL1C') and contains(Name,'"+Segment_Orbit+"') and OData.CSC.Intersects(area=geography'SRID=4326;"+poly_search+"')",':()[]/?=,&')


    #--------------------------------------------------------   
    # Read and Parse the response stored in page variable
    #--------------------------------------------------------
    page  = urllib.request.urlopen(urlrequest).read()

    #--------------------------------------------------------
    # the entry tag contains the results
    #--------------------------------------------------------

    max_number_granules = 0
    for i_orbit in range(len(GranulesPerOrbit)):
        klist = list(GranulesPerOrbit)
        orbit=klist[i_orbit]
        if (len(GranulesPerOrbit[orbit])>max_number_granules):
            max_number_granules = len(GranulesPerOrbit[orbit])

    granule_list_mark=[0]*max_number_granules
    for i_granule in range(len(granule_list_mark)):
        granule_list_mark[i_granule]=0
    
    nentries = len(json.loads(page)['value'])

#   màxim de granules per òrbita (Max datataken = 15000 Km)
    granule_list_mark=[0]*150
    for i_granule in range(len(granule_list_mark)):
        granule_list_mark[i_granule]=0
    
    for i in range(nentries):
        title_element = json.loads(page)['value'][i]['Name']
        if (title_element.find('_MSIL1C_')>0):
            orbit=title_element[33:37]
            for i_orbit in range(len(GranulesPerOrbit)):
                klist = list(GranulesPerOrbit)
                if (orbit==klist[i_orbit]):
                    granule_ID_pos=title_element.find('_T')+1
                    granule_ID = title_element[granule_ID_pos:granule_ID_pos+6]
                    granule_list=GranulesPerOrbit[orbit]
                    
                    for i_granule in range(len(granule_list)):
                        if (granule_ID==granule_list[i_granule]):
                            granule_list_mark[i_granule]=1
                            baseline = "N"+title_element[28:32]
                            print (SearchDateString,orbit,granule_ID, baseline)
                            sys.stdout.flush()
                            break
                        
    print ('\n>>> ',nentries,' products on ', SearchDateString+"\n")
    sys.stdout.flush()
    if (nentries>0):
        for i_granule in range(len(granule_list)):
            if (granule_list_mark[i_granule]==0):
                print ('**** The granule ',GranulesPerOrbit[orbit][i_granule],' is missing!!!!\n')
                sys.stdout.flush()
                return -1
    else:
        return -1
            
    return 0



#
#   Generate ZIP file including EMPTY DIRs. Necessary for compatibility with sen2cor
#
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


def open_xls_s2(nom_xls):
    while True:
        try:
            xlsnom = os.path.join(WorkingFolder,nom_xls)
            xlsfile = openpyxl.load_workbook(xlsnom)
#            sheet = xlsfile.get_sheet_by_name('Sheet1')
            sheet = xlsfile["Sheet1"]
            break
        except:
            print('Excel file cannot be opened!\n')
            sys.stdout.flush()
            time.sleep(time_sleep)
    return xlsfile, sheet
    
    

def unzip_granule(source_file_path, destination_dir, output_folder):
    with zipfile.ZipFile(source_file_path, 'r') as zip_ref:
        zip_ref.extractall(destination_dir)
    return


#----------------------------------------------------------------------------------------------------------
# MAIN
#----------------------------------------------------------------------------------------------------------

# Cal entrar el JSON com a paràmetre en l'execució. Per exemple es següent: 
#json_name = r'I:\Disc_I\S2_CAT_NDVI_Download\SOFT\MainLoop_v7.1.py3\S2_Catalunya.json'


if len(sys.argv)>1:
    json_name = str(sys.argv[1])
else:
    print('\n\nJSON file name is required as a parameter!\n')


try:
    file_json   = open(json_name,'r') 
    params  = json.load(file_json)  
    file_json.close()
except Exception as e:
    print('\n\nSome unexpected problem opening JSON file!\n')
    print(e)
    sys.exit()


url          = params['downloadURL']
auth_url     = params['authentificationURL']
username     = params['urlUser']
password     = params['urlPwd']
time_sleep   = params['timeSleep']
L1C_product  = params['productL1Cgeneration']
LastBaseline = params['onlyLastBaselineForGranule']
poly_search  = params['polySearch']


Soft_Geoproces = params['softGeoproces']
Soft_GeoprocesGDAL = params['softGeoprocesGDAL']

UTM_Zone_per_Orbit = params['perOrbitZoneUTM']

computer_name=socket.gethostname()
if computer_name not in params['machineDependentParameters']: 
    print('\n\nComputer name not in JSON file!\n')
    sys.exit()

MDparams = params['machineDependentParameters'][computer_name]
WorkingFolder = MDparams['workingFolder']
QuickLook_dir = MDparams['quicklookDir']
Path_L2A_INDEX = MDparams['pathL2AforIndex']
Path_L2A_ORTHO = MDparams['pathL2AforOrthoimage']
nom_xls = MDparams['fileXLS']

checkTwoDatastrips = params['checkTwoDatastrips']
if checkTwoDatastrips=="YES":
    TDDparams = params['twoDatastripsDependingParameters']
    granulesToCheckArea = TDDparams['granulesToCheckArea']
    areaForGranulesToCheck = TDDparams['areaForGranulesToCheck']
    areaThreshold = float(TDDparams['areaThreshold'])
    waitingTime = TDDparams['waitingTime']
else:
    TDDparams = [] 
    granulesToCheckArea =  []
    areaForGranulesToCheck = [] 
    areaThreshold = []
    waitingTime = []
                                    
# Days_Increment must be 1 to assure than all tha granules are from the same date
Days_Increment = 1 
something_done=1

must_wait = False
waiting_list = []


while True:
    if (something_done == 0):
        time.sleep(time_sleep)
        
    print ('********************************************************')
    print ('              ',datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print ('********************************************************')
    print ("")
    sys.stdout.flush()
    
    i=0

    TodayDateString=time.strftime("%Y-%m-%d")
    TodayDate=datetime.strptime(TodayDateString, '%Y-%m-%d')

    xlsfile,sheet=open_xls_s2(nom_xls)
    something_done = 0

    while True:
        if (str(sheet['A'+str(1+i)].value)[0:3]=='END'):
            break
        Segment_Date=str(sheet['A'+str(1+i)].value)[0:10]
        Segment_2A_2B_2C = str(sheet['B'+str(1+i)].value)
        Segment_Orbit=str(sheet['C'+str(1+i)].value)
        Segment_Downloaded=str(sheet['D'+str(1+i)].value)
        Segment_Processed_L1C=str(sheet['E'+str(1+i)].value)
        Segment_Generated_L2A=str(sheet['F'+str(1+i)].value)
        Segment_Processed_L2A=str(sheet['G'+str(1+i)].value)
        Segment_QuickLook_L2A=str(sheet['H'+str(1+i)].value)
        Segment_Generated_L2A_DEMCAT=str(sheet['I'+str(1+i)].value)
        Segment_Processed_L2A_DEMCAT=str(sheet['J'+str(1+i)].value)

        UTM_Zone_to_reproject = UTM_Zone_per_Orbit[Segment_Orbit]

        i=i+1
 
        SearchDateString = Segment_Date
        SearchDate = datetime.strptime(SearchDateString, '%Y-%m-%d')

##        Segment_Folder = WorkingFolder+"\\"+SearchDateString+"_"+Segment_Orbit
        Segment_Folder=os.path.join(WorkingFolder,SearchDateString+"_"+Segment_Orbit)
        if (SearchDate>TodayDate):
            break
        else:
            if (Segment_Downloaded!='*'):

#               Mirem si el segment està a la llista de Segments que cal esperar
                if checkTwoDatastrips=="YES":
                    for ii in range(len(waiting_list)):
                        if ((waiting_list[ii]['Segment_Date']==Segment_Date) and (waiting_list[ii]['Segment_Orbit']==Segment_Orbit)):
                            if (time.time()-waiting_list[ii]['Time'] > waitingTime):
                                del waiting_list[ii]
                            else:
                                ngranules = S2_Download.S2_Segment_Number_of_Granules(Segment_Date, url, poly_search, granules_orbit, Segment_Orbit)
                                if (ngranules==len(granules_orbit)):
                                    break
                                else:
                                    del waiting_list[ii]

                      
                #********************************************************************************* 
                #   DESCÀRREGA DE GRÀNULS L1C
                #********************************************************************************* 
                try:
                    ListOfProducts=[]
                    if (SearchProducts(SearchDateString, Days_Increment, url, username, password)==0):

                        print ('..................................................................')
                        print ('              Downloading: ',SearchDateString)
                        print ('..................................................................')
                        print ("")
                        sys.stdout.flush()

                        if not os.path.isdir(Segment_Folder):
                            os.mkdir(Segment_Folder)
                            os.mkdir(Segment_Folder+"/ZIP")                            
                            os.chdir(Segment_Folder)
                        else:
                            if not os.path.isdir(Segment_Folder+"/ZIP"):
                                os.mkdir(Segment_Folder+"/ZIP")                            
                                os.chdir(Segment_Folder)
                           
                            
                        folder_out = Segment_Folder+"/ZIP"
                        extractiondir = Segment_Folder
                        granules_orbit = params['granulesPerOrbit'][Segment_Orbit]
                        resultat_download, must_wait, waiting_list = S2_Download.S2_Segment_Granules_Download_Function(Segment_2A_2B_2C,SearchDateString, folder_out, extractiondir, url, auth_url, username, password, poly_search, granules_orbit, Segment_Orbit, checkTwoDatastrips, granulesToCheckArea, areaForGranulesToCheck, areaThreshold, waiting_list, LastBaseline)

                        if (resultat_download==1):
                            print('\n\nOpen Hub cannot be accessed!\n')
                            print ("")
                        else:
                            if (not must_wait):
                                print ("")
                                xlsfile,sheet=open_xls_s2(nom_xls)
                                sheet['D'+str(i)].value='*'
                                xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                                something_done = 1
                                             
                        sys.stdout.flush()
                except:
                    print('\n\nSome problem when downloading product!\n')
                    if os.path.isdir(Segment_Folder):
                        xlsfile,sheet=open_xls_s2(nom_xls)
                        sheet['D'+str(i)].value=''
                        xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                            
                    sys.stdout.flush()

            elif (Segment_Processed_L1C!='*'):
                #********************************************************************************* 
                #   DESCÀRREGA DE GRÀNULS I OPCIONALMENT GENERACIÓ DEL PRODUCTE L1C
                #********************************************************************************* 

                print ('................................................................................')
                print ('              Creating the mask and optiomally the 4 bands segment image file: ',SearchDateString)
                print ('................................................................................')
                print ("")
                sys.stdout.flush()

 
                try:
                    #   UNZIP TOTS ELS PRODUCTES (GRÀNULS) L1C

                    extractiondir = Segment_Folder
                    rootPath = extractiondir+"/ZIP"
                    pattern = '*.zip'

                    os.chdir(Segment_Folder)
                 
                    for root, dirs, files in os.walk(rootPath):
                        for filename in fnmatch.filter(files, pattern):
                            pos=filename.find('.zip') 
                            output_folder = filename[:pos]
                            if not os.path.isdir(output_folder+".SAFE"):
                                unzip_granule(rootPath+"\\"+filename, extractiondir, output_folder)    


                    #   ZIP TOTS ELS PRODUCTES (GRÀNULS *.SAFE) l1C

                    try:
                        os.chdir(Segment_Folder)

                        if not os.path.isfile(filename[0:26]+'.zip'):
                            first=0
                            file_SAFE=os.listdir(Segment_Folder)            
                            for nom_file in fnmatch.filter(file_SAFE, '*.SAFE'):
                                if (nom_file[0:10]=="S2A_MSIL1C" or nom_file[0:10]=="S2B_MSIL1C" or nom_file[0:10]=="S2C_MSIL1C"):
                                    #   L1c product is zipped
                                    try:
                                        if (first==0):
                                            zipf = zipfile.ZipFile(nom_file[0:26]+'.zip', 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
                                            first=1
                                        zipdir(nom_file+'/', zipf)
                                    except:                          
                                        print('Error when zipping L1C product!\n')
                                        print ("")
                                        sys.stdout.flush()
                                        break
                                
                            zipf.close()                        
                    except:
                        print('Error when zipping the L1C products!\n')
                        print ("")
                        sys.stdout.flush()


                    #   GENERACIÓ DELES MÀSCARES PER CADA GRÀNUL (folder MASK)

                    os.chdir(Segment_Folder)
    
                    dir_in = Segment_Folder
##                    resultat_mask = S2_Mask.S2_MaskGeneration_L1C(dir_in, Soft_Geoproces)
                    resultat_mask = S2_Mask.S2_MaskGeneration_L1C(dir_in, Soft_GeoprocesGDAL)
    
                    if (resultat_mask==1):
                        print('\n\nSome problem when generating the mask!\n')
                        print ("")
#                        something_done = 1                      # si descomentem i l'error persisteix pot creixer molt el LOG file
                        os.chdir(Segment_Folder) 
                        shutil.rmtree(Segment_Folder+"/MASK")   # elimina la carpeta MASK
                        sys.stdout.flush()
                        break

                    #   GENERACIÓ DE L'ARXIU .RF AMB 4 BANDES
                    print('\n\nChecking Generate L1C product\n')
                    if (L1C_product=="YES"):
                        print('\n\nCalling S2_Segment_Process_L1C_4B\n')
                        compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                        nom_escena = "S2"+Segment_2A_2B_2C+"_"+compact_date
                        print ("\n",dir_in)
                        print ("\n",nom_escena)
##                        resultat_proces = S2_L1C_Process.S2_Segment_Process(dir_in, nom_escena, Soft_Geoproces, UTM_Zone_to_reproject)
                        resultat_L1C_4B = S2_L1C_4B.S2_Segment_Process_L1C_4B(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)
                                                    
##                        if (resultat_proces==1):
                        if (resultat_L1C_4B==1):
                            print('\n\nSome problem when generating 4 band product!\n')
                            print ("")
                            sys.stdout.flush()
                            os.chdir(Segment_Folder)
                            break

                    xlsfile,sheet=open_xls_s2(nom_xls)
                    sheet['E'+str(i)].value='*'
                    xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                    something_done = 1

                    os.chdir(Segment_Folder)
                except:
                    print('\n\nSome unexpected problem when generating the mask and(or the 4 band product!\n')
                    print ("")
                    sys.stdout.flush()
                    
            elif (Segment_Generated_L2A!='*'):
                #********************************************************************************* 
                #   GENERACIÓ DEL PRODUCTE L2A AMB SEN2COR SENSE DEM
                #********************************************************************************* 

                print ('..................................................................')
                print ('              Creating L2A product: ',SearchDateString)
                print ('..................................................................')
                print ("")
                sys.stdout.flush()

##                S2_Parxes_BL_05_11.S2_Parxe1(Segment_Folder) # PARXE

                try:
                    os.chdir(Segment_Folder)
                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in fnmatch.filter(file_SAFE, '*.SAFE'):
                        if (nom_file[0:10]=="S2A_MSIL1C" or nom_file[0:10]=="S2B_MSIL1C" or nom_file[0:10]=="S2C_MSIL1C"):
                            nom_file_dir = os.path.join(Segment_Folder,nom_file)
                            command=Path_L2A_ORTHO+" --resolution 10 "+nom_file
                            ier=os.system(command)
                            if (ier!=0):
                                print('Error when executing sen2cor NO-DEM!\n')
                                print ("")
                                sys.stdout.flush()
                                break
                            else:                    
                                shutil.rmtree(nom_file_dir)       # eliminar producte L1C
##                            sys.stdout.flush()
##                            os.system(command)
##                            shutil.rmtree(nom_file_dir)       # eliminar producte L1C                                                     
                except:
                    print('Error when generating the L2A NO-DEM product!\n')
                    print ("")
                    sys.stdout.flush()
                    break

##                S2_Parxes_BL_05_11.S2_Parxe2(Segment_Folder) # PARXE

                #   ZIP TOTS ELS PRODUCTES (GRÀNULS *.SAFE) l2A

                ier=0
                try:
                    first=0
                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in file_SAFE:
                        if (nom_file[0:10]=="S2A_MSIL2A" or nom_file[0:10]=="S2B_MSIL2A" or nom_file[0:10]=="S2C_MSIL2A"):
                            #   L2A product is zipped
                            try:
                                if (first==0):
                                    zipf = zipfile.ZipFile(nom_file[0:26]+'.zip', 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
                                    first=1
                                zipdir(nom_file+'/', zipf)
                            except:                          
                                print('Error when zipping L2A product!\n')
                                print ("")
                                sys.stdout.flush()
                                ier=1
                                break
                            
                    zipf.close()
                    if (ier==0):          
                        xlsfile,sheet=open_xls_s2(nom_xls)
                        sheet['F'+str(i)].value='*'
                        xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                        something_done = 1                        
                except:
                    print('Error when zipping the L2A products!\n')
                    print ("")
                    sys.stdout.flush()
                    
           
            elif (Segment_Processed_L2A!='*'):
                #********************************************************************************* 
                #   GENERACIÓ DE LA IMATGE TIFF DE 10 BANDES A PARTIR DE L2A SENSE DEM
                #********************************************************************************* 

                print ('..................................................................')
                print ('              Creating 10 bands segment image file: ',SearchDateString)
                print ('..................................................................')
                print ("")
                sys.stdout.flush()

                try:
                    if Segment_Orbit not in params['limitsUTM']: 
                        print('\n\nUTM limits not defined for this orbit in JSON file!\n')
                        sys.exit()
                    limits = params['limitsUTM'][Segment_Orbit].replace(" ","")                  
    
                    os.chdir(Segment_Folder)            
                    dir_in = Segment_Folder
                    compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                    nom_escena = "S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date
                    resultat_L2A_10B = S2_L2A_10B.S2_Segment_Process_L2A_10B(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)
    
                    if (resultat_L2A_10B==1):
                        print('\n\nSome problem when generating the 10 band product!\n')
                        print ("")
                        sys.stdout.flush()
                        os.chdir(Segment_Folder) 
                        break
                    
                    try:
                        os.remove("S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date+".btf.xml")
                    except:
                        print("File S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date+".btf.xml  cannot be removed!\n")
                        sys.stdout.flush()
    
                    os.chdir(Segment_Folder)
                    compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                    nom_escena = "S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date
                    resultat_L2A_SCL = S2_L2A_SCL.S2_Segment_Process_L2A_SCL(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)

                    if (resultat_L2A_SCL==1):
                        print('\n\nSome problem when generating the SCL band product!\n')
                        print ("")
                        sys.stdout.flush()
                        os.chdir(Segment_Folder) 
                        break
    
                    try:
                        os.remove("S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date+".tif.xml")
                    except:
                        print("File S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date+".tif.xml  cannot be removed!\n")
                        sys.stdout.flush()    
                                                       


                    #   ELIMINAR TOTS ELS PRODUCTES l2A EN FORMAT .SAFE

                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in fnmatch.filter(file_SAFE, "*.SAFE"):
                        if (nom_file[0:10]=="S2A_MSIL2A" or nom_file[0:10]=="S2B_MSIL2A" or nom_file[0:10]=="S2C_MSIL2A"):
                            try:
                                shutil.rmtree(Segment_Folder+"/"+nom_file)       # eliminar producte L2A
                            except:                          
                                print('Error when removing L2A product!\n')
                                print ("")
                                sys.stdout.flush()
                                break                            

                    xlsfile,sheet=open_xls_s2(nom_xls)
                    sheet['G'+str(i)].value='*'
                    xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                    something_done = 1

                except:
                    print('\n\nSome unexpected problem when generating the 10 band product!\n')
                    print ("")
                    sys.stdout.flush()
                    break

            elif (Segment_QuickLook_L2A!='*'):
                #********************************************************************************* 
                #   GENERACIÓ DEL QUICKLOOK RGB A PARTIR DEL PRODUCTE L2A DE 10 BANDES (SENSE DEM)
                #********************************************************************************* 

                print ('..................................................................')
                print ('              Creating L2A QuickLook: ',SearchDateString)
                print ('..................................................................')
                print ("")
                sys.stdout.flush()

                try:
                    file_BTF=os.listdir(Segment_Folder)            
                    for nom_file in file_BTF:
                        if (nom_file[0:8]=="S2A_L2A_" or nom_file[0:8]=="S2B_L2A_" or nom_file[0:8]=="S2C_L2A_"):
                            
                            dir_in= Segment_Folder            
                            compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                            nom_escena = "S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date
                            resultat_QuickLook_Generation = S2_QL.QuickLook_Generation(dir_in, QuickLook_dir, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL)
    
                            if (resultat_QuickLook_Generation==1):
                                print('\n\nSome problem when generating the QuickLook!\n')
                                print ("")
                                sys.stdout.flush()
                                os.chdir(Segment_Folder) 
                                break
     
                            xlsfile,sheet=open_xls_s2(nom_xls)
                            sheet['H'+str(i)].value='*'
                            xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                            something_done = 1
                            
                                                            
                except:
                    print('\n\nSome unexpected problem when generating the QuickLook!\n')
                    print ("")
                    sys.stdout.flush()
                    break
                
            elif (Segment_Generated_L2A_DEMCAT!='*'):
                #********************************************************************************* 
                #   GENERACIÓ DEL PRODUCTE L2A AMB SEN2COR I CORRECCIÓ TOPOGRÀFICA (DEM-CAT)
                #********************************************************************************* 

                print ('................................................................................')
                print ('              Creating L2A product with DEM-CAT: ',SearchDateString)
                print ('................................................................................')
                print ("")
                sys.stdout.flush()

                try:
                    #   UNZIP TOTS ELS PRODUCTES (GRÀNULS) L1C

                    extractiondir = Segment_Folder
                    rootPath = extractiondir+"/ZIP"
                    pattern = '*.zip'
                 
                    for root, dirs, files in os.walk(rootPath):
                        for filename in fnmatch.filter(files, pattern):
                            pos=filename.find('.zip') 
                            output_folder = filename[:pos]
                            unzip_granule(rootPath+"\\"+filename, extractiondir, output_folder)    
                except:
                    print('Error when unzipping the L1C product to generate NDVI!\n')
                    print ("")
                    sys.stdout.flush()
                    break

##                S2_Parxes_BL_05_11.S2_Parxe1(Segment_Folder) # PARXE

                try:
                    os.chdir(Segment_Folder)
                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in fnmatch.filter(file_SAFE, '*.SAFE'):
                        if (nom_file[0:10]=="S2A_MSIL1C" or nom_file[0:10]=="S2B_MSIL1C" or nom_file[0:10]=="S2C_MSIL1C"):
                            ier = os.system(Path_L2A_INDEX+" --resolution 10 "+Segment_Folder+"/"+nom_file+"\n")
                            if (ier!=0):
                                print('Error when executing sen2cor DEM-CAT!\n')
                                print ("")
                                sys.stdout.flush()
                                break
                            else:                    
                                shutil.rmtree(Segment_Folder+"/"+nom_file)       # eliminar producte L1C                                                     
                except:
                    print('Error when generating the L2A DEM-CAT product!\n')
                    print ("")
                    sys.stdout.flush()
                    break

##                S2_Parxes_BL_05_11.S2_Parxe2(Segment_Folder) # PARXE

                #   ZIP TOTS ELS PRODUCTES (GRÀNULS *.SAFE) l2A

                ier=0
                try:
                    first=0
                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in file_SAFE:
                        if (nom_file[0:10]=="S2A_MSIL2A" or nom_file[0:10]=="S2B_MSIL2A" or nom_file[0:10]=="S2C_MSIL2A"):
                            #   L2A product is zipped
                            try:
                                if (first==0):
                                    zipf = zipfile.ZipFile(nom_file[0:26]+'_DEMCAT.zip', 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
                                    first=1
                                zipdir(nom_file+'/', zipf)
                            except:                          
                                print('Error when zipping L2A product!\n')
                                print ("")
                                sys.stdout.flush()
                                ier=1
                                break
                            
                    zipf.close()
                    if (ier==0):          
                        xlsfile,sheet=open_xls_s2(nom_xls)
                        sheet['I'+str(i)].value='*'
                        xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                        something_done = 1                        
                except:
                    print('Error when zipping the L2A products!\n')
                    print ("")
                    sys.stdout.flush()

                
            elif (Segment_Processed_L2A_DEMCAT!='*'):
                #****************************************************************
                #   GENERACIÓ DE LA IMATGE TIFF AMB EL NDVI
                #****************************************************************

                print ('..................................................')
                print ('              Creating NDVI file: ',SearchDateString)
                print ('..................................................')
                print ("")
                sys.stdout.flush()

                try:
                    if Segment_Orbit not in params['limitsUTM']: 
                        print('\n\nUTM limits not defined for this orbit in JSON file!\n')
                        sys.exit()
                    limits = params['limitsUTM'][Segment_Orbit].replace(" ","")                    
    
                    os.chdir(Segment_Folder)            
                    dir_in = Segment_Folder
                    compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                    nom_escena = "S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date
                    resultat_L2A_10B = S2_NDVI.S2_Segment_Process_NDVI(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)
    
                    if (resultat_L2A_10B==1):
                        print('\n\nSome problem when generating the NDVI!\n')
                        print ("")
                        sys.stdout.flush()
                        os.chdir(Segment_Folder) 
                        break
                    
                    try:
                        os.remove("S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date+"_NDVI.tif.xml")
                    except:
                        print("File S2"+Segment_2A_2B_2C+"_L2A_"+Segment_Orbit+"_"+compact_date+"_NDVI.tif.xml  cannot be removed!\n")
                        sys.stdout.flush()
    
                    os.chdir(Segment_Folder)
                    compact_date=SearchDateString[0:4]+SearchDateString[5:7]+SearchDateString[8:10]
                    nom_escena = "S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date
                    resultat_L2A_SCL = S2_L2A_SCL.S2_Segment_Process_L2A_SCL(dir_in, nom_escena, Soft_Geoproces, Soft_GeoprocesGDAL, limits, UTM_Zone_to_reproject)

                    if (resultat_L2A_SCL==1):
                        print('\n\nSome problem when generating the SCL band product!\n')
                        print ("")
                        sys.stdout.flush()
                        os.chdir(Segment_Folder) 
                        break
    
                    try:
                        os.remove("S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date+".tif.xml")
                    except:
                        print("File S2"+Segment_2A_2B_2C+"_SCL_"+Segment_Orbit+"_"+compact_date+".tif.xml  cannot be removed!\n")
                        sys.stdout.flush()
                        
                    #   ELIMINAR TOTS ELS PRODUCTES L2A EN FORMAT .SAFE

                    file_SAFE=os.listdir(Segment_Folder)            
                    for nom_file in fnmatch.filter(file_SAFE, "*.SAFE"):
                        if (nom_file[0:10]=="S2A_MSIL2A" or nom_file[0:10]=="S2B_MSIL2A" or nom_file[0:10]=="S2C_MSIL2A"):
                            try:
                                shutil.rmtree(Segment_Folder+"/"+nom_file)       # eliminar producte L2A
                            except:                          
                                print('Error when removing L2A product!\n')
                                print ("")
                                sys.stdout.flush()
                                break                            

                    xlsfile,sheet=open_xls_s2(nom_xls)
                    sheet['J'+str(i)].value='*'
                    xlsfile.save(os.path.join(WorkingFolder,nom_xls))
                    something_done = 1

                    rootPath = Segment_Folder+"/ZIP"
                    pattern = '*.zip'
                 
                    for root, dirs, files in os.walk(rootPath):
                        for filename in fnmatch.filter(files, pattern):
                            os.remove(rootPath+"\\"+filename)


                except:
                    print('\n\nSome unexpected problem when generating the NDVI product!\n')
                    print ("")
                    sys.stdout.flush()
                    break
               
