import os
import shutil
import glob
import requests
import pandas as pd
import nczip2geojson as nc
from io import StringIO
from urllib.parse import urlparse

url = 'https://www.kacportal.com/portal/kacs3/arc/tc_realtime/arc_tc_data.csv'
username = os.environ['KAC_USERNAME']
password = os.environ['KAC_PASSWORD']

csv = requests.get(url, auth=(username, password))
data = pd.read_csv(StringIO(csv.text), header=None)

# switching to the appropriate directory
os.chdir('tc_realtime')

if data.iloc[0][0] == 'NONE':
    print('No new data from KAC ...')
    for file in glob.glob('*.*'):
        print(f'\tRemoving {file}')
        os.remove(file)
else:
    print('Data currently on KAC ...')
    for url_file in data[data.columns[-1]].unique():
        filename = os.path.basename(urlparse(url_file).path)
        print(f'\tProcessing {filename} ...')
        r = requests.get(url_file, auth=(username, password))

        # writing the file locally
        if r.status_code == 200:
            with open(filename, 'wb') as out:
                for bits in r.iter_content():
                    out.write(bits)

        # converting it to geojson
        nc.nc2geojson(filename, N=50)

        # removing nc file
        os.remove(filename)

        # moving created files to folder
        filePath = f'{os.path.splitext(filename)[0]}.geojson'
        #shutil.move(filePath, os.path.join('../tc_realtime', filePath))
