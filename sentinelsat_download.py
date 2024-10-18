#!/usr/env python
"""
Find and download Sentinel-1 SLC data using Sentinel Hub Catalog API
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Catalog.html
"""

import argparse
import configparser
import sys
import time

from multiprocessing import Pool
from pathlib import Path

import requests


def refresh_session(refresh_token):
    """
    Session for SLC downlaods is something like 20 minutes so
    we need to refresh every now and again.
    It's entirely possible there's a way of doing this better.
    """
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': f'{refresh_token}',
        'client_id': 'cdse-public',
    }

    response = requests.post(
        'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
        data=data).json()
    # print(f"Refresh response: {response}")
    token = response['access_token']
    refresh_token = response['refresh_token']
    return token, refresh_token


def download_SLC(dl_url, product_name, out_dir):
    global TOKEN, REFRESH_TOKEN
    dl_path = out_dir/Path(product_name.split(".SAFE")[0]+".zip")
    if dl_path.exists():
        print(f"File {dl_path} already exists, skipping")
        return
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with requests.Session() as session:
        session.headers.update(headers)
        response = session.get(dl_url, headers=headers, stream=True)
        print(response)
        while response.status_code == 429:
            print("Too many requests, sleeping for 60 seconds")
            response = session.get(dl_url, headers=headers, stream=True)
            time.sleep(60)
        if response.status_code == 404:
            print(f"File {product_name} not found, skipping")
            return
        elif response.status_code == 401:
            print("refreshing session")
            TOKEN, REFRESH_TOKEN = refresh_session(REFRESH_TOKEN)
            headers = {"Authorization": f"Bearer {TOKEN}"}
            session.headers.update(headers)
            response = session.get(dl_url, headers=headers, stream=True)

        total_length = response.headers.get('content-length')

        dl = 0
        total_length = int(total_length)
        with open(dl_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                dl += len(chunk)
                if chunk:
                    file.write(chunk)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)))
                sys.stdout.flush()


parser = argparse.ArgumentParser(
    prog="sentinelsat_download.py",
    description="Script to download Sentinel-1 SLC data",
    )
parser.add_argument(
    '-d',
    '--date_range',
    nargs=2,
    help='start and end date, must be of form YYYY-MM-DD')

parser.add_argument(
    '-b',
    '--bbox',
    nargs=4,
    help='bounding box for area of interest. Order should be \
        South North West East')

parser.add_argument(
    '-o',
    '--out_dir',
    help='name of output directory where SLCs will be downloaded',
    metavar='DIR')

args = parser.parse_args()
date_range = args.date_range
bbox = args.bbox
out_dir = Path(args.out_dir)

"""
Below is adapted from SentinelHub Authentication example
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
First step is to set up authorisation.
"""
# Read the configuration file
config = configparser.ConfigParser()
config.read('/home/pearse/.copernicus.config')

# Get username and password from the configuration file
username = config['Credentials']['username']
password = config['Credentials']['password']

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
}

data = 'client_id=cdse-public&username='+username+'&password='+password+'&grant_type=password'

print("Generating Access Token")
access_response = requests.post(
    'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    headers=headers,
    data=data,
)
tokens = access_response.json()
TOKEN = tokens['access_token']
REFRESH_TOKEN = tokens['refresh_token']

# create search url from input dates, bounding box, etc.
url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter="
date_filter = f"ContentDate/Start gt {date_range[0]}T00:00:00.000Z and ContentDate/Start lt {date_range[1]}T00:00:00.000Z"
# attrib_filter = "Attributes/OData.CSC.IntegerAttribute/any(att:att/Name eq 'Frame' and att/OData.CSC.IntegerAttribute/Value eq 640)"
collection_filter = "Collection/Name eq 'SENTINEL-1' and contains(Name,'SLC')"
bbox_filter = f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({bbox[2]} {bbox[1]},{bbox[3]} {bbox[1]},{bbox[3]} {bbox[0]},{bbox[2]} {bbox[0]},{bbox[2]} {bbox[1]}))')"
order_by = "&$orderby=ContentDate/Start"
request_url = url + date_filter + " and " + collection_filter + " and " + bbox_filter + order_by

data_response = requests.get(request_url).json()
dl_urls = []
product_names = []

print("Query SLCs")
print("Files to download:")
# make sure to get all responses from request url, not just first 20
while data_response.get('@odata.nextLink') is not None:
    # find product id and name for files to download
    for product in data_response['value']:
        product_id = product['Id']
        product_name = product['Name']
        print(product_name)
        dl_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        dl_urls.append(dl_url)
        product_names.append(product_name)
    data_response = requests.get(data_response['@odata.nextLink']).json()

"""
Catch the last request.
There's probably a better way than copy/pasting the above but here we are :/
"""
for product in data_response['value']:
    product_id = product['Id']
    product_name = product['Name']
    print(product_name)
    dl_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
    dl_urls.append(dl_url)
    product_names.append(product_name)

# create a dictionary with the file name and download urls.
dl_paths = {dl_url: out_dir/Path(product_name.split(".SAFE")[0]+".zip")
            for dl_url, product_name in zip(dl_urls, product_names)}
print(f"Total number of files to download: {len(dl_urls)}")


def dl_parallel(dl_url, product_name):
    print(f"Downloading {product_name}")
    download_SLC(dl_url, product_name, out_dir)


with Pool(processes=4) as pool:
    pool.starmap(dl_parallel, zip(dl_urls, product_names))
