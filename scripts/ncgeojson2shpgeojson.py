import glob
import os
import json
import geopandas as gpd

dir = 'jtwc_history'
list_files = glob.glob(f'{dir}/**/**SLOSH.geojson', recursive=True)

for file in list_files:
    storm_id = file.split('_')[2]
    with open(file, 'r') as f:
        data = json.load(f)
    data_storm = data['storm']
    data_bbox = data['bbox']
    gdf = gpd.read_file(file)
    gdf_shp = gdf[gdf['geometry'].apply(lambda x: x.type == 'Point' or x.type == 'LineString')]
    gdf_shp['text'] = gdf_shp['text'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:00:00' if x else '')
    gdf_shp.rename(columns={'text': 'DTG', 'val2': 'VMAX', 'field': 'TECH', 'val1': 'NAME'}, inplace=True)
    gdf_shp['TECH'] = 'TRAK'
    gdf_shp['NAME'] = data['storm']['name']


    geojsonFilePath = f'{os.path.dirname(file)}/{storm_id}_shp.geojson'
    print(f'Writing {geojsonFilePath} ...')
    gdf_shp.to_file(geojsonFilePath, driver='GeoJSON')

    with open(geojsonFilePath, 'r') as f:
        data = json.load(f)

    with open(geojsonFilePath, 'w') as f:
        data['storm'] = data_storm  # adding storm information
        data['bbox'] = data_bbox
        f.write(json.dumps(data, separators=(',', ':')))


