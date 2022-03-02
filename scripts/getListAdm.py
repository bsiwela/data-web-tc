import argparse
import json
import geopandas as gpd

countries = [
    'Comoros',
    'Madagascar',
    'Mayotte',
    'Mauritius',
    'Mozambique',
    'Réunion',
    'Seychelles',
    'United Republic of Tanzania',
]

def adm2json(adm_file, json_file):

    adm_df = gpd.read_file(adm_file)
    boolean_series = adm_df['ADM0_NAME'].isin(countries)
    filtered_adm_df = adm_df[boolean_series]

    df = filtered_adm_df[['ADM0_NAME', 'ADM1_NAME', 'ADM2_NAME']]

    dict_adm = {}
    dict_adm.setdefault('adm0', [])

    for adm0_name in df['ADM0_NAME'].unique():
        dict_adm['adm0'].append({'adm0_name': adm0_name})
        dict_adm['adm0'][-1].setdefault('adm1', [])
        for adm1_name in df[df['ADM0_NAME'] == adm0_name]['ADM1_NAME'].unique():
            dict_adm['adm0'][-1]['adm1'].append({'adm1_name': adm1_name})
            dict_adm['adm0'][-1]['adm1'][-1].setdefault('adm2', [])
            for adm2_name in df[(df['ADM0_NAME'] == adm0_name) & (df['ADM1_NAME'] == adm1_name)]['ADM2_NAME'].unique():
                dict_adm['adm0'][-1]['adm1'][-1]['adm2'].append({'adm2_name': adm2_name})

    with open(json_file, 'w') as f:
        json.dump(dict_adm, f, sort_keys=True, indent=4)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Arguments to be passed to the script')
    parser.add_argument('-adm', '--admfile', type=str, help='Path to JSON adm file', default='adm2_full_precision.json', dest='adm_file')
    parser.add_argument('-json', '--jsonfile', type=str, help='Path to json file', default='admList.json', dest='json_file')
    args = parser.parse_args()

    adm2json(adm_file=args.adm_file, json_file=args.json_file)