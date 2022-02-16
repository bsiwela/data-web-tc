import os
import shutil
import requests
import pandas as pd
import geopandas as gpd
import numpy as np
import shapely.geometry as geom
import nczip2geojson as nc
from io import StringIO
from urllib.parse import urlparse
from bs4 import BeautifulSoup

import xarray as xr
from zipfile import ZipFile

url = 'https://www.kacportal.com/portal/kacs3/arc/mpres_data/postevent/'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']


def listFilesUrl(url, username, password, ext=''):
    page = requests.get(url, auth=(username, password)).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]

list_subfolder = ['taos_swio30s_ofcl_windwater_nc', 'taos_swio30s_ofcl_windwater_shp']

os.chdir('mpres_data/postevent')
dir_root = os.path.abspath(os.getcwd())

for subfolder in list_subfolder:

    os.chdir(dir_root)

    # check if directory exists
    exists = os.path.isdir(subfolder)
    if not exists:
        os.makedirs(subfolder)

    os.chdir(subfolder)

    url_subfolder = f'{url}{subfolder}'

    file_list = listFilesUrl(url_subfolder, username, password, ext='.zip')

    for url_file in file_list:
        filename = os.path.basename(urlparse(url_file).path)

        print(f'Dealing with {filename}')
        r = requests.get(url_file, auth=(username, password))

        # writing the file locally
        if r.status_code == 200:
            with open(filename, 'wb') as out:
                for bits in r.iter_content():
                    out.write(bits)

        print(f'\tCopied local file {filename}')

        # converting it to geojson
        nc.zip2geojson(filename)

        # adding lineString for storm shapefile
        if 'shp' in filename:
            gdf = gpd.read_file(filename)

            # looping through storms
            for storm_id in gdf.ATCFID.unique():
                last_lon = None
                last_lat = None
                if 'TECH' in gdf.columns:
                    for tech in gdf['TECH'].unique():
                        gdf_storm = gdf[(gdf.ATCFID == storm_id) & (gdf.TECH == tech)].sort_values(by=['DTG'])
                        lons = gdf_storm['LON'].values
                        lats = gdf_storm['LAT'].values
                        if tech == 'FCST' and last_lon and last_lat:
                            lons = np.insert(lons, 0, last_lon)
                            lats = np.insert(lats, 0, last_lat)
                        if len(lons) > 1 and len(lats) > 1:
                            lineString = geom.LineString([(lon, lat) for lon, lat in zip(lons, lats)])
                            row = gdf_storm.iloc[-1]
                            if tech == 'TRAK':
                                last_lon = row.LON
                                last_lat = row.LAT
                            row.geometry = lineString
                            gdf = gdf.append(row)


            geojsonFilePath = f'{os.path.splitext(filename)[0]}.geojson'
            gdf.to_file(geojsonFilePath, driver='GeoJSON')

        # removing nc file
        os.remove(filename)



