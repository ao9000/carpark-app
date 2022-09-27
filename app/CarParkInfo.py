from app import db
import requests
import json
from sqlalchemy import exc


class CarParkInfo(db.Model):
    __tablename__ = 'carparkinfo'
    carpark_number = db.Column(db.String(4), primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    x_coord_EPSG3414 = db.Column(db.Float, nullable=False)
    y_coord_EPSG3414 = db.Column(db.Float, nullable=False)
    x_coord_WGS84 = db.Column(db.Float, nullable=False)
    y_coord_WGS84 = db.Column(db.Float, nullable=False)
    carpark_type = db.Column(db.String(50), nullable=False)
    electronic_parking_system = db.Column(db.Boolean, nullable=False)
    short_term_parking = db.Column(db.String(255), nullable=False)
    free_parking = db.Column(db.String(255), nullable=True)
    night_parking = db.Column(db.Boolean, nullable=False)
    carpark_deck_number = db.Column(db.Integer, nullable=False)
    gantry_height = db.Column(db.Float(255), nullable=True)
    carpark_basement = db.Column(db.Boolean, nullable=False)
    avabilities = db.relationship('CarParkAvailability', backref='carparkinfo', lazy=True)

    def __eq__(self, other_instance):
        a = self.__dict__
        b = other_instance.__dict__

        for key, value in a.items():
            if key == '_sa_instance_state':
                continue
            if value != b[key]:
                return False
        return True

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def convert_coords_3414_to_4326(lat, long):
        API_LINK = "https://developers.onemap.sg/commonapi/convert/3414to4326"
        params = {'X': lat, 'Y': long}
        response = requests.get(API_LINK, params=params)

        if response.status_code == 200:
            data = json.loads(response.text)
            return data['latitude'], data['longitude']

    @staticmethod
    def get(carpark_number):
        return CarParkInfo.query.filter_by(carpark_number=carpark_number).first()

    @staticmethod
    def get_all():
        return CarParkInfo.query.all()

    @staticmethod
    def update(existing_record, new_record):
        existing_record.address = new_record.address
        existing_record.x_coord_EPSG3414 = new_record.x_coord_EPSG3414
        existing_record.y_coord_EPSG3414 = new_record.y_coord_EPSG3414
        existing_record.x_coord_WGS84 = new_record.x_coord_WGS84
        existing_record.y_coord_WGS84 = new_record.y_coord_WGS84
        existing_record.carpark_type = new_record.carpark_type
        existing_record.electronic_parking_system = new_record.electronic_parking_system
        existing_record.short_term_parking = new_record.short_term_parking
        existing_record.free_parking = new_record.free_parking
        existing_record.night_parking = new_record.night_parking
        existing_record.carpark_deck_number = new_record.carpark_deck_number
        existing_record.gantry_height = new_record.gantry_height
        existing_record.carpark_basement = new_record.carpark_basement

        db.session.commit()

    @staticmethod
    def update_table():
        API_LINK = "https://data.gov.sg/api/action/datastore_search?resource_id=139a3035-e624-4f56-b63f-89ae28d4ae4c&limit=3000"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_info = json.loads(response.text)

            for record in carpark_info['result']['records']:
                # Check if record is already in database
                try:
                    # Convert the coordinates to WGS84
                    wgs84_coords = CarParkInfo.convert_coords_3414_to_4326(record['x_coord'], record['y_coord'])

                    # Record does not exist
                    new_record = CarParkInfo(carpark_number=record['car_park_no'],
                                             address=record['address'],
                                             x_coord_EPSG3414=record['x_coord'],
                                             y_coord_EPSG3414=record['y_coord'],
                                             x_coord_WGS84=wgs84_coords[0],
                                             y_coord_WGS84=wgs84_coords[1],
                                             carpark_type=record['car_park_type'],
                                             electronic_parking_system=True if record['type_of_parking_system'] == "ELECTRONIC PARKING" else False,
                                             short_term_parking=record['short_term_parking'],
                                             free_parking=record['free_parking'],
                                             night_parking=True if record['night_parking'] == "YES" else False,
                                             carpark_deck_number=record['car_park_decks'],
                                             gantry_height=record['gantry_height'],
                                             carpark_basement=True if record['car_park_basement'] == "Y" else False
                                             )
                    new_record.save()
                except exc.IntegrityError as e:
                    db.session.rollback()
                    # Record already exists
                    # Check if record is different
                    # Convert the coordinates to WGS84
                    wgs84_coords = CarParkInfo.convert_coords_3414_to_4326(record['x_coord'], record['y_coord'])

                    # Record does not exist
                    new_record = CarParkInfo(carpark_number=record['car_park_no'],
                                             address=record['address'],
                                             x_coord_EPSG3414=record['x_coord'],
                                             y_coord_EPSG3414=record['y_coord'],
                                             x_coord_WGS84=wgs84_coords[0],
                                             y_coord_WGS84=wgs84_coords[1],
                                             carpark_type=record['car_park_type'],
                                             electronic_parking_system=True if record['type_of_parking_system'] == "ELECTRONIC PARKING" else False,
                                             short_term_parking=record['short_term_parking'],
                                             free_parking=record['free_parking'],
                                             night_parking=True if record['night_parking'] == "YES" else False,
                                             carpark_deck_number=record['car_park_decks'],
                                             gantry_height=record['gantry_height'],
                                             carpark_basement=True if record['car_park_basement'] == "Y" else False
                                             )
                    if (existing_record := CarParkInfo.get(record['car_park_no'])) != new_record:
                        # Record is different
                        # Update record
                        CarParkInfo.update(existing_record, new_record)
                        print(f"{existing_record.carpark_number} is updated")
