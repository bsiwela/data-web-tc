import os  # import os library for interacting with the operating system
import geopandas as gpd  # import geopandas for working with geographic data
import numpy as np  # import numpy for working with arrays
import shapely.geometry as geom  # import shapely.geometry for creating geometric objects
import nczip2geojson as nc  # import nczip2geojson for converting NetCDF files to GeoJSON
from urllib.parse import urlparse  # import urlparse from urllib.parse for parsing URLs
from utils import listFilesUrl, fetchUrl, get_current_utc_timestamp  # import functions from utils module

# define URL and retrieve username and password from environment variables
url = 'https://www.kacportal.com/portal/kacs3/arc/mpres_data/'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

# list all files in URL with extension .zip and set working directory to mpres_data
file_list = listFilesUrl(url, username, password, ext='.zip')
os.chdir('mpres_data')

# print current UTC timestamp
utc_timestamp = get_current_utc_timestamp()
print(f'\033[32mTIMESTAMP: {utc_timestamp}\n\033[0m')

# loop through each file in the list
for url_file in file_list:
    filename = os.path.basename(urlparse(url_file).path)  # get the filename from the URL
    downloaded = fetchUrl(url_file, username, password)  # download the file

    if downloaded:  # if the file was successfully downloaded
        # convert the file to GeoJSON format
        print(f'\033[32m\tConverting {filename} to geojson\033[0m')
        nc.zip2geojson(filename)

        # add lineString for storm shapefile
        if 'storm' in filename:  # if the file contains storm data
            gdf = gpd.read_file(filename)  # read in the file as a geopandas dataframe

            # loop through each storm
            for storm_id in gdf.ATCFID.unique():
                last_lon = None
                last_lat = None

                # loop through each technology used to track the storm
                for tech in gdf.TECH.unique():
                    gdf_storm = gdf[(gdf.ATCFID == storm_id) & (gdf.TECH == tech)].sort_values(by=['DTG'])
                    lons = gdf_storm['LON'].values
                    lats = gdf_storm['LAT'].values

                    if tech == 'FCST' and last_lon and last_lat:  # if the technology is 'FCST' and last_lon and last_lat are not None
                        lons = np.insert(lons, 0, last_lon)  # add the last longitude to the beginning of the list of longitudes
                        lats = np.insert(lats, 0, last_lat)  # add the last latitude to the beginning of the list of latitudes

                    if len(lons) > 1 and len(lats) > 1:  # if there is more than one longitude and latitude
                        lineString = geom.LineString([(lon, lat) for lon, lat in zip(lons, lats)])  # create a LineString object
                        row = gdf_storm.iloc[-1]  # get the last row of the current storm
                        if tech == 'TRAK':  # if the technology is 'TRAK'
                            last_lon = row.LON  # set last_lon to the current longitude
                            last_lat = row.LAT
                            
                            
            geojsonFilePath = f'{os.path.splitext(filename)[0]}.geojson'
            gdf.to_file(geojsonFilePath, driver='GeoJSON')

        # removing nc file
        os.remove(filename)

        downloaded = fetchUrl(f'{url_file}.sha256', username, password)
