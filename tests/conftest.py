import pytest
from app import create_app, db
from app.models.PublicCarParkInfo import PublicCarParkInfo
from app.models.PrivateCarParkInfo import PrivateCarParkInfo
from app.models.CarParkAvailability import CarParkAvailability


@pytest.fixture(scope="session", autouse=True)
def app_client():
    app = create_app()
    client = app.test_client

    # setup
    with app.app_context():
        db.create_all()
        PublicCarParkInfo.update_table()
        PrivateCarParkInfo.update_table()
        CarParkAvailability.update_table()
        yield client
        # teardown
        db.session.remove()
        db.drop_all()
