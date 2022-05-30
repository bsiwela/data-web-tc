import os
import argparse
import json
import glob
import pandas as pd

def checkIfKeyAddValue(d, year, value, field='loss'):
    value = round(value)

    keys_to_remove = ['population', 'wind_cat']
    for key in keys_to_remove:
        if key in d:
            del d[key]

    d.setdefault(field, {})

    # check whether 'loss' has already been turned into a list
    if not(isinstance(d[field], dict)):
        d[field] = {year: value}
        return

    if year not in d[field]:
        d[field].setdefault(year, value)
    else:
        d[field][year] += value

    return

def getAllStorms(json_storms):
    list_past = glob.glob('jtwc_history/**/**_shp.geojson')
    list_latest = glob.glob('mpres_data/postevent/taos_swio30s_ofcl_windwater_shp/**.geojson')
    dict_storms = {'records': list_past + list_latest}
    dict_storms['counter_total'] = len(set(list_past + list_latest))

    with open(json_storms, 'w') as f:
        json.dump(dict_storms, f, sort_keys=True, indent=4)

def getHistory(json_years, json_adm, json_past='pastStorms.json', json_latest='latestStorms.json'):

    dir = 'jtwc_history'
    list_losses = glob.glob(f'{dir}/**/**_losses_adm.json', recursive=True)
    list_years = list(set([item.split('/')[1] for item in list_losses]))
    dict_years = {}
    dict_adm = {'records': []}

    # reading past storms information
    with open(json_past, 'r') as f:
        past_storms = json.load(f)
    past_storm_dict = {s['id']: s['shp'] for s in past_storms['jtwc_history'] if 'shp' in s}

    # reading latest storms information
    with open(json_latest, 'r') as f:
        latest_storms = json.load(f)
    latest_storm_dict = {s['id']: s['shp'] for s in latest_storms['mpres_data'] if 'shp' in s}

    # updating past storms with latest storms
    past_storm_dict.update(latest_storm_dict)
    list_years.insert(0, str(int(max(list_years)) + 1))
    list_losses = glob.glob(f'mpres_data/postevent/taos_swio30s_ofcl_windwater_nc/**_losses_adm.json',
              recursive=True) + list_losses

    counter_total = 0
    for year in list_years:

        counter_year = 0
        if year == list_years[0]:
            list_losses_year = glob.glob(f'mpres_data/postevent/taos_swio30s_ofcl_windwater_nc/**_losses_adm.json',
                                         recursive=True)
        else:
            list_losses_year = glob.glob(f'{dir}/{year}/**_losses_adm.json', recursive=True)

        for losses in list_losses_year:
            counter_year += 1
            counter_total += 1
            with open(losses, 'r') as f:
                data = json.load(f)
            if year == list_years[0]:
                storm_id = losses.split('/')[-1].split('_')[0]
            else:
                storm_id = losses.split('/')[2].split('_')[0]

            print(f'Dealing with {storm_id} ...')

            for adm0 in data['records']:
                if adm0['adm0_name'] not in [s['adm0_name'] for s in dict_adm['records']]:
                    adm0['storms'] = []
                    dict_adm['records'].append(adm0)
                i0 = [i for i, s in enumerate(dict_adm['records']) if s['adm0_name'] == adm0['adm0_name']][0]

                dict_adm['records'][i0].setdefault('counter_year', {year: counter_year})
                dict_adm['records'][i0]['counter_year'][year] = counter_year

                checkIfKeyAddValue(dict_adm['records'][i0], year, 1, field='counter_adm0')
                checkIfKeyAddValue(dict_adm['records'][i0], year, adm0['loss'], field='loss')

                if storm_id in past_storm_dict:
                    if 'storms' not in dict_adm['records'][i0]:
                        dict_adm['records'][i0]['storms'] = []
                    if past_storm_dict[storm_id] not in dict_adm['records'][i0]['storms']:
                        dict_adm['records'][i0]['storms'].append(past_storm_dict[storm_id])


                for adm1 in adm0['adm1']:
                    if adm1['adm1_name'] not in [s['adm1_name'] for s in dict_adm['records'][i0]['adm1']]:
                        dict_adm['records'][i0]['adm1'].append(adm1)

                    i1 = [i for i, s in enumerate(dict_adm['records'][i0]['adm1']) if s['adm1_name'] == adm1['adm1_name']][0]

                    dict_adm['records'][i0]['adm1'][i1].setdefault('counter_year', {year: counter_year})
                    dict_adm['records'][i0]['adm1'][i1]['counter_year'][year] = counter_year

                    checkIfKeyAddValue(dict_adm['records'][i0]['adm1'][i1], year, 1, field='counter_adm1')
                    checkIfKeyAddValue(dict_adm['records'][i0]['adm1'][i1], year, adm1['loss'], field='loss')

                    if storm_id in past_storm_dict:
                        if not ('storms' in dict_adm['records'][i0]['adm1'][i1]):
                            dict_adm['records'][i0]['adm1'][i1]['storms'] = []
                        if past_storm_dict[storm_id] not in dict_adm['records'][i0]['adm1'][i1]['storms']:
                            dict_adm['records'][i0]['adm1'][i1]['storms'].append(past_storm_dict[storm_id])

                    for adm2 in adm1['adm2']:
                        if adm2['adm2_name'] not in [s['adm2_name'] for s in dict_adm['records'][i0]['adm1'][i1]['adm2']]:
                            dict_adm['records'][i0]['adm1'][i1]['adm2'].append(adm2)
                        i2 = [i for i, s in enumerate(dict_adm['records'][i0]['adm1'][i1]['adm2']) if s['adm2_name'] == adm2['adm2_name']][0]

                        dict_adm['records'][i0]['adm1'][i1]['adm2'][i2].setdefault('counter_year', {year: counter_year})
                        dict_adm['records'][i0]['adm1'][i1]['adm2'][i2]['counter_year'][year] = counter_year

                        checkIfKeyAddValue(dict_adm['records'][i0]['adm1'][i1]['adm2'][i2], year, 1, field='counter_adm2')
                        checkIfKeyAddValue(dict_adm['records'][i0]['adm1'][i1]['adm2'][i2], year, adm2['loss'], field='loss')

                        if storm_id in past_storm_dict:
                            if not ('storms' in dict_adm['records'][i0]['adm1'][i1]['adm2'][i2]):
                                dict_adm['records'][i0]['adm1'][i1]['adm2'][i2]['storms'] = []
                            if past_storm_dict[storm_id] not in dict_adm['records'][i0]['adm1'][i1]['adm2'][i2]['storms']:
                                dict_adm['records'][i0]['adm1'][i1]['adm2'][i2]['storms'].append(past_storm_dict[storm_id])


    dict_adm['counter_total'] = counter_total

    with open(json_adm, 'w') as f:
        json.dump(dict_adm, f, sort_keys=True, indent=4)


    for year in list_years:
        dict_years.setdefault(year, [])
        list_losses_year = glob.glob(f'{dir}/{year}/**_losses_adm.json', recursive=True)
        for losses in list_losses_year:
            with open(losses, 'r') as f:
                data = json.load(f)
            for adm0 in data['records']:
                if adm0['adm0_name'] not in [s['adm0_name'] for s in dict_years[year]]:
                    dict_years[year].append(adm0)
                else:
                    i0 = [i for i, s in enumerate(dict_years[year]) if s['adm0_name'] == adm0['adm0_name']][0]
                    dict_years[year][i0]['loss'] += adm0['loss']
                    for adm1 in adm0['adm1']:
                        if adm1['adm1_name'] not in [s['adm1_name'] for s in dict_years[year][i0]['adm1']]:
                            dict_years[year][i0]['adm1'].append(adm1)
                        else:
                            i1 = [i for i, s in enumerate(dict_years[year][i0]['adm1']) if s['adm1_name'] == adm1['adm1_name']][0]
                            dict_years[year][i0]['adm1'][i1]['loss'] += adm1['loss']
                            for adm2 in adm1['adm2']:
                                if adm2['adm2_name'] not in [s['adm2_name'] for s in dict_years[year][i0]['adm1'][i1]['adm2']]:
                                    dict_years[year][i0]['adm1'][i1]['adm2'].append(adm2)
                                else:
                                    i2 = [i for i, s in enumerate(dict_years[year][i0]['adm1'][i1]['adm2']) if s['adm2_name'] == adm2['adm2_name']][0]
                                    dict_years[year][i0]['adm1'][i1]['adm2'][i2]['loss'] += adm2['loss']


    with open(json_years, 'w') as f:
        json.dump(dict_years, f, sort_keys=True, indent=4)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-s', '--storms', type=str, help='Path to json file', default='storms.json', dest='json_storms')
    parser.add_argument('-y', '--years', type=str, help='Path to json file', default='historyYears.json', dest='json_years')
    parser.add_argument('-a', '--adm', type=str, help='Path to json file', default='historyAdm.json', dest='json_adm')
    args = parser.parse_args()

    getAllStorms(json_storms=args.json_storms)
    getHistory(json_years=args.json_years, json_adm=args.json_adm)
