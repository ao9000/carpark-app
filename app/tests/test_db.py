import requests


def test_get_all_carparks_api():
    response = requests.get("http://127.0.0.1:5000/carparks/all")
    assert response.status_code == 200


def test_get_top_5_public_carparks_api():
    response = requests.get("http://127.0.0.1:5000/carparks/top/public?x_coord=1.287953&y_coord=103.851784&limit=5")
    assert response.status_code == 200

def test_get_top_5_private_carparks_api():
    response = requests.get("http://127.0.0.1:5000/carparks/top/private?x_coord=1.287953&y_coord=103.851784&limit=5")
    assert response.status_code == 200

def test_get_top_5_all_carparks_api():
    response = requests.get("http://127.0.0.1:5000/carparks/top/all?x_coord=1.287953&y_coord=103.851784&limit=5")
    assert response.status_code == 200

def test_get_carparks_by_id_api():
    response = requests.get("http://127.0.0.1:5000/carparks/id/?carpark_id=PV2")
    assert response.status_code == 200

