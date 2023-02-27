import os
import glob
import requests
import json
import pandas as pd
import nczip2geojson as nc  # custom library to convert netcdf files to geojson
from io import StringIO
from urllib.parse import urlparse
# custom utility functions for fetching files, listing files, and getting timestamps
from utils import listFilesUrl, fetchUrl, get_current_utc_timestamp
# custom library for calculating losses from a storm
from ncgzip2losses import calculateLosses

# URL to fetch data from
url = 'https://www.kacportal.com/portal/kacs3/arc/tc_realtime/arc_tc_data.csv'
# KAC portal login credentials
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

# get the absolute path of the current working directory
root_root = os.path.abspath(os.getcwd())

# print the current UTC timestamp
utc_timestamp = get_current_utc_timestamp()
print(f'\033[32mTIMESTAMP: {utc_timestamp}\n\033[0m')

# fetch the CSV data from the KAC portal and load it into a Pandas dataframe
csv = requests.get(url, auth=(username, password))
data = pd.read_csv(StringIO(csv.text), header=None)

# read in the index file that lists the existing files on disk
with open('index.json', 'r') as f:
    index = json.load(f)

# get a list of files that are currently on disk
files_tc_realtime = [os.path.splitext(os.path.split(p)[1])[0] for p in index['tc_realtime']]
# get a list of files that are on the KAC portal
files_tc_realtime_url = [os.path.splitext(os.path.split(url)[1])[0] for url in data[data.columns[-1]].values if
                         isinstance(data[data.columns[-1]].values[0], str)]
# get a list of files that need to be removed
files_to_remove = [file for file in files_tc_realtime if file not in files_tc_realtime_url and file != 'README']

# if any of the files to be removed are loss files, keep them if there are no files on the KAC portal
for file in files_to_remove:
    if 'losses' in file and len(files_tc_realtime_url) > 0:
        files_to_remove.remove(file)

# print the files that are currently on disk and on the KAC portal, and the files to be removed
print(f'Files currently in: ')
print(f'* tc_realtime: ')
for file in files_tc_realtime:
    print(f'\t - {file}')
print(f'* tc_realtime (remote): ')
for file in files_tc_realtime_url:
    print(f'\t - {file}')
print('----------------------------')
print(f'Files to remove: ')
for file in files_to_remove:
    print(f'-{file}')

# change the current working directory to the "tc_realtime" directory
os.chdir('tc_realtime')
dir_root = os.path.abspath(os.getcwd())

# if there is no new data from the KAC portal, remove all files on disk
if data.iloc[0][0] == 'NONE':
    print('No new data from KAC ...')
    for file in glob.glob('*.*'):
        print(f'\tRemoving {file}')
        if file.endswith('.zip') or file.endswith('.nc') or file.endswith('.json') or file.endswith('.geojson'):
            print(f'\t\t\033[91mRemoving {file} ...\033[0m')
            os.remove(file)
else:
    # if there is, convert the NetCDF files (.nc) into .geojson and loss files
    print('Data currently on KAC ...')
    for url_file in [url for url in data[data.columns[-1]].unique() if 'JTWC' in url]: #for url_file in data[data.columns[-1]].unique():
        print(f'dir : {os.getcwd()}')
        os.chdir(dir_root)
        print(f'dir : {os.getcwd()}')
        filename = os.path.basename(urlparse(url_file).path)

        downloaded = fetchUrl(url_file, username, password)

        if downloaded:
            # converting it to geojson
            print(f'\033[32m\tConverting {filename} to geojson\033[0m')
            nc.nc2geojson(filename, N=50, fcst_peak_wind=True)

            if 'JTWC' in filename:
                # running loss generation
                print(f'\033[32m\tCalculating losses for {filename} \033[0m')
                calculateLosses(storm_file=filename, exp_file=os.path.join(root_root, 'arc_exposure.gzip'),
                                adm_file=os.path.join(root_root, 'adm2_full_precision.json'),
                                mapping_file=os.path.join(root_root, 'mapping.gzip'), split=False,
                                geojson=False, prefix='fcst')

            print(f'\t\t\033[91mRemoving {filename} ...\033[0m')
            os.remove(filename)  # removing nc file

    print(f'dir : {os.getcwd()}')
    os.chdir(dir_root)
    print(f'dir : {os.getcwd()}')
    for file in files_to_remove:
        try:
            file_path = f'{file}.geojson'
            print(f'\t\t\033[91mRemoving {file_path} which is not anymore on KAC repo tc_realtime ...\033[0m')
            os.remove(file_path)
        except:
            continue
