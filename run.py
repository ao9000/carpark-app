from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import requests
import json
from datetime import datetime, timedelta, time
from sqlalchemy import exc
import math

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

db = SQLAlchemy(app)


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
        API_LINK = f"https://developers.onemap.sg/commonapi/convert/3414to4326"
        params = {'X': lat, 'Y': long}
        response = requests.get(API_LINK, params=params)
        data = json.loads(response.text)
        print(f"success {lat, long}")
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
        existing_record.x_coord = new_record.x_coord
        existing_record.y_coord = new_record.y_coord
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
                    # Convert first
                    wgs84_coords = CarParkInfo.convert_coords_3414_to_4326(record['x_coord'], record['y_coord'])

                    # Record does not exist
                    new_record = CarParkInfo(carpark_number=record['car_park_no'],
                                             address=record['address'],
                                             x_coord_EPSG3414=record['x_coord'],
                                             y_coord_EPSG3414=record['y_coord'],
                                             x_coord_WGS84=wgs84_coords[0],
                                             y_coord_WGS84=wgs84_coords[1],
                                             carpark_type=record['car_park_type'],
                                             electronic_parking_system=1 if record['type_of_parking_system'] == "ELECTRONIC PARKING" else 0,
                                             short_term_parking=record['short_term_parking'],
                                             free_parking=record['free_parking'],
                                             night_parking=1 if record['night_parking'] == "YES" else 0,
                                             carpark_deck_number=record['car_park_decks'],
                                             gantry_height=record['gantry_height'],
                                             carpark_basement=1 if record['car_park_basement'] == "Y" else 0
                                             )
                    new_record.save()
                except exc.IntegrityError as e:
                    db.session.rollback()
                    # Record already exists
                    # Check if record is different
                    new_record = CarParkInfo(carpark_number=record['car_park_no'],
                                             address=record['address'],
                                             x_coord=record['x_coord'],
                                             y_coord=record['y_coord'],
                                             carpark_type=record['car_park_type'],
                                             electronic_parking_system=1 if record['type_of_parking_system'] == "ELECTRONIC PARKING" else 0,
                                             short_term_parking=record['short_term_parking'],
                                             free_parking=record['free_parking'],
                                             night_parking=1 if record['night_parking'] == "YES" else 0,
                                             carpark_deck_number=record['car_park_decks'],
                                             gantry_height=record['gantry_height'],
                                             carpark_basement=1 if record['car_park_basement'] == "Y" else 0
                                             )
                    if (existing_record := CarParkInfo.get(record['car_park_no'])) != new_record:
                        # Record is different
                        # Update record
                        CarParkInfo.update(existing_record, new_record)
                        print(f"{existing_record.carpark_number} is updated")


class CarParkAvailability(db.Model):
    __tablename__ = 'carparkavailability'
    id = db.Column(db.String(22), primary_key=True)
    carpark_number = db.Column(db.String(4), db.ForeignKey('carparkinfo.carpark_number'))
    lots_available = db.Column(db.Integer, nullable=False)
    total_lots = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get(row_id):
        return CarParkAvailability.query.filter_by(id=row_id).first()

    @staticmethod
    def update_table():
        API_LINK = "https://api.data.gov.sg/v1/transport/carpark-availability"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_availability = json.loads(response.text)

            for item in carpark_availability['items'][0]['carpark_data']:
                try:
                    # Check if record is already in database
                    record = CarParkAvailability(id=f"{item['carpark_number']} {item['update_datetime']}",
                                                 carpark_number=item['carpark_number'],
                                                 lots_available=item['carpark_info'][0]['lots_available'],
                                                 total_lots=item['carpark_info'][0]['total_lots'],
                                                 timestamp=datetime.strptime(item['update_datetime'], "%Y-%m-%dT%H:%M:%S"))
                    record.save()
                except exc.IntegrityError as e:
                    db.session.rollback()
                    print(f"Record id {e.params[0]} already exists, rolling back")


def short_term_parking_HDB_car(time_to_from, carpark_number, eps):
    # Fare Source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
    # EPS Source: https://www.hdb.gov.sg/car-parks/shortterm-parking/electronic-parking

    # Convert into datetime objects
    from_time = datetime.strptime(time_to_from[0], "%Y-%m-%dT%H:%M")
    to_time = datetime.strptime(time_to_from[1], "%Y-%m-%dT%H:%M")

    # Get total time in minutes/half-hours first
    total_minutes = (to_time - from_time).total_seconds() / 60

    # 10-minute grace period
    if total_minutes <= 10:
        return 0

    # While loop to split up into 3 time categories
    # 1. (7:00am to 5:00pm, Mondays to Saturdays) -> 1.20/1/2hr
    # 2. (Other hours) -> $0.60/1/2hr
    # 3. Night parking scheme capped at $5 per night (10:30pm to 7:00am)

    # Define time ranges
    central_expensive_time_range = (time(7, 0), time(16, 59))

    # Night parking range
    night_parking_time_range = (time(22, 30), time(6, 59))

    counter = 0
    expensive_time_counter_minute = 0
    night_parking_counter_minute = 0
    while counter < total_minutes:
        datetime_now = from_time + timedelta(minutes=counter)
        if central_expensive_time_range[0] <= datetime_now.time() <= central_expensive_time_range[1] and datetime_now.weekday() != 6:
            # Within expensive range
            expensive_time_counter_minute += 1
        if datetime_now.time() >= night_parking_time_range[0] or datetime_now.time() <= night_parking_time_range[1]:
            # Night parking
            night_parking_counter_minute += 1
        counter += 1

    # Get non-expensive time counter
    non_expensive_time_counter_minute = total_minutes - expensive_time_counter_minute

    # Check if night parking hit $5 quota
    quota_minute = round((5 / 0.60) * 30, 0)
    if night_parking_counter_minute >= quota_minute:
        # Hit $5 quota
        total_cost = 5
        non_expensive_time_counter_minute -= night_parking_counter_minute
        total_minutes -= night_parking_counter_minute
    else:
        # Never hit, but still init cost
        total_cost = 0

    # Calculate total cost
    central_carpark_numbers = ['ACB', 'BBB', 'BRB1', 'CY', 'DUXM', 'HLM', 'KAB', 'KAM', 'KAS', 'PRM', 'SLS', 'SR1',
                               'SR2', 'TPM', 'UCS', 'WCB']
    if carpark_number in central_carpark_numbers:
        # Central area
        if eps:
            # Pro-rate every minute
            total_cost += round(expensive_time_counter_minute * (1.20/30), 2)
            total_cost += round(non_expensive_time_counter_minute * (0.60/30), 2)
        else:
            # Assume coupons, count only every half hour
            total_cost += round(math.ceil(expensive_time_counter_minute / 30) * 1.20, 2)
            total_cost += round(math.ceil(non_expensive_time_counter_minute / 30) * 0.60, 2)
    else:
        # Non-central carpark, $0.60/1/2hr
        if eps:
            # Pro-rate every minute
            total_cost += round(total_minutes * (0.60/30), 2)
        else:
            # Assume coupons, count only every half hour
            total_cost += round(math.ceil(total_minutes / 30) * 0.60, 2)

    return total_cost


def short_term_parking_HDB_motorbike(time_to_from):
    # Fare source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
    # $0.65 per lot for whole day (7:00am to 10:30pm) or whole night (10.30pm to 7.00am)

    # Convert into datetime objects
    from_time = datetime.strptime(time_to_from[0], "%Y-%m-%dT%H:%M")
    to_time = datetime.strptime(time_to_from[1], "%Y-%m-%dT%H:%M")-timedelta(minutes=1)

    # Get total time in minutes first
    total_minutes = (to_time - from_time).total_seconds() / 60

    # 10-minute grace period
    if total_minutes <= 10:
        return 0

    # Define time ranges
    day_time_range = (time(7, 0), time(22, 29))
    # Night parking range
    night_time_range = (time(22, 30), time(6, 59))

    total_cost = 0
    # While loop
    counter = 0
    day = False
    night = False
    while counter <= total_minutes:
        datetime_now = from_time + timedelta(minutes=counter)
        if day_time_range[0] <= datetime_now.time() <= day_time_range[1]:
            # Day
            if not day and not night:
                # First day
                day = True
                total_cost += 0.65
            elif not day:
                # Check if new day
                day = True
                night = False
                total_cost += 0.65
        elif datetime_now.time() >= night_time_range[0] or datetime_now.time() <= night_time_range[1]:
            # Night
            if not night and not day:
                # First night
                night = True
                total_cost += 0.65
            elif not night:
                # Check if new night
                day = False
                night = True
                total_cost += 0.65
        counter += 1

    return round(total_cost, 2)


def short_term_parking_HDB_heavy(time_to_from, eps):
    # Fare source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
    # $1.20 per half hour

    # Convert into datetime objects
    from_time = datetime.strptime(time_to_from[0], "%Y-%m-%dT%H:%M")
    to_time = datetime.strptime(time_to_from[1], "%Y-%m-%dT%H:%M")

    # Get total time in minutes first
    total_minutes = (to_time - from_time).total_seconds() / 60

    # 10-minute grace period
    if total_minutes <= 10:
        return 0

    if eps:
        # Pro-rated per minute
        total_cost = round(total_minutes * (1.20 / 30), 2)
    else:
        # Assume coupons, count only every half hour
        total_cost = round(math.ceil(total_minutes/30) * 1.20, 2)

    return total_cost



def get_top_carparks(xy_coords):
    from geopy import distance
    # 2 ways to get top carpark
    # 1. Get top matches via Google Maps API
    # 2. Get top matches via distance calculation in xy_coords, Distance squared = x squared + y squared

    # Get all carparks locations
    records = CarParkInfo.get_all()

    # Calculate distance
    distance_dict = {}
    for record in records:
        distance_dict[record.carpark_number] = {
            'x_coord': record.x_coord_EPSG3414,
            'y_coord': record.y_coord_EPSG3414,
            'x_coord_WGS84': record.x_coord_WGS84,
            'y_coord_WGS84': record.y_coord_WGS84,
            'distance': distance.distance(xy_coords, (record.x_coord_WGS84, record.y_coord_WGS84)).km
        }

    # Sort by distance
    distance_dict = {k: v for k, v in sorted(distance_dict.items(), key=lambda item: item[1]['distance'])}

    return dict(list(distance_dict.items())[:5])
    #
    # for record in records:
    #     print(record.carpark_number)

    #distance_squared =


if __name__ == '__main__':
    # db.create_all()
    # CarParkInfo.update_table()
    #CarParkAvailability.update_table()


    xy_coords = (1.3599598294961113, 103.93624551183646)
    sorted_carparks = get_top_carparks(xy_coords)
    for key, val in sorted_carparks.items():
        print(key)
        print(CarParkInfo.get(key).address)

    # app.run(debug=True)

    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_car(time_range, "ACB", True))
    # print(short_term_parking_HDB_car(time_range, "ACB", False))
    #
    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_motorbike(time_range))
    #
    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_heavy(time_range, True))

