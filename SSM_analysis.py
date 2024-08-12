#!/usr/bin/env python

from datetime import datetime, timedelta
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd

from matplotlib.colors import Normalize

from eo_utils import geojson_to_shapely
from insar4sm.prep_meteo import convert_to_df

plot_compare = True
root_path = Path("/data/tapas/pearse/malawi")
ssm_path = root_path/"SSM/malawi_InSAR_SSM_1km_southern_20230101_20240531"
gdf = gpd.read_file(
    ssm_path /
    "sm_inversions_malawi_InSAR_SSM_1km_southern_20230101_20230531_500.shp")
polys = gpd.read_file(
    ssm_path /
    "malawi_InSAR_SSM_1km_southern_20230101_20240531/INSAR4SM_processing/SM/SM_polygons.geojson")
gdf = gdf.drop(columns="geometry")
gdf = pd.concat([polys, gdf], axis=1)

plot = True
aoi_dir = "/data/tapas/pearse/malawi/sentinel1/aoi"
# big json of all national parks
# kasungu is at index 25, Liwonde is 6
national_parks = aoi_dir + "/protected_areas.json"
npark = geojson_to_shapely(national_parks, 6)
gdf['intersects_park'] = gdf['geometry'].map(lambda x: x.intersects(npark))
gdf = gdf.where(gdf['intersects_park']).dropna()
inside_or_outside = "inside_park"

# aoi = aoi_dir + "/kasungu_small.geojson"
# ERA5_file = root_path/"ERA5/kasungu/kasungu_20230101_20240531.nc"
aoi = aoi_dir + "/liwonde_np.geojson"
ERA5_file = root_path/"ERA5/ERA5_20230101T000000_20240531T230000_malawi_bbox.nc"
meteo_df = convert_to_df(ERA5_file, aoi, True)
df_datetimes = pd.to_datetime(gdf.columns[1:-1], format="D%Y%m%d")

ERA5_data = netCDF4.Dataset(ERA5_file)
d0 = datetime.strptime(
    'T'.join(ERA5_data["time"].units.split(' ')[-2:]),
    "%Y-%m-%dT%H:%M:%S")
days = d0 + ERA5_data["time"][:].data[::24]*timedelta(hours=1)

SSM_mean = gdf.mean(numeric_only=True)
# SSM_median = gdf.median(numeric_only=True)
fig, ax1 = plt.subplots(figsize=(12.5, 7))
# mean_tp = np.mean(ERA5_data["tp"][:], axis=(1,2))
mean_tp = meteo_df['tp__m'].values*1e3
daily_cumulative_tp = np.sum(mean_tp.reshape(-1, 24), axis=1)
days_start, days_end = 8, -5
revisit_cumulitave_tp = np.sum(
    daily_cumulative_tp[days_start:days_end].reshape(-1, 12), axis=1)

tp_hour = ax1.plot(
    meteo_df.index,
    mean_tp,
    label="hourly cumulative precipitation")
tp_day = ax1.plot(
    days,
    daily_cumulative_tp/24,
    label="daily cumulative preciptiation (average per hour)")
tp = ax1.plot(
    days[days_start:days_end][::12],
    revisit_cumulitave_tp/(12*24),
    'o-',
    label="12 day cumulative precipitation (average per hour)")

ax1.set_ylabel("Total precipitation (mm)", fontdict={"size": 16})
ax2 = ax1.twinx()
smi = ax2.plot(
    df_datetimes,
    SSM_mean,
    'o-',
    color="grey",
    label="Soil moisture inversion")
ax1.set_xlabel("Date", fontdict={"size": 16})
ax2.set_ylabel("Soil moisture level (percentage)", fontdict={"size": 16})

handles = tp_hour + tp_day + tp + smi
labels = [label.get_label() for label in handles]
ax1.legend(handles, labels, loc=(0.25, 0.8))
plt.tight_layout()
plt.savefig(ssm_path/f"soil_moisture_inversion_vs_hourly_cumulative_precipitation_{inside_or_outside}.png")

# liwonde_geojson = \
#     "/data/tapas/pearse/malawi/sentinel1/aoi/Liwonde_National_Park.geojson"
# with open(liwonde_geojson) as gj:
#     liwonde_poly = geojson.load(gj)
# liwonde_poly = Polygon(
#     liwonde_poly['features'][0]['geometry']['coordinates'][0])

if plot:
    cmap = cm.get_cmap('viridis')
    normalizer = Normalize(0, 50)
    im = cm.ScalarMappable(norm=normalizer)

    print("Plotting soil moisture")
    scaler = 3.5
    if plot_compare:
        rows = 5
        columns = 8
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                columns*scaler,
                rows*scaler
                ),
            sharex=True,
            sharey=True,
            layout='constrained')
        fig.subplots_adjust(hspace=0.15, wspace=0.2)
        rav_ax = np.ravel(axs)
        for i, ax in enumerate(rav_ax):
            col = gdf.columns[1+i]
            gax = gdf.plot(
                ax=ax,
                column=col,
                legend=False,
                cmap=cmap,
                norm=normalizer,
                aspect=None)
            col_date = datetime.strptime(col, "D%Y%m%d")
            ax.set_title(col_date.date(), fontdict={"size": 14})
            if i < len(rav_ax) - 1:
                provider = cx.providers.CartoDB.Voyager(attribution="")
            else:
                provider = cx.providers.CartoDB.Voyager
            cx.add_basemap(gax, crs=gdf.crs.to_string(), source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
        # axs[2, 0].set_ylabel("Latitude", fontdict={"size": 16})
        # axs[4, 4].set_xlabel("Longitude", fontdict={"size": 16})
        fig.supxlabel("Longitude", x=0.45, y=0.05, fontsize=16) #fontdict={"size": 18})
        fig.supylabel("Latitude", x=0.05, fontsize=16)#fontdict={"size": 18})
        # plt.tight_layout()
        cb = fig.colorbar(im, ax=axs.ravel().tolist(), aspect=50)
        cb.set_label(label="Soil Moisture Level (%)", size=14)
        plt.savefig(ssm_path/f"soil_moisture_pngs/all_date_compare_{inside_or_outside}.png")
        # plt.show()
    else:
        for col in gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9))
            gax = gdf.plot(
                column=col,
                ax=ax,
                legend=False,
                cmap=cmap,
                norm=normalizer)
            cb = fig.colorbar(im, ax=ax)
            cb.set_label(label="Soil Moisture Level (%)", size=14)
            col_date = datetime.strptime(col, "D%Y%m%d")
            ax.set_title(col_date.date(), fontdict={"size": 14})
            ax.set_ylabel("Latitude", fontdict={"size": 14})
            ax.set_xlabel("Longitude", fontdict={"size": 14})
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            plt.tight_layout()
            plt.savefig(ssm_path/f"soil_moisture_pngs/{col}.png")
            plt.close()


# month on month running difference

running_difference = gdf[gdf.columns[2:-1]].values - \
    gdf[gdf.columns[1:-2]].values

running_difference_col_names = [d1[3:] + '-' + d0[3:] for d1, d0 in zip(
    gdf.columns[2:-1], gdf.columns[1:-2])]
running_difference_dict = {col_name: value for col_name, value in zip(
    running_difference_col_names, running_difference.T)}
running_difference_df = pd.DataFrame(running_difference_dict)
running_difference_gdf = gpd.GeoDataFrame(pd.concat([gdf['geometry'].reset_index(drop=True), running_difference_df], axis=1))
plot=True
if plot:
    cmap = cm.get_cmap('PuOr')
    normalizer = Normalize(-50, 50)
    im = cm.ScalarMappable(norm=normalizer, cmap=cmap)
    scaler = 3.5
    print("Plotting running differences")
    if plot_compare:
        rows = 5
        columns = 8
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                columns*scaler,
                rows*scaler
                ),
            sharex=True,
            sharey=True)
        # fig.subplots_adjust(hspace=0.15, wspace=0.15)
        for i, ax in enumerate(np.ravel(axs)[:-1]):
            col = running_difference_gdf.columns[1+i]
            gax = running_difference_gdf.plot(
                ax=ax,
                column=col,
                legend=False,
                cmap=cmap,
                norm=normalizer,
                aspect=None)
            ax.set_title(col)
            if i < len(np.ravel(axs)[:-1]) - 1:
                provider = cx.providers.CartoDB.Voyager(attribution="")
            else:
                provider = cx.providers.CartoDB.Voyager
            cx.add_basemap(
                gax,
                crs=running_difference_gdf.crs.to_string(),
                source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
        axs[-1, -1].set_visible(False)
        axs[-2, -1].xaxis.set_tick_params(labelbottom=True)
        fig.suptitle("Soil Moisture Level Running Difference")
        fig.supxlabel("Longitude", x=0.45, y=0.05, fontsize=16)
        fig.supylabel("Latitude", x=0.05, fontsize=16)
        # plt.tight_layout()
        # cbar = fig.colorbar(im, ax=axs.ravel().tolist(), aspect=50)
        # cbar.set_label(label="Percentage Point difference", size=14)
        plt.savefig(
            ssm_path/f"running_difference_pngs/running_difference_compare_{inside_or_outside}.pdf")
        plt.savefig(
            ssm_path/f"running_difference_pngs/running_difference_compare_{inside_or_outside}.png")
        # plt.show()
    else:
        for col in running_difference_gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9))
            gax = running_difference_gdf.plot(
                column=col,
                ax=ax,
                legend=False,
                cmap=cmap,
                norm=normalizer)
            cb = fig.colorbar(im, ax=ax)
            cb.set_label(label="Percentage Point Difference", size=14)
            ax.set_title(col, fontdict={"size": 14})
            ax.set_ylabel("Latitude", fontdict={"size": 14})
            ax.set_xlabel("Longitude", fontdict={"size": 14})
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            plt.tight_layout()
            plt.savefig(ssm_path/f"running_difference_pngs/{col}.png")
            plt.close()

    fig, ax = plt.subplots(figsize=(9,6))
    slc_dates = [datetime.strptime(col, "D%Y%m%d") for col in gdf.columns[2:-1]]
    mean_rd = running_difference_gdf.mean(numeric_only=True).values
    ax.plot(slc_dates, mean_rd/np.nanmax(mean_rd), 'o', color='grey', label="normalised soil moisture running difference")

    ax.plot(
        meteo_df.index,
        mean_tp/np.nanmax(mean_tp),
        label="normalised hourly cumulative precipitation")
    ax.plot(
        days,
        daily_cumulative_tp/np.nanmax(daily_cumulative_tp),
        label="normalised daily cumulative preciptiation")
    ax.plot(
        days[days_start:days_end][::12],
        revisit_cumulitave_tp/np.nanmax(revisit_cumulitave_tp),
        'o-',
        label="normalised 12 day cumulative precipitation")
    ax.axhline(0, color='red')
    rainy_start1 = datetime(2022,11,15)
    rainy_end1 = datetime(2023,4,15)
    rainy_start2 = datetime(2023,11,15)
    rainy_end2 = datetime(2024,4,15)
    ax.axvspan(rainy_start1, rainy_end1, color="aqua")
    ax.axvspan(rainy_start2, rainy_end2, color="aqua", label="Approximate Rainy season")
    ax.set_xlim(datetime(2022,12,15))
    ax.legend()
    plt.savefig(ssm_path/f"mean_running_diff_{inside_or_outside}.png")


year_on_year = gdf[gdf.columns[30:-1]].values - gdf[gdf.columns[1:12]].values
year_on_year_col_names = [d24[1:] + '-' + d23[1:] for d23, d24 in zip(
    gdf.columns[1:12], gdf.columns[30:-1])]
year_on_year_dict = {col_name: value for col_name, value in zip(
    year_on_year_col_names, year_on_year.T)}
year_on_year_df = pd.DataFrame(year_on_year_dict)
year_on_year_gdf = gpd.GeoDataFrame(pd.concat([gdf['geometry'].reset_index(drop=True), year_on_year_df], axis=1))

if plot:
    print("Plotting year on year")
    cmap = cm.get_cmap('PuOr')
    normalizer = Normalize(-50, 50)
    im = cm.ScalarMappable(norm=normalizer, cmap=cmap)
    scaler = 3.5
    if plot_compare:
        rows = 4
        columns = 3
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                columns*scaler, rows*scaler
                ),
            sharex=True,
            sharey=True)
        fig.subplots_adjust(hspace=0.15, wspace=0.15)
        for i, ax in enumerate(np.ravel(axs)[:-1]):
            col = year_on_year_gdf.columns[1+i]
            gax = year_on_year_gdf.plot(
                ax=ax,
                column=col,
                legend=False,
                cmap=cmap,
                norm=normalizer,
                aspect=None)
            ax.set_title(col)
            if i < len(np.ravel(axs)[:-1]) - 1:
                provider = cx.providers.CartoDB.Voyager(attribution="")
            else:
                provider = cx.providers.CartoDB.Voyager
            cx.add_basemap(
                gax,
                crs=year_on_year_gdf.crs.to_string(),
                source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
        axs[-1, -1].set_visible(False)
        axs[2, -1].xaxis.set_tick_params(labelbottom=True)
        fig.suptitle("Soil Moisture Level Year on Year Difference")
        fig.supxlabel("longitude", fontdict={"size": 14})
        fig.supylabel("latitude", fontdict={"size": 14})
        plt.tight_layout()
        cbar = fig.colorbar(im, ax=axs.ravel().tolist(), aspect=50)
        cbar.set_label(label="Percentage Point difference", size=14)

        plt.savefig(ssm_path/f"year_on_year_pngs/year_on_year_compare_{inside_or_outside}.png")

    else:
        for col in year_on_year_gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9))
            gax = year_on_year_gdf.plot(
                column=col,
                ax=ax,
                legend=False,
                cmap=cmap,
                norm=normalizer)
            cb = fig.colorbar(im, ax=ax)
            cb.set_label(label="Percentage Point Difference", size=14)
            ax.set_title(col, fontdict={"size": 14})
            ax.set_ylabel("Latitude", fontdict={"size": 14})
            ax.set_xlabel("Longitude", fontdict={"size": 14})
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager)
            plt.tight_layout()
            plt.savefig(ssm_path/f"year_on_year_pngs/{col}.png")
            plt.close()


plt.figure(figsize=(9,5))
plt.plot(
    [
        "Jan 16-9",
        "Jan 28-21",
        "Feb 9-14",
        "Feb 21-26",
        "Mar 4-1",
        "Mar 16-22",
        "Mar 28-Apr 3",
        "Apr 9-15",
        "Apr 21-27",
        "May 5-9",
        "May 27-21"
    ],
    # [
    #     "Dec 28-Jan 2",
    #     "Jan 9-14",
    #     "Jan 21-26",
    #     "Feb 2-7",
    #     "Feb 26-19",
    #     "Mar 9-3",
    #     "Mar 21-15",
    #     "Apr 2-27",
    #     "Apr 14-8",
    #     "Apr 26-20",
    #     "May 8-2",
    #     "May 20-14"
    # ],
    year_on_year_gdf.mean(numeric_only=True).values,
    'o')
plt.axhline(0, color='red')
plt.xticks(rotation=45)
plt.ylabel("Mean Percentage Difference")
plt.xlabel("2024-2023")

plt.show()
