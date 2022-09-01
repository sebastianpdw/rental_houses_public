import os

import pandas as pd
from geopy import Nominatim
from geopy.distance import geodesic, great_circle
from loguru import logger as lg

from helpers.addresses import parse_address_str, extract_zipcode


def calculate_distance(geo1, geo2, method='geodesic') -> float:
    """
    Calculates distances between two geographical objects

    Args:
        geo1 (geopy.location.Location): Geographical object 1
        geo2 (geopy.location.Location): Geographical object 2
        method (str): The method to use for calculating the distance. Can be either 'geodesic' or 'great_circle'

    Returns:
        float: The distance between the two geographical objects
    """
    METHOD_MAPPING = {"geodesic": geodesic, 'great_circle': great_circle}
    method_func = METHOD_MAPPING[method]

    geo1_gps = (geo1.latitude, geo1.longitude)
    geo2_gps = (geo2.latitude, geo2.longitude)

    return method_func(geo1_gps, geo2_gps).kilometers


def calculate_distance_addrs(addr1, addr2, method='geodesic', geolocator=None, cache_filepath=None):
    """
    Calculates distances between two addresses using the geopy geolocator

    Args:
        addr1 (str): Address 1
        addr2 (str): Address 2
        method (str): The method to use for calculating the distance. Can be either 'geodesic' or 'great_circle'
        geolocator (geopy.geocoders.Nominatim): The geolocator to use
        cache_filepath (str): The filepath to the cache file to use (this makes it faster and less likely to get blocked
                due to too many requests)

    Returns:
        float: The distance between the two addresses
    """
    if addr1 is None or addr2 is None:
        return None

    # Simplify addresses to zipcodes if possible
    if extract_zipcode(addr1):
        addr1 = extract_zipcode(addr1)
    if extract_zipcode(addr2):
        addr2 = extract_zipcode(addr2)

    # If cache enabled, check whether we already calculated these distances
    cache_df = None
    if cache_filepath:
        # speed can be improved with Pickle files instead of CSVS
        # however CSV chosen because it allows us to read the file easily
        if not os.path.exists(cache_filepath):
            os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
            lg.debug("Cache file does not exist, creating: %s" % cache_filepath)
            cache_df = pd.DataFrame({"route": [], "distance": []})
            cache_df.to_csv(cache_filepath, index=False)
        else:
            cache_df = pd.read_csv(cache_filepath)
            # lg.debug("Loaded cache file, with %s rows: %s" % (len(cache_df), cache_filepath))

        if len(cache_df) > 0:
            rel_row = cache_df[(cache_df['route'] == str((addr1, addr2))) | (cache_df['route'] == str((addr2, addr1)))]
            if len(rel_row) > 0:
                return rel_row.iloc[0]['distance']

    # Else query the distance
    if not geolocator:
        geolocator = Nominatim(user_agent="TestApp")

    addr1_geo = parse_address_str(addr1, geolocator=geolocator)
    addr2_geo = parse_address_str(addr2, geolocator=geolocator)

    if addr1_geo is None or addr2_geo is None:
        if addr1_geo is None:
            lg.warning("GeoAddress could not be found for: %s" % addr1)
        if addr2_geo is None:
            lg.warning("GeoAddress could not be found for: %s" % addr2)
        return None

    distance = calculate_distance(addr1_geo, addr2_geo, method=method)
    if cache_filepath:
        new_df = pd.DataFrame({"route": [(addr1, addr2)], "distance": [distance]})
        new_df.to_csv(cache_filepath, mode='a+', header=False, index=False)

    return distance
