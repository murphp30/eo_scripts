#!/usr/bin/env python

import csv
import os
import sys

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio as rio

from osgeo import gdal
from rasterstats import zonal_stats
from scipy.stats import linregress
from shapely import Polygon, MultiPolygon

from eo_utils import geojson_to_shapely, load_ssm, get_zonal_means

ndvi_dir = "/data/tapas/pearse/ee_downloads"
root_path = Path("/data/tapas/pearse/malawi/")
aoi_dir = root_path/"sentinel1/aoi"
national_parks = aoi_dir/"protected_areas.json"

if len(sys.argv) == 1:
    park_name = "liwonde"
else:
    park_name = sys.argv[1]

if park_name == "kasungu":
    park_aoi = aoi_dir/"kasungu_small.geojson"
    npark = geojson_to_shapely(national_parks, 25)

    ssm_path = root_path/"SSM/kasungu_1km_20230101_20240531"
    shp_file = ssm_path/"sm_inversions_kasungu_1km_20230101_20240531_500.shp"
    polygon_geojson = ssm_path/"kasungu_1km_20230101_20240531/INSAR4SM_processing/SM/SM_polygons.geojson"

elif park_name == "liwonde":
    park_aoi = aoi_dir/"southern_malawi_aoi.geojson"
    npark = geojson_to_shapely(national_parks, 6)

    ssm_path = root_path/"SSM/malawi_InSAR_SSM_1km_southern_20230101_20240531"
    shp_file = ssm_path/"sm_inversions_malawi_InSAR_SSM_1km_southern_20230101_20230531_500.shp"
    polygon_geojson = ssm_path/"malawi_InSAR_SSM_1km_southern_20230101_20240531/INSAR4SM_processing/SM/SM_polygons.geojson"

else:
    print(f"Park name {park_name} not recognised. Must be either 'liwonde' or 'kasungu'")
    print("Exiting script")
    sys.exit()

bbox = geojson_to_shapely(park_aoi)
merged_dir = root_path/f"sentinel1/{park_name}_stack/merged/interferograms"

coherences = merged_dir.glob("*/geo_filt_fine.cor")
zone_means = {}
# this could/should be optimised. Run in parallel or something more clever.
for coh in sorted(coherences):
    time_range = coh.parts[-2].split('_')[0]
    zone_means[time_range] = get_zonal_means(coh, bbox, npark)

# Load soil moisture results
gdf = load_ssm(shp_file, polygon_geojson)
ssm_datetime_array = pd.to_datetime(gdf.columns[1:], format="D%Y%m%d")
gdf['intersects_park'] = gdf['geometry'].map(lambda x: x.intersects(npark))
gdfi = gdf.where(gdf['intersects_park']).dropna()
gdfo = gdf.where(~gdf['intersects_park']).dropna()

# plot it all
coh_datetime_array = [datetime.strptime(zm, "%Y%m%d") for zm in zone_means]
fig, ax1 = plt.subplots(2, 1, figsize=(9, 7), sharex=True, sharey=True, layout="constrained")
fig_cor, ax1_cor = plt.subplots(2, 1, figsize=(9, 7), sharex=True, sharey=True, layout="constrained")
outside_zone = [zone_means[zm]["outside"] for zm in zone_means]
i = 0
for gdf, zone in zip([gdfi, gdfo], ["inside", "outside"]):

    SSM_mean = gdf.mean(numeric_only=True)
    coh_mean = [zone_means[zm][zone] for zm in zone_means]

    coh_plot = ax1[i].plot(
        coh_datetime_array,
        coh_mean,
        '-o',
        label="Coherence")
    ax1[i].set_title(
        f"{zone.capitalize()} {park_name.capitalize()} National Park")
    ax1[i].set_ylabel("Coherence and NDVI", fontdict={"size": 14})

    ndvi_stats = os.path.join(ndvi_dir, f"{zone}_{park_name}_mean_ndvi.csv")
    with open(ndvi_stats) as stats:
        csv_read = csv.reader(stats)
        date_row = next(csv_read)
        data_row = next(csv_read)
    ndvi_datetime_array = np.array(
        [datetime.strptime(dr, "%Y_%m_%d_NDVI") for dr in date_row[:-1]])
    ndvi_mean = np.array(data_row[:-1], dtype=float)
    ndvi_plot = ax1[i].plot(
        ndvi_datetime_array,
        ndvi_mean,
        '-^',
        color='forestgreen',
        label='ndvi')
    ax2 = ax1[i].twinx()
    smi = ax2.plot(
        ssm_datetime_array,
        SSM_mean,
        'o-',
        color="grey",
        label="Soil moisture inversion")
    ax2.set_ylabel("Soil moisture content (%)",fontdict={"size": 14})
    ax1[i].set_ylim(0, 1)
    ax2.set_ylim(0, 50)
    # hack for now to account for different number of coherence measurements
    if park_name == "kasungu":
        SSM_mean = SSM_mean[1:-1]
    elif park_name == "liwonde":
        SSM_mean = SSM_mean[:-1]
    ax1_cor[i].plot(SSM_mean, coh_mean, 'o')
    best_fit_params = linregress(SSM_mean, coh_mean)
    x = np.linspace(np.min(SSM_mean), np.max(SSM_mean), 100)
    best_fit = best_fit_params.slope*x + best_fit_params.intercept
    ax1_cor[i].plot(
        x,
        best_fit,
        'red',
        label=f"R coeff:{np.round(best_fit_params.rvalue, 3)}")
    ax1_cor[i].set_ylabel("Coherence", fontdict={"size": 14})
    ax1_cor[i].set_title(
        f"{zone.capitalize()} {park_name.capitalize()} National Park")
    ax1_cor[i].legend()
    i += 1
handles = coh_plot + ndvi_plot + smi
labels = [label.get_label() for label in handles]

ax1[1].legend(handles, labels,)  # loc=(0.25, 0.8))
ax1[1].set_xlabel("Date", fontdict={"size": 14})
ax1_cor[1].set_xlabel("Soil Moisture Content (%)", fontdict={"size": 14})

fig.savefig(
    f"/data/tapas/pearse/malawi/Coherence_NDVI_and_SSM_{park_name}.png")
fig_cor.savefig(
    f"/data/tapas/pearse/malawi/SSM_coherence_cor_{park_name}.png")
plt.show()
