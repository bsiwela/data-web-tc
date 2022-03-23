import os
import glob
import requests
import json
import pandas as pd
import nczip2geojson as nc
from io import StringIO
from urllib.parse import urlparse
from utils import listFilesUrl, fetchUrl
from ncgzip2losses import calculateLosses

url = 'https://www.kacportal.com/portal/kacs3/arc/tc_realtime/arc_tc_data.csv'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

root_root = os.path.abspath(os.getcwd())

csv = requests.get(url, auth=(username, password))
data = pd.read_csv(StringIO(csv.text), header=None)
with open('index.json', 'r') as f:
    index = json.load(f)
files_tc_realtime = [os.path.splitext(os.path.split(p)[1])[0] for p in index['tc_realtime']]
files_tc_realtime_url = [os.path.splitext(os.path.split(url)[1])[0] for url in data[data.columns[-1]].values if isinstance(data[data.columns[-1]].values[0], str)]
files_to_remove = [file for file in files_tc_realtime if file not in files_tc_realtime_url and file != 'README.md']

for file in files_to_remove:
    if 'losses' in file and len(files_tc_realtime_url) > 0:
        files_to_remove.remove(file)
    

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

# switching to the appropriate directory
os.chdir('tc_realtime')
dir_root = os.path.abspath(os.getcwd())

if data.iloc[0][0] == 'NONE':
    print('No new data from KAC ...')
    for file in glob.glob('*.*'):
        print(f'\tRemoving {file}')
        if file.endswith('.zip') or file.endswith('.nc') or file.endswith('.json') or file.endswith('.geojson'):
            print(f'\t\t\033[91mRemoving {file} ...\033[0m')
            os.remove(file)
else:
    print('Data currently on KAC ...')
    for url_file in data[data.columns[-1]].unique():
        os.chdir(dir_root)
        filename = os.path.basename(urlparse(url_file).path)

        downloaded = fetchUrl(url_file, username, password)

        if downloaded:
            nc.nc2geojson(filename, N=50, fcst_peak_wind=True)  # converting it to geojson

            if 'JTWC' in filename:
                # running loss generation
                calculateLosses(storm_file=filename, exp_file=os.path.join(root_root, 'arc_exposure.gzip'),
                                adm_file=os.path.join(root_root, 'adm2_full_precision.json'),
                                mapping_file=os.path.join(root_root, 'mapping.gzip'), split=False,
                                geojson=False, prefix='fcst')

            print(f'\t\t\033[91mRemoving {filename} ...\033[0m')
            os.remove(filename) # removing nc file

    os.chdir(dir_root)
    for file in files_to_remove:
        try:
            file_path = f'{file}.geojson'
            print(f'\t\t\033[91mRemoving {file_path} which is not anymore on KAC repo tc_realtime ...\033[0m')
            os.remove(file_path)
        except:
            continue
