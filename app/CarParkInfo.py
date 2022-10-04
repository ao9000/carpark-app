from app import db
import requests
import json
from sqlalchemy import exc


class CarParkInfo(db.Model):
    __tablename__ = 'CarParkInfo'

    # Constants
    CENTRAL_CARPARK_NUMBERS = ['ACB', 'BBB', 'BRB1', 'CY', 'DUXM', 'HLM', 'KAB', 'KAM', 'KAS', 'PRM', 'SLS', 'SR1',
                               'SR2', 'TPM', 'UCS', 'WCB']
    # All rates are per half hour
    FARE_RATE_DICT = {
        'car': {
            'central': {
                'premium_hours': 1.20,
                'non_premium_hours': 0.60
            },
            'non_central': 0.60
        },
        'motorbike': {
            'whole_day': 0.65,
            'whole_night': 0.65
        },
        'heavy': 1.20
    }

    # CarParkInfo Gov.sg API columns
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
    # Relationship to CarParkAvailability
    avabilities = db.relationship('CarParkAvailability', backref='CarParkInfo', lazy=True)

    # Additional tables
    # Differentiate from public and private carparks
    public_carpark = db.Column(db.Boolean, nullable=False)

    # Parking fares for calculations
    # Fares are per half hour
    short_term_parking_car_fare = db.Column(db.Float, nullable=True)
    short_term_parking_motorbike_fare = db.Column(db.Float, nullable=True)
    short_term_parking_heavy_fare = db.Column(db.Float, nullable=True)

    def __eq__(self, other_instance):
        a = self.__dict__
        b = other_instance.__dict__

        for key, value in a.items():
            if key.startswith('_sa'):
                continue
            if isinstance(value, str):
                if value != b[key]:
                    return False
        return True

    def to_dict(self):
        obj = {}
        for key, value in self.__dict__.items():
            if not str(key).startswith('_sa'):
                obj[key] = value

        return obj

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_short_term_carpark_rates():
        return CarParkInfo.FARE_RATE_DICT

    @staticmethod
    def get_central_carpark_numbers():
        return CarParkInfo.CENTRAL_CARPARK_NUMBERS

    @staticmethod
    def convert_coords_3414_to_4326(latitude, longitude):
        API_LINK = "https://developers.onemap.sg/commonapi/convert/3414to4326"
        params = {'X': latitude, 'Y': longitude}
        response = requests.get(API_LINK, params=params)

        if response.status_code == 200:
            data = json.loads(response.text)
            return float(data['latitude']), float(data['longitude'])

    @staticmethod
    def get(carpark_number):
        return CarParkInfo.query.filter_by(carpark_number=carpark_number).first()

    @staticmethod
    def get_all():
        return CarParkInfo.query.all()

    @staticmethod
    def update(existing_record, new_record):
        existing_record.__dict__ = new_record.__dict__

        db.session.commit()

    @staticmethod
    def update_table():
        API_LINK = "https://data.gov.sg/api/action/datastore_search?resource_id=139a3035-e624-4f56-b63f-89ae28d4ae4c&limit=3000"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_info = json.loads(response.text)

            for index, record in enumerate(carpark_info['result']['records'], start=1):
                print(f"CarParkInfo: Processing record {index}/{len(carpark_info['result']['records'])}")
                # Create CarParkInfo Object
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
                                         carpark_basement=True if record['car_park_basement'] == "Y" else False,

                                         # Additional columns
                                         public_carpark=True
                                         )

                # Try to insert into db
                try:
                    new_record.save()
                except exc.IntegrityError as e:
                    # Duplicated record, check if the existing record is the same
                    # Rollback first
                    db.session.rollback()

                    # Check if record is different
                    if (existing_record := CarParkInfo.get(record['car_park_no'])) != new_record:
                        # Record is different, Update record. Else do nothing
                        CarParkInfo.update(existing_record, new_record)
