#!/usr/bin/env python

from pathlib import Path

import geopandas as gpd
import geojson
import pandas as pd

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
        shp_file: str | Path,
        polygon_geojson: str | Path
        ) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_file)
    polys = gpd.read_file(polygon_geojson)
    gdf = gdf.drop(columns="geometry")
    gdf = pd.concat([polys, gdf], axis=1)
    return gdf
