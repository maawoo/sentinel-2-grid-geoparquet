from pathlib import Path
import requests
import re
import pandas as pd

URL_ESA_S2_GRID_KML = "https://sentinel.esa.int/documents/247904/1955685/S2A_OPER_GIP_TILPAR_MPC__20151209T095117_V20150622T000000_21000101T000000_B00.kml"
URL_NE_VEC_10m_LAND_GEOJSON = "https://github.com/nvkelso/natural-earth-vector/raw/v5.1.2/geojson/ne_10m_land.geojson"


def get_esa_s2_grid_kml(url: str = URL_ESA_S2_GRID_KML) -> Path | None:
    """
    Download the ESA S2 grid KML file to the current working directory.
    
    Parameters
    ----------
    url : str
        URL to the ESA S2 grid KML file.
    
    Returns
    -------
    out : pathlib.Path or None
        Path to the downloaded file if successful, otherwise None.
    """
    out = Path.cwd() / url.split("/")[-1]
    if out.exists():
        print(f"{out.name} already exists; skip downloading.")
        return out
    
    response = requests.get(url)
    if response.status_code == 200:
        with open(out, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {out.name} to {out.parent}")
        return out
    else:
        print(f"Failed to download {url}")
        print(f"Status code & reason: {response.status_code} / {response.reason}")
        return None


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
    m = re.findall('MULTIPOLYGON\(\(\((.+?)\)\)\)', text)
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
