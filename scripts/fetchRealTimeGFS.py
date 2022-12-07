import os, glob
import json
import requests
import datetime as dt
import xarray as xr
import numpy as np
import pandas as pd
import geopandas as gpd
import shapely.geometry as geom
import rasterio.features
from scipy import interpolate
from compactGeoJSON import densify



def find_nearest_idx(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx

def getGFSurl(date, hour, time, sp_res=0.25, t_sep=1.00, leftlon=-13.36, rightlon=99.14, toplat=3.79, bottomlat=-41.3):

    sp_res = f'{sp_res:.2f}'.replace('.','p')

    url_gfs = f'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_{sp_res}_1hr.pl?file=gfs.t{hour:02d}z.pgrb2.{sp_res}.f{time:03d}&lev_surface=on&var_APCP=on&leftlon={leftlon+180}&rightlon={rightlon+180}&toplat={toplat}&bottomlat={bottomlat}&dir=%2Fgfs.{date}%2F{hour:02d}%2Fatmos'

    file_tmp = file_tmp = f'{date}.gfs.t{hour:02d}z.pgrb2.{sp_res}.f{time:03d}'

    return url_gfs, file_tmp

def grib2geojson(url_gfs_list, file_tmp_list, start, end, field='tp', factor=4, N=50, decimals=2, folder='gfs_realtime', leftlon=-13.36, rightlon=99.14, toplat=3.79, bottomlat=-41.3):
    print(f'GFS data from +{start:03d}h to +{end:03d}h')

    for url_gfs, file_tmp in zip(url_gfs_list, file_tmp_list):
        response = requests.get(url_gfs)
        if response.status_code != 200 or len(response.content) == 0:
            print(f'\tSomething went wrong in getting the data for {file_tmp}')
            continue
        file_tmp = f'{folder}/{file_tmp}'
        open(file_tmp, "wb").write(response.content)
        ds = xr.open_dataset(file_tmp, engine='cfgrib')

        allowed_fields = ds.variables.keys()

        if 'latitude' and 'longitude' in allowed_fields:
            lats = ds['latitude'].values
            lons = ds['longitude'].values - 180
        else:
            return

        if field in allowed_fields:
            data_array_tmp = ds[field].values # array of interest
            lon_start = find_nearest_idx(lons, leftlon)
            lon_end = find_nearest_idx(lons, rightlon)
            lat_end = find_nearest_idx(lats, bottomlat)
            lat_start = find_nearest_idx(lats, toplat)
            lats = np.linspace(ds['latitude'].values[lat_start], ds['latitude'].values[lat_end], (lat_end-lat_start) * factor + 1)
            lons = np.linspace((ds['longitude'].values - 180)[lon_start], (ds['longitude'].values - 180)[lon_end], (lon_end-lon_start) * factor + 1)
            data_array_tmp = data_array_tmp[lat_start:lat_end, lon_start:lon_end]
            #lats = np.linspace(ds['latitude'].values[0], ds['latitude'].values[-1], ds['latitude'].values.shape[0] * FACTOR)
            #lons = np.linspace(ds['longitude'].values[0], ds['longitude'].values[-1], ds['longitude'].values.shape[0] * FACTOR)
            x = np.linspace(0, 1, data_array_tmp.shape[0])
            y = np.linspace(0, 1, data_array_tmp.shape[1])
            f = interpolate.interp2d(y, x, data_array_tmp, kind='cubic')
            x2 = np.linspace(0, 1, data_array_tmp.shape[0] * factor)
            y2 = np.linspace(0, 1, data_array_tmp.shape[1] * factor)
            data_array_tmp = f(y2, x2)
            try:
                data_array += data_array_tmp
            except:
                data_array = data_array_tmp
        else:
            return
        # remove temporary file (including the index .idx file created when downloading)
        for filename in glob.glob(f'{file_tmp}*'):
            if not (filename.endswith('.geojson')):
                os.remove(filename)  # os.remove(file_tmp)

    data_array[data_array < 0] = 0  # MAKING SURE IT'S POSITIVE!!

    geometries = []
    val_series = []
    field_series = []

    # range
    max_value = np.max(data_array)
    min_value = np.min(data_array[data_array > 0.0])
    min_value += 0.05 * (max_value - min_value) # previously set @ 0.01...  /!\ the "noisy" empty value is around e-15. It is therefore decided to clip it from 15% of max value
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
        [val_series.append(np.round((range_values[n] + range_values[n+1]) / 2, decimals=2)) for poly in polygon if poly is not None]
        [field_series.append(field) for poly in polygon if poly is not None]

    df = pd.DataFrame({
        'val': val_series,
        'field': field_series
    })
    gdf = gpd.GeoDataFrame(df,geometry=geometries)
    geojsonFilePath = f'{folder}/gfs_{start:03d}h_{end:03d}h.geojson' #TODO: replace with appropriate naming f'{os.path.splitext(ncfile)[0]}.geojson'
    gdf.to_file(geojsonFilePath, driver='GeoJSON')
    densify(geojsonFilePath, decimals=decimals)

    # compacting geojson even further, by removing blank spaces
    with open(geojsonFilePath, 'r') as f:
        data = json.load(f)

    with open(geojsonFilePath, 'w') as f:
        f.write(json.dumps(data, separators=(',', ':')))

def getGFSdata(start, end, folder, date=None, N=50):

    if date is None:
        today = dt.datetime.today()
        date = f'{today.year}{today.month:02d}{today.day:02d}'
        hour = int(dt.datetime.today().hour / 6) * 6
    else:
        hour = 18

    url_gfs_list = []
    file_tmp_list = []

    for time in range(start, end + 1):
        url_gfs, file_tmp = getGFSurl(date=date, hour=hour, time=time)
        url_gfs_list.append(url_gfs)
        file_tmp_list.append(file_tmp)

    if not os.path.isdir(folder):
        os.makedirs(folder)
    grib2geojson(url_gfs_list, file_tmp_list, start=start, end=end, folder=folder, N=N)


def getGPMdata(folder, date=None, hour=None, decimals=2, days_archived=15, threshold_precip=10):

    if not os.path.isdir(folder):
        os.makedirs(folder)

    if date is None:
        today = dt.datetime.today()
    else:
        today = dt.date(date[0],date[1],date[2])

    if hour is None:
        hour = 23

    day_of_year = today.timetuple().tm_yday
    year = today.year
    date = f'{today.year}{today.month:02d}{today.day:02d}'

    print(f'Dealing with {today.year}-{today.month:02d}-{today.day:02d} {hour:02d}:59:59')

    bbox = '-13.36,-41.3,99.14,3.79'


    url_gpm = f'https://pmmpublisher.pps.eosdis.nasa.gov/products/gpm_3hr_1d/subset/Global/{year}/{day_of_year}/gpm_3hr_1d.{date}.{hour:02d}5959?bbox={bbox}'

    file_tmp = f'{folder}/gpm_{date}_{hour:02d}.geojson'

    response = requests.get(url_gpm)
    if response.status_code != 200:
        print(f'\tFailed to download data')
        raise Exception
    open(file_tmp, "wb").write(response.content)

    with open(file_tmp, 'r') as f:
        data = json.load(f)
        data['features'] = [e for e in data['features'] if e['properties']['precip'] >= threshold_precip]
    with open(file_tmp, 'w') as f:
        f.write(json.dumps(data, separators=(',', ':')))
    densify(file_tmp, decimals=decimals)

    # date of the last allowed file
    last_allowed_day = dt.datetime.today() - dt.timedelta(days=days_archived)
    date_allowed = f'{last_allowed_day.year}{last_allowed_day.month:02d}{last_allowed_day.day:02d}'

    # remove temporary file (including the index .idx file created when downloading)
    for filename in glob.glob(f'{folder}/*'):
        if filename.endswith('.geojson') and filename < f'{folder}/gpm_{date_allowed}.geojson':
            os.remove(filename)



os.chdir('rain')

# GPM Real-Time
folder = 'gpm_realtime'
for hour in range(2, 23 + 3, 3):
    try:
        getGPMdata(hour=hour, folder=folder)
    except:
        pass


# GFS Real-Time
folder = 'gfs_realtime'
# getting 1d accumulation for cast for the next 5 days, with 3h interval
for day in range(5):
    for hour in range(0,24,3):
        try:
            getGFSdata(start = day * 24 + hour, end=(day + 1) * 24 + hour, folder = folder, N=25)
        except:
            print(f'The GFS data was probably not ready')

# getting 5d accumulation for cast for the next 5 days
try:
    getGFSdata(start=0, end=5*24, folder=folder)
except:
    print(f'The GFS data was probably not ready')
