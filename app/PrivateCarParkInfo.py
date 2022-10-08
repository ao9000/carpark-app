from app import db
from sqlalchemy import exc
from app.api import get_private_carpark_fare, get_coords_from_address_sg
import re


class PrivateCarParkInfo(db.Model):
    __tablename__ = 'PrivateCarParkInfo'

    # CarParkInfo Gov.sg API columns
    carpark_number = db.Column(db.String(10), primary_key=True)
    address = db.Column(db.String(255), nullable=True)
    x_coord_WGS84 = db.Column(db.Float, nullable=True)
    y_coord_WGS84 = db.Column(db.Float, nullable=True)
    weekday_parking_fare = db.Column(db.String(255), nullable=True)
    saturday_parking_fare = db.Column(db.String(255), nullable=True)
    sunday_ph_parking_fare = db.Column(db.String(255), nullable=True)
    weekday_entry_fare = db.Column(db.String(255), nullable=True)
    weekend_entry_fare = db.Column(db.String(255), nullable=True)

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
    def get(carpark_number):
        return PrivateCarParkInfo.query.filter_by(carpark_number=carpark_number).first()

    @staticmethod
    def get_all():
        return PrivateCarParkInfo.query.all()

    @staticmethod
    def update(existing_record, new_record):
        existing_record.__dict__ = new_record.__dict__

        db.session.commit()

    @staticmethod
    def update_table():
        # Private carparks
        private_carpark_info = get_private_carpark_fare()

        for index, record in enumerate(private_carpark_info['result']['records'], start=1):
            print(f"CarParkInfo: Processing private carpark record {index}/{len(private_carpark_info['result']['records'])}")

            # Retrieve the coordinates from the address using Google Maps API
            data = get_coords_from_address_sg(record['carpark'])

            # Extract fare for private carparks
            weekday_entry_fare = PrivateCarParkInfo.pv_extract_entry_fare(record['weekdays_rate_1']) or PrivateCarParkInfo.pv_extract_entry_fare(record['weekdays_rate_2'])
            weekend_entry_fare = weekday_entry_fare if "Same as wkdays" in record['saturday_rate'] or "Same as wkdays" in record['sunday_publicholiday_rate'] else PrivateCarParkInfo.pv_extract_entry_fare(record['saturday_rate']) or PrivateCarParkInfo.pv_extract_entry_fare(record['sunday_publicholiday_rate'])
            weekday_parking_fare = PrivateCarParkInfo.pv_extract_parking_fare(record['weekdays_rate_1']) or PrivateCarParkInfo.pv_extract_parking_fare(record['weekdays_rate_2'])
            saturday_parking_fare = weekday_parking_fare if "Same as wkdays" in record['saturday_rate'] else PrivateCarParkInfo.pv_extract_parking_fare(record['saturday_rate'])
            sunday_ph_parking_fare = saturday_parking_fare if "Same as Saturday" in record['sunday_publicholiday_rate'] else PrivateCarParkInfo.pv_extract_parking_fare(record['sunday_publicholiday_rate'])

            # Create CarParkInfo Object
            # Required to fabricate some values
            new_record = PrivateCarParkInfo(carpark_number=f"PV{index}",
                                            address=f"{record['carpark']}, {data['results'][0]['formatted_address']}",
                                            x_coord_WGS84=data['results'][0]['geometry']['location']['lat'],
                                            y_coord_WGS84=data['results'][0]['geometry']['location']['lng'],
                                            weekday_entry_fare=weekday_entry_fare,
                                            weekend_entry_fare=weekend_entry_fare,
                                            weekday_parking_fare=weekday_parking_fare,
                                            saturday_parking_fare=saturday_parking_fare,
                                            sunday_ph_parking_fare=sunday_ph_parking_fare
                                            )

            try:
                # Try to insert into db
                new_record.save()
            except exc.IntegrityError as e:
                # Duplicated record, check if the existing record is the same
                # Rollback first
                db.session.rollback()

                # Check if record is different
                if (existing_record := PrivateCarParkInfo.get(f"PV{index}")) != new_record:
                    # Record is different, Update record. Else do nothing
                    PrivateCarParkInfo.update(existing_record, new_record)
