#!/usr/bin/env python

from pathlib import Path

import geojson
import geopandas as gpd

import matplotlib.pyplot as plt
import pandas as pd

from shapely.geometry import MultiPolygon, Polygon

from eo_utils import geojson_to_shapely


def find_ind_for_park(
        park_name: str,
        nparks: dict
        ) -> int:
    for i, feature in enumerate(nparks['features']):
        # TYPE seems to be 300 for national parks
        # 100 for forest reserves
        # 200 for game reserves
        if feature["properties"]["TYPE"] != 100:
            if feature["properties"]["NAME"] == park_name.upper():
                return i
    raise ValueError(f"Park {park_name.upper()} not found")
    return


def split_inside_outside(
        gdf: gpd.GeoDataFrame,
        park_poly: Polygon | MultiPolygon
        ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:

    gdf['intersects_park'] = gdf['geometry'].map(
        lambda x: x.intersects(park_poly))
    gdf_inside = gdf.where(gdf['intersects_park']).dropna()
    gdf_outside = gdf.where(gdf['intersects_park'] != True).dropna()
    return (gdf_inside, gdf_outside)


def plot_region(
        gdf: gpd.GeoDataFrame,
        nparks_geojson: str,
        park_name: str
        ) -> None:

    with open(nparks_geojson) as gj:
        nparks = geojson.load(gj)
    park_ind = find_ind_for_park(park_name, nparks)
    park_poly = geojson_to_shapely(
        nparks_geojson, park_ind)
    gdf_inside, gdf_outside = split_inside_outside(gdf, park_poly)
    fig, ax = plt.subplots(1, 1, figsize=(9, 7))
    for gdf_sub, sub_label in zip(
            [gdf_inside, gdf_outside],
            ["Inside", "Outside"]
            ):
        SSM_mean = gdf_sub.mean(numeric_only=True)
        df_datetimes = pd.to_datetime(gdf_sub.columns[1:-1], format="D%Y%m%d")
        ax.plot(
            df_datetimes,
            SSM_mean,
            '-o',
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
            )
        ax.set_xlabel("Date")
        ax.set_ylabel("Soil Moisture Level (percent)")
    ax.legend()
    plt.savefig(f"/data/tapas/pearse/malawi/SSM_{park_name}.png")
    return


def load_ssm(
        shp_file: str | Path,
        polygon_geojson: str | Path
        ) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_file)
    polys = gpd.read_file(polygon_geojson)
    gdf = gdf.drop(columns="geometry")
    gdf = pd.concat([polys, gdf], axis=1)
    return gdf


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
        plot_region(gdf, nparks_geojson, park_name)
    plt.show()
