# globals.py
import os

LICENSE_PLATE = os.getenv('LICENSE_PLATE', 'ABC-123')

USERNAME = os.getenv('USERNAME', 'default_user')
PASSWORD = os.getenv('PASSWORD', 'default_password')
PIN = os.getenv('PIN', '0000')
VIN = os.getenv('VIN', 'default_vin')

vehicle_id = ''
vm = None

latest_update = None
battery_soc_num = 99.0
battery_soh_num = 0.0
battery_12v_soc = 99.0
battery_range_num = 999.0
charging_busy = False
mileage_num = 0
airo_status = False
outside_temp = 0.0
vehicle_pos = {'Vehicle': [LICENSE_PLATE], 'latitude': [51.0], 'longitude': [5.5]}
vehicle_pos_num = [51.0, 5.5]
vehicle_id = None
mapbox_style = 'open-street-map'
