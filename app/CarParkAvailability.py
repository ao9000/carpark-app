from app import db
import requests
import json
from datetime import datetime
from sqlalchemy import exc


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
