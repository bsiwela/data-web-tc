[![fetchRealTimeSHP](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchRealTimeSHP.yml/badge.svg)](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchRealTimeSHP.yml)
[![fetchRealTimeNC](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchRealTimeNC.yml/badge.svg)](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchRealTimeNC.yml)
[![fetchPostevent](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchPostevent.yml/badge.svg)](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/fetchPostevent.yml)
[![createIndex](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/createIndex.yml/badge.svg)](https://github.com/bertranddelvaux/data-web-tc/actions/workflows/createIndex.yml)

# Tropical Cyclone Exporer (Web) - Backend

This documents aims at describing the processes and scripts running in the backend of Tropical Cyclone Explorer (Web).

## High-level description

The data populating the Tropical Cyclone Explorer (Web) is based on data fetched and transformed from KAC portal (https://www.kacportal.com/portal/welcome.php).

It consists in a series of python scripts running on Github Actions at regular intervals:

- `fetchRealTimeSHP.yml`:
  - python script: `fetchRealTimeSHP.py`
  - cron schedule expression: `0 * * * *`
  - schedule expression: every hour
  - description: fetches the Shapefiles (.zip) from KAC portal and transforms them into .geojson
- `fetchRealTimeNC.yml`:
  - python script: `fetchRealTimeNC.py`
  - cron schedule expression: `30 0/3 * * *`
  - schedule expression: at minute 30 past every 3rd hour from 0 through 23
  - description: fetches the NetCDF files (.zip up until 2022, now .nc) from KAC portal and transforms them into .geojson and losses
- `fetchRealTimeGFS.yml`:
  - python script: `fetchRealTimeGFS.py`
  - cron schedule expression: `30 1/3 * * *`
  - schedule expression: at minute 30 past every 3rd hour from 1 through 23
  - description: fetches the weather files (GPM for the last n days, GFS for the next 5 days)
- `fetchPostevent.yml`:
  - python script: `fetchPostevent.py`
  - cron schedule expression: `30 2/3 * * *`
  - schedule expression: at minute 30 past every 3rd hour from 2 through 23
  - description: fetches, after an event is finished (postevent), the shapefiles (.zip) and the NetCDF files (.zip up until 2022, now .nc) from KAC portal and transforms them into .geojson

#### Note
After each action fetching data from KAC portal (namely `fetchRealTimeSHP.yml`, `fetchRealTimeNC.yml` and `fetchPostevent.py`), the following scripts are generally being run:
- `createIndex.py`: creates `index.json` file that indexes all the files from the repository folders *mpres_data* and *tc_realtime*
- `latestStorms.py`: creates a `latestStorms.json` that keeps track of the storms in *mpres_data* and *tc_realtime*, with the following properties:
  - __bbox__: the bounding box of the storm, used in the frontend to zoom automatically to the appropriate zone, when a storm is selected
  - __id__: the storm identification token
  - __losses__: relative path to the .json file for the losses (economic losses and exposed population)
  - __nc__: relative path to the .geojson file for the converted NetCDF file (containing the wind profile, surge profile, ...)
  - __shp__: relative path to the .geojson file for the converted Shapefile (containing the track of the storm and the temporal information on position, speed, ...)
  - __storm_name__: the name of the storm
- `pastStorms.py`: creates `pastStormsSeason.json` that keeps track of the past storms (including the most recent ones), with the same format as the one used in `latestStorms.json`
- `getHistory.py`: creates `historyAdm.json` and `historyYears.json` which uses for each storm the same format as the one used in `latestStorms.json`, and whose nested structure is organized according to the administrative levels or the years respectively.

Example of storm properties stored in `latestStorms.json`:
```json
        {
            "bbox": [
                32.8,
                -25.0708,
                120.3292,
                -11.1125
            ],
            "id": "SH112023",
            "losses": "mpres_data/postevent/taos_swio30s_ofcl_windwater_nc/SH112023_losses_adm.json",
            "nc": "mpres_data/postevent/taos_swio30s_ofcl_windwater_nc/taostc_SH112023_JTWC_SLOSH.geojson",
            "shp": "mpres_data/postevent/taos_swio30s_ofcl_windwater_shp/taos_swio30s_ofcl_windwater_shp_SH112023.geojson",
            "storm_name": "FREDDY"
        }
```

### Utils

#### utils.py
* `listFilesUrl()` to list the file urls present on a url, given a username and a password, and a potential extension filter
* `fetchUrl()` to fetch a file based on its url, username and password
* `get_current_utc_timestamp()` to get the current utc-timestamp to be used in .json files

#### nczip2geojson.py

This code converts NetCDF files (.zip files up until 2022, .nc files afer 2022) into .geojson (see description below).

#### ncgzip2losses.py

This code calculates losses from NetCDF files (see description below).


## Low-level description

### fetchLatestSHP.py

#### Description of the code

This code performs the following tasks:

* Imports required packages such as os, geopandas, numpy, shapely.geometry, nczip2geojson, urllib.parse, and utils.
* Defines a URL that will be used to download data and retrieves the username and password from the environment variables.
* Lists all files in the URL with the extension '.zip' and sets the working directory to 'mpres_data'.
* Prints the current UTC timestamp.
* Loops through each file in the list and performs the following actions:
  * Gets the filename and downloads the file.
  * Converts the file to GeoJSON format using the nczip2geojson package.
  * If the file contains storm data, adds a lineString for the storm shapefile.
  * Writes the converted file to a GeoJSON file and removes the original NC file.
  * Downloads the file's SHA256 hash.

Overall, this code is downloading data from a specified URL, converting it to a more usable format, and adding additional information to the data for better analysis. It appears to be used for analyzing storm data, as it has specific code for adding lineStrings to the shapefile for storms.


### fetchLatestNC.py

#### Description of the code

This code performs the following tasks:

* Imports required packages
* Defines a URL that will be used to download data and retrieves the username and password from the environment variables.
* Sets the root directory path.
* Prints the current UTC timestamp.
* Gets the csv data from KAC portal and converts it to a dataframe
* Loads the index.json file to get the list of files
* Gets the list of files that are currently in the tc_realtime directory
* Gets the list of files that are currently in the remote tc_realtime directory
* Gets the list of files that need to be removed from the tc_realtime directory
* Prints the list of files in the tc_realtime directory and the remote repository, and the list of files to remove
* Switches to the appropriate directory
* If there is no new data from KAC, remove all the files in the tc_realtime directory
* If there is new data from KAC, convert the nc files to geojson and calculate the losses

Overall, this code checks the differences between the remote tc_realtime folder (on KAC portal) and the local tc_realtime folder, and removes the files that are not mirrored remotely anymore. If there are files that are in tc_realtime remote folder, it converts the nc files to geojson's and calculate the losses.


### nczip2geojson.py

#### Description of the code

This code converts NetCDF files (.zip files up until 2022, .nc files afer 2022) into .geojson with the following parameters:
* __fields__: fields to choose from (default values below)
```python
fields=['storm_position', 'past_rain_total', 'past_peak_wind', 'past_peak_water', 'fcst_peak_wind']
```
* __N__: the number of (multi-)polygons for each field (default value below)
```python
N=50
```
* __decimals__: the decimal precision for the .geojson (this impacts the size, default value below)
```python
decimals=2
```
* __fcst_peak_wind__ and __past_rain_total__: boolean flags for the fields
```python
fcst_peak_wind=False, past_rain_total=False
```

The geojson contains the geometries of the (multi-)polygon per field and contains the metadata of the storm: see format described in `latestStorms.json` above.

### ncgzip2losses.py

#### Description of the code

This code implements the pseudo-code document from KAC, aimed at calculating the losses and exposed population. It takes the following arguments:

* __storm_file__: relative path to the NetCDF hazard file (.nc) of the storm
* __exp_file__: relative path to gzip (parquet) exposure file
* __adm_file__: relative path to the JSON admin file
* __mapping_file__: relative path to gzip (parquet) mapping file
* __split__: boolean flag to split into admin losses or keep it in one file
* __geojson__: relative path to the JSON losses file (output)
* __prefix__: the type of field to look for (by default, 'swath')
* __csv_file__: temporary csv file for the loss calculation




