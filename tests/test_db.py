import json

# Top carparks route testing
xy_coords = (1.287953, 103.851784)
def test_get_top_carparks_all(app_client):
    res = app_client().get(f'/carparks/top/all?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 5

def test_get_top_carparks_public(app_client):
    res = app_client().get(f'/carparks/top/public?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 5

def test_get_top_carparks_private(app_client):
    res = app_client().get(f'/carparks/top/private?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 5

def test_get_top_carparks_invalid_type(app_client):
    res = app_client().get(f'/carparks/top/ABC?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}')
    assert res.status_code == 400
def test_get_top_carparks_missing_xy_coords(app_client):
    # Both missing
    res = app_client().get(f'/carparks/top/all?&x_coord= &y_coord= ')
    assert res.status_code == 400

    # One missing
    res = app_client().get(f'/carparks/top/all?&x_coord= ')
    assert res.status_code == 400

    res = app_client().get(f'/carparks/top/all?&y_coord= ')
    assert res.status_code == 400
def test_get_top_carparks_all_valid_limit(app_client):
    res = app_client().get(f'/carparks/top/all?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}&limit=10')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 10

def test_get_top_carparks_all_invalid_zero_limit(app_client):
    res = app_client().get(f'/carparks/top/all?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}&limit=0')
    assert res.status_code == 400

def test_get_top_carparks_all_invalid_negative_limit(app_client):
    res = app_client().get(f'/carparks/top/all?&x_coord={xy_coords[0]}&y_coord={xy_coords[1]}&limit=-1')
    assert res.status_code == 400


# Search by carpark id testing
def test_get_carpark_by_id_valid_id(app_client):
    # Public carpark id
    res = app_client().get(f'/carparks/id?carpark_id=BBB')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 1

    # Private carpark id
    res = app_client().get(f'/carparks/id?carpark_id=PV1')
    assert res.status_code == 200
    assert len(json.loads(res.data)) == 1

def test_get_carpark_by_id_invalid_id(app_client):
    res = app_client().get(f'/carparks/id?carpark_id=ABC')
    assert res.status_code == 404

def test_get_carpark_by_id_empty_id(app_client):
    res = app_client().get(f'/carparks/id?carpark_id=')
    assert res.status_code == 400

# Get all carpark route testing
def test_get_all_carpark(app_client):
    res = app_client().get(f'/carparks/all')
    assert res.status_code == 200

# Invalid route testing
def test_invalid_route(app_client):
    res = app_client().get(f'/carparks')
    assert res.status_code == 404