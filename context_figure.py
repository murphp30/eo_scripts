#!/usr/bin/env python

import contextily as cx
import geojson
# import geopandas as gpd
import matplotlib.pyplot as plt
# import numpy as np
import rasterio as rio
import rioxarray as rxr

from rasterio.enums import ColorInterp
from rasterio.plot import show
from shapely.geometry import MultiPolygon, Polygon


def geojson_to_shapely(gj_file):
    with open(gj_file) as gj:
        poly_coords = geojson.load(gj)
    # try account for multipolygon
    # really only works for the specific files here :/
    if len(poly_coords['features'][0]['geometry']['coordinates']) > 1:
        multipoly = []
        for coords in poly_coords['features'][0]['geometry']['coordinates']:
            poly = Polygon(coords[0])
            multipoly.append(poly)
        multipoly = MultiPolygon(multipoly)
        return multipoly
    else:
        poly = Polygon(
            poly_coords['features'][0]['geometry']['coordinates'][0])
        return poly


aoi_dir = "/data/tapas/pearse/malawi/sentinel1/aoi"
malawi = \
    aoi_dir + "/geoBoundaries-MWI-ADM0.geojson"
sentinel1_footprint_640 = \
    aoi_dir + "/frame_640_approx_footprint.geojson"
sentinel1_footprint_152 = \
    aoi_dir + "/path_152_footprint.geojson"
southern_aoi = aoi_dir + "/southern_malawi_aoi.geojson"
kasungu_aoi = aoi_dir + "/kasungu_small.geojson"


malawi_poly = geojson_to_shapely(malawi)
footprint_frame640_poly = geojson_to_shapely(sentinel1_footprint_640)
footprint_path152_poly = geojson_to_shapely(sentinel1_footprint_152)
footprint_poly = MultiPolygon([footprint_frame640_poly, footprint_path152_poly])
southern_poly = geojson_to_shapely(southern_aoi)
kasungu_poly = geojson_to_shapely(kasungu_aoi)
rois = MultiPolygon([southern_poly, kasungu_poly])
context_tif = "/data/tapas/pearse/malawi/MODIS/MODIS_context.tif"
with rio.open(context_tif, "r+") as modis_rgb:
    modis_rgb.colorinterp = [
        ColorInterp.red,
        ColorInterp.green,
        ColorInterp.blue]
    modis_masked, modis_transform = rio.mask.mask(
        modis_rgb,
        [malawi_poly],
        nodata=-999)
    modis_crs = modis_rgb.crs
# hacky way to get a white background
modis_masked[modis_masked == -999] = 255

west, south, east, north = malawi_poly.bounds
provider = cx.providers.CartoDB.Voyager
malawi_img, malawi_ext = cx.bounds2img(
    west,
    south,
    east,
    north,
    ll=True,
    source=provider,
    zoom=8
)
# print(cx.tile._calculate_zoom(west, south, east, north))
# print(malawi_ext)
warped_img, warped_ext = cx.warp_tiles(malawi_img, malawi_ext, "EPSG:4326")
# f, ax = plt.subplots(1, figsize=(9, 9))
# ax.imshow(malawi_img, extent=malawi_ext)

f, ax = plt.subplots(1, figsize=(4, 7))

# im = ax.imshow(warped_img, extent=warped_ext)
# cx.add_basemap(
#             ax,
#             crs=modis_crs.to_string(),
#             # alpha=0.1,
#             source=cx.providers.CartoDB.Voyager)
show(modis_masked, ax=ax, transform=modis_transform)
for i, footprint in enumerate(footprint_poly):
    if i == 1:
        label = "S1A footprint"
    else:
        label = None
    ax.plot(
        *footprint.exterior.xy,
        color='cyan',
        linewidth=2,
        label=label)
for i, roi in enumerate(rois):
    if i == 1:
        label = "Region of interest"
    else:
        label = None
    ax.plot(
        *roi.exterior.xy,
        color='orange',
        linewidth=2,
        label=label)
# cx.add_basemap(

#             ax,
#             # crs=
#             alpha=0.1,
#             source=provider)
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.xlim(32.5)
plt.legend()
plt.tight_layout()
# plt.savefig("/data/tapas/pearse/context_figure.pdf")
plt.show()
