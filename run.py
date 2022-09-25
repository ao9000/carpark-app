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
    id = db.Column(db.Integer, primary_key=True)
    carpark_number = db.Column(db.String(4), nullable=False)
    address = db.Column(db.String(255), nullable=False)

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
    def get(carpark_number):
        return CarParkInfo.query.filter_by(carpark_number=carpark_number).first()

    @staticmethod
    def update(existing_record, new_record):
        existing_record.carpark_number = new_record.carpark_number
        existing_record.address = new_record.address

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
                    # Record does not exist
                    new_record = CarParkInfo(id=record['_id'],
                                             carpark_number=record['car_park_no'],
                                             address=record['address'])
                    new_record.save()
                except exc.IntegrityError as e:
                    db.session.rollback()
                    # Record already exists
                    # Check if record is different
                    new_record = CarParkInfo(id=record['_id'],
                                             carpark_number=record['car_park_no'],
                                             address=record['address'])
                    if (existing_record := CarParkInfo.get(record['car_park_no'])) != new_record:
                        # Record is different
                        # Update record
                        CarParkInfo.update(existing_record, new_record)
                        print(f"Updated record of CarPark Number: {new_record.carpark_number}")


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
                    print(f"Record id {e.params[0]} already exists, rolling back")
                    db.session.rollback()


def short_term_parking_HDB_car(time_to_from, carpark_number, eps):
    # Source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges

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

    # Hours start from 0 to 23
    central_expensive_time_range = (time(6, 0), time(15, 59))

    # Night parking range
    night_parking_time_range = (time(21, 30), time(5, 59))

    counter = 0
    expensive_time_counter_minute = 0
    night_parking_counter_minute = 0
    while counter < total_minutes:
        counter += 1
        datetime_now = from_time + timedelta(minutes=counter)
        if central_expensive_time_range[0] <= datetime_now.time() <= central_expensive_time_range[1] and datetime_now.weekday() != 6:
            # Within expensive range
            expensive_time_counter_minute += 1
        if datetime_now.time() >= night_parking_time_range[0] or datetime_now.time() <= night_parking_time_range[1]:
            # Night parking
            night_parking_counter_minute += 1

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


def calculate_parking_fare_HDB(carpark_number, hours):
    pass


if __name__ == '__main__':
    # db.create_all()
    # CarParkInfo.update_table()
    # CarParkAvailability.update_table()

    # app.run(debug=True)

    time_range = ("2021-03-01T12:00", "2021-03-02T12:00")
    print(short_term_parking_HDB_car(time_range, "ACB", True))

