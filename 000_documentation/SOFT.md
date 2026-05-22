# Programari S2-PROCESS: Històric i Arquitectura Original (SOFT)

> [!NOTE]
> Aquest document conserva l'essència arquitectònica i de negoci del projecte original S2-PROCESS (legacy). Per a les instruccions del pipeline refactoritzat actual, referiu-vos a `SOFT_new.md`.

## 1. Visió General
El **S2-PROCESS** va ser concebut com un sistema de processament automàtic d'imatges **Sentinel-2** per cobrir **Catalunya**. Creat per V. Pala i P. Ríos (ICGC), la seva missió original era orquestrar: `Descàrrega → Descomprimir → Mosaic L1C → Sen2Cor → Mosaic L2A 10B → NDVI → SCL → Màscara → QuickLook`.

## 2. Arquitectura del Pipeline
El flux original s'executava en 6 etapes estrictament seqüencials per a cada "segment" (combinació de data i òrbita):

1. **DOWNLOAD**: Descàrrega de grànuls L1C via Copernicus DataSpace.
2. **MASK + L1C**: Generació de màscares i mosaic L1C a 4 bandes (B02, B03, B04, B08).
3. **SEN2COR**: Correcció atmosfèrica (L1C a L2A) grànul a grànul.
4. **L2A 10B**: Mosaic L2A de 10 bandes (B02-B12) i classificació SCL.
5. **NDVI**: Càlcul d'índex de vegetació.
6. **QUICKLOOK**: Generació de visuals RGB i 16b.

## 3. Fitxer Excel com a Màquina d'Estats
El nucli del control de flux es basava en un fitxer **Excel (.xlsx)**. Aquest fitxer marcava amb un asterisc (`*`) les etapes completades de cada segment. El bucle infinit de l'orquestrador (`MainLoop_v7.4.py`) llegia l'Excel, executava la primera columna buida de cada fila i tornava a escriure-hi un asterisc un cop acabada la tasca.

## 4. Evolució al Nou Model (SOFT_new)
Les limitacions d'espai al disc i complexitat de dependències van portar a crear `SOFT_new`, que substitueix la màquina d'estats d'Excel per un flux pur en memòria (JSON config + Netedja proactiva de disc), i elimina les dependències pesades mantenint Sen2Cor com a procés desacoblat però natiu en Windows.
