#!/usr/bin/env python
# insar4sm_dev environment
from datetime import datetime, timedelta
from pathlib import Path
import sys

import cmocean
import contextily as cx
import geopandas as gpd
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import netCDF4
import numpy as np
import pandas as pd

from matplotlib.colors import Normalize

from eo_utils import geojson_to_shapely, load_ssm
from insar4sm.prep_meteo import convert_to_df


plot_compare = True
# figure setup from https://duetosymmetry.com/code/latex-mpl-fig-tips/
# doesn't really work
# plt.style.use("/data/tapas/pearse/scripts/paper.mplstyle")
# pt = 1./72.27
width_onecol = 12.5# 222. * pt
width_twocol = 9# 468. * pt
golden = (1 + 5**0.5) / 2

# root_path = Path("/data/tapas/pearse/vietnam")
# ssm_path = root_path/"SSM/F56_20230104_20240815"
# shp_file = ssm_path/"sm_inversions_F56_20230104_20240815_125.shp"
# polygon_geojson = ssm_path/"F56_20230104_20240815/INSAR4SM_processing/SM/SM_polygons.geojson"

# gdf = load_ssm(shp_file, polygon_geojson)
# plot = True
# aoi_dir = "/data/tapas/pearse/vietnam/aoi"
# big json of all national parks
# kasungu is at index 25, Liwonde is 6
# national_parks = aoi_dir + "/protected_areas.json"
# npark = geojson_to_shapely(national_parks, 6)
# gdf['intersects_park'] = gdf['geometry'].map(lambda x: x.intersects(npark))
# gdf = gdf.where(gdf['intersects_park']).dropna()
# inside_or_outside = "inside_park"

# aoi = aoi_dir + "/kasungu_small.geojson"
# ERA5_file = root_path/"ERA5/kasungu/kasungu_20230101_20240531.nc"
# aoi = aoi_dir + "/F56_bbox.geojson"
# ERA5_file = root_path/"ERA5/F56/F56_20230104_20240815.nc"

root_path = Path("/data/tapas/pearse/malawi/")
aoi_dir = root_path/"sentinel1/aoi"
national_parks = aoi_dir/"protected_areas.json"

if len(sys.argv) == 1:
    park_name = "liwonde"
else:
    park_name = sys.argv[1]

if park_name == "kasungu":
    aoi = aoi_dir/"kasungu_small.geojson"
    npark = geojson_to_shapely(national_parks, 25)

    ssm_path = root_path/"SSM/kasungu_1km_20230101_20240531"
    shp_file = ssm_path/"sm_inversions_kasungu_1km_20230101_20240531_500.shp"
    polygon_geojson = ssm_path/"kasungu_1km_20230101_20240531/INSAR4SM_processing/SM/SM_polygons.geojson"
    ERA5_file = root_path/"ERA5/kasungu/kasungu_20230101_20240531.nc"

elif park_name == "liwonde":
    aoi = aoi_dir/"southern_malawi_aoi.geojson"
    npark = geojson_to_shapely(national_parks, 6)

    ssm_path = root_path/"SSM/malawi_InSAR_SSM_1km_southern_20230101_20240531"
    shp_file = ssm_path/"sm_inversions_malawi_InSAR_SSM_1km_southern_20230101_20230531_500.shp"
    polygon_geojson = ssm_path/"malawi_InSAR_SSM_1km_southern_20230101_20240531/INSAR4SM_processing/SM/SM_polygons.geojson"
    ERA5_file = root_path/"ERA5/liwonde/liwond_20230101_20240531.nc"

else:
    print(f"Park name {park_name} not recognised. Must be either 'liwonde' or 'kasungu'")
    print("Exiting script")
    sys.exit()



gdf = load_ssm(shp_file, polygon_geojson)
meteo_df = convert_to_df(ERA5_file, aoi, True)
df_datetimes = pd.to_datetime(gdf.columns[1:], format="D%Y%m%d")

ERA5_data = netCDF4.Dataset(ERA5_file)
if park_name == "kasungu":
    d0 = datetime.strptime(
        'T'.join(ERA5_data["valid_time"].units.split(' ')[-2:]),
        "%Y-%m-%dT%H:%M:%S")
    
    days = d0 + ERA5_data["valid_time"][:].data[::24]*timedelta(hours=1)
elif park_name == "liwonde":
    d0 = datetime.fromtimestamp(ERA5_data["valid_time"][0])
    days = d0 + (ERA5_data["valid_time"][:].data[::24] - ERA5_data["valid_time"][0])*timedelta(seconds=1)
SSM_mean = gdf.mean(numeric_only=True)
# SSM_median = gdf.median(numeric_only=True)
fig, ax1 = plt.subplots(
    figsize=(
        12.5,
        7
        ),
    )
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

ax1.set_ylabel("Total precipitation (mm)", fontdict={"size": 14})
ax2 = ax1.twinx()
smi = ax2.plot(
    df_datetimes,
    SSM_mean,
    'o-',
    color="grey",
    label="Soil moisture inversion")
ax1.set_xlabel("Date", fontdict={"size": 14})
ax2.set_ylabel("Soil moisture level (percentage)", fontdict={"size": 14})

handles = tp_hour + tp_day + tp + smi
labels = [label.get_label() for label in handles]
if park_name == "liwonde":
    ax1.legend(handles, labels, loc=(0.255, 0.81), prop={"size":12})
else:
    ax1.legend(handles, labels, loc=(0.2, 0.81), prop={"size":12})
ax1.tick_params(labelsize=14)
ax2.tick_params(labelsize=14)
plt.tight_layout()
plt.savefig(ssm_path/"soil_moisture_inversion_vs_hourly_cumulative_precipitation.eps")

# liwonde_geojson = \
#     "/data/tapas/pearse/malawi/sentinel1/aoi/Liwonde_National_Park.geojson"
# with open(liwonde_geojson) as gj:
#     liwonde_poly = geojson.load(gj)
# liwonde_poly = Polygon(
#     liwonde_poly['features'][0]['geometry']['coordinates'][0])
n_plots = len(gdf.columns[1:])
plot = True
scaler = 2
if plot:
    cmap = cmocean.cm.rain #cm.get_cmap('viridis')
    normalizer = Normalize(0, 50)
    im = cm.ScalarMappable(norm=normalizer, cmap=cmap)

    print("Plotting soil moisture")
    
    if plot_compare:
        rows = 4
        columns = 5
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                scaler*columns,
                scaler*rows,
                ),
            sharex=True,
            sharey=True,
            layout='constrained')
        # fig.subplots_adjust(hspace=0.15, wspace=0.2)
        rav_ax = np.ravel(axs)
        i = 1
        for ax in rav_ax[:n_plots//2]:
            col = gdf.columns[i]
            gax = gdf.plot(
                ax=ax,
                column=col,
                legend=False,
                cmap=cmap,
                norm=normalizer,
                aspect=None)
            col_date = datetime.strptime(col, "D%Y%m%d")
            ax.set_title(col_date.date(), fontdict={"size": 14})
            # if i < len(rav_ax) - 1:
            #     provider = cx.providers.CartoDB.Voyager(attribution="")
            # else:
            #     provider = cx.providers.CartoDB.Voyager
            provider = cx.providers.CartoDB.Voyager(attribution="")
            cx.add_basemap(gax, crs=gdf.crs.to_string(), source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            i+=2
        # axs[2, 0].set_ylabel("Latitude", fontdict={"size": 14})
        # axs[4, 4].set_xlabel("Longitude", fontdict={"size": 14})
        fig.supxlabel("Longitude",) #x=0.45, y=0.05, fontsize=16) #fontdict={"size": 14})
        fig.supylabel("Latitude",) #x=0.05, fontsize=16)#fontdict={"size": 14})
        # cax = axs[2,-1].inset_axes([1, 0, 0.1, 1])
        cb = fig.colorbar(im, ax=axs[:,-1], aspect=50)
        cb.set_label(label="Soil Moisture Level (%)", size=14)
        # plt.tight_layout()
        plt.savefig(ssm_path/"soil_moisture_pngs/all_date_compare.eps")
        # plt.show()
    else:
        for col in gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9), layout='constrained')
            gax = gdf.plot(
                column=col,
                ax=ax,
                legend=False,
                cmap=cmap,
                norm=normalizer)
            cb = fig.colorbar(im, ax=ax, shrink=0.7)
            cb.set_label(label="Soil Moisture Level (%)", size=14)
            col_date = datetime.strptime(col, "D%Y%m%d")
            ax.set_title(col_date.date(), fontdict={"size": 14})
            ax.set_ylabel("Latitude", fontdict={"size": 14})
            ax.set_xlabel("Longitude", fontdict={"size": 14})
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager(attribution=""))
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            # plt.tight_layout()
            plt.savefig(ssm_path/f"soil_moisture_pngs/{col}.eps")
            plt.close()



# month on month running difference

running_difference = gdf[gdf.columns[2:]].values - \
    gdf[gdf.columns[1:-1]].values

running_difference_col_names = [d1[3:] + '-' + d0[3:] for d1, d0 in zip(
    gdf.columns[2:], gdf.columns[1:-1])]
running_difference_dict = {col_name: value for col_name, value in zip(
    running_difference_col_names, running_difference.T)}
running_difference_df = pd.DataFrame(running_difference_dict)
running_difference_gdf = gpd.GeoDataFrame(pd.concat([gdf['geometry'].reset_index(drop=True), running_difference_df], axis=1))
n_running_difference_plots = len(running_difference_gdf.columns[1:])
# plot = False
if plot:
    cmap = cm.get_cmap('PuOr')
    normalizer = Normalize(-50, 50)
    im = cm.ScalarMappable(norm=normalizer, cmap=cmap)
    
    print("Plotting running differences")
    if plot_compare:
        rows = 4
        columns = 5
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                scaler*columns,
                scaler*rows
                ),
            sharex=True,
            sharey=True,
            layout='constrained')
        # fig.subplots_adjust(hspace=0.15, wspace=0.15)
        i = 2
        for ax in np.ravel(axs)[:n_running_difference_plots//2]:
            col = running_difference_gdf.columns[i]
            gax = running_difference_gdf.plot(
                ax=ax,
                column=col,
                legend=False,
                cmap=cmap,
                norm=normalizer,
                aspect=None)
            ax.set_title(col)
            # if i < len(np.ravel(axs)[:-1]) - 1:
            #     provider = cx.providers.CartoDB.Voyager(attribution="")
            # else:
            #     provider = cx.providers.CartoDB.Voyager
            provider = cx.providers.CartoDB.Voyager(attribution="")
            cx.add_basemap(
                gax,
                crs=running_difference_gdf.crs.to_string(),
                source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            i+=2
        if park_name == "liwonde":
            axs[-1, -1].set_visible(False)
            axs[-2, -1].xaxis.set_tick_params(labelbottom=True)
        # fig.suptitle("Soil Moisture Level Running Difference")
        fig.supxlabel("Longitude")#, x=0.45, y=0.05, fontsize=16)
        fig.supylabel("Latitude")#, x=0.05, fontsize=16)
        
        cbar = fig.colorbar(im, ax=axs[:, -1], aspect=50) # ax=axs.ravel().tolist()
        cbar.set_label(label="Percentage Point difference", size=14)
        # plt.tight_layout()
        plt.savefig(
            ssm_path/"running_difference_pngs/running_difference_compare.pdf")
        plt.savefig(
            ssm_path/"running_difference_pngs/running_difference_compare.eps")
        # plt.show()
    else:
        for col in running_difference_gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9), layout='constrained')
            gax = running_difference_gdf.plot(
                column=col,
                ax=ax,
                legend=False,
                cmap=cmap,
                norm=normalizer)
            cb = fig.colorbar(im, ax=ax, shrink=0.7)
            cb.set_label(label="Percentage Point Difference", size=14)
            ax.set_title(col, fontdict={"size": 14})
            ax.set_ylabel("Latitude", fontdict={"size": 14})
            ax.set_xlabel("Longitude", fontdict={"size": 14})
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager(attribution=""))
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
            # plt.tight_layout()
            plt.savefig(ssm_path/f"running_difference_pngs/{col}.eps")
            plt.close()

    fig, ax = plt.subplots(figsize=(width_onecol, width_onecol/golden), layout='constrained')
    slc_dates = [datetime.strptime(col, "D%Y%m%d") for col in gdf.columns[2:]]
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
    plt.savefig(ssm_path/"mean_running_diff.eps")

if park_name == "kasungu":
    year_on_year = gdf[gdf.columns[30:-1]].values - gdf[gdf.columns[1:12]].values
    year_on_year_col_names = [d24[1:] + '-' + d23[1:] for d23, d24 in zip(
        gdf.columns[1:12], gdf.columns[30:-1])]
elif park_name == "liwonde":
    year_on_year = gdf[gdf.columns[30:]].values - gdf[gdf.columns[1:12]].values
    year_on_year_col_names = [d24[1:] + '-' + d23[1:] for d23, d24 in zip(
        gdf.columns[1:12], gdf.columns[30:])]
year_on_year_dict = {col_name: value for col_name, value in zip(
    year_on_year_col_names, year_on_year.T)}
year_on_year_df = pd.DataFrame(year_on_year_dict)
year_on_year_gdf = gpd.GeoDataFrame(pd.concat([gdf['geometry'].reset_index(drop=True), year_on_year_df], axis=1))

# plot = True
scaler =3
if plot:
    print("Plotting year on year")
    cmap = cm.get_cmap('PuOr')
    normalizer = Normalize(-50, 50)
    im = cm.ScalarMappable(norm=normalizer, cmap=cmap)
    
    if plot_compare:
        rows = 3
        columns = 4
        fig, axs = plt.subplots(
            rows,
            columns,
            figsize=(
                scaler*columns,
                scaler*rows
                ),
            sharex=True,
            sharey=True,
            layout='constrained')
        # fig.subplots_adjust(hspace=0.15, wspace=0.15)
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
            # if i < len(np.ravel(axs)[:-1]) - 1:
            #     provider = cx.providers.CartoDB.Voyager(attribution="")
            # else:
            #     provider = cx.providers.CartoDB.Voyager
            provider = cx.providers.CartoDB.Voyager(attribution="")

            cx.add_basemap(
                gax,
                crs=year_on_year_gdf.crs.to_string(),
                source=provider)
            ax.plot(*npark.geoms[0].exterior.xy, color='r')
        axs[-1, -1].set_visible(False)
        axs[1, 3].xaxis.set_tick_params(labelbottom=True)
        # fig.suptitle("Soil Moisture Level Year on Year Difference")
        fig.supxlabel("Longitude", fontdict={"size": 14})
        # axs[-1,1].set_xlabel("Longitgude", fontdict={"size": 14})
        fig.supylabel("Latitude", fontdict={"size": 14})
        # plt.tight_layout()
        cbar = fig.colorbar(im, ax=axs.ravel().tolist(), aspect=50)
        cbar.set_label(label="Percentage Point difference", size=14)

        plt.savefig(ssm_path/"year_on_year_pngs/year_on_year_compare.eps")

    else:
        for col in year_on_year_gdf.columns[1:]:
            fig, ax = plt.subplots(1, 1, figsize=(9, 9), layout='constrained')
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
            # ax.plot(*npark.geoms[0].exterior.xy, color='r')
            cx.add_basemap(
                gax,
                crs=gdf.crs.to_string(),
                source=cx.providers.CartoDB.Voyager)
            plt.tight_layout()
            plt.savefig(ssm_path/f"year_on_year_pngs/{col}.eps")
            plt.close()


# plt.figure(figsize=(9,5))
# plt.plot(
#     [
#         "Jan 16-9",
#         "Jan 28-21",
#         "Feb 9-14",
#         "Feb 21-26",
#         "Mar 4-1",
#         "Mar 16-22",
#         "Mar 28-Apr 3",
#         "Apr 9-15",
#         "Apr 21-27",
#         "May 5-9",
#         "May 27-21"
#     ],
#     # [
#     #     "Dec 28-Jan 2",
#     #     "Jan 9-14",
#     #     "Jan 21-26",
#     #     "Feb 2-7",
#     #     "Feb 26-19",
#     #     "Mar 9-3",
#     #     "Mar 21-15",
#     #     "Apr 2-27",
#     #     "Apr 14-8",
#     #     "Apr 26-20",
#     #     "May 8-2",
#     #     "May 20-14"
#     # ],
#     year_on_year_gdf.mean(numeric_only=True).values,
#     'o')
# plt.axhline(0, color='red')
# plt.xticks(rotation=45)
# plt.ylabel("Mean Percentage Difference")
# plt.xlabel("2024-2023")

plt.show()
