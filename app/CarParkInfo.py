from app import db


class CarParkInfo(db.Model):
    __abstract__ = True

    carpark_number = db.Column(db.String(10), primary_key=True)
    address = db.Column(db.String(255), nullable=True)
    x_coord_WGS84 = db.Column(db.Float, nullable=True)
    y_coord_WGS84 = db.Column(db.Float, nullable=True)

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
        pass
