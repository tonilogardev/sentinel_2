# Programari S2-PROCESS: Processament d'Imatges Sentinel-2

## Index

1. [Visió General](#1-visió-general)
2. [Estructura de Directoris](#2-estructura-de-directoris)
3. [Arquitectura del Pipeline](#3-arquitectura-del-pipeline)
4. [Configuració amb JSON](#4-configuració-amb-json)
5. [Fitxer Excel de Seguiment (XLS)](#5-fitxer-excel-de-seguiment-xls)
6. [Mòdul Principal: MainLoop_v7.4](#6-mòdul-principal-mainloop_v74)
7. [Mòdul de Descàrrega (Download)](#7-mòdul-de-descàrrega-download)
8. [Llibreria Client API Copernicus DataSpace (dataspace_lib)](#8-llibreria-client-api-copernicus-dataspace-dataspace_lib)
9. [Mòdul de Generació de Màscares (Mask)](#9-mòdul-de-generació-de-màscares-mask)
10. [Mòdul de Processament L1C 4 Bandes](#10-mòdul-de-processament-l1c-4-banderes)
11. [Correcció Atmosfèrica amb Sen2Cor](#11-correcció-atmosfèrica-amb-sen2cor)
12. [Mòdul de Processament L2A 10 Bandes](#12-mòdul-de-processament-l2a-10-banderes)
13. [Mòdul de Classificació SCL](#13-mòdul-de-classificació-scl)
14. [Mòdul de Càlcul NDVI](#14-mòdul-de-càlcul-ndvi)
15. [Mòdul de Generació de QuickLook](#15-mòdul-de-generació-de-quicklook)
16. [Llibreries de Suport](#16-llibreries-de-suport)
17. [Eines Auxiliars Independents](#17-eines-auxiliars-independents)
18. [Scripts de Pass-Finder](#18-scripts-de-pass-finder)
19. [Entorn i Dependències](#19-entorn-i-dependències)
20. [Evolució del Programari (Versions)](#20-evolució-del-programari-versions)

---

## 1 Visió General

El **S2-PROCESS** és un sistema de processament automàtic d'imatges **Sentinel-2** (ESA) que cobreix **Catalunya**. Descarrega, processa i genera productes derivats (mosaics, NDVI, màscares, QuickLooks) de forma completament automatitzada.

El sistema és obra de **V. Pala** i **P. Ríos** (ICGC), escrit en **Python 3.8** amb **GDAL 3.2.2**, i s'executa en entorn **Windows Server** amb **Conda**.

![Pipeline S2-PROCESS](./img/SOFT_pipeline.png)

***Funció principal***: Orquestrar la cadena: `Descàrrega → Descomprimir → Mosaic L1C → Sen2Cor → Mosaic L2A 10B → NDVI → SCL → Màscara → QuickLook`

[←Index](#index)

---

## 2 Estructura de Directoris

```
SOFT/
├── MainLoop_v7.4.py3/                  # ★ Codi principal (actiu)
│   ├── MainLoop_v7.4_new.py            #   Orquestrador principal
│   ├── MainLoop_v7.4.py                #   Versió base v7.4
│   ├── MainLoop_v7.4-PARXE.py          #   Variant campanya PARXE
│   ├── MainLoop_v7.4_segu200125.py     #   Variant Seguiment 2025-01-20
│   ├── MainLoop_v7.4_GEOAICUBE.py      #   Variant campanya GEOAICUBE
│   ├── MainLoop_v7.4_add2C.py          #   Variant amb suport Sentinel-2C
│   ├── S2_Catalunya.json               #   Configuració estàndard CAT
│   ├── S2_Catalunya_GEOAICUBE.json     #   Configuració GEOAICUBE
│   ├── S2_Catalunya_2019.json          #   Configuració 2019
│   ├── S2_Catalunya_Abril.json         #   Configuració Abril
│   ├── S2_Catalunya_Maig.json          #   Configuració Maig
│   ├── S2_Catalunya_New.json           #   Configuració New
│   ├── S2_Catalunya_*.json             #   Altres configuracions
│   ├── S2_Segment_Granules_Download_Modules.py        #   Mòdul descàrrega
│   ├── S2_Segment_Process_L1C_4B_Module_new.py        #   Mosaic L1C 4 bandes
│   ├── S2_Segment_Process_L2A_10B_Module_new.py       #   Mosaic L2A 10 bandes
│   ├── S2_Segment_Process_L2A_SCL_Module_new.py       #   Extracció SCL
│   ├── S2_Segment_Process_NDVI_Module_new.py          #   Càlcul NDVI
│   ├── S2_MaskGeneration_L1C_Module_new.py            #   Màscares (GDAL+OpenCV)
│   ├── S2_QuickLook_Module.py                         #   QuickLook (ICCImage)
│   ├── S2_QuickLook_Module_SEGU.py                    #   QuickLook (GDAL)
│   ├── S2_safe_mosaic_vrt_v2.py                       #   Mosaic VRT (classe)
│   ├── S2_Parxes_BL_05_11.py                          #   Parxe Baseline 05.11
│   ├── dataspace_lib.py                               #   Client API DataSpace
│   ├── S2lib.py                                       #   Llibreria S2 principal
│   ├── aux_fun.py                                     #   Funcions auxiliars GDAL
│   ├── aux_fun_old.py                                 #   Auxiliars antics (CuPy)
│   ├── S2_offset_gain.py                              #   Lector offset/gain XML
│   ├── S2_utis.py                                     #   Utilitats COG/QL
│   ├── SAVE/                                          #   Còpies de seguretat
│   └── Test_Python.py, test_main.py, ...              #   Tests
│
├── MainLoop_v7.3.py3/                  # ★ Codi anterior v7.3 (autocontingut)
├── Sen2Cor-02.12.03-win64/             # Sen2Cor 2.12.03 (actual)
├── Sen2Cor-02.11.00-win64/             # Sen2Cor 2.11.00 (antic)
├── sen2cor_data/                       # Dades de runtime Sen2Cor
├── sen2cor_data-SAVE-2.11/             # Còpia de seguretat dades 2.11
├── Environment S2-PROCESS/             # Recepta d'entorn Conda
├── tiff2cog.py                         # Convertidor TIFF→COG autònom
├── Genera_ZIPs_py3.py                  # Reestructurador de ZIPs
├── Proces_Imatges_Velles_S2.py         # Processador d'imatges històriques
├── Pas_S2_CAT_py3.py                   # Pass-finder (S2A+S2B)
├── Pas_S2_AND_py3.py                   # Pass-finder AND (S2A+S2B)
├── Pas_S2_CAT_S2A_S2B_S2C_py3.py      # Pass-finder CAT (S2A+S2B+S2C)
├── Pas_S2_AND_S2A_S2B_S2C_py3.py      # Pass-finder AND (S2A+S2B+S2C)
├── Pas_S2_CAT_py3_oldversion_190925.py # Pass-finder CAT antic
├── Python_Generic.txt                  # Notes generals Python
├── S2_Tiles_Catalunya_geo.gpkg         # Índex de tiles de Catalunya
└── S2_World_Tile.qgz                   # Projecte QGIS
```

[←Index](#index)

---

## 3 Arquitectura del Pipeline

El pipeline principal s'executa per a cada segment (data + òrbita) processant seqüencialment 6 etapes. Cada etapa s'enregistra en un fitxer **Excel** que serveix com a màquina d'estats:

```
1. 📥 DOWNLOAD     → Descarrega granules L1C (DataSpace API)
2. 🎭 MASK + L1C   → Genera màscares + mosaic L1C 4 bandes (B02,B03,B04,B08)
3. 🌤️ SEN2COR      → Correcció atmosfèrica L1C→L2A (sense DEM o amb DEM-CAT)
4. 🖼️ L2A 10B      → Mosaic L2A de 10 bandes (B02-B12) + SCL
5. 🌿 NDVI         → Càlcul d'índex de vegetació
6. 👁️ QUICKLOOK    → Generació RGB JPEG + 16b COG
```

***Decisió arquitectònica clau***: El procés Sen2Cor s'executa **grànul a grànul** (no sobre el mosaic complet) per evitar problemes amb imatges que tenen dos "datatake" (dos segments). Això es va implementar a la versió 4.0.

[←Index](#index)

---

## 4 Configuració amb JSON

El sistema es configura exclusivament mitjançant fitxers **JSON**. Cada variant del programa té el seu propi JSON.

Exemple: [S2_Catalunya.json](../SOFT/MainLoop_v7.4.py3/S2_Catalunya.json)

| Paràmetre | Descripció |
|---|---|
| `downloadURL` | URL base API DataSpace Copernicus |
| `authentificationURL` | URL d'autenticació OAuth2 |
| `urlUser` / `urlPwd` | Credencials d'accés |
| `softGeoproces` | Path al programari ICCImage |
| `softGeoprocesGDAL` | Path al programari GDAL |
| `timeSleep` | Temps d'espera entre iteracions (segons) |
| `productL1Cgeneration` | "YES"/"NO" - genera mosaic L1C |
| `AllowedInnerzerosproductL2A` | "YES"/"NO" - neteja zeros interiors |
| `onlyLastBaselineForGranule` | "YES"/"NO" - només darrera baseline |
| `polySearch` | Polígon WKT de cerca |
| `limitsUTM` | Límits UTM per òrbita (xmin,xmax,ymax,ymin) |
| `perOrbitZoneUTM` | Zona UTM per òrbita |
| `granulesPerOrbit` | Llista de granules per òrbita |
| `checkTwoDatastrips` | "YES"/"NO" - detecció de dos datastrips |
| `machineDependentParameters` | Paràmetres per màquina (WorkingFolder, XLS, etc.) |

### machineDependentParameters

Cada màquina té la seva secció amb:
- `fileXLS`: Fitxer Excel de seguiment
- `workingFolder`: Directori de treball
- `quicklookDir`: Directori de sortida QuickLooks
- `pathL2AforIndex`: Path al batch de Sen2Cor amb DEM
- `pathL2AforOrthoimage`: Path al batch de Sen2Cor sense DEM

[←Index](#index)

---

## 5 Fitxer Excel de Seguiment (XLS)

El fitxer **Excel** (`.xlsx`) actua com a **màquina d'estats** i **cua de processament**. Conté una fulla "Sheet1" amb columnes:

| Columna | Camp | Significat |
|---|---|---|
| A | `Segment_Date` | Data del segment (YYYY-MM-DD) |
| B | `Segment_2A_2B_2C` | Satèl·lit (A, B, C) |
| C | `Segment_Orbit` | Òrbita relativa (R051, R008) |
| D | `Segment_Downloaded` | `*` = descarregat |
| E | `Segment_Processed_L1C` | `*` = L1C processat |
| F | `Segment_Generated_L2A` | `*` = L2A generat |
| G | `Segment_Processed_L2A` | `*` = L2A processat (10B + SCL) |
| H | `Segment_QuickLook_L2A` | `*` = QuickLook generat |
| I | `Segment_Generated_L2A_DEMCAT` | `*` = L2A amb DEM generat |
| J | `Segment_Processed_L2A_DEMCAT` | `*` = NDVI + SCL DEMCAT generat |

Les files acaben amb `END` a la columna A. El MainLoop itera sobre les files i processa la primera etapa pendent (primera columna sense `*`).

[←Index](#index)

---

## 6 Mòdul Principal: MainLoop_v7.4

[MainLoop_v7.4_new.py](../SOFT/MainLoop_v7.4.py3/MainLoop_v7.4_new.py)

És l'orquestrador principal. Executa un **bucle infinit** que:

1. Llegeix el fitxer **JSON** de configuració (paràmetre d'entrada)
2. Llegeix el fitxer **Excel** de seguiment
3. Itera sobre cada fila (segment)
4. Per cada segment, executa la **primera etapa pendent** (columna sense `*`)
5. Espera `timeSleep` segons si no hi ha res a fer

### Etapes processades seqüencialment

1. **`Segment_Downloaded != '*'`** → Crida `SearchProducts` + `S2_Download.S2_Segment_Granules_Download_Function`. Marca columna D amb `*`.
2. **`Segment_Processed_L1C != '*'`** → Descomprimeix ZIPs, genera màscares (MASK), opcionalment mosaic L1C 4B. Marca columna E.
3. **`Segment_Generated_L2A != '*'`** → Executa Sen2Cor sense DEM sobre cada grànul L1C, comprimeix resultats L2A. Marca columna F.
4. **`Segment_Processed_L2A != '*'`** → Genera mosaic L2A 10 bandes + SCL, elimina .SAFE. Marca columna G.
5. **`Segment_QuickLook_L2A != '*'`** → Genera QuickLook RGB. Marca columna H.
6. **`Segment_Generated_L2A_DEMCAT != '*'`** → Descomprimeix L1C, executa Sen2Cor amb DEM-CAT, comprimeix. Marca columna I.
7. **`Segment_Processed_L2A_DEMCAT != '*'`** → Genera mosaic L2A DEMCAT 10B, calcula NDVI, genera SCL DEMCAT, neteja. Marca columna J.

### Detecció de Two Datastrips

Quan `checkTwoDatastrips=YES`, el sistema detecta si un segment conté dos datastrips (per àrea de footprint inferior al llindar). En aquest cas, afegeix el segment a una llista d'espera i intenta la descàrrega més tard, permetent que el segon datastrip estigui disponible.

[←Index](#index)

---

## 7 Mòdul de Descàrrega (Download)

[S2_Segment_Granules_Download_Modules.py](../SOFT/MainLoop_v7.4.py3/S2_Segment_Granules_Download_Modules.py)

Gestiona la descàrrega de productes **L1C** des del **Copernicus DataSpace**.

### Funcions principals

- `S2_Segment_Granules_Download_Function(...)`: Funció principal de descàrrega
  - Fa query OData a l'API de DataSpace
  - Filtra per data, òrbita, polígon i satèl·lit
  - **Deduplica** productes: si dos productes tenen el mateix footprint, es queda amb la baseline més recent o la data més recent
  - Autenticació OAuth2 amb `client_id=cdse-public`
  - Descarrega amb `curl` i capçalera `Authorization: Bearer`
  - **Verifica checksum MD5** després de la descàrrega (versió 7.2+)
  - Gestiona **two datastrips**: calcula àrea de footprint per decidir si cal esperar

- `downloading_granule(...)`: Descarrega un grànul individual amb curl i verificació MD5

- `calcular_area_poligon(...)`: Calcula àrea d'un polígon en km² (WGS84)

- `same_footprint(...)`: Compara si dos footprints són equivalents (>99% d'intersecció)

- `S2_Segment_Number_of_Granules(...)`: Compta quants grànuls d'una òrbita estan disponibles

[←Index](#index)

---

## 8 Llibreria Client API Copernicus DataSpace (dataspace_lib)

[dataspace_lib.py](../SOFT/MainLoop_v7.4.py3/dataspace_lib.py)

És una llibreria client per a l'API **OData** del Copernicus DataSpace. Creada per **L. Pipia**.

### Classe `eoData`

- `__init__(url, url_token, userID, userPSW)`: Inicialitza el client. Detecta l'usuari del sistema per credencials automàtiques.
- `search(...)`: Cerca productes amb múltiples filtres (data, cobertura de núvols, productType, orbitDirection, etc.)
- `get_access_token()`: Obté token OAuth2
- `get_refresh_token()`: Refresca el token
- `download(im_dict, nmax_flux, out_dir)`: Descarrega múltiples productes en paral·lel amb **threads** (semàfor per controlar concurrència)

### Suporta múltiples sensors

Sentinel-1, Sentinel-2, Sentinel-3, Sentinel-5P, Landsat-7, Landsat-8.

[←Index](#index)

---

## 9 Mòdul de Generació de Màscares (Mask)

[S2_MaskGeneration_L1C_Module_new.py](../SOFT/MainLoop_v7.4.py3/S2_MaskGeneration_L1C_Module_new.py)

Genera màscares binàries per a cada grànul L1C utilitzant **GDAL** i **OpenCV**.

### Procés per grànul

1. **Converteix la banda B04** a TIFF 1-bit amb `gdal.Translate`
2. **Dilata** (1 iteració, kernel 3x3) per evitar pixels no-data interiors
3. **Erosiona** (51 iteracions) per eliminar vores
4. **Esborra les vores** (primeres/últimes 51 fileres i columnes)
5. **Converteix a GeoPackage** (polígon) via `gdal.Polygonize`
6. **Converteix a Shapefile**

### Funcions auxiliars

- `mask_to_geopackageraster(maskfile, gpkgfile)`: Converteix màscara raster a GeoPackage vectorial
- `mask_to_shaperaster(maskfile, shapefile)`: Converteix màscara raster a Shapefile

[←Index](#index)

---

## 10 Mòdul de Processament L1C 4 Bandes

[S2_Segment_Process_L1C_4B_Module_new.py](../SOFT/MainLoop_v7.4.py3/S2_Segment_Process_L1C_4B_Module_new.py)

Genera un **mosaic L1C de 4 bandes** (B02, B03, B04, B08) a 10m de resolució.

### Procés per cada grànul

1. Llegeix **gain** i **offset** del datastrip XML amb [S2_offset_gain.py](../SOFT/MainLoop_v7.4.py3/S2_offset_gain.py)
2. Aplica transformació: `TOAi = 10000*OFFi/GAIN + 10000*DNi/GAIN` via `gdal_calc.Calc`
3. Genera un TIFF per banda, després els combina en VRT
4. Converteix VRT a TIFF (COG)

### Mosaic final

1. Per cada grànul, aplica **màscara** (`cutline` via `gdal.Warp`)
2. Si el grànul és de zona UTM diferent, el **reprojecta** (cubic)
3. Combina tots els grànuls en un VRT
4. Converteix a COG (Cloud Optimized GeoTIFF)

[←Index](#index)

---

## 11 Correcció Atmosfèrica amb Sen2Cor

Directoris:
- [Sen2Cor-02.12.03-win64/](../SOFT/Sen2Cor-02.12.03-win64/) (actual)
- [Sen2Cor-02.11.00-win64/](../SOFT/Sen2Cor-02.11.00-win64/) (antic)

S'executa **Sen2Cor** (ESA) per convertir productes L1C a L2A (correcció atmosfèrica). Cada variant DEM té el seu propi script `.bat`:

| Script | DEM | Terrain Correction |
|---|---|---|
| `L2A_Process_NO-DEM.bat` | Sense DEM | No |
| `L2A_Process_DEM-CAT.bat` | DEM de Catalunya (5m) | Sí |
| `L2A_Process_DEM-SRTM.bat` | SRTM global | Sí |
| `L2A_Process_NO-DEM-NODEMTERRAINCORREC.bat` | Sense DEM | No |
| `L2A_Process_DEM-CAT-NODEMTERRAINCORREC.bat` | DEM-CAT | No |
| `L2A_Process_DEM-SRTM-NODEMTERRAINCORREC.bat` | SRTM | No |

Cada batch:
1. Configura `PATH` i variables d'entorn aïllades
2. Configura `SEN2COR_HOME` apuntant al directori de dades específic
3 Executa `L2A_Process.py` amb els arguments rebuts

### Parxe Baseline 05.11

[S2_Parxes_BL_05_11.py](../SOFT/MainLoop_v7.4.py3/S2_Parxes_BL_05_11.py)

Aquest parxe és **necessari** per a productes amb **Baseline 05.11** (a partir del 23 de juliol de 2024). Modifica les segones línies dels fitxers XML `MTD_TL.xml` i `MTD_DS.xml` per actualitzar els schemas XSD, ja que Sen2Cor 2.12 no els reconeix.

- `S2_Parxe1()`: Aplica el parxe a productes **L1C**
- `S2_Parxe2()`: Aplica el parxe a productes **L2A**

[←Index](#index)

---

## 12 Mòdul de Processament L2A 10 Bandes

[S2_Segment_Process_L2A_10B_Module_new.py](../SOFT/MainLoop_v7.4.py3/S2_Segment_Process_L2A_10B_Module_new.py)

Genera un **mosaic L2A de 10 bandes** (B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12) a 10m.

### Procés per banda de cada grànul

1. Llegeix **offset** i **gain** del metadata XML
2. Correggeix **zeros interiors** (pixels amb valor entre 0 i offset) amb `correct_jp2_data` de [aux_fun.py](../SOFT/MainLoop_v7.4.py3/aux_fun.py)
3. Aplica transformació: `A*gain + offset` via `gdal_calc.Calc`
4. Per bandes de 20m, remostreja a 10m amb `gdal.Warp` (cubic)
5. Combina totes les bandes en un VRT i converteix a TIFF

### Mosaic final

1. Per cada grànul:
   - Si `AllowedInnerzerosproductL2A=NO`: converteix zeros a 1 (per diferenciar de NoData), aplica màscara
   - Aplica **màscara** (cutline) i **reprojecta** si cal
2. Combina en VRT
3. Converteix a COG (`.btf` - BigTIFF)

[←Index](#index)

---

## 13 Mòdul de Classificació SCL

[S2_Segment_Process_L2A_SCL_Module_new.py](../SOFT/MainLoop_v7.4.py3/S2_Segment_Process_L2A_SCL_Module_new.py)

Extreu la banda **SCL** (Scene Classification Layer) dels productes L2A i genera un mosaic.

### Procés

1. Per cada grànul, extreu la banda SCL del directori `R20m`
2. Remostreja a 10m amb `gdal.Warp` (nearest neighbour)
3. Aplica màscara i reprojecta si cal
4. Combina en VRT
5. Converteix a COG

### Valors de la banda SCL

| Valor | Significat |
|---|---|
| 0 | No Data |
| 1 | Saturat/Defectuós |
| 2 | Ombres |
| 3 | Ombres de núvols |
| 4 | Vegetació |
| 5 | No vegetació |
| 6 | Aigua |
| 7 | No classificat |
| 8 | Núvol probabilitat mitjana |
| 9 | Núvol probabilitat alta |
| 10 | Cirrus prims |
| 11 | Neu |

[←Index](#index)

---

## 14 Mòdul de Càlcul NDVI

[S2_Segment_Process_NDVI_Module_new.py](../SOFT/MainLoop_v7.4.py3/S2_Segment_Process_NDVI_Module_new.py)

Calcula l'índex de vegetació **NDVI** a partir del mosaic L2A amb correcció DEMCAT.

### Fórmula

```
NDVI = (NIR - RED) / (NIR + RED)
```

On:
- **RED** = B04 (banda 3 del mosaic)
- **NIR** = B08 (banda 7 del mosaic)

### Implementació

- Utilitza `gdal_calc.Calc` amb la fórmula:
  `where((A==0)|(B==0)|(A+B==0), 0, minimum(200, maximum(1, round((200.0*A)/(A+B)))))`
- **Escalat**: el NDVI [-1, 1] s'escala a [0, 200] com a **Byte** (0=NoData)
- Si A=B=0 (NoData) → resultat 0
- Si el resultat és 0 → es força a 1 per diferenciar de NoData

### Variants

- `S2_Segment_Process_NDVI.py`: Versió estàndard
- `S2_Segment_Process_NDVI-2B.py`: Sortida de 2 bandes
- `S2_Segment_Process_NDVI_segu_030206.py`: Versió Seguiment

[←Index](#index)

---

## 15 Mòdul de Generació de QuickLook

[S2_QuickLook_Module.py](../SOFT/MainLoop_v7.4.py3/S2_QuickLook_Module.py)

Genera dues versions de QuickLook a partir del mosaic L2A de 10 bandes:

### Producte 1: RGB 8-bit JPEG COG

- Converteix a **8-bit** amb `ICCImageDataTypeChange.exe` (ICCImageOperations)
- Selecciona bandes RGB (B04, B03, B02 = bandes 3, 2, 1)
- Factor d'escala: 0.1
- Qualitat JPEG: 75
- Format: `S2_RGB_8b_<data>_<orbita>.tif`

### Producte 2: RGBNir 16-bit COG

- Utilitza [S2_utis.py](../SOFT/MainLoop_v7.4.py3/S2_utis.py) (`tiff2cog_QL_16b`)
- 4 bandes: R, G, B, NIR
- Compressió LZW
- Format: `S2_RGBI_16b_<data>_<orbita>.btf`

[Totes les funcions de S2_utis.py](../SOFT/MainLoop_v7.4.py3/S2_utis.py):
- `tiff2cog()`: Converteix qualsevol TIFF a COG
- `tiff2cog_QL_8b()`: Genera QuickLook RGB 8-bit
- `tiff2cog_QL_16b()`: Genera QuickLook RGBNir 16-bit

[←Index](#index)

---

## 16 Llibreries de Suport

### S2lib.py

[S2lib.py](../SOFT/MainLoop_v7.4.py3/S2lib.py)

Llibreria orientada a objectes per treballar amb imatges Sentinel-2. Creada per L. Pipia.

**Classe `S2image`**: Gestiona productes S2 en format `.SAFE` o `.ZIP`.

- `read_band(band_id, ...)`: Llegeix una banda real o virtual
- `read_radiance(band_id, ...)`: Converteix a radiància
- `read_reflectivity(band_id, ...)`: Converteix a reflectivitat
- `extract_real_bands(...)`: Extreu bandes reals via GDAL Sentinel-2 driver
- `extract_virtual_bands(...)`: Extreu bandes virtuals via **ESA SNAP GPT**
- `index_calc(vi_in, ...)`: Calcula índexs de vegetació (NDVI, GNDVI, EVI, EVI2, CHLRE, MCARI, NDMI, NDWI, SAVI)
- `read_sclimage(...)`: Llegeix i mascara la banda SCL

### aux_fun.py

[aux_fun.py](../SOFT/MainLoop_v7.4.py3/aux_fun.py)

Funcions auxiliars GDAL/NumPy:

- `correct_jp2_data(img_in_f, offset, ...)`: **Funció crítica**. Corregeix els **zeros interiors** (pixels amb valor 0 < pixel < offset) que apareixen en productes recents de Sentinel-2. Assigna `offset+1` a aquests pixels.
- `open_image()`, `read_image()`, `get_im_info()`: IO d'imatges
- `image_output_gen()`, `write_im_band()`: Creació d'imatges de sortida
- `get_epsg_transform()`, `utm2utm_transf()`, etc.: Transformacions de coordenades
- `bbox2wkt()`: Converteix bounding box a WKT

### S2_offset_gain.py

[S2_offset_gain.py](../SOFT/MainLoop_v7.4.py3/S2_offset_gain.py)

Llegeix els valors de **gain** i **offset** dels fitxers `MTD_DS.xml` dels productes S2:

- `search_offset(product_type, rootPath, iband)`: Cerca l'offset per una banda específica (L1C: `RADIO_ADD_OFFSET`, L2A: `BOA_ADD_OFFSET`)
- `search_gain(product_type, rootPath)`: Cerca el quantification value (L1C: `QUANTIFICATION_VALUE`, L2A: `BOA_QUANTIFICATION_VALUE`)

### S2_safe_mosaic_vrt_v2.py

[S2_safe_mosaic_vrt_v2.py](../SOFT/MainLoop_v7.4.py3/S2_safe_mosaic_vrt_v2.py)

Classe `s2_mosaic` per crear mosaics VRT a partir de múltiples productes S2:

- Gestiona múltiples FUS (tiles de diferentes zones UTM)
- Aplica buffer d'erosió per evitar artefactes a les vores
- Genera màscara de footprint
- Opció de reprojectar entre zones UTM

[←Index](#index)

---

## 17 Eines Auxiliars Independents

### tiff2cog.py

[tiff2cog.py](../SOFT/tiff2cog.py)

Script autònom per convertir qualsevol TIFF a **Cloud Optimized GeoTIFF (COG)** fent servir GDAL:

```
Ús: introdueix path d'entrada i path de sortida per terminal
```

### Genera_ZIPs_py3.py

[Genera_ZIPs_py3.py](../SOFT/Genera_ZIPs_py3.py)

Descomprimeix un ZIP de cintoteca `OT_SENTINEL2` i reestructura els productes L1C en el format estàndard de Copernicus Open Access Hub (cada `.SAFE` → `.zip`).

### Proces_Imatges_Velles_S2.py

[Proces_Imatges_Velles_S2.py](../SOFT/Proces_Imatges_Velles_S2.py)

Script per processar **imatges històriques** (L2A ja existents) i generar QuickLooks RGB + SCL:

1. Demana data i directori de treball
2. Cerca productes L2A al DataSpace
3. Descarrega i descomprimeix
4. Genera mosaic RGB (banda TCI) + SCL via GDAL
5. Comprimeix i mou els resultats al directori arrel

Utilitza `eoData` de [dataspace_lib.py](../SOFT/MainLoop_v7.4.py3/dataspace_lib.py) per a la descàrrega.

[←Index](#index)

---

## 18 Scripts de Pass-Finder

Aquests scripts independents determinen quines **òrbites** i **granules** cobreixen una àrea d'interès:

| Script | Cobertura | Satèl·lits |
|---|---|---|
| `Pas_S2_CAT_py3.py` | Catalunya | S2A + S2B |
| `Pas_S2_AND_py3.py` | Andorra | S2A + S2B |
| `Pas_S2_CAT_S2A_S2B_S2C_py3.py` | Catalunya | S2A + S2B + S2C |
| `Pas_S2_AND_S2A_S2B_S2C_py3.py` | Andorra | S2A + S2B + S2C |
| `Pas_S2_CAT_py3_oldversion_190925.py` | Catalunya (antic) | S2A només |

A partir del **21 de gener de 2025**, el Sentinel-2C substitueix el S2A. Per això es van crear les variants amb suport S2C.

[←Index](#index)

---

## 19 Entorn i Dependències

[Environment S2-PROCESS/S2-PROCESS_Environment.txt](../SOFT/Environment%20S2-PROCESS/S2-PROCESS_Environment.txt)

### Entorn Conda

```
conda create --name S2-PROCESS python=3.8.5
activate S2-PROCESS
pip install openpyxl
pip install opencv-python
pip install requests
pip install pyproj
pip install GDAL-3.2.2-cp38-cp38-win_amd64.whl
```

### Dependències crítiques

| Llibreria | Ús |
|---|---|
| **GDAL 3.2.2** | Totes les operacions geoespacials (warp, translate, VRT, etc.) |
| **OpenCV** | Erosió/dilatació de màscares |
| **NumPy** | Càlculs matricials |
| **OpenPyXL** | Lectura/escriptura Excel |
| **Requests** | Autenticació OAuth2 |
| **PyProj** | Càlculs d'àrea de polígons |
| **Shapely** | Intersecció de polígons |
| **rasterio** | Lectura escriptura de ràsters per blocs |
| **gdal_calc** | `gdal_calc.Calc` per operacions aritmètiques |

### Programari extern

- **Sen2Cor** (ESA): Correcció atmosfèrica L1C→L2A
- **ICCImage** (ICGC): Suite de processament d'imatge propietària
- **curl**: Descàrrega de fitxers via HTTP
- **ESA SNAP** (opcional, per S2lib): Per bandes virtuals via GPT

[←Index](#index)

---

## 20 Evolució del Programari (Versions)

| Versió | Data | Canvis Principals |
|---|---|---|
| **v4.0** | - | Procés L2A grànul a grànul (evita problema dos datatake) |
| **v4.1** | - | Procés L1C 4B i MASK grànul a grànul |
| **v4.2** | - | Dilation abans d'erosió (pixels no-data), ZIPs amb AUX_DATA buit, Sen2Cor 2.8 |
| **v4.3** | - | Descàrrega automàtica de productes OFFLINE |
| **v4.4** | - | Sen2Cor 2.9, correcció UNZIP |
| **v4.5** | - | **Configuració JSON** (externalització paràmetres) |
| **v5.0** | - | Adaptació Baseline 4.00, Sen2Cor 2.10, gain=10000 offset=-1000 |
| **v5.1** | - | Lectura gain/offset de metadades |
| **v5.2** | - | Generació COG TIF (GDAL) |
| **v6.0** | Mar 2023 | **Nova API DataSpace Copernicus** (OData) |
| **v6.1** | - | Mecanisme d'espera per datastrips pendents |
| **v6.2** | - | Eliminació d'email, JSON com a paràmetre |
| **v6.3** | - | Eliminació d'arxius dins ZIP |
| **v7.0** | - | **Generació NDVI** amb correcció topogràfica DEM-CAT |
| **v7.1** | - | Opció de descarregar només la darrera BASELINE |
| **v7.2** | - | Eliminació de duplicats (mateix footprint), **verificació checksum MD5**, L2A 10B amb correcció topogràfica |
| **v7.3** | - | Generació `.RF` L1C 4 bandes (segona etapa) |
| **v7.4** | Oct 2024 | **COG amb gdal_translate**, suport Sentinel-2C |
| | Mar 2025 | Suport SCL en via DEMCAT |
| | Jul 2024 | **Parxe Baseline 05.11** |

### Branques actuals (v7.4)

| Variant | Propòsit |
|---|---|
| `MainLoop_v7.4_new.py` | Principal actiu |
| `MainLoop_v7.4-PARXE.py` | Campanya PARXE |
| `MainLoop_v7.4_segu200125.py` | Seguiment 2025-01-20 |
| `MainLoop_v7.4_GEOAICUBE.py` | Campanya GEOAICUBE |
| `MainLoop_v7.4_add2C.py` | Suport Sentinel-2C |
| `MainLoop_v7.4.py` | Versió base |

[←Index](#index)

---

## 3 Next steps

- [Documentació del sistema de backup (PrepararCopiaSeguretat)](../SOFT/PrepararCopiaSeguretat_S2_py3_v2.py)
- [Directori d'orquestradors v7.4](../SOFT/MainLoop_v7.4.py3/)
- [Projecte QGIS de referència](../SOFT/S2_World_Tile.qgz)
