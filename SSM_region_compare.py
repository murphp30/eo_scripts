#!/usr/bin/env python

import csv

from datetime import datetime
from pathlib import Path

import geojson
import geopandas as gpd

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cycler import cycler
from matplotlib.lines import Line2D
from scipy.signal import correlate, correlation_lags
from shapely.geometry import MultiPolygon, Polygon

from eo_utils import geojson_to_shapely, load_ssm

cbtab_cycler = cycler(
    color=[
        '#006BA4',
        '#FF800E',
        '#ABABAB',
        '#595959',
        '#5F9ED1',
        '#C85200',
        '#898989',
        '#A2C8EC',
        '#FFBC79',
        '#CFCFCF'])
matplotlib.rcParams['axes.prop_cycle'] = cbtab_cycler


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


def get_gdf_split(
        gdf: gpd.GeoDataFrame,
        nparks_geojson: str,
        park_name: str
        ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    with open(nparks_geojson) as gj:
        nparks = geojson.load(gj)
    park_ind = find_ind_for_park(park_name, nparks)
    park_poly = geojson_to_shapely(
        nparks_geojson, park_ind)
    gdf_inside, gdf_outside = split_inside_outside(gdf, park_poly)
    return gdf_inside, gdf_outside


def plot_region_ssm(
        gdf: gpd.GeoDataFrame,
        nparks_geojson: str,
        park_name: str
        ) -> None:

    gdf_inside, gdf_outside = get_gdf_split(gdf, nparks_geojson, park_name)
    fig, ax = plt.subplots(
        2, 1, figsize=(9, 7), sharex=True, layout="constrained")
    fig_cor, ax_cor = plt.subplots(
        1, 1, figsize=(9, 7)
    )
    grad_cycler = cycler(
        color=[
            '#006BA4',
            '#006BA4',
            '#006BA4',
            '#FF800E',
            '#FF800E',
            '#FF800E',
        ])
    ax[1].set_prop_cycle(grad_cycler)
    for gdf_sub, sub_label in zip(
            [gdf_inside, gdf_outside],
            ["Inside", "Outside"]
            ):
        SSM_mean = gdf_sub.mean(numeric_only=True)
        df_datetimes = pd.to_datetime(gdf_sub.columns[1:-1], format="D%Y%m%d")
        ax[0].plot(
            df_datetimes,
            SSM_mean,
            '-o',
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
            )

        ax[0].set_ylabel("Soil Moisture Level (percent)",fontdict={"size": 14})
        sentinel1_revist = (df_datetimes - df_datetimes[0]).days
        moisture_rate = np.gradient(SSM_mean, sentinel1_revist)
        drying_inds = moisture_rate <= 0
        ax[1].plot(
            df_datetimes[~drying_inds],
            moisture_rate[~drying_inds],
            '^',
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
        )

        ax[1].plot(
            df_datetimes[drying_inds],
            moisture_rate[drying_inds],
            'v',
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
        )
        ax[1].plot(
            df_datetimes,
            moisture_rate,
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
        )
        ax[1].set_xlabel("Date",fontdict={"size": 14})
        ax[1].set_ylabel("Soil moisture rate (pecent per day)",fontdict={"size": 14})

    SSM_mean_outside = gdf_outside.mean(numeric_only=True)
    SSM_mean_inside = gdf_inside.mean(numeric_only=True)
    ssm_cor = correlate(
        SSM_mean_outside/np.max(SSM_mean_outside),
        SSM_mean_inside/np.max(SSM_mean_inside)
        )
    cor_lags = correlation_lags(len(SSM_mean_outside), len(SSM_mean_inside))
    ax_cor.plot(
        cor_lags,
        ssm_cor
    )
    print(f"Max SSM correlation {park_name}: {np.max(ssm_cor)}")
    ax_cor.set_xlabel("lag (days)")
    ax_cor.set_ylabel("correlation coefficient")
    ax[0].legend()
    ax1_legend_elements = [
        Line2D([0], [0], marker='^', label='Increasing Moisture'),
        Line2D([0], [0], marker='v', label='Decreasing Moisture')
    ]
    ax[1].legend(handles=ax1_legend_elements)
    fig.savefig(f"/data/tapas/pearse/malawi/SSM_{park_name}.eps")
    fig_cor.savefig(f"/data/tapas/pearse/malawi/SSM_correlation_{park_name}.eps")
    return


def plot_ssm_ndvi(
        gdf: gpd.GeoDataFrame,
        nparks_geojson: str,
        park_name: str
        ) -> None:
    gdf_inside, gdf_outside = get_gdf_split(gdf, nparks_geojson, park_name)

    fig, ax = plt.subplots(
        2, 1, figsize=(9, 7), sharex=True)
    fig_cor, ax_cor = plt.subplots(
        1, 1, figsize=(9, 7)
    )
    for gdf_sub, sub_label in zip(
            [gdf_inside, gdf_outside],
            ["Inside", "Outside"]
            ):
        SSM_mean = gdf_sub.mean(numeric_only=True)
        df_datetimes = pd.to_datetime(gdf_sub.columns[1:-1], format="D%Y%m%d")
        ax[0].plot(
            df_datetimes,
            SSM_mean,
            '-o',
            label="SSM " + sub_label
            + " "
            + park_name.capitalize()
            + " Park"
            )

        stat_file = f"/data/tapas/pearse/ee_downloads/{sub_label.lower()}_{park_name.lower()}_mean_ndvi.csv"
        with open(stat_file) as stats:
            csv_read = csv.reader(stats)
            date_row = next(csv_read)
            data_row = next(csv_read)
        dt_arr = np.array(
            [datetime.strptime(dr, "%Y_%m_%d_NDVI") for dr in date_row[:-1]])
        ndvi_mean = np.array(data_row[:-1], dtype=float)
        ax[1].plot(
            dt_arr,
            ndvi_mean,
            "--o",
            label="NDVI " + sub_label
            + " "
            + park_name.capitalize()
            + " Park")
        day0 = datetime(2023, 1, 1)
        total_days = (datetime(2024, 5, 31) - day0).days
        day_array = np.arange(0, total_days, 4)
        ssm_days = (df_datetimes - df_datetimes[0]).days
        ndvi_days = np.array([(day - dt_arr[0]).days for day in dt_arr])

        ssm_interp = np.interp(day_array, ssm_days, SSM_mean)
        ndvi_interp = np.interp(day_array, ndvi_days, ndvi_mean)
        ssm_ndvi_cor = correlate(
            ssm_interp/np.max(ssm_interp),
            ndvi_interp/np.max(ndvi_interp))
        cor_lags = correlation_lags(len(ssm_interp), len(ndvi_interp))
        print(f"Max correlation between SSM and NDVI {sub_label} {park_name}: {np.max(ssm_ndvi_cor)}")
        ax_cor.plot(
            cor_lags,
            ssm_ndvi_cor,
            label="correlation " + sub_label
            + " "
            + park_name.capitalize()
            + " Park"
        )
    ax_cor.set_ylabel("correlation coefficient")
    ax_cor.set_xlabel("lag (days)")
    ax_cor.legend()
    ax[1].set_ylabel("NDVI")
    ax[0].set_ylabel("Soil Moisture Level (percent)")
    ax[0].legend()
    ax[1].legend()
    ax[1].set_xlabel("Date")

    fig.savefig(f"/data/tapas/pearse/malawi/SSM_NDVI_{park_name}.png")
    fig_cor.savefig(
        f"/data/tapas/pearse/malawi/SSM_NDVI_correlation_{park_name}.png")
    return


def plot_region_ndvi(
        nparks_geojson: str,
        park_name: str
        ) -> None:

    fig, ax = plt.subplots(
        2, 1, figsize=(9, 7), sharex=True)
    fig_cor, ax_cor = plt.subplots(1, 1, figsize=(9, 7))
    ndvi_means = []
    for sub_label in ["Inside", "Outside"]:
        stat_file = f"/data/tapas/pearse/ee_downloads/{sub_label.lower()}_{park_name.lower()}_mean_ndvi.csv"
        with open(stat_file) as stats:
            csv_read = csv.reader(stats)
            date_row = next(csv_read)
            data_row = next(csv_read)
        dt_arr = np.array(
            [datetime.strptime(dr, "%Y_%m_%d_NDVI") for dr in date_row[:-1]])
        ndvi_mean = np.array(data_row[:-1], dtype=float)
        days_arr = np.array(
            [(dt_arr - dt_arr[0])[i].days for i in range(len(dt_arr))])
        ndvi_rate = np.gradient(ndvi_mean, days_arr)
        ax[0].plot(
            dt_arr,
            ndvi_mean,
            "-o",
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park")
        ax[1].plot(
            dt_arr,
            ndvi_rate,
            "-o",
            label=sub_label
            + " "
            + park_name.capitalize()
            + " Park"
        )
        ndvi_means.append(ndvi_mean)
    ndvi_mean_inside, ndvi_mean_outside = ndvi_means
    ndvi_cor = correlate(
        ndvi_mean_outside/np.max(ndvi_mean_outside),
        ndvi_mean_inside/np.max(ndvi_mean_inside)
        )
    cor_lags = correlation_lags(len(ndvi_mean_outside), len(ndvi_mean_inside))
    print(f"Max NDVI correlation {park_name}: {np.max(ndvi_cor)}")
    ax_cor.plot(
        cor_lags,
        ndvi_cor
    )
    ax_cor.set_xlabel("lag (days)")
    ax_cor.set_ylabel("correlation coefficient")
    ax[0].set_ylabel("NDVI")
    ax[1].set_ylabel("NDVI rate (per day)")
    # ax[0].legend()
    ax[1].legend()
    ax[1].set_xlabel("Date")
    fig.savefig(f"/data/tapas/pearse/malawi/NDVI_{park_name}.png")
    fig_cor.savefig(f"/data/tapas/pearse/malawi/NDVI_correlation_{park_name}.png")
    return


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
        plot_region_ssm(gdf, nparks_geojson, park_name)
        plot_region_ndvi(nparks_geojson, park_name)
        plot_ssm_ndvi(gdf, nparks_geojson, park_name)

    # plt.show()
