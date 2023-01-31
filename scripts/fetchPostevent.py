import os
import json
import re
import geopandas as gpd
import numpy as np
import shapely.geometry as geom
import nczip2geojson as nc
from urllib.parse import urlparse
from ncgzip2losses import calculateLosses
from utils import listFilesUrl, fetchUrl

import xarray as xr
from zipfile import ZipFile

url = 'https://www.kacportal.com/portal/kacs3/arc/mpres_data/postevent/'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

with open('index.json', 'r') as f:
    index = json.load(f)
# files_tc_realtime = [os.path.splitext(os.path.split(p)[1])[0] for p in index['tc_realtime']]
# files_tc_realtime_url = [os.path.splitext(os.path.split(url)[1])[0] for url in data[data.columns[-1]].values]
# files_to_remove = [file for file in files_tc_realtime if file not in files_tc_realtime_url]

list_subfolder = ['taos_swio30s_ofcl_windwater_nc', 'taos_swio30s_ofcl_windwater_shp']

root_root = os.path.abspath(os.getcwd())
os.chdir('mpres_data/postevent')
dir_root = os.path.abspath(os.getcwd())

for subfolder, ext in zip(list_subfolder, ['.nc', '.zip']):

    os.chdir(dir_root)

    # check if directory exists
    exists = os.path.isdir(subfolder)
    if not exists:
        os.makedirs(subfolder)

    os.chdir(subfolder)

    url_subfolder = f'{url}{subfolder}'

    file_list = listFilesUrl(url_subfolder, username, password, ext=ext)

    try:
        local_storm_files = [f'SH{re.search("SH(.+?)_", os.path.splitext(os.path.split(file)[1])[0]).group(1)}' for file in index['mpres_data'] if f'postevent/{subfolder}' in file and file.endswith('geojson')]
    except:
        local_storm_files = []  # in the case of shp files

    for url_file in file_list:
        filename = os.path.basename(urlparse(url_file).path)

        common_list = [storm_name for storm_name in local_storm_files if storm_name in filename]  # check if already processed

        if len(common_list) == 0:
            downloaded = fetchUrl(url_file, username, password)

            if downloaded:

                if subfolder == 'taos_swio30s_ofcl_windwater_nc':
                    nc.nc2geojson(filename)
                    # running loss generation
                    calculateLosses(storm_file=filename, exp_file=os.path.join(root_root, 'arc_exposure.gzip'),
                                    adm_file=os.path.join(root_root, 'adm2_full_precision.json'),
                                    mapping_file=os.path.join(root_root, 'mapping.gzip'), split=False,
                                    geojson=False)
                    #os.remove(filename)

                elif subfolder == 'taos_swio30s_ofcl_windwater_shp':
                    filename_shp = f'shp_{filename}'
                    with ZipFile(filename, 'r') as zipObject:
                        zippedFiles = zipObject.namelist()
                        with ZipFile(filename_shp, 'w') as zipObject2write:
                            for zippedFile in zippedFiles:
                                if 'tk_pts' in zippedFile:
                                    zipObject.extract(zippedFile)
                                    zipObject2write.write(zippedFile)
                                    os.remove(zippedFile)

                    gdf = gpd.read_file(filename_shp)

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

                    # removing intermediate shp file
                    os.remove(filename_shp)

                # removing zip and nc files
                os.remove(filename)
