from geopy.geocoders import Nominatim
from loguru import logger as lg
import pytest

from distance.calculators import calculate_distance, calculate_distance_addrs


@pytest.fixture()
def geo_locator():
    return Nominatim(user_agent="TestApp")


class TestDistances:
    def test_calculate_distance(self, geo_locator: Nominatim):
        """
        Test the distance calculator with a few known locations

        Args:
            geo_locator (Nominatim): The geolocator to use
        """
        geo1 = geo_locator.geocode("Utrecht Centraal Station")
        geo2 = geo_locator.geocode("Laan van Nieuw-Guinea Utrecht")
        calculate_distance(geo1, geo2)

    def test_calculate_distance_addrs(self, geo_locator: Nominatim):
        """
        Test the distance calculator with addressess with a few known locations

        Args:
            geo_locator (Nominatim): The geolocator to use
        """
        utrecht_central_station_str = "Utrecht Centraal Station"

        test_dict = {(utrecht_central_station_str, "Laan van Nieuw-Guinea Utrecht"): 2,
                     (utrecht_central_station_str, "Appartement Laan van Nieuw-Guinea Utrecht"): 2,
                     (utrecht_central_station_str, "3531JB"): 1,
                     (utrecht_central_station_str, "3531  JB"): 1,
                     (utrecht_central_station_str, "9726AE"): 159,
                     (utrecht_central_station_str, "9726AE, Groningen"): 159,
                     ("alkdjdsa", "lkjasdl"): None}

        for addr_tup, expected_result in test_dict.items():
            addr1, addr2 = addr_tup
            dist = calculate_distance_addrs(addr1, addr2)
            if dist:
                rounded_found_dist = round(dist)
            else:
                rounded_found_dist = dist
            lg.debug("Distance between %s and %s: %s " % (addr1, addr2, rounded_found_dist))
            assert rounded_found_dist == expected_result

    def test_calculate_distance_addrs_with_cache(self, geo_locator: Nominatim):
        """
        Test the distance calculator with addressess (with cache option) with a few known locations

        Args:
            geo_locato (Nominatim): The geolocator to use
        """
        cache_filepath = "./01_data/distances_cache.csv"
        utrecht_central_station_str = "Utrecht Centraal Station"

        test_dict = {(utrecht_central_station_str, "Laan van Nieuw-Guinea Utrecht"): 2,
                     (utrecht_central_station_str, "Appartement Laan van Nieuw-Guinea Utrecht"): 2,
                     (utrecht_central_station_str, "3531JB"): 1,
                     (utrecht_central_station_str, "3531  JB"): 1,
                     (utrecht_central_station_str, "9726AE"): 159,
                     (utrecht_central_station_str, "9726AE, Groningen"): 159,
                     ("alkdjdsa", "lkjasdl"): None}

        for addr_tup, expected_result in test_dict.items():
            addr1, addr2 = addr_tup
            dist = calculate_distance_addrs(addr1, addr2, cache_filepath=cache_filepath)
            if dist:
                rounded_found_dist = round(dist)
            else:
                rounded_found_dist = dist
            lg.debug("Distance between %s and %s: %s " % (addr1, addr2, rounded_found_dist))
            assert rounded_found_dist == expected_result
