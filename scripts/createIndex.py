import glob
import json


dict_files = {}
dirs = ['mpres_data','tc_realtime']

for dir in dirs:
    dict_files[dir] = glob.glob(f'{dir}/**/**.*', recursive=True)

with open('index.json', 'w') as f:
    json.dump(dict_files, f, sort_keys=True, indent=4)
