"""NDVI calculation from L2A 10-band mosaic."""

from __future__ import annotations

from pathlib import Path

from osgeo_utils.gdal_calc import Calc


RED_BAND = 3
NIR_BAND = 7


def calculate_ndvi(
    input_mosaic: str | Path,
    output_file: str | Path,
) -> str:
    output_file = str(output_file)
    Calc(
        A=str(input_mosaic),
        A_band=NIR_BAND,
        B=str(input_mosaic),
        B_band=RED_BAND,
        outfile=output_file,
        calc="where((A==0)|(B==0)|(A+B==0), 0, minimum(200, maximum(1, round((200.0*A)/(A+B)))))",
        type="Byte",
        NoDataValue=0,
    )
    return output_file
