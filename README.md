## A collection of scripts for downloading and analysing SAR SLC data for soil moisture analysis.

My python environment is a mess so I leave it to you to figure out what libraries need to be installed.
One unusual prerequisit for `SSM_analysis.py` in particular is having my fork of the `INSAR4SM` code [available here](https://github.com/murphp30/INSAR4SM).

Python notebook files were used to play around with the data and probably aren't much use to anybody.

For the soil moisture code you need SLCs, ERA5 meteorlogical data, and a soil model from soil grids. I explain how to get each below.

### SAR SLCs
There are loads of ways to do this so do whatever you're comfortable with. I hadn't a clue when I started so this is what I ended up with.
- Follow the steps to authenticate the Sentinel Hub Catalogue API https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
- Edit line 100 in `sentinelsat_download.py` to include the location of your `.copernicus.config` file.
- Run `sentinelsat_download.py` with a date range, bounding box, and output directory as arguments.
- It _should_ "just work". Downloading data can take a long time so consider running in a tmux screen.

Note: the alluringly named `sentinelsat_async_download.py` doesn't actually work asynchronously (or at all, for that matter). I include it here incase anyone knows how to actually do things properly.
### ERA5

- Set up account on https://cds.climate.copernicus.eu.
- Create .cdsapirc file as described in https://cds.climate.copernicus.eu/how-to-api.
- Edit `/data/tapas/pearse/download_ERA5.py` with appropriate start date, end date and area of interest and run to download and combine ERA5 dataset.

### Soilgrids
- Edit `download_soilgrid.py` to include the location of your area of interest geojson, output directory, and desired resolution.
- Run and hope it works.