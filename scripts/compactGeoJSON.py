import sys
import json
import argparse
import numpy as np


def densify(geojsonFilePath, decimals=2):

    with open(geojsonFilePath, 'r') as f:
        data = json.load(f)

    for i, p in enumerate(data['features']):
        try:
            p['geometry']['coordinates'] = [np.round(np.array(poly), decimals=decimals).tolist() for poly in p['geometry']['coordinates']]
        except:
            print(f'{i}: Could not be transformed ')
            continue


    with open(geojsonFilePath, 'w') as f:
        f.write(json.dumps(data, separators=(',', ':')))

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-g', '--geojson', type=str, help='Path to GeoJSON file', default=None, dest='geojsonFilePath')
    parser.add_argument('-d', '--decimals', type=int, help='Decimal precision', default=4, dest='decimals')
    args = parser.parse_args()

    densify(geojsonFilePath=args.geojsonFilePath, decimals=args.decimals)
