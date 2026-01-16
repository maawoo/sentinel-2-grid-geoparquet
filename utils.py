import re
import numpy as np
import geopandas as gpd
from geopandas.array import GeometryArray
import pandas as pd
import shapely
from shapely import wkt, MultiPolygon, Point, Polygon, Geometry, STRtree

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
    text = row.description.split('<b>')[-2]
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
    text = row.description.split('<b>')[2]
    m = re.findall('<font COLOR="#008000">(.+?)</font>', text)
    epsg = int(m[0])
    return epsg


def union_query_strtree(
    gdf: gpd.GeoDataFrame,
    gdf_to_query: gpd.GeoDataFrame,
    predicate: str = 'intersects') -> np.ndarray:
    """ 
    @thx sehoffmann
    Perform a union query using shapely.STRtree spatial index. Unlike `shapely.STRtree.query`, 
    this function efficiently handles MultiPolygons by querying with their individual 
    Polygons and then forming the union over the matching indices.

    For some predicates, this can lead to different results than shapely.STRtree.query!

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        GeoDataFrame containing geometries to be indexed.
    gdf_to_query : geopandas.GeoDataFrame
        GeoDataFrame containing geometries to query against the index.
    predicate : str, optional
        Spatial predicate to use for the query. Default is 'intersects'.
    
    Returns
    -------
    indices : numpy.ndarray
        Array of indices of geometries in `gdf` that satisfy the predicate with any 
        geometry in `gdf_to_query`.
    """
    # Ensure both GeoDataFrames are in the same CRS (WGS 84)
    gdf = gdf.to_crs(epsg=4326)
    gdf_to_query = gdf_to_query.to_crs(epsg=4326)

    # Prepare the union geometry from gdf_to_query
    geometry = shapely.union_all(gdf_to_query.geometry)
    shapely.prepare(geometry)
    if isinstance(geometry, MultiPolygon):
        geometries = geometry.geoms
    elif isinstance(geometry, Geometry):
        geometries = [geometry]
    else:
        raise ValueError('geometry must be a shapely.Geometry')

    # Build STRtree from gdf geometries and perform union query
    geoms = GeometryArray(np.array([g for g in gdf.geometry]))
    tree = STRtree(geoms)
    all_indices = []
    for geometry in geometries:
        indices = tree.query(geometry, predicate=predicate)
        all_indices.append(indices)

    if len(all_indices) == 1:
        return all_indices[0]
    else:
        return np.unique(np.concatenate(all_indices))


def multipolygon_from_geoms(geoms: list[Geometry]) -> MultiPolygon | Polygon:
    """ Construct a MultiPolygon or Polygon from a list of geometries """
    polys = [g for g in geoms if not isinstance(g, Point)]
    if len(polys) == 1:
        return Polygon(polys[0])
    else:
        return MultiPolygon(polys)


def center_from_geoms(geoms: list[Geometry]) -> Point:
    """ Extract the center Point from a list of geometries """
    return [g for g in geoms if isinstance(g, Point)][0]


if __name__=='__main__':
    #################################################
    # Load and process ESA Sentinel-2 grid KML file for all available tiles
    gdf = gpd.read_file(URL_ESA_S2_GRID_KML, 
                        engine="pyogrio", force_2d=True, 
                        layer='Features',
                        columns=["Name", "description", "geometry"])
    gdf.rename(columns=dict(Name='tile'), inplace=True)

    gdf['center'] = gdf.geometry.apply(lambda x: center_from_geoms(x.geoms))
    gdf['geometry'] = gdf.geometry.apply(lambda x: multipolygon_from_geoms(x.geoms))
    gdf['epsg'] = gdf.apply(get_epsg, axis=1)
    gdf['utm_wkt'] = gdf.apply(get_utm_wkt, axis=1)
    gdf['utm_bounds'] = gdf.utm_wkt.apply(lambda x: wkt.loads(x).bounds).astype(str)
    gdf = gdf.drop(columns=['description'])

    print(f"Saving GDF containing {len(gdf)} tiles to sentinel-2-grid.parquet...")
    gdf.to_parquet("sentinel-2-grid.parquet")

    #################################################
    # Filter tiles that intersect land using high resolution land mask
    land_highres = gpd.read_file(URL_NE_VEC_10m_LAND_GEOJSON, engine="pyogrio")

    land = union_query_strtree(gdf=gdf, gdf_to_query=land_highres, 
                               predicate='intersects')
    gdf_land = gdf.iloc[land].reset_index(drop=True)

    print(f"Saving GDF containing {len(gdf_land)} land tiles to sentinel-2-grid_LAND.parquet...")
    gdf_land.to_parquet("sentinel-2-grid_LAND.parquet")
