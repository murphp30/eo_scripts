#!/usr/bin/env python

from datetime import datetime
from pathlib import Path

import geojson
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scipy.stats import linregress

from eo_utils import geojson_to_shapely, load_ssm
from SSM_region_compare import split_inside_outside, find_ind_for_park


def date_to_ind(date_array:np.array, date:datetime) -> int:
    date_ind = np.argmin(np.abs(date_array-date))
    return date_ind

def drying_rate(
        mean_ssm: np.array,
        date_array: np.array,
        dry_start: datetime,
        dry_end: datetime
        ) -> tuple[float, float]:
    """inputs: mean soil moisture
               array of date values
            start of drying
            end of drying
    perform linear fit
    return parameters
    """
    dry_start_ind = date_to_ind(date_array, dry_start)
    dry_end_ind = date_to_ind(date_array, dry_end)
    day_array = np.arange(dry_end_ind - dry_start_ind)
    result = linregress(day_array,mean_ssm[dry_start_ind:dry_end_ind])

    plt.plot(day_array, mean_ssm[dry_start_ind:dry_end_ind], 'o')
    plt.plot(day_array, (result.slope*day_array) + result.intercept)
    return result.slope, result.intercept


if __name__ == "__main__":
    root_path = Path("/data/tapas/pearse/malawi/SSM")
    nparks_geojson = root_path.parent/"sentinel1/aoi/protected_areas.json"
    for ssm_results, park_name in zip(
        [
            "malawi_InSAR_SSM_1km_southern_20230101_20240531",
            "kasungu_1km_20230101_20240531"
        ],
        [
            "LIWONDE",
            "KASUNGU"
        ]
    ):
        ssm_path = root_path/ssm_results
        shp_file = list(ssm_path.glob("*shp"))[0]
        polygon_geojson = ssm_path/ssm_results/"INSAR4SM_processing/SM/SM_polygons.geojson"
        gdf = load_ssm(
            shp_file,
            polygon_geojson
            )
    with open(nparks_geojson) as gj:
        nparks = geojson.load(gj)
    park_ind = find_ind_for_park(park_name, nparks)
    park_poly = geojson_to_shapely(
        nparks_geojson, park_ind)
    gdf_inside, gdf_outside = split_inside_outside(gdf, park_poly)
    mean_ssm = gdf_inside.mean(numeric_only=True)
    df_datetimes = pd.to_datetime(gdf.columns[1:-1], format="D%Y%m%d")

    day_start = datetime(2024, 4, 15)
    day_end = datetime(2024, 5, 31)
    
    dry_start_ind = date_to_ind(df_datetimes, day_start)
    dry_end_ind =  date_to_ind(df_datetimes, day_end)
    
    day_array = np.arange(dry_end_ind - dry_start_ind)
    slope, intercept = drying_rate(mean_ssm.values, df_datetimes, day_start, day_end)
    print(slope, intercept)
    # plt.plot(df_datetimes, mean_ssm.values, 'o')
    # plt.plot(df_datetimes[day_array], (slope*day_array)+intercept)
    plt.show()