import argparse
import os
import json
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
from compactGeoJSON import densify

url = 'https://www.kacportal.com/portal/kacs3/arc/arc_proj21/jtwc_history/'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']


def listFilesUrl(url, username, password, ext=''):
    page = requests.get(url, auth=(username, password)).text
    soup = BeautifulSoup(page, 'html.parser')
    return [url + '/' + node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]


def fetchHistoryJTWC(url, adm_file, mapping_file, geojson=False):

    dir_list = listFilesUrl(url, username, password, ext='/')[1:]
    adm_df = gpd.read_file(adm_file)
    mapping = pd.read_parquet(mapping_file)

    for url_dir in dir_list:
        file_list_zip = listFilesUrl(url_dir, username, password, ext='.zip')
        file_list_nc = listFilesUrl(url_dir, username, password, ext='.nc')

        # check if directory exists
        year_dir = os.path.join('jtwc_history',os.path.basename(os.path.normpath(url_dir)))
        exists = os.path.isdir(year_dir)
        if not exists:
            os.makedirs(year_dir)

        os.chdir(year_dir)

        for url_file in file_list_zip:

            filename = os.path.basename(urlparse(url_file).path)
            print(f'Dealing with {filename}')
            r = requests.get(url_file, auth=(username, password))

            # writing the file locally
            if r.status_code == 200:
                with open(filename, 'wb') as out:
                    for bits in r.iter_content():
                        out.write(bits)

            with nc.ZipFile(filename, 'r') as zipObject:
                zippedFiles = zipObject.namelist()
                for zippedFile in zippedFiles:
                    if zippedFile.endswith('.csv'):
                        zipObject.extract(zippedFile, '')  # f'{os.path.splitext(os.path.basename(filename))[0]}.csv'

                        df = pd.read_csv(zippedFile)
                        if not(df.empty):
                            df = df.merge(df['exposure_id'].apply(lambda s: pd.Series(
                                {f'adm{i}_code': int(mapping.loc[s, f'adm{i}_code']) for i in range(3)})), left_index=True,
                                     right_index=True)
                            df_groupby = df.groupby(by=['adm0_code','adm1_code','adm2_code'], as_index=False).sum()
                            df_merge = pd.merge(df_groupby, adm_df.dissolve(by='ADM2_CODE', as_index=False), left_on='adm2_code', right_on='ADM2_CODE')

                            cols2keep = ['ADM0_NAME','ADM1_NAME','ADM2_NAME','ADM0_CODE','ADM1_CODE','ADM2_CODE','population','tloss','geometry']
                            df_merge = df_merge[cols2keep]
                            df_merge.rename(columns={'tloss': 'loss', 'ADM0_NAME': 'adm0_name', 'ADM1_NAME': 'adm1_name', 'ADM2_NAME': 'adm2_name', 'ADM0_CODE': 'adm0_code', 'ADM1_CODE': 'adm1_code', 'ADM2_CODE': 'adm2_code'}, inplace=True)

                            if geojson:
                                df_final = gpd.GeoDataFrame(df_merge)
                            else:
                                df_final = df_merge.drop(columns='geometry')

                            jsonFileBase = f'{os.path.splitext(os.path.basename(filename))[0]}_losses_adm'

                            for i in range(3):
                                jsonFile = f'{jsonFileBase}{i}.{"geo" if geojson else ""}json'
                                adm_group_list = [f'adm{j}_name' for j in range(i + 1)]
                                if geojson:
                                    gdf_adm = df_final.dissolve(by=adm_group_list, aggfunc='sum', as_index=False)
                                    gdf_adm.to_file(jsonFile, driver='GeoJSON')
                                    densify(jsonFile)
                                else:
                                    df_final.groupby(adm_group_list, as_index=False).sum().to_json(jsonFile, orient='records')

                        os.remove(filename)
                        os.remove(zippedFile)

        # for url_file in file_list_nc:
        #
        #     filename = os.path.basename(urlparse(url_file).path)
        #     print(f'Dealing with {filename} ... ', end='')
        #     r = requests.get(url_file, auth=(username, password))
        #
        #     # writing the file locally
        #     if r.status_code == 200:
        #         with open(filename, 'wb') as out:
        #             for bits in r.iter_content():
        #                 out.write(bits)
        #     print('received')
        #
        #     # converting it to geojson
        #     nc.nc2geojson(filename, N=50)
        #
        #     # adding lineString for storm shapefile
        #     if 'storm' in filename:
        #         gdf = gpd.read_file(filename)
        #
        #         # looping through storms
        #         for storm_id in gdf.ATCFID.unique():
        #             last_lon = None
        #             last_lat = None
        #             for tech in gdf.TECH.unique():
        #                 gdf_storm = gdf[(gdf.ATCFID == storm_id) & (gdf.TECH == tech)].sort_values(by=['DTG'])
        #                 lons = gdf_storm['LON'].values
        #                 lats = gdf_storm['LAT'].values
        #                 if tech == 'FCST' and last_lon and last_lat:
        #                     lons = np.insert(lons, 0, last_lon)
        #                     lats = np.insert(lats, 0, last_lat)
        #                 if len(lons) > 1 and len(lats) > 1:
        #                     lineString = geom.LineString([(lon, lat) for lon, lat in zip(lons, lats)])
        #                     row = gdf_storm.iloc[-1]
        #                     if tech == 'TRAK':
        #                         last_lon = row.LON
        #                         last_lat = row.LAT
        #                     row.geometry = lineString
        #                     gdf = gdf.append(row)
        #
        #
        #         geojsonFilePath = f'{os.path.splitext(filename)[0]}.geojson'
        #         gdf.to_file(geojsonFilePath, driver='GeoJSON')
        #
        #     # removing nc file
        #     os.remove(filename)




if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-u', '--url', type=str, help='Url to jtwc history', default='https://www.kacportal.com/portal/kacs3/arc/arc_proj21/jtwc_history/', dest='url')
    parser.add_argument('-adm', '--admfile', type=str, help='Path to JSON adm2 file', default='adm2_full_precision.json', dest='adm_file')
    parser.add_argument('-m', '--mappingfile', type=str, help='Path to mapping file', default='mapping.gzip', dest='mapping_file')
    parser.add_argument('-g', '--geojson', action='store_true', help='geojson', default=False, dest='geojson')
    args = parser.parse_args()

    fetchHistoryJTWC(url=args.url, adm_file=args.adm_file, mapping_file=args.mapping_file, geojson=args.geojson)


