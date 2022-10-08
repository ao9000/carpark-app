from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, time
import math
from flask_apscheduler import APScheduler
from geopy import distance

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

    def short_term_parking_HDB_car(from_time_to_time, carpark_number, eps):
        # Fare Source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
        # EPS Source: https://www.hdb.gov.sg/car-parks/shortterm-parking/electronic-parking

        # Unpack
        from_time, to_time = from_time_to_time

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
        # Non-central and central non-premium times is same rate
        # Therefore, night parking is always the same rate regardless of central or not
        quota_minute = round((5 / CarParkInfo.get_short_term_carpark_rates()['car']['central']['non_premium_hours']) * 30, 0)
        if night_parking_counter_minute >= quota_minute:
            # Hit $5 quota
            total_cost = 5
            non_expensive_time_counter_minute -= night_parking_counter_minute
            total_minutes -= night_parking_counter_minute
        else:
            # Never hit, but still init cost
            total_cost = 0

        # Calculate total cost
        if carpark_number in CarParkInfo.get_central_carpark_numbers():
            # Central area
            if eps:
                # Pro-rate every minute
                total_cost += round(expensive_time_counter_minute * (CarParkInfo.get_short_term_carpark_rates()['car']['central']['premium_hours']/30), 2)
                total_cost += round(non_expensive_time_counter_minute * (CarParkInfo.get_short_term_carpark_rates()['car']['central']['non_premium_hours']/30), 2)
            else:
                # Assume coupons, count only every half hour
                total_cost += round(math.ceil(expensive_time_counter_minute / 30) * CarParkInfo.get_short_term_carpark_rates()['car']['central']['premium_hours'], 2)
                total_cost += round(math.ceil(non_expensive_time_counter_minute / 30) * CarParkInfo.get_short_term_carpark_rates()['car']['central']['non_premium_hours'], 2)
        else:
            # Non-central carpark, $0.60/1/2hr
            if eps:
                # Pro-rate every minute
                total_cost += round(total_minutes * (CarParkInfo.get_short_term_carpark_rates()['car']['non_central']/30), 2)
            else:
                # Assume coupons, count only every half hour
                total_cost += round(math.ceil(total_minutes / 30) * CarParkInfo.get_short_term_carpark_rates()['car']['non_central'], 2)

        return total_cost

    def short_term_parking_HDB_motorbike(from_time_to_time):
        # Fare source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
        # $0.65 per lot for whole day (7:00am to 10:30pm) or whole night (10.30pm to 7.00am)

        # Unpack
        from_time, to_time = from_time_to_time
        to_time -= timedelta(minutes=1)

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
                    total_cost += CarParkInfo.get_short_term_carpark_rates()['motorbike']['whole_day']
                elif not day:
                    # Check if new day
                    day = True
                    night = False
                    total_cost += CarParkInfo.get_short_term_carpark_rates()['motorbike']['whole_day']
            elif datetime_now.time() >= night_time_range[0] or datetime_now.time() <= night_time_range[1]:
                # Night
                if not night and not day:
                    # First night
                    night = True
                    total_cost += CarParkInfo.get_short_term_carpark_rates()['motorbike']['whole_night']
                elif not night:
                    # Check if new night
                    day = False
                    night = True
                    total_cost += CarParkInfo.get_short_term_carpark_rates()['motorbike']['whole_night']
            counter += 1

        return round(total_cost, 2)

    def short_term_parking_HDB_heavy(from_time_to_time, eps):
        # Fare source: https://www.hdb.gov.sg/car-parks/shortterm-parking/short-term-parking-charges
        # $1.20 per half hour

        # Unpack
        from_time, to_time = from_time_to_time

        # Get total time in minutes first
        total_minutes = (to_time - from_time).total_seconds() / 60

        # 10-minute grace period
        if total_minutes <= 10:
            return 0

        if eps:
            # Pro-rated per minute
            total_cost = round(total_minutes * (CarParkInfo.get_short_term_carpark_rates()['heavy'] / 30), 2)
        else:
            # Assume coupons, count only every half hour
            total_cost = round(math.ceil(total_minutes/30) * CarParkInfo.get_short_term_carpark_rates()['heavy'], 2)

        return total_cost

    # def long_term_parking_family_season_parking(carpark_number, vehicle_type):
    #     # Source: https://www.hdb.gov.sg/car-parks/season-parking/family-season-parking-fsp/charges
    #
    #     # Get type of carpark from carpark number
    #     carpark_type = CarParkInfo.get(carpark_number).carpark_type
    #
    #     # Normalize vehicle type
    #     match carpark_type:
    #         case 'COVERED CAR PARK' | 'BASEMENT CAR PARK' | 'MECHANISED CAR PARK' | 'MULTI-STOREY CAR PARK':
    #             carpark_type = "sheltered"
    #         case 'MECHANISED AND SURFACE CAR PARK' | 'SURFACE CAR PARK' | 'SURFACE/MULTI-STOREY CAR PARK':
    #             carpark_type = "surface"
    #
    #     fare_dict = {
    #         'car': {'surface': 40, 'sheltered': 55, 'precinct': 47.50},
    #         'motorcycle': {'surface': 7.50, 'sheltered': 8.50, 'precinct': 8.50},
    #         'commercial': {'surface': 92.50, 'sheltered': 92.50, 'precinct': 92.50}
    #     }
    #
    #     return fare_dict[vehicle_type][carpark_type]

    def parking_fare_calculation(short_or_long_term, from_time_to_time, **kwargs):
        # Unpack **kwargs
        carpark_number = kwargs['carpark_number']

        # Get db table for eps
        eps = CarParkInfo.get(carpark_number).electronic_parking_system

        func_mapper_dict = {
            'short_term': {
                'car': short_term_parking_HDB_car(from_time_to_time, carpark_number, eps),
                'motorbike': short_term_parking_HDB_motorbike(from_time_to_time),
                'heavy': short_term_parking_HDB_heavy(from_time_to_time, eps),
            }
        }

        return func_mapper_dict[short_or_long_term]

    def get_nearest_carparks(latitude, longitude, limit=5):
        # 2 ways to get top carpark
        # 1. Get top matches via Google Maps API
        # 2. Get top matches via distance calculation in xy_coords, Distance squared = x squared + y squared

        # Method 1: Google Maps API
        # Google Maps API can allow collation of carpark coordinates to perform 1 API call for all carpark distances
        # API_KEY = "API_KEY_HERE"
        # API_LINK = f"https://maps.googleapis.com/maps/api/distancematrix/json?"
        #
        # # Therefore, collate all carpark coordinates first
        # records = CarParkInfo.get_all()
        #
        # # Call API in groups of 20
        # # Google API has a 2048 character limit for requests
        # distance_dict = {}
        # counter = 0
        # carpark_numbers = []
        # combined_destinations = ''
        # for record in records:
        #     counter+=1
        #     carpark_numbers.append(record.carpark_number)
        #     if combined_destinations == '':
        #         combined_destinations += f"{record.x_coord_WGS84}%2C{record.y_coord_WGS84}"
        #     else:
        #         combined_destinations += f"%7C{record.x_coord_WGS84}%2C{record.y_coord_WGS84}"
        #
        #     if counter == 25:
        #         params = {'key': API_KEY,
        #                   'origins': f"{latitude}%2C{longitude}",
        #                   'destinations': combined_destinations,
        #                   'mode': 'walking'
        #                   }
        #
        #         params_string = "&".join("%s=%s" % (k, v) for k, v in params.items())
        #         response = requests.get(API_LINK, params=params_string)
        #         if response.status_code == 200:
        #             print("SENT API")
        #             data = json.loads(response.text)
        #
        #             for index, item in enumerate(data['rows'][0]['elements'], start=0):
        #                 distance_dict[carpark_numbers[index]] = item['distance']['value']
        #
        #         counter=0
        #         combined_destinations = ''
        #         carpark_numbers = []
        #
        # # Sort by distance
        # sorted_distance_dict = {k: v for k, v in sorted(distance_dict.items(), key=lambda item: item[1], reverse=False)}
        #
        # return dict(list(sorted_distance_dict.items())[:limit])


        # Pros and cons about second method:
        # Pros: No need to call Google Maps API, faster, so much faster. Google API takes time for all the rows of carparks
        # Cons #1: Inaccurate calculation of actual distance, 3D distance not taken into account, if carpark is on a hill, it will ignore the altitude
        # Cons #2: Ignoring un-traversable routes, if carpark is opposite a river, it will ignore the river

        # Method 2: Use formula to calculate distance based on x and y coordinates
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
        # Carpark finding params
        x_coord = request.args.get('x_coord', default=None, type=float)
        y_coord = request.args.get('y_coord', default=None, type=float)
        limit = request.args.get('limit', default=5, type=int)

        # Parking fare params
        datetime_from = request.args.get('datetime_from', default=None, type=str)
        datetime_to = request.args.get('datetime_to', default=None, type=str)

        # Integrity check for carpark finding params
        # Check if both x_coord and y_coord are present
        if not x_coord or not y_coord:
            return jsonify({'error': 'Please provide both x_coord and y_coord'}), 400

        # Check if limit is valid
        if limit < 1:
            return jsonify({'error': 'Limit cannot be below 1'}), 400

        # After performing checks, get top carparks results
        # Get the nearest carparks dict
        nearest_carparks = get_nearest_carparks(x_coord, y_coord, limit)

        # Integrity check fare calculation params
        if datetime_from and datetime_to:
            # Both datetime_from and datetime_to are present and eps is present
            # Check if both are valid
            try:
                from_time = datetime.strptime(datetime_from, "%Y-%m-%dT%H:%M")
                to_time = datetime.strptime(datetime_to, "%Y-%m-%dT%H:%M")
            except ValueError:
                return jsonify({"error": "Invalid datetime format"}), 400

            # Check if datetime_from is later than datetime_to
            if from_time > to_time:
                return jsonify({"error": "datetime_from cannot be later than datetime_to"}), 400
            # Check if datetime_from is equal to datetime_to
            if from_time == to_time:
                return jsonify({"error": "datetime_from cannot be equal to datetime_to"}), 400

            # Calculate short term parking cost
            # Check vehicle type
            parking_fare = {}
            for carpark_number in nearest_carparks.keys():
                parking_fare[carpark_number] = parking_fare_calculation(short_or_long_term='short_term',
                                                                        from_time_to_time=(from_time, to_time),
                                                                        carpark_number=carpark_number)

        elif datetime_from or datetime_to:
            # One of datetime_from or datetime_to is present
            return jsonify({"error": "Both datetime_from and datetime_to must be present together"}), 400
        else:
            # Both datetime_from and datetime_to are not present, no fare calculation
            parking_fare = {}

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
                'short_term_parking_fare': {
                    'car': CarParkInfo.get_short_term_carpark_rates()['car']['central'] if key in CarParkInfo.get_central_carpark_numbers() else CarParkInfo.get_short_term_carpark_rates()['car']['non_central'],
                    'motorbike': CarParkInfo.get_short_term_carpark_rates()['motorbike'],
                    'heavy': CarParkInfo.get_short_term_carpark_rates()['heavy']
                },
                'parking_fare': parking_fare[key] if parking_fare else None,
                **carpark_info.to_dict(),
                'total_lots': carpark_availability[0].total_lots if carpark_availability else None,
                'availability': {item.timestamp.strftime("%m/%d/%Y, %H:%M:%S"): item.lots_available for item in carpark_availability}
            }

        return jsonify(response_dict), 200

    @app.route("/carparks/all", methods=["GET"])
    def return_all_carparks():
        # Get all carparks
        records = CarParkInfo.get_all()

        # Construct response
        response_dict = {}
        # Loop through all carparks
        for record in records:
            # Get carpark availability from carpark number
            carpark_availability = CarParkAvailability.get_all(record.carpark_number)

            # Combine data into response
            response_dict[record.carpark_number] = {
                'short_term_parking_fare': {
                    'car': CarParkInfo.get_short_term_carpark_rates()['car'][
                        'central'] if record.carpark_number in CarParkInfo.get_central_carpark_numbers() else
                    CarParkInfo.get_short_term_carpark_rates()['car']['non_central'],
                    'motorbike': CarParkInfo.get_short_term_carpark_rates()['motorbike'],
                    'heavy': CarParkInfo.get_short_term_carpark_rates()['heavy']
                },
                **record.to_dict(),
                'total_lots': carpark_availability[0].total_lots if carpark_availability else None,
                'availability': {item.timestamp.strftime("%m/%d/%Y, %H:%M:%S"): item.lots_available for item in
                                 carpark_availability}
            }

        return jsonify(response_dict), 200

    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Invalid route"}), 404

    # Create all required tables
    with app.app_context():
        db.create_all()
        CarParkInfo.update_table()
        # CarParkAvailability.update_table()

    return app
