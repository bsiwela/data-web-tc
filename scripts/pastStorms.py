import os
import glob
import json

dict_files = {}
dirs = ['jtwc_history']

for dir in dirs:
    dict_files[dir] = glob.glob(f'{dir}/**/**.*', recursive=True)

dict_storms = {}
dict_storms_season = {}


for dir in dirs:
    for file in dict_files[dir]:
        if file.endswith('.geojson'):
            dict_storms_season.setdefault(dir, {})
            year = file.split('/')[1]
            dict_storms_season[dir].setdefault(year, [])
            if file.endswith('SLOSH.geojson'):  # nc file
                storm_id = file.split('_')[2]
            else:
                storm_id = file.split('/')[2].split('_')[0]
            if storm_id not in [s['id'] for s in dict_storms_season[dir][year]]:
                rec = {'id': storm_id, 'year': year}
                dict_storms_season[dir][year].append(rec)
            i = [i for i, s in enumerate(dict_storms_season[dir][year]) if s['id'] == storm_id][0]
            if file.endswith('SLOSH.geojson'):  # nc file
                dict_storms_season[dir][year][i]['nc'] = file
                with open(file, 'r') as f:
                    data = json.load(f)
                dict_storms_season[dir][year][i]['storm_name'] = data['storm']['name']
                dict_storms_season[dir][year][i]['bbox'] = data['bbox']
                loss_file = f'{os.path.dirname(file)}/{storm_id}_losses_adm.json'
                if os.path.exists(loss_file):
                    dict_storms_season[dir][year][i]['losses'] = loss_file
                else:
                    dict_storms_season[dir][year][i]['losses'] = ''
            else:
                with open(file, 'r') as f:
                    data = json.load(f)
                date, time = min([f['properties']['DTG'] for f in data['features'] if f['properties']['DTG'] != '']).split(' ')
                dict_storms_season[dir][year][i]['shp'] = file
                dict_storms_season[dir][year][i]['date'] = date
                dict_storms_season[dir][year][i]['time'] = time

# Adding latest storms

dir = 'jtwc_history'
dir_latest = 'mpres_data/postevent/taos_swio30s_ofcl_windwater_nc'
dict_files[dir] = glob.glob(f'{dir_latest}/**.*', recursive=True)
for file in dict_files[dir]:
    if file.endswith('.geojson'):
        dict_storms_season.setdefault(dir, {})
        storm_id = 'SH' + file.split('SH')[1].split('_')[0]
        year = storm_id[4:]
        dict_storms_season[dir].setdefault(year, [])
        if storm_id not in [s['id'] for s in dict_storms_season[dir][year]]:
            rec = {'id': storm_id, 'year': year}
            dict_storms_season[dir][year].append(rec)
        i = [i for i, s in enumerate(dict_storms_season[dir][year]) if s['id'] == storm_id][0]
        if file.endswith('SLOSH.geojson'):  # nc file
            dict_storms_season[dir][year][i]['nc'] = file
            with open(file, 'r') as f:
                data = json.load(f)
            dict_storms_season[dir][year][i]['storm_name'] = data['storm']['name']
            dict_storms_season[dir][year][i]['bbox'] = data['bbox']
            loss_file = f'{os.path.dirname(file)}/{storm_id}_losses_adm.json'
            if os.path.exists(loss_file):
                dict_storms_season[dir][year][i]['losses'] = loss_file
            else:
                dict_storms_season[dir][year][i]['losses'] = ''
            shp_file = f'{os.path.dirname(file.replace("nc", "shp"))}/taos_swio30s_ofcl_windwater_shp_{storm_id}.geojson'
            with open(shp_file, 'r') as f:
                data = json.load(f)
            date, time = min([f['properties']['DTG'] for f in data['features'] if f['properties']['DTG'] != '']).split(
                ' ')
            dict_storms_season[dir][year][i]['shp'] = shp_file
            dict_storms_season[dir][year][i]['date'] = date
            dict_storms_season[dir][year][i]['time'] = time



with open('pastStormsSeason.json', 'w') as f:
    json.dump(dict_storms_season, f, sort_keys=True, indent=4)


for dir in dirs:
    for file in dict_files[dir]:
        if file.endswith('.geojson'):
            dict_storms.setdefault(dir, [])
            year = file.split('/')[1]
            if file.endswith('SLOSH.geojson'):  # nc file
                storm_id = file.split('_')[2]
            else:
                storm_id = file.split('/')[2].split('_')[0]
            if storm_id not in [s['id'] for s in dict_storms[dir]]:
                rec = {'id': storm_id, 'year': year}
                dict_storms[dir].append(rec)
            i = [i for i, s in enumerate(dict_storms[dir]) if s['id'] == storm_id][0]
            if file.endswith('SLOSH.geojson'):  # nc file
                dict_storms[dir][i]['nc'] = file
                with open(file, 'r') as f:
                    data = json.load(f)
                dict_storms[dir][i]['storm_name'] = data['storm']['name']
                dict_storms[dir][i]['bbox'] = data['bbox']
                loss_file = f'{os.path.dirname(file)}/{storm_id}_losses_adm.json'
                if os.path.exists(loss_file):
                    dict_storms[dir][i]['losses'] = loss_file
                else:
                    dict_storms[dir][i]['losses'] = ''
            else:
                dict_storms[dir][i]['shp'] = file



# for dir in dirs:
#     for file in dict_files[dir]:
#         if file.endswith('.geojson'):
#             dict_storms.setdefault(dir, {})
#             year = file.split('/')[1]
#             dict_storms[dir].setdefault(year, [])
#             storm_id = file.split('_')[2]
#             if storm_id not in [s['id'] for s in dict_storms[dir][year]]:
#                 rec = {'id': storm_id}
#                 dict_storms[dir][year].append(rec)
#             i = [i for i, s in enumerate(dict_storms[dir][year]) if s['id'] == storm_id][0]
#             dict_storms[dir][year][i]['nc'] = file
#             with open(file, 'r') as f:
#                 data = json.load(f)
#             dict_storms[dir][year][i]['storm_name'] = data['storm']['name']
#             dict_storms[dir][year][i]['bbox'] = data['bbox']

with open('pastStorms.json', 'w') as f:
    json.dump(dict_storms, f, sort_keys=True, indent=4)
