# -*- coding: utf-8 -*-
"""
Created on Mon Dec 04 12:15:22 2017

Aquest programa cerca les dates (dins d'un rang que es defineix) on hi ha prevista 
l'adquisició d'una imatge Sentinel-2 sobre Catalunya. Per cada possible imatge s'indica
si és el satèl.lit 2A o 2B qui fa l'adquisició. També, per cada imatge, indica quina
òrbita hi ha associada, la R051 (oest), o bé la R008 (est).


@author: v.pala
"""

from datetime import datetime
from datetime import timedelta
        

def HiHa_PAS_2A_2B(Date_Ask_String):
                      
    Date_Ask=datetime.strptime(Date_Ask_String, '%Y-%m-%d')

    Initial_2B_Date_String = '2017-06-30'
    Initial_2B_Date = datetime.strptime(Initial_2B_Date_String, '%Y-%m-%d')

    if (Date_Ask < Initial_2B_Date):     

        InitialDate_S2A_R008_String = '2015-12-30'
        InitialDate_S2A_R051_String = '2016-01-02'
        date_S2A_R008 = datetime.strptime(InitialDate_S2A_R008_String, '%Y-%m-%d')
        date_S2A_R051 = datetime.strptime(InitialDate_S2A_R051_String, '%Y-%m-%d')
    
        Found = False
        Sat_2A_2B = "None"
        Orbit = "None"
    
        while True:
    
            if (date_S2A_R008==Date_Ask):
                Found = True
                Orbit = "R008"
                Sat_2A_2B="A"
                break
            elif (date_S2A_R008>Date_Ask):
                break

            if (date_S2A_R051==Date_Ask):
                Found = True
                Sat_2A_2B="A"
                Orbit = "R051"
                break
            elif (date_S2A_R051>Date_Ask):
                break
                
            date_S2A_R008 += timedelta(days=10)
            date_S2A_R051 += timedelta(days=10)
    
    else:
        InitialDate_S2B_R051_String = '2017-06-30'
        InitialDate_S2A_R008_String = '2017-07-02'
        InitialDate_S2A_R051_String = '2017-07-05'
        InitialDate_S2B_R008_String = '2017-07-07'
        date_S2B_R051 = datetime.strptime(InitialDate_S2B_R051_String, '%Y-%m-%d')
        date_S2A_R008 = datetime.strptime(InitialDate_S2A_R008_String, '%Y-%m-%d')
        date_S2A_R051 = datetime.strptime(InitialDate_S2A_R051_String, '%Y-%m-%d')
        date_S2B_R008 = datetime.strptime(InitialDate_S2B_R008_String, '%Y-%m-%d')
    
        Found = False
        Sat_2A_2B = "None"
        Orbit = "None"
        
        while True:
    
            if (date_S2B_R051==Date_Ask):
                Found = True
                Sat_2A_2B = "B"
                Orbit = "R051"
                break
            elif (date_S2B_R051>Date_Ask):
                break       
            
            if (date_S2A_R008==Date_Ask):
                Found = True
                Sat_2A_2B = "A"
                Orbit = "R008"
                break
            elif (date_S2A_R008>Date_Ask):
                break
            
            if (date_S2A_R051==Date_Ask):
                Found = True
                Sat_2A_2B = "A"
                Orbit = "R051"
                break
            elif (date_S2A_R051>Date_Ask):
                break

            if (date_S2B_R008==Date_Ask):
                Found = True
                Sat_2A_2B = "B"
                Orbit = "R008"
                break
            elif (date_S2B_R008>Date_Ask):
                break
        
        
            date_S2B_R051 += timedelta(days=10)
            date_S2A_R008 += timedelta(days=10)
            date_S2A_R051 += timedelta(days=10)
            date_S2B_R008 += timedelta(days=10)
                     

    return Found, Sat_2A_2B, Orbit




#InitialDateString = "2016-01-01"
#FinalDateString   = "2018-12-31"

InitialDateString = input("Initial Date [ex: 2016-01-01]?: ")
FinalDateString   = input("Final   Date [ex: 2018-12-31]?: ")


InitialDate = datetime.strptime(InitialDateString, '%Y-%m-%d')
FinalDate   = datetime.strptime(FinalDateString, '%Y-%m-%d')

SearchDateString = InitialDateString
SearchDate = InitialDate

print ("\n")
while (SearchDate <= FinalDate):
    Found,Sat_2A_2B, Orbit = HiHa_PAS_2A_2B(SearchDateString)
    if (Found): print (SearchDateString[8:10]+"-"+SearchDateString[5:7]+"-"+SearchDateString[0:4]+"\t"+Sat_2A_2B+"\t"+Orbit)

    SearchDate += timedelta(days=1)
    SearchDateString=(SearchDate).strftime("%Y-%m-%d")
 

                  