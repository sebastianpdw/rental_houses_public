"""
Just some example scripts to test geopy packages
"""
import geopy
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

geolocator = Nominatim(user_agent="TestApp")

location_station = geolocator.geocode("Utrecht Centraal Station")
location_house = geolocator.geocode("Laan van Nieuw-Guinea Utrecht")
print("Location house: %s" % location_house)
geo_station = (location_station.latitude, location_station.longitude)
geo_house = (location_house.latitude, location_house.longitude)
print(geopy.distance.geodesic(geo_station, geo_house).kilometers)

geolocator = Nominatim(user_agent="TestApp")
location_station = geolocator.geocode("Utrecht Centraal Station")
location_house = geolocator.geocode({"postalcode": "3531JB", "country": "Netherlands"})
print("Location house: %s" % location_house)

geo_station = (location_station.latitude, location_station.longitude)
geo_house = (location_house.latitude, location_house.longitude)

print(geodesic(geo_station, geo_house).kilometers)

geolocator = Nominatim(user_agent="TestApp")
location_station = geolocator.geocode("Utrecht Centraal Station")
# groningen central station
location_house = geolocator.geocode({"postalcode": "9726AE", "country": "Netherlands"})
print("Location house: %s" % location_house)

geo_station = (location_station.latitude, location_station.longitude)
geo_house = (location_house.latitude, location_house.longitude)

print(geodesic(geo_station, geo_house).kilometers)
