#!/usr/bin/python3
###################################################################
# Simplified python3 based economic impact estimation program
# Version 1.0
# Copyright (c) 2022, Bertrand Delvaux
#
# Parameters:
#       -nc: NetCDF file
#       -csv: SEM exposure file in csv format
#       -adm: JSON administrative polygon file
#
# Examples:
#       * ncgzip2losses.py -nc taostc_SH082022_JTWC_30_SLOSH.nc -csv arc_exposure.csv -adm adm2.json
#

import argparse
import os

import numpy as np

import csv
import json
import pandas as pd
import geopandas as gpd
import xarray as xr

from compactGeoJSON import densify
from utils import get_current_utc_timestamp



sem = {'LS_RURAL':{'stories':1,'vmin':26,'vmax':130,'cmin':0.0,'cmax':0.6,'dmin':0.01},
       'LS_MIXED':{'stories':1,'vmin':28,'vmax':150,'cmin':0.1,'cmax':0.9,'dmin':0.02},
       'LS_MDPOP':{'stories':2,'vmin':30,'vmax':160,'cmin':0.1,'cmax':0.9,'dmin':0.01},
       'LS_HDPOP':{'stories':5,'vmin':30,'vmax':175,'cmin':0.1,'cmax':0.9,'dmin':0.01},
      }

wind_bins = [17.5,24.72222,32.77778,46.38889,58.88889]

wind_list = {
    0: ['\033[96m','less than 63 km/h'],
    1: ['\033[94m','63 - 89 km/h'],
    2: ['\033[92m','89 - 118 km/h'],
    3: ['\033[93m','118 - 167 km/h'],
    4: ['\033[95m','167 - 212 kmh'],
    5: ['\033[91m','212 km/h and higher'],
    99: ['\033[0m',''],
}


def wind_damage(expclass, vms):
    wstdam = 0.0

    vkts = vms * 1.94384
    vmin = sem[expclass]['vmin']
    vmax = sem[expclass]['vmax']

    if vkts > vmin:
        wstdam = (vkts - vmin) ** 3 / (vmax - vmin) ** 3
        wstdam = np.min([wstdam, 1.0])

    dprob = np.sqrt(wstdam/0.7)  # ??? did they mean square root of 2 / 2?
    dprob = np.min([dprob, 1.0])

    return wstdam, dprob


def hydrology_damage(expclass, surge, dprob):
    sstdam = 0.0

    if surge > 0.5:
        sstdam = ((surge - 0.5) / (4 * sem[expclass]['stories'])) ** 2
        sstdam = np.min([sstdam, 1.0])
        dprob = 1.0

    return sstdam, dprob


def wind_hydrology_damage_st(wstdam, sstdam, dprob, dmin=0.01):
    dprob = np.max([dprob, dmin])  # Why exactly should the minimum probability be set to 0.01? -----> dmin?
    stdam = sstdam + wstdam
    stdam = np.min([stdam, 1.0])
    return stdam, dprob


def wind_hydrology_damage_co(stdam, expclass):
    cmin = sem[expclass]['cmin']
    cmax = sem[expclass]['cmax']
    codam = 0.0

    if stdam > cmin:
        codam = (stdam - cmin) / (cmax - cmin)
        codam = np.min([codam, 1.0])

    return codam


def loss_calculation(expclass, vms, surge, numexp, stval, coval, dmin=0.01):

    wstdam, dprob = wind_damage(expclass, vms)
    sstdam, dprob = hydrology_damage(expclass, surge, dprob)
    stdam, dprob = wind_hydrology_damage_st(wstdam, sstdam, dprob, dmin)
    codam = wind_hydrology_damage_co(stdam, expclass)

    stdam = np.min([stdam, 0.95])

    loss = numexp * stval * stdam * dprob + numexp * coval * codam * dprob

    return loss


def calculateLosses(storm_file, exp_file, adm_file, mapping_file, split, geojson, prefix='swath', csv_file='losses.csv'):

    # reading files: storm (nc), exposure (dbf), adm (json), mapping (json)
    storm_df = xr.open_dataset(storm_file, engine='netcdf4', decode_times=False)
    exp_df = pd.read_parquet(exp_file)
    adm_df = gpd.read_file(adm_file)
    mapping = pd.read_parquet(mapping_file)

    # reading latitudes and longitudes, creating derived variables
    lats = storm_df.variables['latitude'][:].values
    lons = storm_df.variables['longitude'][:].values
    nlats = len(lats)
    nlons = len(lons)
    ymin = lats[0]
    xmin = lons[0]
    dy = lats[2] - lats[1]
    dx = lons[2] - lons[1]

    # reading variables of interest
    if prefix == 'fcst':
        swath_peak_wind = storm_df.variables['fcst_peak_wind'][:].values
    else:
        swath_peak_wind = storm_df.variables['swath_peak_wind'][:].values
    swath_peak_water = storm_df.variables[f'{prefix}_peak_water'][:].values
    swath_peak_sigwaveht = storm_df.variables[f'{prefix}_peak_sigwaveht'][:].values
    stormId = storm_df.atcfid

    # initializing count of unidentified exp_id's
    unid_count = 0

    # writing csv file
    with open(csv_file, 'w') as f:
        writer = csv.writer(f)
        header = ['lat', 'lon', 'expid', 'admin_id', 'adm0_code', 'adm1_code', 'adm2_code', 'numexp', 'wind_cat', 'population', 'loss']
        writer.writerow(header)

        # initializing values
        vmax = 0.0
        tloss = 0.0
        totnum = 0
        numhit = 0

        ctry_id_dict = {}

        # looping through grid points
        for i, row in exp_df.iterrows():

            # increasing index by one
            totnum += 1

            # getting lat, lon
            lat = row['lat']
            lon = row['lon']
            x = int((lon - xmin)/dx)

            # if point is not not on the grid don't bother
            if x < 0:
                continue
            if x >= nlons:
                continue
            y = int((lat - ymin)/dy)
            if y < 0:
                continue
            if y >= nlats:
                continue

            expclass = row['exp_class'].rstrip()  # to remove ending blank spaces
            vms = swath_peak_wind[y][x]
            surge = swath_peak_water[y][x]
            numexp = row['numexp']
            stval = row['stval']
            coval = row['coval']
            dmin = sem[expclass]['dmin']

            loss = loss_calculation(expclass, vms, surge, numexp, stval, coval)

            # data to be written
            expid = row['exposure_id']
            ctry_id = row['ctry_id']
            admin_id = row['admin_id']
            try:
                adm0_code = mapping.loc[expid,'adm0_code']
                adm1_code = mapping.loc[expid,'adm1_code']
                adm2_code = mapping.loc[expid,'adm2_code']
                population = mapping.loc[expid,'population']
            except:
                #print(f'\033[91mCould not find any existing mapping for {expid} {ctry_id, admin_id}, lon {lon}, lat {lat}\033[0m')
                unid_count += 1
                population = 0
                try:
                    if adm0_code not in ctry_id_dict.keys():
                        ctry_id_dict[adm0_code] = [1,loss]
                    else:
                        ctry_id_dict[adm0_code][0] += 1
                        ctry_id_dict[adm0_code][1] += loss
                except:
                    continue
                # !!!!!!!!!!!! Population needs to be handled here !!!!!!!!!!!!!!

            wind_cat = np.digitize(vms, wind_bins)
            data = [lat, lon, expid, admin_id, adm0_code, adm1_code, adm2_code, numexp, wind_cat, population, loss]
            writer.writerow(data)

            # accumulate loss and get update vmax
            vmax = np.max([vms, vmax])
            loss = loss + tloss
            if (loss > 0):
                numhit = numhit + 1

            # REMOVE!!
            # if totnum >= 800000:
            #     break

    # print('\033[91m----------------------------------------------------')
    # print(f'In total, {unid_count} exp_ids were not identified')
    # for adm0_code in ctry_id_dict.keys():
    #     print(f'{adm_df[adm_df["ADM0_CODE"] == adm0_code]["ADM0_NAME"].unique()[0]} : {ctry_id_dict[adm0_code][0]} ${ctry_id_dict[adm0_code][1]}')
    # print('\033[0m')

    # reading csv into GeoDataFrame and adding geometry
    df = pd.read_csv(csv_file, index_col=False)
    if df.empty:
        # removing csv_file
        os.remove(csv_file)
        return
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=adm_df.crs)

    # removing csv_file
    os.remove(csv_file)

    # columns to drop from gdf_dis datasets
    colums_to_drop = ['geometry','lat','lon','expid','admin_id','adm0_code','adm1_code']

    df_groupby = df[df['loss'] > 0.0].groupby(by=['adm0_code', 'adm1_code', 'adm2_code', 'wind_cat'], as_index=False).sum()
    df_merge = pd.merge(df_groupby, adm_df.dissolve(by='ADM2_CODE', as_index=False), left_on='adm2_code', right_on='ADM2_CODE')

    cols2keep = ['ADM0_NAME', 'ADM1_NAME', 'ADM2_NAME', 'ADM0_CODE', 'ADM1_CODE', 'ADM2_CODE', 'wind_cat', 'population', 'loss', 'geometry']
    df_merge = df_merge[cols2keep]
    df_merge.rename(
        columns={'ADM0_NAME': 'adm0_name', 'ADM1_NAME': 'adm1_name', 'ADM2_NAME': 'adm2_name',
                 'ADM0_CODE': 'adm0_code', 'ADM1_CODE': 'adm1_code', 'ADM2_CODE': 'adm2_code'}, inplace=True)

    if geojson:
        df_final = gpd.GeoDataFrame(df_merge)
    else:
        df_final = df_merge.drop(columns='geometry')



    jsonFileBase = f'{stormId}_losses_adm'

    # saving to adm levels
    adm_group_list = []
    for i in range(3):
        jsonFile = f'{jsonFileBase}{i}.{"geo" if geojson else ""}json'
        adm_group_list = [f'adm{j}_{k}' for j in range(i + 1) for k in ['name', 'code']]

        df_final_adm = df_final.copy(deep=True)

        wind_cat_dict = {}
        df_final_cat = df_final_adm.groupby(adm_group_list + ['wind_cat'], as_index=False).sum()
        for adm_code in df_final_cat[f'adm{i}_code'].unique():
            wind_cat_dict[adm_code] = {}
            df_final_cat_adm = df_final_cat[df_final_cat[f'adm{i}_code'] == adm_code]
            for wind_cat in df_final_cat_adm['wind_cat'].unique():
                wind_cat_dict[adm_code].update(
                    {wind_cat: df_final_cat_adm[df_final_cat_adm['wind_cat'] == wind_cat]['population'].values[0]})

        df_final_adm.drop(columns=['wind_cat'], inplace=True)

        if geojson:
            gdf_adm = df_final_adm.dissolve(by=adm_group_list, aggfunc='sum', as_index=False)
            gdf_adm['wind_cat'] = gdf_adm[f'adm{i}_code'].apply(lambda row: wind_cat_dict[row])
            gdf_adm.to_file(jsonFile, driver='GeoJSON')
            densify(jsonFile)
        else:
            df_final_groupby = df_final_adm.groupby(adm_group_list, as_index=False)['population','loss'].sum()
            df_final_groupby['wind_cat'] = df_final_groupby[f'adm{i}_code'].apply(lambda row: wind_cat_dict[row])
            jsonString = df_final_groupby.to_json(orient='records').replace('[','{"records":[').replace(']', ']}')
            with open(jsonFile, 'w') as f:
                f.write(jsonString)

    i = 0
    with open(f'{jsonFileBase}{i}.json', 'r') as f:
        data = json.load(f)
        print(' | '.join(
            [f'{wind_list[cat][0]}cat {cat} : {wind_list[cat][1] if cat >= 1 else ""} {wind_list[99][0]}' for cat in range(len(wind_bins))]))
        for r in data['records']:
            pop = ' | '.join([f'{wind_list[int(key)][0]}{value:,}{wind_list[99][0]}' for key, value in r["wind_cat"].items() if int(key) >= 1])
            print(f'{r["adm0_name"]}: ${r["loss"]:,.2f} // pop {r["population"]:,} ({pop})')

    if not(split):
        with open(f'{jsonFileBase}0.json', 'r') as f:
            data0 = json.load(f)
        with open(f'{jsonFileBase}1.json', 'r') as f:
            data1 = json.load(f)
        with open(f'{jsonFileBase}2.json', 'r') as f:
            data2 = json.load(f)

        data = {}
        data['records'] = data0['records']
        for r0 in data['records']:
            r0['adm1'] = [{k: a[k] for k in a if k not in ['adm0_name', 'adm0_code']}
                          for a in data1['records'] if a['adm0_name'] == r0['adm0_name']]
            for r1 in r0['adm1']:
                r1['adm2'] = [{k: a[k] for k in a if k not in ['adm0_name', 'adm0_code', 'adm1_name', 'adm1_code']}
                              for a in data2['records'] if a['adm1_name'] == r1['adm1_name']]

        # adding timestamp
        utc_timestamp = get_current_utc_timestamp()
        data['utc_timestamp'] = utc_timestamp

        with open(f'{jsonFileBase}.json', 'w') as f:
            json.dump(data, f)

        for i in range(3):
            os.remove(f'{jsonFileBase}{i}.json')

    return


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-nc', '--ncfile', type=str, help='Path to NetCDF hazard file', default=None, dest='storm_file')
    parser.add_argument('-z', '--gzipfile', type=str, help='Path to gzip (parquet) exposure file', default=None, dest='exp_file')
    parser.add_argument('-adm', '--admfile', type=str, help='Path to JSON adm file', default=None, dest='adm_file')
    parser.add_argument('-m', '--mappingfile', type=str, help='Path to mapping file', default='mapping.gzip', dest='mapping_file')
    parser.add_argument('-s', '--split', action='store_true', help='split json files ', default=False, dest='split')
    parser.add_argument('-g', '--geojson', action='store_true', help='geojson', default=False, dest='geojson')
    args = parser.parse_args()

    calculateLosses(storm_file=args.storm_file, exp_file=args.exp_file, adm_file=args.adm_file, mapping_file=args.mapping_file, split=args.split, geojson=args.geojson)
