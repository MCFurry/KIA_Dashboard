#!/usr/bin/python3

from flask import Flask
import dash
from hyundai_kia_connect_api import *
from dash import dcc, html
import dash_daq as daq
import plotly.express as px

from threading import Thread
import time
import os

import influxdb_client, os, time
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS

USERNAME = os.getenv('USERNAME', 'default_user')
PASSWORD = os.getenv('PASSWORD', 'default_password')
PIN = os.getenv('PIN', '0000')
VIN = os.getenv('VIN', 'default_vin')

INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', 'default_influxdb_token')

LICENSE_PLATE = os.getenv('LICENSE_PLATE', 'HDK-78-N')

vm = VehicleManager(region=1, brand=1, username=USERNAME, password=PASSWORD, pin=PIN)
vehicle_id = ''

influx_org = "myorg"
influx_url = "http://influxdb:8086"
influx_client = influxdb_client.InfluxDBClient(url=influx_url, token=INFLUXDB_TOKEN, org=influx_org)
influx_bucket = "mybucket"
influx_api = influx_client.write_api(write_options=SYNCHRONOUS)

battery_soc_num = 99.0
battery_soh_num = 0.0
battery_12v_soc = 99.0
battery_range_num = 999.0
charging_busy = False
mileage_num = 0
vehicle_pos = {"Vehicle": [LICENSE_PLATE], "latitude": [51.0], "longitude": [5.5]}
vehicle_pos_num = [51.0, 5.5]
latest_update = ''
outside_temp = 0
airo_status = False

mapbox_style='open-street-map'
map_fig = px.scatter_map(vehicle_pos,
                         lat="latitude",
                         lon="longitude",
                         hover_name="Vehicle",
                         map_style=mapbox_style,
                         size=[12],
                         width=100,
                         height=100,
                        )

server = Flask(__name__)

############################## Create Dash app ##############################
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/',
    external_stylesheets=external_stylesheets,
    prevent_initial_callbacks="initial_duplicate",
)
app.title=f'{LICENSE_PLATE} car status'

# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )

# Layout
app.layout = html.Div([
    dcc.Interval(
        id='interval-component', interval=10*1000
    ),
    html.H1(f'{LICENSE_PLATE} car status'),
    html.Div(id='update-txt', style=dict(height='3pc', overflow='auto')),
    html.H4('Battery state of charge:'),
    daq.GraduatedBar(
        id='battery-soc',
        showCurrentValue=True,
        step=5,
        max=100,
        value=0,
    ),
    html.H4('Battery state of health:'),
    daq.GraduatedBar(
        id='battery-soh',
        showCurrentValue=True,
        step=5,
        max=100,
        value=0,
    ),
    html.H4('12v battery state:'),
    daq.GraduatedBar(
        id='12v-soc',
        showCurrentValue=True,
        step=5,
        max=100,
        value=0,
    ),
    html.Div(id='range-txt', style=dict(height='3pc', overflow='auto')),
    html.Div([
        daq.Indicator(
            id='charging-indicator',
            label="Charging status",
            size=25,
            value=False,
            style={'display': 'table-cell'},
        ),
    ], style={'display': 'inline-block'}),
    html.Div(id='dummy-spacer', children='___', style={'display': 'inline-block'}, hidden=True),
    html.Div([
        daq.Indicator(
            id='airco-indicator',
            label="Airco status",
            size=25,
            value=False,
            style={'display': 'table-cell'},
        ),
    ], style={'display': 'inline-block'}),
    html.H4('Outside temperature:'),
    html.Div(id='temperature-txt', style=dict(height='3pc', overflow='auto')),
    html.H4('Car Odometer:'),
    daq.LEDDisplay(
        id='mileage',
        label='total km',
        labelPosition='bottom',
        value=0,
        style={'display': 'table-cell'},
    ),
    html.H4('Gimmicks:'),
    html.Div([
        html.Div(id='airco-output', hidden=True),
        html.Button('Airco', id='airco-button', style={'display': 'inline-block'}),
        html.Div(id='start-charge-output', hidden=True),
        html.Button('Start Charge', id='start-charge-button', style={'display': 'inline-block'}),
        html.Div(id='stop-charge-output', hidden=True),
        html.Button('Stop Charge', id='stop-charge-button', style={'display': 'inline-block'}),
    ]),
    html.Div(id='log-div', style=dict(height='5pc', overflow='auto', border='2px solid powderblue')),
    html.H4('Car Position:'),
    html.Div(id='latitude-txt', style=dict(height='3pc', overflow='auto')),
    html.Div(id='longitude-txt', style=dict(height='3pc', overflow='auto')),
    dcc.Link(
        id='car-position-url',
        href='https://www.google.com/maps?q=51.0,5.5',
        target='_blank',
        title='Google Maps link to location',
    ),
    dash.dcc.Graph(id="map", figure=map_fig)
])

# Callbacks
@app.callback(
    dash.dependencies.Output('update-txt', 'children'),
    dash.dependencies.Input('interval-component', 'n_intervals')
)
def update_stamp(n):
    global latest_update
    print(f'Latest update from: {latest_update} UTC')
    return f'Latest update from: {latest_update} UTC'

@app.callback(
    [dash.dependencies.Output('battery-soc', 'value'),
     dash.dependencies.Output('battery-soh', 'value'),
     dash.dependencies.Output('12v-soc', 'value'),
     dash.dependencies.Output('range-txt', 'children'),
     dash.dependencies.Output('charging-indicator', 'value'),
     dash.dependencies.Output('charging-indicator', 'label')],
    dash.dependencies.Input('interval-component', 'n_intervals')
)
def update_soc(input_value):
    global battery_soc_num, battery_soh_num, battery_12v_soc, battery_range_num, charging_busy
    range_txt = f'Remaining range: {battery_range_num} km'
    charging_txt= 'Charging in progress' if charging_busy else 'Charger disconnected'
    return battery_soc_num, battery_soh_num, battery_12v_soc, range_txt, charging_busy, charging_txt

@app.callback(
    dash.dependencies.Output('mileage', 'value'),
    dash.dependencies.Input('interval-component', 'n_intervals')
)
def update_mileage(input_value):
    global mileage_num
    return mileage_num

@app.callback(
    dash.dependencies.Output('airco-indicator', 'value'),
    dash.dependencies.Output('temperature-txt', 'children'),
    dash.dependencies.Input('interval-component', 'n_intervals')
)
def update_aux(input_value):
    global airo_status, outside_temp
    return airo_status, f'{outside_temp} °C'

@app.callback(
    dash.dependencies.Output('airco-output', 'children'),
    dash.dependencies.Output('log-div', 'children', allow_duplicate=True),
    dash.dependencies.Input('airco-button', 'n_clicks')
)
def update_output(n_clicks):
    cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    res = ''
    if cb_trigger == 'airco-button':
        res = vm.start_climate(vehicle_id=vehicle_id, options=ClimateRequestOptions(set_temp=20.5, duration=15, defrost=True))
        print(f'Airco response: {res}')
    return '', f'Airco response: {res}'

@app.callback(
    dash.dependencies.Output('start-charge-output', 'children'),
    dash.dependencies.Output('log-div', 'children', allow_duplicate=True),
    dash.dependencies.Input('start-charge-button', 'n_clicks')
)
def update_output(n_clicks):
    cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    res = ''
    if cb_trigger == 'start-charge-button':
        res = vm.start_charge(vehicle_id=vehicle_id)
        print(f'start-charge response: {res}')
    return '', f'start-charge response: {res}'

@app.callback(
    dash.dependencies.Output('stop-charge-output', 'children'),
    dash.dependencies.Output('log-div', 'children', allow_duplicate=True),
    dash.dependencies.Input('stop-charge-button', 'n_clicks')
)
def update_output(n_clicks):
    cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    res = ''
    if cb_trigger == 'stop-charge-button':
        res = vm.stop_charge(vehicle_id=vehicle_id)
        print(f'stop-charge response: {res}')
    return '', f'stop-charge response: {res}'

@app.callback(
    [dash.dependencies.Output('latitude-txt', 'children'),
     dash.dependencies.Output('longitude-txt', 'children'),
    dash.dependencies.Output('car-position-url', 'href'),
    dash.dependencies.Output('map', 'figure')],
    [dash.dependencies.Input('interval-component', 'n_intervals')],
    [dash.dependencies.State("map", "figure")]
)
def update_position(value, fig):
    global vehicle_pos_num, vehicle_pos
    lat_text = f'Latitude: {vehicle_pos_num[0]}'
    lon_text = f'Longitude: {vehicle_pos_num[1]}'
    url = f'https://maps.google.com/maps?q={vehicle_pos_num[0]},{vehicle_pos_num[1]}'
    fig = px.scatter_map(vehicle_pos,
                         lat="latitude",
                         lon="longitude",
                         hover_name="Vehicle",
                         map_style=mapbox_style,
                         zoom=13,
                         size=[12],
                         width=1000,
                         height=1000,
                        )
    return lat_text, lon_text, url, fig

############################## Create Flask app ##############################
@server.route("/")
def my_dash_app():
    return app.index()

def rest_updater():
    global vm, vehicle_id, battery_soc_num, battery_soh_num, battery_12v_soc,\
           battery_range_num, charging_busy,\
           vehicle_pos, vehicle_pos_num,\
           mileage_num, latest_update, outside_temp, airo_status
    while True:
        try:
            # Request vehicle info
            vm.check_and_refresh_token()
            vm.update_all_vehicles_with_cached_state()
            for vehicle in vm.vehicles:
                if vm.vehicles[vehicle].VIN == VIN:
                    car = vm.vehicles[vehicle]
                    vehicle_id = car.id
            print(f'Response: {car}')
            battery_soc_num = car.ev_battery_percentage
            print(f"Latest soc found: {battery_soc_num}")
            battery_soh_num = car.ev_battery_soh_percentage
            print(f"Latest soh found: {battery_soh_num}")
            battery_12v_soc = car.car_battery_percentage
            battery_range_num = car.ev_driving_range
            charging_busy = bool(car.ev_battery_is_plugged_in)
            mileage_num = car.odometer
            vehicle_pos_num[0] = car.location_latitude
            vehicle_pos_num[1] = car.location_longitude
            update_db = False
            if latest_update != car.last_updated_at:
                update_db = True
                latest_update = car.last_updated_at

            # Put the latest scraped info in memory
            print(f"Latest range found: {battery_range_num}")
            print(f"Latest mileage found: {mileage_num}")
            print(f"Latest position found: latitude: {vehicle_pos_num[0]} longitude: {vehicle_pos_num[1]}")
            vehicle_pos["latitude"] = vehicle_pos_num[0]
            vehicle_pos["longitude"] = vehicle_pos_num[1]
            outside_temp = car.air_temperature
            airo_status = bool(car.air_control_is_on)

            # Put interesting data in influxDb IF new data is here
            if update_db:
                print(f"Writing data to InfluxDB at t={latest_update}")
                p = (
                    Point("car_status")
                    .tag("car_id", car.id)
                    .time(car.last_updated_at)
                    .field("12v_battery_percentage", car.car_battery_percentage)
                    .field("engine_is_running", car.engine_is_running)
                    .field("smart_key_battery_warning_is_on", car.smart_key_battery_warning_is_on)
                    .field("washer_fluid_warning_is_on", car.washer_fluid_warning_is_on)
                    .field("brake_fluid_warning_is_on", car.brake_fluid_warning_is_on)

                    .field("air_control_is_on", car.air_control_is_on)
                    .field("defrost_is_on", car.defrost_is_on)
                    .field("steering_wheel_heater_is_on", car.steering_wheel_heater_is_on)
                    .field("back_window_heater_is_on", car.back_window_heater_is_on)
                    .field("side_mirror_heater_is_on", car.side_mirror_heater_is_on)
                    .field("front_left_seat_status", True if car.front_left_seat_status == "On" else False)
                    .field("front_right_seat_status", True if car.front_right_seat_status == "On" else False)
                    .field("rear_left_seat_status", True if car.rear_left_seat_status == "On" else False)
                    .field("rear_right_seat_status", True if car.rear_right_seat_status == "On" else False)

                    .field("is_locked", car.is_locked)
                    .field("front_left_door_is_open", car.front_left_door_is_open)
                    .field("front_right_door_is_open", car.front_right_door_is_open)
                    .field("back_left_door_is_open", car.back_left_door_is_open)
                    .field("back_right_door_is_open", car.back_right_door_is_open)
                    .field("trunk_is_open", car.trunk_is_open)
                    .field("hood_is_open", car.hood_is_open)
                    .field("front_left_window_is_open", car.front_left_window_is_open)
                    .field("front_right_window_is_open", car.front_right_window_is_open)
                    .field("back_left_window_is_open", car.back_left_window_is_open)
                    .field("back_right_window_is_open", car.back_right_window_is_open)

                    .field("tire_pressure_all_warning_is_on", car.tire_pressure_all_warning_is_on)
                    .field("tire_pressure_rear_left_warning_is_on", car.tire_pressure_rear_left_warning_is_on)
                    .field("tire_pressure_front_left_warning_is_on", car.tire_pressure_front_left_warning_is_on)
                    .field("tire_pressure_front_right_warning_is_on", car.tire_pressure_front_right_warning_is_on)
                    .field("tire_pressure_rear_right_warning_is_on", car.tire_pressure_rear_right_warning_is_on)

                    .field("total_power_consumed", car.total_power_consumed)
                    .field("total_power_regenerated", car.total_power_regenerated)
                    .field("power_consumption_30d", car.power_consumption_30d)

                    .field("ev_battery_percentage", car.ev_battery_percentage)
                    .field("ev_battery_soh_percentage", car.ev_battery_soh_percentage)
                    .field("ev_battery_is_charging", car.ev_battery_is_charging)
                    .field("ev_battery_is_plugged_in", car.ev_battery_is_plugged_in)

                    .field("location_latitude", car.location_latitude)
                    .field("location_longitude", car.location_longitude)

                    .field("odometer", car.odometer)
                    .field("air_temperature", car.air_temperature)
                    .field("ev_driving_range", car.ev_driving_range)
                )
                influx_api.write(bucket=influx_bucket, record=p)
        except Exception as e:
            print(f"Error requesting info: {e}")
        time.sleep(15*60)

if __name__ == '__main__':
    t = Thread(target=rest_updater)
    t.daemon = True
    t.start()

    server.run(host='0.0.0.0', port=8080, threaded=True, debug=False)
