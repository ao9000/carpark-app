from app import db
import requests
import json
from datetime import datetime
from sqlalchemy import exc


class CarParkAvailability(db.Model):
    __tablename__ = 'CarParkAvailability'
    id = db.Column(db.String(22), primary_key=True)
    carpark_number = db.Column(db.String(4), db.ForeignKey('CarParkInfo.carpark_number'))
    lots_available = db.Column(db.Integer, nullable=False)
    total_lots = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_all(carpark_number):
        return CarParkAvailability.query.filter_by(carpark_number=carpark_number).all()

    @staticmethod
    def update_table():
        API_LINK = "https://api.data.gov.sg/v1/transport/carpark-availability"

        response = requests.get(API_LINK)
        if response.status_code == 200:
            carpark_availability = json.loads(response.text)

            for index, record in enumerate(carpark_availability['items'][0]['carpark_data'], start=1):
                print(f"CarParkAvailability: Processing record {index}/{len(carpark_availability['items'][0]['carpark_data'])}")
                # Create CarParkAvailability object
                new_record = CarParkAvailability(id=f"{record['carpark_number']} {record['update_datetime']}",
                                                 carpark_number=record['carpark_number'],
                                                 lots_available=record['carpark_info'][0]['lots_available'],
                                                 total_lots=record['carpark_info'][0]['total_lots'],
                                                 timestamp=datetime.strptime(record['update_datetime'], "%Y-%m-%dT%H:%M:%S"))
                # Check if record is already in database
                # Try to save the record
                try:
                    new_record.save()
                except exc.IntegrityError as e:
                    # Duplicate record exists, rollback and move on
                    # Duplicated record is confirmed to be the same, therefore no need check
                    db.session.rollback()
