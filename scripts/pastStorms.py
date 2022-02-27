import glob
import json

dict_files = {}
dirs = ['jtwc_history']

for dir in dirs:
    dict_files[dir] = glob.glob(f'{dir}/**/**.*', recursive=True)

dict_storms = {}


for dir in dirs:
    for file in dict_files[dir]:
        if file.endswith('.geojson'):
            dict_storms.setdefault(dir, {})
            year = file.split('/')[1]
            dict_storms[dir].setdefault(year, [])
            storm_id = file.split('_')[2]
            if storm_id not in [s['id'] for s in dict_storms[dir][year]]:
                rec = {'id': storm_id}
                dict_storms[dir][year].append(rec)
            i = [i for i, s in enumerate(dict_storms[dir][year]) if s['id'] == storm_id][0]
            dict_storms[dir][year][i]['nc'] = file
            with open(file, 'r') as f:
                data = json.load(f)
            dict_storms[dir][year][i]['storm_name'] = data['storm']['name']
            dict_storms[dir][year][i]['bbox'] = data['bbox']

with open('pastStorms.json', 'w') as f:
    json.dump(dict_storms, f, sort_keys=True, indent=4)


