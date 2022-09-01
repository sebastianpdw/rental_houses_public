import re

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from loguru import logger as lg


def remove_keywords(s: str):
    """
    Remove keywords from a string

    Args:
        s(str): The string to clean

    Returns:
        str: string without keywords
    """
    KEYWORDS = ["appartement", "huis", "kamer"]

    for keyword in KEYWORDS:
        s = re.sub(keyword, '', s, flags=re.I)

    s = re.sub(r"\s\s+", " ", s)  # remove double spaces
    s = s.lstrip().rstrip()
    return s


def extract_zipcode(s: str):
    """
    Extract a zipcode from a string

    Note: only works for Dutch zipcodes and only if the zipcode is in the format 1234AB
    Args:
        s (str): The string to extract the zipcode from

    Returns:
        str: The zipcode
    """
    regex_str = r"[0-9]{4}\s*?[A-Z]{2}"
    regex_found = re.findall(regex_str, s)

    if len(regex_found) > 0:
        if len(regex_found) > 1:
            lg.warning("Multiple zipcode found, taking the first occurence")
        zipcode = regex_found[0]
        zipcode = re.sub(r"\s+", "", zipcode)  # remove spaces
        return zipcode
    else:
        return None


def parse_address_str(s, geolocator=None):
    """
    Parse an address string to a geopy location object

    Note: this function is not very robust, it is only meant to be used for this project (Dutch country)
    Args:
        s (str): The Dutch address string to parse
        geolocator (Nominatim): The geolocator to use

    Returns:
        geopy.location.Location: The geopy location object
    """
    if not geolocator:
        geolocator = Nominatim(user_agent="TestApp")

    cleaned_s = remove_keywords(s)

    # Check for zipcode
    zipcode = extract_zipcode(s)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    if zipcode:
        return geocode({"postalcode": zipcode, "country": "Netherlands"})
    else:
        return geocode(cleaned_s)
