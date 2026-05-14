"""Binary mask generation from L1C B04 band using GDAL + OpenCV."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
from osgeo import gdal, ogr, osr, gdalconst


def mask_to_geopackage(mask_tif: str, gpkg_file: str) -> None:
    src_ds = gdal.Open(mask_tif)
    src_band = src_ds.GetRasterBand(1)
    proj_wkt = src_ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(proj_wkt) if proj_wkt else None

    drv = ogr.GetDriverByName("GPKG")
    drv.DeleteDataSource(gpkg_file)
    out_ds = drv.CreateDataSource(gpkg_file)
    out_lyr = out_ds.CreateLayer("polygons", srs=srs, geom_type=ogr.wkbPolygon)

    field_defn = ogr.FieldDefn("value", ogr.OFTInteger)
    out_lyr.CreateField(field_defn)
    idx = out_lyr.GetLayerDefn().GetFieldIndex("value")

    mask_band = src_band.GetMaskBand()
    gdal.Polygonize(src_band, mask_band, out_lyr, idx)
    out_ds = None
    src_ds = None


def generate_mask(
    safe_dir: str | Path,
    granule_name: str,
    granule_id: str,
    mask_dir: str | Path,
    erosion_iter: int = 51,
) -> tuple[str, str, str]:
    mask_dir = Path(mask_dir)
    mask_dir.mkdir(parents=True, exist_ok=True)

    file_in = f"{safe_dir}/GRANULE/{granule_name}/IMG_DATA/{granule_id[:22]}_B04.jp2"
    file_1b = str(mask_dir / f"{granule_id}_B04_1b.tif")

    gdal.Translate(
        file_1b, file_in,
        format="GTiff", outputType=gdalconst.GDT_Byte, noData=0,
        creationOptions=["NBITS=1", "TILED=YES", "BLOCKXSIZE=1024", "BLOCKYSIZE=1024", "INTERLEAVE=BAND", "BIGTIFF=NO", "TFW=YES"],
    )

    img = cv2.imread(file_1b, 0)
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(img, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=erosion_iter)
    eroded[:erosion_iter, :] = 0
    eroded[-erosion_iter:, :] = 0
    eroded[:, :erosion_iter] = 0
    eroded[:, -erosion_iter:] = 0

    file_eroded = str(mask_dir / f"{granule_id}_B04_1b_eroded.tif")
    cv2.imwrite(file_eroded, eroded)

    file_mask = str(mask_dir / f"{granule_id}_mask.tif")
    ds = gdal.Open(file_1b)
    epsg = osr.SpatialReference(wkt=ds.GetProjection()).GetAttrValue("AUTHORITY", 1)
    ds = None

    gdal.Translate(
        file_mask, file_eroded,
        format="GTiff", outputType=gdalconst.GDT_Byte,
        outputSRS=f"EPSG:{epsg}", noData=0,
        creationOptions=["NBITS=1", "TILED=YES", "BLOCKXSIZE=1024", "BLOCKYSIZE=1024", "INTERLEAVE=BAND", "BIGTIFF=NO"],
    )

    file_gpkg = str(mask_dir / f"{granule_id}_mask.gpkg")
    mask_to_geopackage(file_mask, file_gpkg)

    file_shp = str(mask_dir / f"{granule_id}_mask.shp")
    mask_to_geopackage(file_mask, file_shp)

    for f in [file_1b, file_eroded]:
        Path(f).unlink(missing_ok=True)

    return file_mask, file_gpkg, file_shp
