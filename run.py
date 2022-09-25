from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import requests
import json
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

db = SQLAlchemy(app)


class CarParkInfo(db.Model):
    __tablename__ = 'carparkinfo'
    id = db.Column(db.Integer, primary_key=True)
    carpark_number = db.Column(db.String(3), nullable=False)
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
    def update(record, new_record):
        record.car_park_no = new_record.carpark_number
        record.address = new_record.address
        print("Updated!")

        db.session.commit()

    @staticmethod
    def update_all():
        API_LINK = "https://data.gov.sg/api/action/datastore_search?resource_id=139a3035-e624-4f56-b63f-89ae28d4ae4c&limit=3000"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_info = json.loads(response.text)

            for item in carpark_info['result']['records']:
                # Check if record is already in database
                if record := CarParkInfo.get(item['car_park_no']):
                    if record.carpark_number == "ACB":
                        print("Found!")
                    # Record exists
                    # Check if record is different
                    new_record = CarParkInfo(id=item['_id'],
                                          carpark_number=item['car_park_no'],
                                          address=item['address'])
                    if not record == new_record:
                        print("DIFFERENT")
                        # Record is different
                        # Update record
                        CarParkInfo.update(record, new_record)
                else:
                    # Record does not exist
                    record = CarParkInfo(id=item['_id'],
                                          carpark_number=item['car_park_no'],
                                          address=item['address'])
                    record.save()


class CarParkAvailability(db.Model):
    __tablename__ = 'carparkavailability'
    id = db.Column(db.Integer, primary_key=True)
    carpark_number = db.Column(db.String(3), db.ForeignKey('carparkinfo.carpark_number'))
    lots_available = db.Column(db.Integer, nullable=False)
    total_lots = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get(carpark_number):
        return CarParkAvailability.query.filter_by(car_park_no=carpark_number).first()

    @staticmethod
    def update_all():
        API_LINK = "https://api.data.gov.sg/v1/transport/carpark-availability"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_availability = json.loads(response.text)

            for item in carpark_availability['items'][0]['carpark_data']:
                record = CarParkAvailability(car_park_no=item['carpark_number'],
                                                           lots_available=item['carpark_info'][0]['lots_available'],
                                                           total_lots=item['carpark_info'][0]['total_lots'],
                                                           timestamp=datetime.strptime(item['update_datetime'],
                                                                                       "%Y-%m-%dT%H:%M:%S"))
                record.save()


if __name__=='__main__':
    db.create_all()
    CarParkInfo.update_all()
    #CarParkAvailability.update_all()

    # app.run(debug=True)





