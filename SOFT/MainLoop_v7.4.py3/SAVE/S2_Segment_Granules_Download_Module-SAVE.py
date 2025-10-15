import urllib
import urllib.request
import urllib.parse
import os
import requests
import json
import time
import zipfile
import shutil
from   pyproj import Geod
from   shapely.geometry import Polygon

       

def S2_Segment_Granules_Download_Function(AcquisitionDate, folder_out, extractiondir, url, auth_url, username, password, poly_search, granules_orbit, Segment_Orbit, checkTwoDatastrips, granulesToCheckArea, areaForGranulesToCheck, areaThreshold, waiting_list, LastBaseline):

    folder_out.replace('\\','//');

    filename_out = folder_out+'//granulelist.txt'
    must_wait = False

   
#--------------------------------        
# Authenticate at scihub webpage
#--------------------------------        

    try:

#---------------------------------------        
# Sentinel 2 : Request QUERY definition 
#--------------------------------------- 
#        urlrequest = urllib.parse.quote('https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=ContentDate/Start ge '+AcquisitionDate+'T00:00:00.000Z and ContentDate/Start le '+AcquisitionDate+'T23:59:59.999Z'+" and contains(Name,'MSIL1C') and contains(Name,'"+Segment_Orbit+"') and OData.CSC.Intersects(area=geography'SRID=4326;"+poly_search+"')",':()[]/?=,&')
        urlrequest = urllib.parse.quote(url+'odata/v1/Products?$top=500&$filter=ContentDate/Start ge '+AcquisitionDate+'T00:00:00.000Z and ContentDate/Start le '+AcquisitionDate+'T23:59:59.999Z'+" and contains(Name,'MSIL1C') and contains(Name,'"+Segment_Orbit+"') and OData.CSC.Intersects(area=geography'SRID=4326;"+poly_search+"')",':()[]/?=,&')


#--------------------------------------------------------   
# Read and Parse the response stored in page variable
#--------------------------------------------------------
        page  = urllib.request.urlopen(urlrequest).read()
    except:
        return 1, must_wait, waiting_list

#--------------------------------------------------------
# the entry tag contains the results
#--------------------------------------------------------
    nentries = len(json.loads(page)['value'])

#----------------------------------------------------------------------------------------------------------------------------------------
# Generation of the list of products to be processed.
# Two products are considered "identical" (execpt for the baseline or the date) if the footprint is the same 
# If two "identical" products have different baselines, only the last baseline is considered when the option is activated
# If two "identical" products have the same baseline but different dates, only the most recent is considered when the option is activated
#-----------------------------------------------------------------------------------------------------------------------------------------

    ListOfProducts=[]   

    for i in range(nentries):
        title_element = json.loads(page)['value'][i]['Name']
        footprint = json.loads(page)['value'][i]['Footprint']
        poligon = footprint[footprint.find('((')+2:footprint.find('))')]
        poligon = poligon.replace(",","")

        if (title_element.find('_MSIL1C_')>0):

            granule_ID_pos=title_element.find('_T')+1
            granule_ID = title_element[granule_ID_pos:granule_ID_pos+6]
            if (granule_ID not in granules_orbit):
                continue
            else:
                baseline = title_element[28:32]
#                ListOfProducts.append([title_element[0:44],baseline,int(baseline),poligon])
                ListOfProducts.append([title_element[0:60],baseline,int(baseline),poligon])
     

    for i in range(len(ListOfProducts)):
        name_i     = ListOfProducts[i][0][0:44]
        baseline_i = ListOfProducts[i][2]
        granule_ID_pos=name_i.find('_T')+1
        granule_ID_i = name_i[granule_ID_pos:granule_ID_pos+6]

        for k in range(i+1,len(ListOfProducts)):
            name_k     = ListOfProducts[k][0][0:44]
            baseline_k = ListOfProducts[k][2]
            granule_ID_pos=name_k.find('_T')+1
            granule_ID_k = name_k[granule_ID_pos:granule_ID_pos+6]

            if (name_i[0:26]+granule_ID_i==name_k[0:26]+granule_ID_k):
                if same_footprint(ListOfProducts[i][3], ListOfProducts[k][3]):
                    if (baseline_i < baseline_k):
                        ListOfProducts[i][1]='XXXX'
                    elif (baseline_i == baseline_k):
                        data_i = int(ListOfProducts[i][0][45:53])
                        data_k = int(ListOfProducts[k][0][45:53])
                        if (data_i < data_k):  # ens quedem amb el producte de data més recent
                            ListOfProducts[i][1]='XXXX'
                        else:
                            ListOfProducts[k][1]='XXXX'                            
                    else:
                        ListOfProducts[k][1]='XXXX'
                        

    ListOfProducts2process = []
    for i in range(len(ListOfProducts)):
        if (LastBaseline.upper()!="YES"):
            ListOfProducts2process.append(ListOfProducts[i][0])
        else:                
            if (ListOfProducts[i][1]!='XXXX'):
                ListOfProducts2process.append(ListOfProducts[i][0])

#--------------------------------------------------------------------------------------        
        
    if os.path.isfile(filename_out):
        f_out = open(filename_out, "a")
#        os.remove(filename_out)
    else:
        f_out = open(filename_out, 'w')

    access_token_exist = False
    
    ngranules = 0
    two_datastrips = False
    
    for i in range(nentries):
        uuid_element = json.loads(page)['value'][i]['Id']
        title_element = json.loads(page)['value'][i]['Name']

        if (title_element.find('_MSIL1C_')>0 and title_element[0:60] in ListOfProducts2process):

            outdir  = folder_out+'//'
            destinationpath = outdir +title_element + '.zip'


            if not os.path.isfile(destinationpath):

                granule_ID_pos=title_element.find('_T')+1
                granule_ID = title_element[granule_ID_pos:granule_ID_pos+6]
                if (granule_ID not in granules_orbit):
                    continue
                else:
                    print (" "+granule_ID)
     
                text_out = uuid_element+' '+title_element+' '+outdir+'\n'
                f_out.write(text_out)
    
                try:
                    os.stat(outdir)
                except:
                    os.mkdir(outdir) 
         
        
            ##################################################
            # Sentinel (single) WHOLE IMAGE Download Block   #
            ##################################################            

    
            # Sentinel FULLIMAGE Download Block  #
                try: 
                    if (not access_token_exist):
                        data = {
                            'grant_type': 'password',
                            'username': username,
                            'password': password,
                            'client_id': 'cdse-public',
                            }

                        start_time = time.time()
                        response = requests.post(auth_url+'auth/realms/CDSE/protocol/openid-connect/token', data=data)    
                        access_token = json.loads(response.text)['access_token']
                        refresh_token = json.loads(response.text)['refresh_token']
                        refresh_expires_in = int(json.loads(response.text)['refresh_expires_in'])
                        access_token_exist = True 
                    else:
#                       CALCULAR access_token a partir de refresh_token i refer refresh_token
                        
                        data = {
                            'grant_type': 'refresh_token',
                            'refresh_token': refresh_token,
                            'client_id': 'cdse-public',
                        }

                        start_time = time.time()
                        response = requests.post(auth_url+'auth/realms/CDSE/protocol/openid-connect/token', data=data)
                        access_token = json.loads(response.text)['access_token']
                        refresh_token = json.loads(response.text)['refresh_token']
                        refresh_expires_in = int(json.loads(response.text)['refresh_expires_in'])

                    downloading_granule(destinationpath,uuid_element,url,access_token)
                    ngranules += 1
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    if (elapsed_time > refresh_expires_in): access_token_exist = False
                    
#                   CAL ESPERAR MÉS TEMPS PER TAL DE QUE ES FACI INGESTION D'UN ALTRE DATASTRIP?
#                   Només per els granules que intervenen en la decisió es calcula l'àrea i es mira el % respecte de l'àrea teòrica 
                    if checkTwoDatastrips=="YES":
                        if (not two_datastrips):
                            if (granule_ID in granulesToCheckArea[Segment_Orbit]):
                                with zipfile.ZipFile(destinationpath) as zf:
                                    zf.extract(title_element+'/MTD_MSIL1C.xml', extractiondir+'/tmp')
                                file_xml   = open(extractiondir+'/tmp/'+title_element+'/MTD_MSIL1C.xml','r')
                                lines = file_xml.readlines()
                                for ii in range(len(lines)):
                                    pos_ini=lines[ii].find('<EXT_POS_LIST>')
                                    if (pos_ini>0):
                                        pos_fin = lines[ii].find('</EXT_POS_LIST>')
                                        poligon = lines[ii][pos_ini+14:pos_fin-1]
                                        area_granule = calcular_area_poligon(poligon)
                                        file_xml.close()
                                        shutil.rmtree(extractiondir+'/tmp')
                                        break
                                fraccio_area = area_granule / float(areaForGranulesToCheck[Segment_Orbit])
                                if (fraccio_area<areaThreshold):
                                    two_datastrips = True
                        
                except:
                    if os.path.isfile(destinationpath): os.remove(destinationpath)
                    return 1, must_wait, waiting_list

    f_out.close()

    if checkTwoDatastrips=="YES":
#        if (two_datastrips):
        if ((ngranules==len(granules_orbit)) and two_datastrips):
            element = {"Segment_Date" : AcquisitionDate, "Segment_Orbit": Segment_Orbit, "Time" : time.time()}
            waiting_list.append(element)
            must_wait = True

    return 0,  must_wait, waiting_list



def downloading_granule(destinationpath,uuid_element,url,access_token):

    import os
 
    while True:
            try:

                os.system('curl -H "Authorization: Bearer '+access_token+'" "'+url+'odata/v1/Products('+uuid_element+')/$value" --location-trusted --output '+destinationpath+'')

                file_size = os.stat(destinationpath).st_size
                if (file_size != 0):
                    break
                else:
                    os.remove(destinationpath)
                
            except urllib.request.HTTPError as error:
                print ("ERROR: ", error.read())
            except urllib.request.URLError as error:
                print ("ERROR: ", error.read())




def calcular_area_poligon(poligon):
#   Define WGS84 as CRS:
    geod = Geod('+a=6378137 +f=0.0033528106647475126')

    footprint = poligon.split()
    lons = []
    lats = []
    for i in range(0, len(footprint)-2):
        if i % 2:
            lons.append(float(footprint[i]))
        else :
            lats.append(float(footprint[i]))

    area, perim = geod.polygon_area_perimeter(lons, lats)
    return abs(area)/1000000.



def convertir_pol(poligon):
    footprint = poligon.split()
    llista_punts = []
    k=0
    while k<len(footprint)-2:
        llista_punts.append((float(footprint[k]), float(footprint[k+1])))
        k=k+2
    return Polygon(llista_punts)



def same_footprint(footprint1, footprint2):
#   Define WGS84 as CRS:
    geod = Geod('+a=6378137 +f=0.0033528106647475126')

    area1 = calcular_area_poligon(footprint1) # Positive is counterclockwise, the data is clockwise.
    pol1 = convertir_pol(footprint1)

    area2 = calcular_area_poligon(footprint2) # Positive is counterclockwise, the data is clockwise.
    pol2 = convertir_pol(footprint2)

    points = pol1.intersection(pol2) # multipoint
    
    intersect_lat = points.exterior.xy[0]
    intersect_lon = points.exterior.xy[1]
    area_intersect, perim = geod.polygon_area_perimeter(intersect_lon, intersect_lat)  # Intersection is positive since it is counterclockwise.
    
    area_intersect = area_intersect/1000000
    if (area_intersect/max(area1,area2)>0.99):
        return True
    else:
        return False



def S2_Segment_Number_of_Granules(AcquisitionDate, url, poly_search, granules_orbit, Segment_Orbit):

    try:
        
        #---------------------------------------        
        # Sentinel 2 : Request QUERY definition 
        #--------------------------------------- 
        urlrequest = urllib.parse.quote(url+'odata/v1/Products?$top=500&$filter=ContentDate/Start ge '+AcquisitionDate+'T00:00:00.000Z and ContentDate/Start le '+AcquisitionDate+'T23:59:59.999Z'+" and contains(Name,'MSIL1C') and contains(Name,'"+Segment_Orbit+"') and OData.CSC.Intersects(area=geography'SRID=4326;"+poly_search+"')",':()[]/?=,&')

        #--------------------------------------------------------   
        # Read and Parse the response stored in page variable
        #--------------------------------------------------------
        page  = urllib.request.urlopen(urlrequest).read()

    except:
        return 0

    nentries = len(json.loads(page)['value'])
    ngranules = 0
    
    for i in range(nentries):
        title_element = json.loads(page)['value'][i]['Name']

        if (title_element.find('_MSIL1C_')>0):

            granule_ID_pos=title_element.find('_T')+1
            granule_ID = title_element[granule_ID_pos:granule_ID_pos+6]
            if (granule_ID in granules_orbit):
                ngranules += 1

    return ngranules


