from app import db


class CarParkInfo(db.Model):
    __abstract__ = True

    carpark_number = db.Column(db.String(10), primary_key=True)
    address = db.Column(db.String(255), nullable=False)
    x_coord_WGS84 = db.Column(db.Float, nullable=False)
    y_coord_WGS84 = db.Column(db.Float, nullable=False)

    def __eq__(self, other_instance):
        pass

    def to_dict(self):
        pass

    def save(self):
        pass

    @staticmethod
    def update(existing_record, new_record):
        pass

    @staticmethod
    def update_table():
        pass
