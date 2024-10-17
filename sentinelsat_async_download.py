#!/usr/env python
"""
Find and download Sentinel-1 SLC data using Sentinel Hub Catalog API 
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Catalog.html

I couldn't actually get this to work.
"""

import argparse
import asyncio
import configparser
import sys
import time

from datetime import date
from multiprocessing import Pool
from pathlib import Path

import aiohttp
import requests



def refresh_session(refresh_token):

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': f'{refresh_token}',
        'client_id': 'cdse-public',
    }

    response = requests.post('https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token', data=data).json()
    print(f"Refresh response: {response}")
    token =  response['access_token']
    refresh_token = response['refresh_token']
    return token, refresh_token




async def download_SLC(dl_url, product_name, out_dir, token, refresh_token):
    dl_path = out_dir/Path(product_name.split(".SAFE")[0]+".zip")
    if dl_path.exists():
        print(f"File {dl_path} already exists, skipping")
        return
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession(headers=headers) as session:

        async with session.get(dl_url) as response:
            print(response)
            # if response.status == 429:
            #     print("Too many requests, exiting")
            #     response = session.get(dl_url, headers=headers, stream=True)
            #     time.sleep(60)
            # elif response.status == 404:
            #     print(f"File {product_name} not found, skipping")
            #     return
            # elif response.status != 200:
            #     print("Unknown error, exiting")
            #     return
            #     token,  refresh_token = refresh_session(refresh_token)
            #     headers = {"Authorization": f"Bearer {token}"}
            #     session.headers.update(headers)
            #     response = session.get(dl_url, headers=headers, stream=True)

        total_length = response.headers['Content-Length']

        dl = 0
        total_length = int(total_length)
        with open(dl_path, "wb") as file:
            async for chunk in response.content.iter_chunked(chunk_size=8192):
                dl += len(chunk)
                percentage = (dl / total_length) * 100
                if chunk:
                    file.write(chunk)
                done = int(50 * dl / total_length)
                sys.stdout.write("\r[%s%s] .2f%" % ('=' * done, ' ' * (50-done), percentage) )    
                sys.stdout.flush()


parser = argparse.ArgumentParser(prog="sentinelsat_download.py", 
        description="Script to download Sentinel-1 SLC data",
        )
parser.add_argument('-d', '--date_range', nargs=2,
        help='start and end date, must be of form YYYY-MM-DD')

parser.add_argument('-b', '--bbox', nargs=4,
        help='bounding box for area of interest. Order should be\
        South North West East')

parser.add_argument('-o', '--out_dir',
        help='name of output directory where SLCs will be downloaded',
        metavar='DIR')

args = parser.parse_args()
date_range = args.date_range
bbox = args.bbox
out_dir = Path(args.out_dir)

"""
Below is adapted from SentinelHub Authentication example
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
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
url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=" 
date_filter = f"ContentDate/Start gt {date_range[0]}T00:00:00.000Z and ContentDate/Start lt {date_range[1]}T00:00:00.000Z"
collection_filter = "Collection/Name eq 'SENTINEL-1' and contains(Name,'SLC')"
bbox_filter = f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({bbox[2]} {bbox[1]},{bbox[3]} {bbox[1]},{bbox[3]} {bbox[0]},{bbox[2]} {bbox[0]},{bbox[2]} {bbox[1]}))')"
order_by = "&$orderby=ContentDate/Start"
request_url = url + date_filter + " and " + collection_filter + " and " + bbox_filter + order_by

data_response = requests.get(request_url).json()
dl_urls = []
product_names = []

print("Query SLCs")
print("Files to download:")
while data_response.get('@odata.nextLink') is not None:
    # do get data stuff
    for product in data_response['value']:
        product_id = product['Id']
        product_name = product['Name']
        print(product_name)
        dl_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
        dl_urls.append(dl_url)
        product_names.append(product_name)
    data_response = requests.get(data_response['@odata.nextLink']).json()

#Catch the last request
for product in data_response['value']:
    product_id = product['Id']
    product_name = product['Name']
    print(product_name)
    dl_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"    
    dl_urls.append(dl_url)
    product_names.append(product_name)


dl_paths = {dl_url: out_dir/Path(product_name.split(".SAFE")[0]+".zip") 
            for dl_url,product_name in zip(dl_urls, product_names)}
print(f"Total number of files to download: {len(dl_urls)}")
print(f"downloading {dl_url}")
asyncio.run(download_SLC(dl_url, product_name, out_dir, TOKEN, REFRESH_TOKEN))
"""
def dl_parallel(dl_url, product_name):
    print(f"Downloading {product_name}")
    download_SLC(dl_url, product_name, out_dir, TOKEN, REFRESH_TOKEN)

with Pool(processes=4) as pool:
    pool.starmap(dl_parallel, zip(dl_urls, product_names))

#one at a time otherwise 429 response from server :(
for dl_url, product_name in zip(dl_urls, product_names):
    response = session.get(dl_url, headers=headers, stream=True)
    print(response)
    print(f"Downloading {product_name}")
    download_SLC(session, dl_url, product_name, out_dir)
    time.sleep(12)

# trying and failing to speed up downloads
headers = {"Authorization": f"Bearer {TOKEN}"}
responses = {}
for dl_url in dl_urls[:7]:
    dl_path = dl_paths[dl_url]
    if dl_path.exists():
        print(f"File {dl_path} already exists, skipping")
        continue
    resp = requests.get(dl_url, headers=headers, stream=True)
    if resp.status_code == 429:
        wait_attempt = 0 
        while resp.status_code == 429:
            print(f"Response for {dl_url} too many requests")
            wait_time = 60 + 10*wait_attempt
            print(f"Waiting {wait_time} seconds")
            time.sleep(wait_time)
            resp = requests.get(dl_url, headers=headers, stream=True)
            wait_attempt += 1
    elif resp.status_code == 401:
        print(f"Response for {dl_url} unauthorised")
        print("Refreshing token")
        token, refresh_token = refresh_session(refresh_token)
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(dl_url, headers=headers, stream=True)
    print(f"Response for {dl_url} ok")
    responses[dl_url] = resp

streams = {dl_url: responses[dl_url].iter_content(chunk_size=8192) for dl_url in responses.keys()}
dl_paths = {key: dl_paths[key] for key in responses.keys()}
def dl_parallel(stream, dl_path):
    print(f"Downloading {dl_path}")
    
    if dl_path.exists():
        print(f"File {dl_path} already exists, skipping")
        return
    #total_length = response.headers.get('content-length')

    #dl = 0
    #total_length = int(total_length)
    with open(dl_path, "wb") as file:
        for chunk in stream:
            #dl += len(chunk)
            if chunk:
                file.write(chunk)
            #done = int(50 * dl / total_length)
            #sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )    
            #sys.stdout.flush()


with Pool() as pool:
    pool.starmap(dl_parallel, zip(streams.values(), dl_paths.values()))
"""
