#!/usr/bin/env python
"""
Copy paste the coordinates of a polygon defined in the ASF map
https://search.asf.alaska.edu/
And convert it to a geojson
"""

from geojson import Feature, FeatureCollection, dump
from shapely.geometry import Polygon

print("HI")
poly_coords_str = "31.519726 -13.459048,31.909353 -11.840684,34.172108 -12.359115,33.798531 -13.984308,31.519726 -13.459048"
# poly_coords_str = "33.0618 -13.2815,33.6052 -13.2815,33.6052 -12.8528,33.0618 -12.8528,33.0618 -13.2815" # kasungu
poly_coords = [
    [
        float(lat), float(lon)
    ] for lat, lon in [
        coord.split(' ') for coord in poly_coords_str.split(',')
    ]
]

poly = Polygon(poly_coords)
features = []
features.append(Feature(geometry=poly))
feature_collection = FeatureCollection(features)
with open("/data/tapas/pearse/malawi/sentinel1/aoi/pathe_152_footprint.geojson", "w") as gj:
    dump(feature_collection, gj)
print("BYE")
