#!/usr/bin/env python
import numpy as np
from owslib.wcs import WebCoverageService

from eo_utils import geojson_to_shapely


def get_soil_layers(poly, out_dir, res=250):
    lon1, lat1, lon2, lat2 = poly.bounds
    subsets = [('lat', lat1, lat2), ('long', lon1, lon2)]
    for soil_type in ['sand', 'clay']:
        soil_wcs = WebCoverageService(f"https://maps.isric.org/mapserv?map=/map/{soil_type}.map")
        soil = soil_wcs.contents[f'{soil_type}_0-5cm_mean']
        response = soil_wcs.getCoverage(
            identifier=[soil.id],
            SUBSETTINGCRS="http://www.opengis.net/def/crs/EPSG/0/4326",
            OUTPUTCRS="http://www.opengis.net/def/crs/EPSG/0/4326",
            subsets=subsets,
            resx=res,
            resy=res,
            format=soil.supportedFormats[0])
        with open(out_dir+f'{soil_type}_0-5cm_mean_{res}.tif', 'wb') as file:
            file.write(response.read())


if __name__ == "__main__":
    poly = geojson_to_shapely("/data/tapas/pearse/vietnam/aoi/F56_bbox.geojson")
    out_dir = "/data/tapas/pearse/vietnam/SSM/soilgrids/"
    get_soil_layers(poly, out_dir, 250)
    print("BYE!")
