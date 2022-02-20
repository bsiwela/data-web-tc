import os
import geopandas as gpd
import numpy as np
import shapely.geometry as geom
import nczip2geojson as nc
from urllib.parse import urlparse
from utils import listFilesUrl, fetchUrl

url = 'https://www.kacportal.com/portal/kacs3/arc/mpres_data/'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']



file_list = listFilesUrl(url, username, password, ext='.zip')

os.chdir('mpres_data')

for url_file in file_list:
    filename = os.path.basename(urlparse(url_file).path)
    downloaded = fetchUrl(url_file, username, password)

    if downloaded:
        # converting it to geojson
        nc.zip2geojson(filename)

        # adding lineString for storm shapefile
        if 'storm' in filename:
            gdf = gpd.read_file(filename)

            # looping through storms
            for storm_id in gdf.ATCFID.unique():
                last_lon = None
                last_lat = None
                for tech in gdf.TECH.unique():
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

        downloaded = fetchUrl(f'{url_file}.sha256', username, password)



