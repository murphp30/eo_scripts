#!/usr/bin/env python

import geojson

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
