"""Read offset and gain from SAFE product XML metadata."""

from __future__ import annotations

import os
from pathlib import Path
from xml.etree import ElementTree as ET


def find_datastrip_xml(safe_dir: str | Path) -> str | None:
    safe_dir = Path(safe_dir)
    datastrip = safe_dir / "DATASTRIP"
    if not datastrip.exists():
        return None
    subdirs = list(datastrip.iterdir())
    if not subdirs:
        return None
    return str(datastrip / subdirs[0].name / "MTD_DS.xml")


def search_offset(product_type: str, root_path: str | Path, band_index: int) -> float:
    band_map = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "11", 10: "12"}
    tag = "RADIO_ADD_OFFSET" if product_type == "L1C" else "BOA_ADD_OFFSET"
    text2search = f"<{tag} band_id="
    band_id = band_map.get(band_index, str(band_index))

    xml_path = find_datastrip_xml(root_path)
    if not xml_path:
        return -9999.0
    with open(xml_path) as f:
        for line in f:
            if text2search in line and f'_id="{band_id}"' in line:
                return float(line.split(">")[1].split("<")[0])
    return -9999.0


def search_gain(product_type: str, root_path: str | Path) -> float:
    tag = "QUANTIFICATION_VALUE" if product_type == "L1C" else "BOA_QUANTIFICATION_VALUE"

    xml_path = find_datastrip_xml(root_path)
    if not xml_path:
        return -9999.0
    with open(xml_path) as f:
        for line in f:
            if tag in line:
                return float(line.split(">")[1].split("<")[0])
    return -9999.0
