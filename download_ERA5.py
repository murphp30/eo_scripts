#!/usr/bin/env python

import datetime
import os

import pandas as pd
import numpy as np
import geopandas as gpd
import xarray as xr

from multiprocessing import Pool

from insar4sm.download_ERA5_land import retrieve_ERA5_land_data

def Get_ERA5_data(ERA5_variables:list,
                 start_datetime:datetime.datetime,
                 end_datetime:datetime.datetime,
                 AOI_file:str,
                ERA5_dir:str,) -> pd.DataFrame:
    """Downloads ERA5 datasets between two given dates.
    Args:
        ERA5_variables (list): list of ERA5 variables e.g. ['total_precipitation',]
        start_datetime (datetime.datetime): Starting Datetime e.g.  datetime.datetime(2021, 12, 2, 0, 0)
        end_datetime (datetime.datetime): Ending Datetime e.g.  datetime.datetime(2022, 2, 8, 0, 0)
        AOI_file (str): vector polygon file of the AOI.
        ERA5_dir (str): Path that ERA5 data will be saved.
    Returns:
        ERA5_sm_filename (str): the filename of the merged ERA5-land information
    """

    lon_min, lat_min,  lon_max, lat_max = np.squeeze(gpd.read_file(AOI_file).bounds.values)
    half_res = 0.1
    bbox_cdsapi =  [np.ceil(lat_max*10)/10+half_res,
                    np.floor(lon_min*10)/10-half_res,
                    np.floor(lat_min*10)/10-half_res,
                    np.ceil(lon_max*10)/10+half_res,]

    # change end_datetime in case ERA5 are not yet available
    if datetime.datetime.now()-end_datetime < datetime.timedelta(days=5):
        end_datetime = datetime.datetime.now() - datetime.timedelta(days=5)

    ERA5_sm_filename = os.path.join(ERA5_dir,'ERA5_{Start_time}_{End_time}_{bbox_cdsapi}.nc'.format(Start_time=start_datetime.strftime("%Y%m%dT%H%M%S"),
                                                                                            End_time=end_datetime.strftime("%Y%m%dT%H%M%S"),
                                                                                            bbox_cdsapi='_'.join(str(round(e,3)) for e in bbox_cdsapi)))
    
    if not os.path.exists(ERA5_sm_filename):
        
        Downloaded_datasets = []
        
        df = pd.date_range(start=start_datetime, end=end_datetime, freq='h').to_frame(name='Datetime')
        
        df['year'] = df['Datetime'].dt.year
        df["year_str"] = ['{:02d}'.format(year) for year in df['year']]
        
        df['month'] = df['Datetime'].dt.month
        df["month_str"] = ['{:02d}'.format(month) for month in df['month']]
        
        df['day'] = df['Datetime'].dt.day
        df["day_str"] = ['{:02d}'.format(day) for day in df['day']]

        df['hour'] = df['Datetime'].dt.hour
        df["hour_str"] = ['{:02d}'.format(hour) for hour in df['hour']]
        
        
        # for the last datetime we do a single request
        
        last_day_df = df.sort_values(by = 'Datetime').iloc[-1]
        last_day_times = np.arange(last_day_df.hour+1)
        last_day_times_str = ['{:02d}'.format(last_day_time) for last_day_time in last_day_times]
        #print("Downloading precipitation for the flood date: {}".format(last_day_df.Datetime.strftime("%Y-%m-%d")))

        # last_day_dataset = retrieve_ERA5_land_data(ERA5_variables = ERA5_variables,
        #                                             year_str = last_day_df.year_str,
        #                                             month_str = last_day_df.month_str,
        #                                             days_list = last_day_df.day_str,
        #                                             time_list = last_day_times_str,
        #                                             bbox_cdsapi = bbox_cdsapi,
        #                                             export_filename = os.path.join(ERA5_dir,'Last_day.nc'))

        # For each month we do a request
        df2 = df.truncate(after=datetime.datetime(last_day_df.year, last_day_df.month, last_day_df.day, 0)).iloc[:-1]
        year_requests = [last_day_df.year_str]
        month_requests = [last_day_df.month_str]
        days_requests = [last_day_df.day_str]
        hours_requests = [last_day_times_str]
        export_filenames = [os.path.join(ERA5_dir,'Last_day.nc')]
        for year in np.unique(df2["year_str"].values):
            df_year = df2[df2['year_str']==year]
            year_request = year

            for month in np.unique(df_year["month_str"].values):
                month_request = month
                df_month = df_year[df_year['month_str']==month]
                days_request = np.unique(df_month['day_str']).tolist()
                hours_request = np.unique(df_month['hour_str']).tolist()
                export_filename = os.path.join(ERA5_dir,'{}_{}_ssm.nc'.format(month_request,year_request))
                
                year_requests.append(year_request)
                month_requests.append(month_request)
                days_requests.append(days_request)
                hours_requests.append(hours_request)
                export_filenames.append(export_filename)
                # monthly_dataset = retrieve_ERA5_land_data(ERA5_variables = ERA5_variables,
                #                                       year_str = year_request,
                #                                       month_str = month_request,
                #                                       days_list = days_request,
                #                                       time_list = hours_request,
                #                                       bbox_cdsapi = bbox_cdsapi,
                #                                       export_filename = export_filename)
                
                # Downloaded_datasets.append(monthly_dataset)


    return bbox_cdsapi, year_requests, month_requests, days_requests, hours_requests, export_filenames

def retrieve_ERA5_parallel(year_request, month_request, days_request, hours_request, export_filename):
    print(f"Downloading {year_request}, {month_request}")
    monthly_dataset = retrieve_ERA5_land_data(ERA5_variables = ERA5_variables,
                                                year_str = year_request,
                                                month_str = month_request,
                                                days_list = days_request,
                                                time_list = hours_request,
                                                bbox_cdsapi = bbox_cdsapi,
                                                export_filename = export_filename)
    return monthly_dataset

if __name__ == "__main__":
    print("It's STARTING")
    ERA5_variables = ['total_precipitation','skin_temperature','volumetric_soil_water_layer_1']
    start_date = '20230101' # format is YYYYMMDD
    end_date = '20240531' # format is YYYYMMDD
    start_datetime = datetime.datetime.strptime('{}T000000'.format(start_date), '%Y%m%dT%H%M%S')
    end_datetime =  datetime.datetime.strptime('{}T230000'.format(end_date), '%Y%m%dT%H%M%S')
    AOI_file = "/data/tapas/pearse/malawi/sentinel1/aoi/southern_malawi_aoi.geojson"
    ERA5_dir = "/data/tapas/pearse/malawi/ERA5/liwonde/"
    (bbox_cdsapi,
     year_requests,
     month_requests,
     days_requests,
     hours_requests,
     export_filenames) = Get_ERA5_data(ERA5_variables,
                                       start_datetime,
                                       end_datetime,
                                       AOI_file,
                                       ERA5_dir)

    print("starting pool")
    with Pool() as pool:
        Downloaded_datasets = pool.starmap(retrieve_ERA5_parallel,
                                            zip(year_requests,
                                                month_requests,
                                                days_requests,
                                                hours_requests,
                                                export_filenames))
    # Downloaded_datasets.append(last_day_dataset)
    ds = xr.open_mfdataset(Downloaded_datasets, combine='by_coords', engine="netcdf4")
    ERA5_sm_filename = ERA5_dir+"liwond_"+start_date+"_"+end_date+".nc"
    ds.to_netcdf(ERA5_sm_filename) # Export netcdf file