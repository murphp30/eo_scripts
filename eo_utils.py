#!/usr/bin/env python

from pathlib import Path
from typing import Union

import geopandas as gpd
import geojson
import pandas as pd

from rasterstats import zonal_stats
from shapely.geometry import MultiPolygon, Polygon


def geojson_to_shapely(gj_file, i=0):
    with open(gj_file) as gj:
        poly_coords = geojson.load(gj)
    # try account for multipolygon
    # really only works for the specific files here :/
    if poly_coords['features'][i]['geometry']['type'] == 'MultiPolygon':
        multipoly = []
        for coords in poly_coords['features'][i]['geometry']['coordinates']:
            poly = Polygon(coords[0])
            multipoly.append(poly)
        multipoly = MultiPolygon(multipoly)
        return multipoly
    else:
        poly = Polygon(
            poly_coords['features'][i]['geometry']['coordinates'][0])
        return poly


def load_ssm(
        shp_file: Union[str, Path],
        polygon_geojson: Union[str, Path]
        ) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_file)
    polys = gpd.read_file(polygon_geojson)
    gdf = gdf.drop(columns="geometry")
    gdf = pd.concat([polys, gdf], axis=1)
    return gdf


def get_zonal_means(
        raster_file: Union[str, Path],
        bbox: Union[Polygon, MultiPolygon],
        npark: Union[Polygon, MultiPolygon],
        ):

    inside_park = bbox & npark
    outside_park = bbox ^ inside_park
    zone_means = {"inside": 0, "outside": 0}
    for zone_poly, zone_name in zip(
            [inside_park, outside_park],
            zone_means.keys()):
        stats = zonal_stats(zone_poly, raster_file)
        mean = stats[0]['mean']
        zone_means[zone_name] = mean

    return zone_means
