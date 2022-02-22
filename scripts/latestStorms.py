import glob
import json

dict_storms = {}
mapping_storms = {}
dirs = ['mpres_data','tc_realtime']

with open('index.json', 'r') as f:
    dict_files = json.load(f)

for dir in dirs:
    for file in dict_files[dir]:
        if dir == 'mpres_data':
            dict_storms.setdefault(dir, [])
            if 'postevent' in file:
                if not(file.endswith('.json')):
                    try:
                        storm_id = f'SH{file.split("_SH")[1].split("_")[0].split(".")[0]}'
                        if storm_id not in [s['id'] for s in dict_storms[dir]]:
                            rec = {'id': storm_id}
                            dict_storms[dir].append(rec)
                        i = [i for i, s in enumerate(dict_storms[dir]) if s['id'] == storm_id][0]
                        #dict_storms[dir].setdefault(storm_id, {})
                        if 'taos_swio30s_ofcl_windwater_nc' in file:
                            dict_storms[dir][i]['nc'] = file
                            loss_file = f'mpres_data/postevent/taos_swio30s_ofcl_windwater_nc/{storm_id}_losses_adm.json'
                            if loss_file in dict_files[dir]:
                                dict_storms[dir][i]['losses'] = loss_file
                        elif 'taos_swio30s_ofcl_windwater_shp' in file:
                            dict_storms[dir][i]['shp'] = file
                            with open(file, 'r') as f:
                                data = json.load(f)
                            dict_storms[dir][i]['storm_name'] = data['features'][0]['properties']['NAME']
                            dict_storms[dir][i]['validtime'] = data['features'][0]['properties']['VALIDTIME']
                    except:
                        continue
            elif file.endswith('.geojson'):
                dict_storms.setdefault('current_storms', {})
                with open(file, 'r') as f:
                    data = json.load(f)
                    list_current_storms = list(set([f['properties']['ATCFID'] for f in data['features']]))
                if 'storms_shp' in file:
                    dict_storms['current_storms']['storms_shp'] = list_current_storms
                elif 'windwater_shp' in file:
                    dict_storms['current_storms']['windwater_shp'] = list_current_storms
        elif dir == 'tc_realtime':
            dict_storms.setdefault(dir, [])
            if not (file.endswith('.json')):
                try:
                    storm_id = f'SH{file.split("_SH")[1].split("_")[0].split(".")[0]}'
                    if storm_id not in [s['id'] for s in dict_storms[dir]]:
                        rec = {'id': storm_id}
                        dict_storms[dir].append(rec)
                    i = [i for i, s in enumerate(dict_storms[dir]) if s['id'] == storm_id][0]
                    #dict_storms[dir].setdefault(storm_id, {})
                    if 'JTWC' in file:
                        dict_storms[dir][i]['jtwc'] = file
                    elif 'FMEE' in file:
                        dict_storms[dir][i]['fmee'] = file
                    with open(file, 'r') as f:
                        data = json.load(f)
                    dict_storms[dir][i]['storm_name'] = data['storm']['name']
                    loss_file = f'tc_realtime/{storm_id}_losses_adm.json'
                    if loss_file in dict_files[dir]:
                        dict_storms[dir][i]['losses'] = loss_file
                except:
                    continue
dict_storms['current_storms']['current_storms'] = [storm for storm in dict_storms['current_storms']['storms_shp'] if storm in dict_storms['current_storms']['windwater_shp']]

with open('latestStorms.json', 'w') as f:
    json.dump(dict_storms, f, sort_keys=True, indent=4)
