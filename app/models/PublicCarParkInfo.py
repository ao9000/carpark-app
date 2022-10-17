from app import db
from sqlalchemy import exc
from app.api import get_public_carparks_info, convert_coords_3414_to_4326
from app.models.CarParkInfo import CarParkInfo


class PublicCarParkInfo(CarParkInfo):
    __tablename__ = 'PublicCarParkInfo'

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
    x_coord_EPSG3414 = db.Column(db.Float, nullable=False)
    y_coord_EPSG3414 = db.Column(db.Float, nullable=False)
    carpark_type = db.Column(db.String(50), nullable=False)
    electronic_parking_system = db.Column(db.Boolean, nullable=False)
    short_term_parking = db.Column(db.String(255), nullable=False)
    free_parking = db.Column(db.String(255), nullable=False)
    night_parking = db.Column(db.Boolean, nullable=False)
    carpark_deck_number = db.Column(db.Integer, nullable=False)
    gantry_height = db.Column(db.Float(255), nullable=False)
    carpark_basement = db.Column(db.Boolean, nullable=False)
    # Relationship to CarParkAvailability
    avabilities = db.relationship('CarParkAvailability', backref='PublicCarParkInfo', lazy=True)

    @staticmethod
    def get_all():
        return PublicCarParkInfo.query.all()

    @staticmethod
    def get_short_term_carpark_rates():
        return PublicCarParkInfo.FARE_RATE_DICT

    @staticmethod
    def get_central_carpark_numbers():
        return PublicCarParkInfo.CENTRAL_CARPARK_NUMBERS

    @staticmethod
    def update_table():
        # Public carparks
        public_carpark_info = get_public_carparks_info()

        for index, record in enumerate(public_carpark_info['result']['records'], start=1):
            print(f"CarParkInfo: Processing public carpark ecord {index}/{len(public_carpark_info['result']['records'])}")
            # Create CarParkInfo Object
            # Convert the coordinates to WGS84
            wgs84_coords = convert_coords_3414_to_4326(record['x_coord'], record['y_coord'])
            wgs84_lat, wgs84_long = float(wgs84_coords['latitude']), float(wgs84_coords['longitude'])

            # Record does not exist
            new_record = PublicCarParkInfo(carpark_number=record['car_park_no'],
                                           address=record['address'],
                                           x_coord_EPSG3414=record['x_coord'],
                                           y_coord_EPSG3414=record['y_coord'],
                                           x_coord_WGS84=wgs84_lat,
                                           y_coord_WGS84=wgs84_long,
                                           carpark_type=record['car_park_type'],
                                           electronic_parking_system=True if record['type_of_parking_system'] == "ELECTRONIC PARKING" else False,
                                           short_term_parking=record['short_term_parking'],
                                           free_parking=record['free_parking'],
                                           night_parking=True if record['night_parking'] == "YES" else False,
                                           carpark_deck_number=record['car_park_decks'],
                                           gantry_height=record['gantry_height'],
                                           carpark_basement=True if record['car_park_basement'] == "Y" else False
                                           )

            # Try to insert into db
            try:
                new_record.save()
            except exc.IntegrityError as e:
                # Duplicated record, check if the existing record is the same
                # Rollback first
                db.session.rollback()

                # Check if record is different
                if (existing_record := PublicCarParkInfo.get(record['car_park_no'])) != new_record:
                    # Record is different, Update record. Else do nothing
                    PublicCarParkInfo.update(existing_record, new_record)
