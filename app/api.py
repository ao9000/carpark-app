import requests
from urllib.parse import urljoin
from app.handler import retry_API

data_gov_base_db_url = "https://data.gov.sg/api/action/datastore_search?"
data_gov_base_api_url = "https://api.data.gov.sg/v1/"

one_map_sg_base_url = "https://developers.onemap.sg/commonapi/"

google_maps_api_base_url = "https://maps.googleapis.com/maps/api/"
google_maps_api_key = "AIzaSyD6tFcNbIAY9MU2b7wUsH5ESGLvvcgfqRA"


@retry_API(3)
def get_public_carparks_info():
    params = {
        'resource_id': '139a3035-e624-4f56-b63f-89ae28d4ae4c',
        'limit': 3000
    }

    response = requests.get(data_gov_base_db_url, params=params)

    return response


@retry_API(3)
def get_public_carparks_availability():
    response = requests.get(urljoin(data_gov_base_api_url, "transport/carpark-availability"))

    return response


@retry_API(3)
def get_private_carpark_fare():
    params = {
        'resource_id': '85207289-6ae7-4a56-9066-e6090a3684a5',
        'limit': 400
    }

    response = requests.get(data_gov_base_db_url, params=params)

    return response


@retry_API(3)
def convert_coords_3414_to_4326(latitude, longitude):
    params = {
        'X': latitude,
        'Y': longitude
    }

    response = requests.get(urljoin(one_map_sg_base_url, "convert/3414to4326?"), params=params)

    return response


@retry_API(3)
def get_coords_from_address_sg(address):
    # Retrieve the coordinates from the address using Google Maps API
    params = {'key': google_maps_api_key,
              'address': f"{address} Singapore",
              'language': "en",
              'region': 'sg'
              }

    response = requests.get(urljoin(google_maps_api_base_url, "geocode/json?"), params=params)

    return response


@retry_API(3)
def get_distance_from_carpark(origin_latitude, origin_longitude, destination_location):
    # Call API in groups of 20
    # Google API has a 2048 character limit for requests
    params = {'key': google_maps_api_key,
              'origins': f"{origin_latitude}%2C{origin_longitude}",
              'destinations': destination_location,
              'mode': 'walking'
              }

    params_string = "&".join("%s=%s" % (k, v) for k, v in params.items())
    response = requests.get(urljoin(google_maps_api_base_url, "distancematrix/json?"), params=params_string)

    return response
