# Cloud-native geospatial Sentinel-2 grid

An update of [scottyhq/mgrs](https://github.com/scottyhq/mgrs) to convert the 
[Sentinel-2 grid](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2/data-products) 
from KML to the cloud-native file format [GeoParquet](https://github.com/opengeospatial/geoparquet). 
Two versions are available in this repository:
- `sentinel-2-grid.parquet` - the full grid
- `sentinel-2-grid_LAND.parquet` - only tiles that intersect with land areas based on the high resolution land mask by [Natural Earth]("https://github.com/nvkelso/natural-earth-vector/blob/v5.1.2/geojson/ne_10m_land.geojson")

![Sentinel-2 grid](overview.png)

## Access examples

The GeoParquet files can be accessed directly from this repository without having to download the files.
Here are some examples to get you started:

### GeoPandas

```python
import geopandas as gpd

gdf = gpd.read_file("https://github.com/maawoo/sentinel-2-grid-geoparquet/raw/main/sentinel-2-grid.parquet", engine="pyogrio")
```

### GDAL / OGR

#### Extract individual tile and save as GeoJSON

```bash
ogr2ogr -f "GeoJSON" 32TNT.geojson /vsicurl/https://github.com/maawoo/sentinel-2-grid-geoparquet/raw/main/sentinel-2-grid.parquet -sql "SELECT * FROM \"sentinel-2-grid\" WHERE tile = '32TNT'"
```

#### Print file info

```bash
ogrinfo -al -so /vsicurl/https://github.com/maawoo/sentinel-2-grid-geoparquet/raw/main/sentinel-2-grid.parquet
```
This should print the metadata of the file:

```
INFO: Open of `/vsicurl/https://github.com/maawoo/sentinel-2-grid-geoparquet/raw/main/sentinel-2-grid.parquet'
      using driver `Parquet' successful.

Layer name: sentinel-2-grid
Geometry: Polygon
Feature Count: 56686
Extent: (-180.000000, -83.835951) - (180.000000, 84.644279)
Layer SRS WKT:
GEOGCRS["WGS 84",
    ENSEMBLE["World Geodetic System 1984 ensemble",
        MEMBER["World Geodetic System 1984 (Transit)"],
        MEMBER["World Geodetic System 1984 (G730)"],
        MEMBER["World Geodetic System 1984 (G873)"],
        MEMBER["World Geodetic System 1984 (G1150)"],
        MEMBER["World Geodetic System 1984 (G1674)"],
        MEMBER["World Geodetic System 1984 (G1762)"],
        MEMBER["World Geodetic System 1984 (G2139)"],
        ELLIPSOID["WGS 84",6378137,298.257223563,
            LENGTHUNIT["metre",1]],
        ENSEMBLEACCURACY[2.0]],
    PRIMEM["Greenwich",0,
        ANGLEUNIT["degree",0.0174532925199433]],
    CS[ellipsoidal,2],
        AXIS["geodetic latitude (Lat)",north,
            ORDER[1],
            ANGLEUNIT["degree",0.0174532925199433]],
        AXIS["geodetic longitude (Lon)",east,
            ORDER[2],
            ANGLEUNIT["degree",0.0174532925199433]],
    USAGE[
        SCOPE["Horizontal component of 3D system."],
        AREA["World."],
        BBOX[-90,-180,90,180]],
    ID["EPSG",4326]]
Data axis to CRS axis mapping: 2,1
Geometry Column = geometry
tile: String (0.0)
epsg: Integer64 (0.0)
utm_wkt: String (0.0)
utm_bounds: String (0.0)
```
