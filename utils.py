import re
import requests
import zipfile
from io import BytesIO

import numpy as np
import geopandas as gpd
from geopandas.array import GeometryArray
import pandas as pd
import shapely
from shapely import wkt, MultiPolygon, Point

URL_ESA_S2_GRID_KML = "https://sentiwiki.copernicus.eu/__attachments/1692737/S2A_OPER_GIP_TILPAR_MPC__20151209T095117_V20150622T000000_21000101T000000_B00.zip"
URL_NE_VEC_10m_LAND_GEOJSON = "https://github.com/nvkelso/natural-earth-vector/raw/v5.1.2/geojson/ne_10m_land.geojson"


def get_utm_wkt(row: pd.Series) -> str:
    """
    Extract UTM WKT from the description of the ESA S2 grid KML file.
    
    Parameters
    ----------
    row : pandas.Series
        A row of the ESA S2 grid KML file.
    
    Returns
    -------
    utm_wkt : str
        UTM WKT string.
    """
    text = row.Description.split('<b>')[-2]
    m = re.findall(r'MULTIPOLYGON\(\(\((.+?)\)\)\)', text)
    utm_wkt = f"POLYGON (({m[0]}))"
    return utm_wkt


def get_epsg(row: pd.Series) -> int:
    """
    Extract EPSG code from the description of the ESA S2 grid KML file.
    
    Parameters
    ----------
    row : pandas.Series
        A row of the ESA S2 grid KML file.

    Returns
    -------
    epsg : int
        EPSG code.
    """
    text = row.Description.split('<b>')[2]
    m = re.findall('<font COLOR="#008000">(.+?)</font>', text)
    epsg = int(m[0])
    return epsg


def union_query_strtree(
    tree: shapely.STRtree,
    geometry: shapely.Geometry,
    predicate: str = 'intersects',
) -> np.ndarray:
    """
    @thx sehoffmann
    Queries a shapely STRtree with a geometry.
    Unlike shapely.STRtree.query, this function performantely handles MultiPolygons by 
    querying with their individual Polygons and then forming the union over the matching indices.

    For some predicates, this can lead to different results than shapely.STRtree.query!

    Args:
        tree (shapely.STRtree): The spatial index to query.
        geometry (shapely.Geometry): The geometry or list of geometries to query with.
        predicate (str): The spatial predicate to use for querying. Defaults to 'intersects'.

    Returns:
        np.ndarray: Array of indices of geometries in the tree that match the predicate.
    """
    if isinstance(geometry, shapely.MultiPolygon):
        geometries = geometry.geoms
    elif isinstance(geometry, shapely.Geometry):
        geometries = [geometry]
    else:
        raise ValueError('geometry must be a shapely.Geometry')

    all_indices = []
    for geometry in geometries:
        indices = tree.query(geometry, predicate=predicate)
        all_indices.append(indices)

    if len(all_indices) == 1:
        return all_indices[0]
    else:
        return np.unique(np.concatenate(all_indices))


if __name__=='__main__':
    # Load KML file directly from URL
    url = URL_ESA_S2_GRID_KML

    # download the zip
    resp = requests.get(url)
    resp.raise_for_status()

    # read zip in memory
    zf = zipfile.ZipFile(BytesIO(resp.content))
    kml_name = next(name for name in zf.namelist() if name.lower().endswith(".kml"))
    kml_bytes = zf.read(kml_name)

    gdf = gpd.read_file(
        BytesIO(kml_bytes),
        engine="pyogrio",
        force_2d=True,
    )

    gdf = gdf.rename(columns={"Name": "tile"})

    gdf['geometry'] = gdf.geometry.apply(lambda x: MultiPolygon([g for g in x.geoms if not isinstance(g, Point)]))
    gdf['center'] = gdf.geometry.apply(lambda x: [g for g in x.geoms if isinstance(g, Point)][0])
    
    # Extract UTM_WKT and EPSG from "Description" column
    gdf['epsg'] = gdf.apply(get_epsg, axis=1)
    gdf['utm_wkt'] = gdf.apply(get_utm_wkt, axis=1)


    # Add simple UTM bounds (left, down, right, up)
    gdf[["utm_left", "utm_down", "utm_right", "utm_up"]] = (
        gdf["utm_wkt"]
        .apply(lambda x: wkt.loads(x).bounds)
        .apply(pd.Series)
    )


    gdf = gdf.drop(columns=['Description'])
    gdf.to_parquet("sentinel-2-grid.parquet")

    resp = requests.get(URL_NE_VEC_10m_LAND_GEOJSON)
    resp.raise_for_status()
    land_highres = gpd.read_file(BytesIO(resp.content), engine="pyogrio")
    land_highres = land_highres.to_crs(epsg=4326)  # ensure WGS 84
    land_highres = shapely.union_all(land_highres.geometry)
    shapely.prepare(land_highres)

    geoms = GeometryArray(np.array([g for g in gdf.geometry]))
    land = union_query_strtree(shapely.STRtree(geoms), land_highres)
    gdf_land = gdf.iloc[land]
    gdf_land.to_parquet("sentinel-2-grid_LAND.parquet")