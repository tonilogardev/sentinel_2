# -*- coding: utf-8 -*-
"""
Created on Mon Dec 04 12:15:22 2017

Aquest programa cerca les dates (dins d'un rang que es defineix) on hi ha prevista 
l'adquisició d'una imatge Sentinel-2 sobre Catalunya. Per cada possible imatge s'indica
si és el satèl.lit 2A o 2B qui fa l'adquisició. També, per cada imatge, indica quina
òrbita hi ha associada, la R051 (oest), o bé la R008 (est).


@author: p.rios
"""

from datetime import datetime
from datetime import timedelta
        

def HiHa_PAS_2A_2B_2C(Date_Ask_String):
                      
    Date_Ask=datetime.strptime(Date_Ask_String, '%Y-%m-%d')

    InitialDate_S2A_R008_String = '2025-03-14'
    InitialDate_S2C_R051_String = '2025-03-15'
    InitialDate_S2B_R008_String = '2025-03-17'
    InitialDate_S2A_R051_String = '2025-03-17'
    InitialDate_S2B_R051_String = '2025-03-20'
    InitialDate_S2C_R008_String = '2025-03-22'
    
    Date_S2A_R008 = datetime.strptime(InitialDate_S2A_R008_String, '%Y-%m-%d')
    Date_S2C_R051 = datetime.strptime(InitialDate_S2C_R051_String, '%Y-%m-%d')
    Date_S2B_R008 = datetime.strptime(InitialDate_S2B_R008_String, '%Y-%m-%d')
    Date_S2A_R051 = datetime.strptime(InitialDate_S2A_R051_String, '%Y-%m-%d')
    Date_S2B_R051 = datetime.strptime(InitialDate_S2B_R051_String, '%Y-%m-%d')
    Date_S2C_R008 = datetime.strptime(InitialDate_S2C_R008_String, '%Y-%m-%d')
    
    Found = False
    Sat_2A_2B_2C = "None"
    Orbit = "None"
    
    while True:
    
        if (Date_S2A_R008==Date_Ask):
            Found = True
            Sat_2A_2B_2C = "A"
            Orbit = "R008"
            break
        elif (Date_S2A_R008>Date_Ask):
            break       
        
        if (Date_S2C_R051==Date_Ask):
            Found = True
            Sat_2A_2B_2C = "C"
            Orbit = "R051"
            break
        elif (Date_S2C_R051>Date_Ask):
            break
        
        if (Date_S2B_R008==Date_Ask):
            Found = True
            Sat_2A_2B_2C = "B"
            Orbit = "R008"
            if (Date_S2A_R051==Date_Ask):
                print (Date_Ask_String[8:10]+"-"+Date_Ask_String[5:7]+"-"+Date_Ask_String[0:4]+"\t"+Sat_2A_2B_2C+"\t"+Orbit)
                Sat_2A_2B_2C = "A"
                Orbit = "R051"
            break
        elif (Date_S2B_R008>Date_Ask):
            break

        if (Date_S2B_R051==Date_Ask):
            Found = True
            Sat_2A_2B_2C = "B"
            Orbit = "R051"
            break
        elif (Date_S2B_R051>Date_Ask):
            break
    
        if (Date_S2C_R008==Date_Ask):
            Found = True
            Sat_2A_2B_2C = "C"
            Orbit = "R008"
            break
        elif (Date_S2C_R008>Date_Ask):
            break
 
        Date_S2A_R008 += timedelta(days=10)
        Date_S2C_R051 += timedelta(days=10)
        Date_S2B_R008 += timedelta(days=10)
        Date_S2A_R051 += timedelta(days=10)
        Date_S2B_R051 += timedelta(days=10)
        Date_S2C_R008 += timedelta(days=10)                  

    return Found, Sat_2A_2B_2C, Orbit




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
    Found,Sat_2A_2B_2C, Orbit = HiHa_PAS_2A_2B_2C(SearchDateString)
    if (Found): print (SearchDateString[8:10]+"-"+SearchDateString[5:7]+"-"+SearchDateString[0:4]+"\t"+Sat_2A_2B_2C+"\t"+Orbit)

    SearchDate += timedelta(days=1)
    SearchDateString=(SearchDate).strftime("%Y-%m-%d")
 

                  