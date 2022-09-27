from app.CarParkInfo import CarParkInfo
from app.CarParkAvailability import CarParkAvailability
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    # Init tables with data
    print("Creating tables & populating data...")
    with app.app_context():
        db.create_all()
        CarParkInfo.update_table()
        CarParkAvailability.update_table()

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


    #app.run(host='0.0.0.0', debug=True)