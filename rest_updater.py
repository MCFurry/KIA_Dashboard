import os
import time

import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

import globals

INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'default_influxdb_token')

influx_org = 'myorg'
influx_url = 'http://influxdb:8086'
influx_client = influxdb_client.InfluxDBClient(
    url=influx_url, token=INFLUXDB_TOKEN, org=influx_org
)
influx_bucket = 'mybucket'
influx_api = influx_client.write_api(write_options=SYNCHRONOUS)


def rest_updater():
    while True:
        try:
            if globals.vm is None:
                print('VM not initialized yet, skipping update')
                time.sleep(60)
                continue
            # Request vehicle info
            globals.vm.check_and_refresh_token()
            globals.vm.update_all_vehicles_with_cached_state()
            if not globals.vm.vehicles:
                print('No vehicles found for this account!')
                time.sleep(60)
                continue
            for vehicle in globals.vm.vehicles:
                if globals.vm.vehicles[vehicle].VIN == globals.VIN:
                    car = globals.vm.vehicles[vehicle]
                    globals.vehicle_id = car.id
            if car is None:
                print('Car not found in vehicle list!')
                time.sleep(60)
                continue
            print(f'Response: {car}')
            globals.battery_soc_num = car.ev_battery_percentage
            print(f'Latest soc found: {globals.battery_soc_num}')
            globals.battery_soh_num = car.ev_battery_soh_percentage
            print(f'Latest soh found: {globals.battery_soh_num}')
            globals.battery_12v_soc = car.car_battery_percentage
            globals.battery_range_num = car.ev_driving_range
            globals.charging_busy = bool(car.ev_battery_is_plugged_in)
            globals.mileage_num = car.odometer
            globals.vehicle_pos_num[0] = car.location_latitude
            globals.vehicle_pos_num[1] = car.location_longitude
            update_db = False
            if globals.latest_update != car.last_updated_at:
                update_db = True
                globals.latest_update = car.last_updated_at

            # Put the latest scraped info in memory
            print(f'Latest range found: {globals.battery_range_num}')
            print(f'Latest mileage found: {globals.mileage_num}')
            print(
                f'Latest position found: latitude: {globals.vehicle_pos_num[0]} longitude: {globals.vehicle_pos_num[1]}'
            )
            globals.vehicle_pos['latitude'] = globals.vehicle_pos_num[0]
            globals.vehicle_pos['longitude'] = globals.vehicle_pos_num[1]
            globals.outside_temp = car.air_temperature
            globals.airo_status = bool(car.air_control_is_on)

            # Put interesting data in influxDb IF new data is here
            if update_db:
                print(f'Writing data to InfluxDB at t={globals.latest_update}')
                p = (
                    Point('car_status')
                    .tag('car_id', car.id)
                    .time(car.last_updated_at)
                    .field('12v_battery_percentage', car.car_battery_percentage)
                    .field('engine_is_running', car.engine_is_running)
                    .field('smart_key_battery_warning_is_on', car.smart_key_battery_warning_is_on)
                    .field('washer_fluid_warning_is_on', car.washer_fluid_warning_is_on)
                    .field('brake_fluid_warning_is_on', car.brake_fluid_warning_is_on)
                    .field('air_control_is_on', car.air_control_is_on)
                    .field('defrost_is_on', car.defrost_is_on)
                    .field('steering_wheel_heater_is_on', car.steering_wheel_heater_is_on)
                    .field('back_window_heater_is_on', car.back_window_heater_is_on)
                    .field('side_mirror_heater_is_on', car.side_mirror_heater_is_on)
                    .field(
                        'front_left_seat_status',
                        True if car.front_left_seat_status == 'On' else False,
                    )
                    .field(
                        'front_right_seat_status',
                        True if car.front_right_seat_status == 'On' else False,
                    )
                    .field(
                        'rear_left_seat_status',
                        True if car.rear_left_seat_status == 'On' else False,
                    )
                    .field(
                        'rear_right_seat_status',
                        True if car.rear_right_seat_status == 'On' else False,
                    )
                    .field('is_locked', car.is_locked)
                    .field('front_left_door_is_open', car.front_left_door_is_open)
                    .field('front_right_door_is_open', car.front_right_door_is_open)
                    .field('back_left_door_is_open', car.back_left_door_is_open)
                    .field('back_right_door_is_open', car.back_right_door_is_open)
                    .field('trunk_is_open', car.trunk_is_open)
                    .field('hood_is_open', car.hood_is_open)
                    .field('front_left_window_is_open', car.front_left_window_is_open)
                    .field('front_right_window_is_open', car.front_right_window_is_open)
                    .field('back_left_window_is_open', car.back_left_window_is_open)
                    .field('back_right_window_is_open', car.back_right_window_is_open)
                    .field('tire_pressure_all_warning_is_on', car.tire_pressure_all_warning_is_on)
                    .field(
                        'tire_pressure_rear_left_warning_is_on',
                        car.tire_pressure_rear_left_warning_is_on,
                    )
                    .field(
                        'tire_pressure_front_left_warning_is_on',
                        car.tire_pressure_front_left_warning_is_on,
                    )
                    .field(
                        'tire_pressure_front_right_warning_is_on',
                        car.tire_pressure_front_right_warning_is_on,
                    )
                    .field(
                        'tire_pressure_rear_right_warning_is_on',
                        car.tire_pressure_rear_right_warning_is_on,
                    )
                    .field('total_power_consumed', car.total_power_consumed)
                    .field('total_power_regenerated', car.total_power_regenerated)
                    .field('power_consumption_30d', car.power_consumption_30d)
                    .field('ev_battery_percentage', car.ev_battery_percentage)
                    .field('ev_battery_soh_percentage', car.ev_battery_soh_percentage)
                    .field('ev_battery_is_charging', car.ev_battery_is_charging)
                    .field('ev_battery_is_plugged_in', car.ev_battery_is_plugged_in)
                    .field('location_latitude', car.location_latitude)
                    .field('location_longitude', car.location_longitude)
                    .field('odometer', car.odometer)
                    .field('air_temperature', car.air_temperature)
                    .field('ev_driving_range', car.ev_driving_range)
                )
                influx_api.write(bucket=influx_bucket, record=p)
        except Exception as e:
            print(f'Error requesting info: {e}')
        time.sleep(15 * 60)
