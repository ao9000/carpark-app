from app import db
from sqlalchemy import exc
from app.api import get_public_carparks_info, convert_coords_3414_to_4326, get_private_carpark_fare, get_coords_from_address_sg
import re


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
    carpark_number = db.Column(db.String(10), primary_key=True)
    address = db.Column(db.String(255), nullable=True)
    x_coord_EPSG3414 = db.Column(db.Float, nullable=True)
    y_coord_EPSG3414 = db.Column(db.Float, nullable=True)
    x_coord_WGS84 = db.Column(db.Float, nullable=True)
    y_coord_WGS84 = db.Column(db.Float, nullable=True)
    carpark_type = db.Column(db.String(50), nullable=True)
    electronic_parking_system = db.Column(db.Boolean, nullable=True)
    short_term_parking = db.Column(db.String(255), nullable=True)
    free_parking = db.Column(db.String(255), nullable=True)
    night_parking = db.Column(db.Boolean, nullable=True)
    carpark_deck_number = db.Column(db.Integer, nullable=True)
    gantry_height = db.Column(db.Float(255), nullable=True)
    carpark_basement = db.Column(db.Boolean, nullable=True)
    # Relationship to CarParkAvailability
    avabilities = db.relationship('CarParkAvailability', backref='CarParkInfo', lazy=True)

    # Additional tables
    # Differentiate from public and private carparks
    public_carpark = db.Column(db.Boolean, nullable=True)

    # Private carpark fare
    pv_weekday_fare = db.Column(db.String(255), nullable=True)
    pv_saturday_fare = db.Column(db.String(255), nullable=True)
    pv_sunday_ph_fare = db.Column(db.String(255), nullable=True)
    pv_weekday_entry_fare = db.Column(db.String(255), nullable=True)
    pv_weekend_entry_fare = db.Column(db.String(255), nullable=True)

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
    def pv_extract_entry_fare(text):
        pattern = re.compile(r'(?<=\$)?[0-9]+\.*[0-9]*(?=\s*(\/|per)\s*(entry|car))', re.IGNORECASE)
        capture = pattern.search(text)

        if capture:
            # Return the first capture group (Matched string)
            return float(capture.group(0))
        else:
            return None

    @staticmethod
    def pv_extract_parking_fare(text):
        pattern = re.compile(r'(?<=\$)?([0-9]+\.*[0-9]*)\s*(for+|\/+|per+)\s*(\S*)(?=\s*([0-9\W]*\s*hr|min))', re.IGNORECASE)
        capture = pattern.search(text)

        # Capture groups are as follows:
        # 0. Matched string
        # Group 1. Parking fare price
        # Group 2. 'for', '/', 'per'
        # Group 3. 1st, 2nd, sub etc (Can be NULL)
        # Group 4. number of 'hr', 'min'

        if capture:
            # Standardise all fares to per half and hour
            if capture.group(4) == 'hr':
                return float(capture.group(1)) / 2
            elif capture.group(4) == 'min':
                return float(capture.group(1)) * 30
            elif capture.group(4).endswith('hr') or capture.group(4).endswith('min'):
                # See if it is 1st, 2nd, sub etc
                # Check unit of time
                unit = capture.group(4)[:-2].strip()
                if unit.isdigit():
                    if capture.group(4).endswith('hr'):
                        # Normalise to half an hour
                        return float(capture.group(1)) / (2 * int(unit))
                    else:
                        # Normalise to half an hour
                        return float(capture.group(1)) / (30 * int(unit))
                else:
                    return float(capture.group(1))
            else:
                return float(capture.group(1))
        else:
            return None

    @staticmethod
    def get_short_term_carpark_rates():
        return CarParkInfo.FARE_RATE_DICT

    @staticmethod
    def get_central_carpark_numbers():
        return CarParkInfo.CENTRAL_CARPARK_NUMBERS

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
        # Public carparks
        public_carpark_info = get_public_carparks_info()

        for index, record in enumerate(public_carpark_info['result']['records'], start=1):
            print(f"CarParkInfo: Processing public carpark ecord {index}/{len(public_carpark_info['result']['records'])}")
            # Create CarParkInfo Object
            # Convert the coordinates to WGS84
            wgs84_coords = convert_coords_3414_to_4326(record['x_coord'], record['y_coord'])

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

        # Private carparks
        private_carpark_info = get_private_carpark_fare()

        for index, record in enumerate(private_carpark_info['result']['records'], start=1):
            print(f"CarParkInfo: Processing private carpark record {index}/{len(private_carpark_info['result']['records'])}")

            # Retrieve the coordinates from the address using Google Maps API
            data = get_coords_from_address_sg(record['carpark'])

            # Extract fare for private carparks
            weekday_entry_fare = CarParkInfo.pv_extract_entry_fare(record['weekdays_rate_1']) or CarParkInfo.pv_extract_entry_fare(record['weekdays_rate_2'])
            weekend_entry_fare = weekday_entry_fare if "Same as wkdays" in record['saturday_rate'] or "Same as wkdays" in record['sunday_publicholiday_rate'] else CarParkInfo.pv_extract_entry_fare(record['saturday_rate']) or CarParkInfo.pv_extract_entry_fare(record['sunday_publicholiday_rate'])
            weekday_parking_fare = CarParkInfo.pv_extract_parking_fare(record['weekdays_rate_1']) or CarParkInfo.pv_extract_parking_fare(record['weekdays_rate_2'])
            saturday_parking_fare = weekday_parking_fare if "Same as wkdays" in record['saturday_rate'] else CarParkInfo.pv_extract_parking_fare(record['saturday_rate'])
            sunday_ph_parking_fare = saturday_parking_fare if "Same as Saturday" in record['sunday_publicholiday_rate'] else CarParkInfo.pv_extract_parking_fare(record['sunday_publicholiday_rate'])

            # Create CarParkInfo Object
            # Required to fabricate some values
            new_record = CarParkInfo(carpark_number=f"PV{index}",
                                     address=f"{record['carpark']}, {data['results'][0]['formatted_address']}",
                                     x_coord_WGS84=data['results'][0]['geometry']['location']['lat'],
                                     y_coord_WGS84=data['results'][0]['geometry']['location']['lng'],
                                     pv_weekday_entry_fare=weekday_entry_fare,
                                     pv_weekend_entry_fare=weekend_entry_fare,
                                     pv_weekday_fare=weekday_parking_fare,
                                     pv_saturday_fare=saturday_parking_fare,
                                     pv_sunday_ph_fare=sunday_ph_parking_fare,
                                     public_carpark=False
                                     )

            try:
                # Try to insert into db
                new_record.save()
            except exc.IntegrityError as e:
                # Duplicated record, check if the existing record is the same
                # Rollback first
                db.session.rollback()

                # Check if record is different
                if (existing_record := CarParkInfo.get(f"PV{index}")) != new_record:
                    # Record is different, Update record. Else do nothing
                    CarParkInfo.update(existing_record, new_record)
