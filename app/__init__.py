from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import math
from flask_apscheduler import APScheduler

db = SQLAlchemy()


def create_app():
    from app.CarParkInfo import CarParkInfo
    from app.CarParkAvailability import CarParkAvailability

    # Config
    app = Flask(__name__)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
    db.init_app(app)

    # Init scheduler
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('interval', id='job1', seconds=60*60*24, misfire_grace_time=900)
    def update_carpark_information_db():
        print("Updating CarParkInfo table...")
        with app.app_context():
            db.create_all()
            CarParkInfo.update_table()

    @scheduler.task('interval', id='job2', seconds=60*5, misfire_grace_time=900)
    def update_carpark_availability_db():
        print("Updating CarParkAvailability table...")
        with app.app_context():
            db.create_all()
            CarParkAvailability.update_table()

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

    def get_nearest_carparks(latitude, longitude, limit=5):
        from geopy import distance
        # 2 ways to get top carpark
        # 1. Get top matches via Google Maps API
        # 2. Get top matches via distance calculation in xy_coords, Distance squared = x squared + y squared

        # Try Second method
        # Get all carparks locations
        records = CarParkInfo.get_all()

        # Calculate distance
        distance_dict = {}
        for record in records:
            distance_dict[record.carpark_number] = distance.distance((latitude, longitude), (record.x_coord_WGS84, record.y_coord_WGS84)).km

        # Sort by distance
        sorted_distance_dict = {k: v for k, v in sorted(distance_dict.items(), key=lambda item: item[1], reverse=False)}

        return dict(list(sorted_distance_dict.items())[:limit])

    @app.route("/carparks", methods=["GET"])
    def return_top_carparks():
        # Get route params
        x_coord = request.args.get('x_coord', default=None, type=float)
        y_coord = request.args.get('y_coord', default=None, type=float)
        limit = request.args.get('limit', default=5, type=int)

        # Get the nearest carparks dict
        nearest_carparks = get_nearest_carparks(x_coord, y_coord, limit)

        # Construct response
        response_dict = {}
        for key, value in nearest_carparks.items():
            # key = carpark number
            # value = distance

            # Get carpark details from carpark number
            carpark_info = CarParkInfo.get(key)

            # Get carpark availability from carpark number
            carpark_availability = CarParkAvailability.get_all(key)

            # Combine data into response
            response_dict[key] = {
                'distance': value,
                **carpark_info.to_dict(),
                'total_lots': carpark_availability[0].total_lots,
                'availability': {item.timestamp.strftime("%m/%d/%Y, %H:%M:%S"): item.lots_available for item in carpark_availability}
            }

        return jsonify(response_dict), 200

    @app.errorhandler(404)
    def page_not_found(e):
        return "Invalid route", 404

    # Create all required tables
    with app.app_context():
        db.create_all()

    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_car(time_range, "ACB", True))
    # print(short_term_parking_HDB_car(time_range, "ACB", False))
    #
    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_motorbike(time_range))
    #
    # time_range = ("2021-03-01T07:00", "2021-03-02T07:00")
    # print(short_term_parking_HDB_heavy(time_range, True))

    # xy_coords = (1.3599598294961113, 103.93624551183646)
    # sorted_carparks = get_top_carparks(xy_coords[0], xy_coords[1], 5)
    # for key, val in sorted_carparks.items():
    #     print(key)
    #     print(CarParkInfo.get(key).address)

    return app
