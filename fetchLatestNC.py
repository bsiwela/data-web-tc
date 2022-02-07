import os
import requests
import pandas as pd
import nczip2geojson as nc
from io import StringIO
from urllib.parse import urlparse

url = 'https://www.kacportal.com/portal/kacs3/arc/tc_realtime/arc_tc_data.csv'
username = 'arc2'
password = 'ARC09876KAC54321!'

csv = requests.get(url, auth=(username, password))
data = pd.read_csv(StringIO(csv.text))

if 'NONE' in data.columns:
    print('No new data from KAC')
else:
    print('Could read data from KAC')
    for url_file in data[data.columns[-1]].unique():
    #url_file = data.columns[-1]
        filename = os.path.basename(urlparse(url_file).path)
        r = requests.get(url_file, auth=(username, password))

        # writing the file locally
        if r.status_code == 200:
            with open(filename, 'wb') as out:
                for bits in r.iter_content():
                    out.write(bits)

        # converting it to geojson
        nc.nc2geojson(filename, N=50)



