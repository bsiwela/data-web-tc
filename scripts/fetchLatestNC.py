import os
import shutil
import glob
import requests
import json
import pandas as pd
import nczip2geojson as nc
from io import StringIO
from urllib.parse import urlparse

url = 'https://www.kacportal.com/portal/kacs3/arc/tc_realtime/arc_tc_data.csv'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

csv = requests.get(url, auth=(username, password))
data = pd.read_csv(StringIO(csv.text), header=None)
with open('index.json', 'r') as f:
    index = json.load(f)
files_tc_realtime = [os.path.splitext(os.path.split(p)[1])[0] for p in index['tc_realtime']]
files_to_keep = []

# switching to the appropriate directory
os.chdir('tc_realtime')
dir_root = os.path.abspath(os.getcwd())

if data.iloc[0][0] == 'NONE':
    print('No new data from KAC ...')
    for file in glob.glob('*.*'):
        print(f'\tRemoving {file}')
        if file.endswith('.zip') or file.endswith('.nc') or file.endswith('.json') or file.endswith('.geojson'):
            os.remove(file)
else:
    print('Data currently on KAC ...')
    for url_file in data[data.columns[-1]].unique():
        os.chdir(dir_root)
        filename = os.path.basename(urlparse(url_file).path)
        print(f'\tProcessing {filename} ...')

        r = requests.get(url_file, auth=(username, password))

        print(f'\t\tDownloading {url_file} ...')
        # writing the file locally
        try:
            if r.status_code == 200:
                with open(filename, 'wb') as out:
                    for bits in r.iter_content():
                        out.write(bits)

            # converting it to geojson
            nc.nc2geojson(filename, N=50)

            # keeping file
            files_to_keep.append(os.path.splitext(filename)[0])

            # removing nc file
            os.remove(filename)

        except:
            print(f'\t\t\033[91mCouldnt download {url_file}\033[0m')
            continue

    os.chdir(dir_root)
    for file in [os.path.split(p)[1] for p in index['tc_realtime'] if os.path.splitext(os.path.split(p)[1])[0] not in files_to_keep]:
        try:
            file_path = os.path.join('tc_realtime',file)
            os.remove(file_path)
            print(f'\t\t\033[91mRemoved {file_path} which was not anymore in KAC repo tc_realtime ...\033[0m')
        except:
            continue
