#!/usr/bin/python3
###################################################################
# Simplified python3 based transformation of KAC files into geojsons
# Version 1.1
# Copyright (c) 2021, Bertrand Delvaux
#
# Parameters:
#       --path: path to scan
#       --non_recursive: process the path non-recursively
#       --fields: list of fields to extract from the NetCDF files
#       --n: number of polygons to discretize the raw data
#
# Examples:
#       * nczip2geojson.py
#       * nczip2geojson.py -p data
#       * nczip2geojson.py -p data -nr -f past_peak_wind storm_position -n 200
#

import argparse
import glob, os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import shapely.geometry as geom
import rasterio.features
from zipfile import ZipFile


def processFilesPath(path, recursive, fields, N):

    if path is None:
        path = os.getcwd()

    os.chdir(path)

    for zipfile in glob.glob(f'**/*.zip', recursive=recursive):
        zip2geojson(zipfile, fields, N)

    for ncfile in glob.glob(f'**/*.nc', recursive=recursive):
        nc2geojson(ncfile, fields, N)
        print()


def zip2geojson(zipfile, fields=['storm_position', 'past_rain_total', 'past_peak_wind', 'past_peak_water', 'fcst_peak_wind'], N=100):

    def zip2nc(zipfile):
        with ZipFile(zipfile, 'r') as zipObject:
            zippedFiles = zipObject.namelist()
            for zippedFile in zippedFiles:
                if zippedFile.endswith('.zip') and 'past' in zippedFile:
                    zipObject.extract(zippedFile, os.path.split(zipfile)[0])
                    zippedFile = f'{os.path.split(zipfile)[0]}/{zippedFile}'
                    zip2nc(zippedFile)
                    os.remove(zippedFile)
                elif zippedFile.endswith('.nc') and 'past' in zippedFile: # only keep past and not fcst
                    zipObject.extract(zippedFile, os.path.split(zipfile)[0])
                    zippedFile = f'{os.path.split(zipfile)[0]}/{zippedFile}'
                    nc2geojson(zippedFile, fields, N)
                    os.remove(zippedFile)

    try: # if it is a shapefile .zip
        gdf = gpd.read_file(zipfile)
        gdf.to_file(f'{os.path.splitext(zipfile)[0]}.geojson', driver='GeoJSON')
    except: # if it is another .zip file
        zip2nc(zipfile)
        return # if the zip file is not an actual shapefile


def nc2geojson(ncfile, fields=['storm_position', 'past_rain_total', 'past_peak_wind', 'past_peak_water', 'fcst_peak_wind'], N=100):

    ds = xr.open_dataset(ncfile, decode_times=False)

    storm_dict = {'name': ds.storm_name, 'year': ds.atcfid[-4:], 'id': ds.atcfid}

    allowed_fields = ds.variables.keys()

    if 'latitude' and 'longitude' in allowed_fields:
        lats = ds['latitude'].values
        lons = ds['longitude'].values
    else:
        return

    geometries = []
    val1_series = []
    val2_series = []
    text_series = []
    field_series = []

    for field in fields:

        if field in allowed_fields:
            data_array = ds[field].values # array of interest

            if field == 'storm_position':
                # trajectory
                linestring = geom.LineString([(lon, lat) for lon, lat in zip(data_array[0],data_array[1])])
                geometries.append(linestring)
                val1_series.append(0)
                val2_series.append(0)
                text_series.append('')
                field_series.append(field)
                # points
                points = [geom.Point([(lon, lat)]) for lon, lat in zip(data_array[0],data_array[1])]
                [geometries.append(point) for point in points]
                [val1_series.append(val1) for val1 in data_array[2]]
                [val2_series.append(val2) for val2 in data_array[3]]
                [text_series.append(str(text)) for text in ds['storm_posdtg'].data]
                [field_series.append(field) for point in points]
                continue

            # range
            max_value = np.max(data_array)
            min_value = np.min(data_array[data_array > 0.0])
            min_value += 0.2 * (max_value - min_value) # previously set @ 0.01...  /!\ the "noisy" empty value is around e-15. It is therefore decided to clip it from 15% of max value
            range_values = np.linspace(min_value, max_value, N)

            for n in range(N-1):
                # masked array
                mask = np.logical_and(data_array > range_values[n], data_array <= range_values[n+1]).astype(np.uint8)
                shapes = rasterio.features.shapes(mask, connectivity=8)

                polygon = [
                    geom.Polygon([(lons[int(lon)], lats[int(lat)]) for lon, lat in shape[0]['coordinates'][0]], holes=[[(lons[int(lon)], lats[int(lat)]) for lon, lat in shape[0]['coordinates'][1]]])
                    if shape[1] == 1 and len(shape[0]['coordinates']) > 1
                    else
                    geom.Polygon([(lons[int(lon)], lats[int(lat)]) for lon, lat in shape[0]['coordinates'][0]], holes=None)
                    if shape[1] == 1 and len(shape[0]['coordinates']) == 1
                    else
                    None
                    for shape in shapes
                ]

                #####################

                polygon_rnd = []

                for poly in polygon:
                    if poly:
                        geojson = geom.mapping(poly)
                        if len(geojson['coordinates']) == 1:
                            geojson['coordinates'] = np.round(np.array(geojson['coordinates']), 4)
                        else:
                            geojson_list = []
                            for p in geojson['coordinates']:
                                p = np.round(np.array(p), 4)
                                geojson_list.append(p)
                            geojson['coordinates'] = tuple(geojson_list)
                        poly = geom.shape(geojson)
                    polygon_rnd.append(poly)

                polygon = polygon_rnd  # use the rounded version

                [geometries.append(poly) for poly in polygon if poly is not None]
                [val1_series.append((range_values[n] + range_values[n+1]) / 2) for poly in polygon if poly is not None]
                [val2_series.append(n) for poly in polygon if poly is not None]
                [text_series.append('') for poly in polygon if poly is not None]
                [field_series.append(field) for poly in polygon if poly is not None]

        else:
            continue


    df = pd.DataFrame({
        'val1': val1_series,
        'val2': val2_series,
        'text': text_series,
        'field': field_series
    })
    gdf = gpd.GeoDataFrame(df,geometry=geometries)
    geojsonFilePath = f'{os.path.splitext(ncfile)[0]}.geojson'
    gdf.to_file(geojsonFilePath, driver='GeoJSON')

    # compacting geojson even further, by removing blank spaces
    with open(geojsonFilePath, 'r') as f:
        data = json.load(f)

    with open(geojsonFilePath, 'w') as f:
        data['storm'] = storm_dict  # adding storm information
        data['bbox'] = [np.round(gdf.total_bounds[i], decimals=4) for i in range(4)]
        f.write(json.dumps(data, separators=(',', ':')))




if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-p', '--path', type=str, help='Path to folder to scan', default=None, dest='path')
    parser.add_argument('-nr', '--non_recursive', action='store_true', help='Recursive process', default=False, dest='non_recursive')
    parser.add_argument('-f', '--fields', help='List of fields to extract from NetCDF', nargs='+', default=['storm_position', 'past_rain_total', 'past_peak_wind', 'past_peak_water', 'fcst_peak_wind'], dest='fields')
    parser.add_argument('-n', help='Number of Polygons to discretize the raw data', default=100, dest='N')
    args = parser.parse_args()

    processFilesPath(path=args.path, recursive=not(args.non_recursive), fields=args.fields, N=args.N)
