import dash
import dash_daq as daq
import plotly.express as px
from dash import dcc, html
from hyundai_kia_connect_api import *

import globals


globals.vm = VehicleManager(
    region=1, brand=1, username=globals.USERNAME, password=globals.PASSWORD, pin=globals.PIN
)

def create_vehicle_map(width=600, height=600, zoom=13):
    fig = px.scatter_map(
        globals.vehicle_pos,
        lat='latitude',
        lon='longitude',
        hover_name='Vehicle',
        map_style=globals.mapbox_style,
        size=[12],
        width=width,
        height=height,
        zoom=zoom,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def get_main_layout(prefix='main'):
    return html.Div(
        [
            dcc.Interval(id=f'{prefix}-interval-component', interval=10 * 1000),
            html.H1(f'{globals.LICENSE_PLATE} car status'),
            html.Div(id=f'{prefix}-update-txt', style=dict(height='3pc', overflow='auto')),
            html.H4('Battery state of charge:'),
            daq.GraduatedBar(
                id=f'{prefix}-battery-soc',
                showCurrentValue=True,
                step=5,
                max=100,
                value=0,
            ),
            html.H4('Battery state of health:'),
            daq.GraduatedBar(
                id=f'{prefix}-battery-soh',
                showCurrentValue=True,
                step=5,
                max=100,
                value=0,
            ),
            html.H4('12v battery state:'),
            daq.GraduatedBar(
                id=f'{prefix}-12v-soc',
                showCurrentValue=True,
                step=5,
                max=100,
                value=0,
            ),
            html.Div(id=f'{prefix}-range-txt', style=dict(height='3pc', overflow='auto')),
            html.Div(
                [
                    daq.Indicator(
                        id=f'{prefix}-charging-indicator',
                        label='Charging status',
                        size=25,
                        value=False,
                        style={'display': 'table-cell'},
                    ),
                ],
                style={'display': 'inline-block'},
            ),
            html.Div(
                id=f'{prefix}-dummy-spacer',
                children='___',
                style={'display': 'inline-block'},
                hidden=True,
            ),
            html.Div(
                [
                    daq.Indicator(
                        id=f'{prefix}-airco-indicator',
                        label='Airco status',
                        size=25,
                        value=False,
                        style={'display': 'table-cell'},
                    ),
                ],
                style={'display': 'inline-block'},
            ),
            html.H4('Outside temperature:'),
            html.Div(id=f'{prefix}-temperature-txt', style=dict(height='3pc', overflow='auto')),
            html.H4('Car Odometer:'),
            daq.LEDDisplay(
                id=f'{prefix}-mileage',
                label='total km',
                labelPosition='bottom',
                value=0,
                style={'display': 'table-cell'},
            ),
            html.H4('Gimmicks:'),
            html.Div(
                [
                    html.Div(id=f'{prefix}-airco-output', hidden=True),
                    html.Button(
                        'Airco', id=f'{prefix}-airco-button', style={'display': 'inline-block'}
                    ),
                    html.Div(id=f'{prefix}-start-charge-output', hidden=True),
                    html.Button(
                        'Start Charge',
                        id=f'{prefix}-start-charge-button',
                        style={'display': 'inline-block'},
                    ),
                    html.Div(id=f'{prefix}-stop-charge-output', hidden=True),
                    html.Button(
                        'Stop Charge',
                        id=f'{prefix}-stop-charge-button',
                        style={'display': 'inline-block'},
                    ),
                ]
            ),
            html.Div(
                id=f'{prefix}-log-div',
                style=dict(height='5pc', overflow='auto', border='2px solid powderblue'),
            ),
            html.H4('Car Position:'),
            html.Div(id=f'{prefix}-latitude-txt', style=dict(height='3pc', overflow='auto')),
            html.Div(id=f'{prefix}-longitude-txt', style=dict(height='3pc', overflow='auto')),
            dcc.Link(
                id=f'{prefix}-car-position-url',
                href='https://www.google.com/maps?q=51.0,5.5',
                target='_blank',
                title='Google Maps link to location',
            ),
            dash.dcc.Graph(
                id=f'{prefix}-map',
                figure=create_vehicle_map(),
                style={'width': '100%', 'height': '600px'},
            ),
        ]
    )

def register_main_callbacks(app, prefix='main'):
    # Callbacks
    @app.callback(
        dash.dependencies.Output(f'{prefix}-update-txt', 'children'),
        dash.dependencies.Input(f'{prefix}-interval-component', 'n_intervals'),
    )
    def update_stamp(n):
        print(f'Latest update from: {globals.latest_update} UTC')
        return f'Latest update from: {globals.latest_update} UTC'

    @app.callback(
        [
            dash.dependencies.Output(f'{prefix}-battery-soc', 'value'),
            dash.dependencies.Output(f'{prefix}-battery-soh', 'value'),
            dash.dependencies.Output(f'{prefix}-12v-soc', 'value'),
            dash.dependencies.Output(f'{prefix}-range-txt', 'children'),
            dash.dependencies.Output(f'{prefix}-charging-indicator', 'value'),
            dash.dependencies.Output(f'{prefix}-charging-indicator', 'label'),
        ],
        dash.dependencies.Input(f'{prefix}-interval-component', 'n_intervals'),
    )
    def update_soc(input_value):
        range_txt = f'Remaining range: {globals.battery_range_num} km'
        charging_txt = 'Charging in progress' if globals.charging_busy else 'Charger disconnected'
        return (
            globals.battery_soc_num,
            globals.battery_soh_num,
            globals.battery_12v_soc,
            range_txt,
            globals.charging_busy,
            charging_txt,
        )

    @app.callback(
        dash.dependencies.Output(f'{prefix}-mileage', 'value'),
        dash.dependencies.Input(f'{prefix}-interval-component', 'n_intervals'),
    )
    def update_mileage(input_value):
        return globals.mileage_num

    @app.callback(
        dash.dependencies.Output(f'{prefix}-airco-indicator', 'value'),
        dash.dependencies.Output(f'{prefix}-temperature-txt', 'children'),
        dash.dependencies.Input(f'{prefix}-interval-component', 'n_intervals'),
    )
    def update_aux(input_value):
        return globals.airo_status, f'{globals.outside_temp} °C'

    @app.callback(
        dash.dependencies.Output(f'{prefix}-airco-output', 'children'),
        dash.dependencies.Output(f'{prefix}-log-div', 'children', allow_duplicate=True),
        dash.dependencies.Input(f'{prefix}-airco-button', 'n_clicks'),
    )
    def update_output(n_clicks):
        cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
        res = ''
        if cb_trigger == f'{prefix}-airco-button':
            res = globals.vm.start_climate(
                vehicle_id=globals.vehicle_id,
                options=ClimateRequestOptions(set_temp=20.5, duration=15, defrost=True),
            )
            print(f'Airco response: {res}')
        return '', f'Airco response: {res}'

    @app.callback(
        dash.dependencies.Output(f'{prefix}-start-charge-output', 'children'),
        dash.dependencies.Output(f'{prefix}-log-div', 'children', allow_duplicate=True),
        dash.dependencies.Input(f'{prefix}-start-charge-button', 'n_clicks'),
    )
    def update_output(n_clicks):
        cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
        res = ''
        if cb_trigger == f'{prefix}-start-charge-button':
            res = globals.vm.start_charge(vehicle_id=globals.vehicle_id)
            print(f'start-charge response: {res}')
        return '', f'start-charge response: {res}'

    @app.callback(
        dash.dependencies.Output(f'{prefix}-stop-charge-output', 'children'),
        dash.dependencies.Output(f'{prefix}-log-div', 'children', allow_duplicate=True),
        dash.dependencies.Input(f'{prefix}-stop-charge-button', 'n_clicks'),
    )
    def update_output(n_clicks):
        cb_trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
        res = ''
        if cb_trigger == f'{prefix}-stop-charge-button':
            res = globals.vm.stop_charge(vehicle_id=globals.vehicle_id)
            print(f'stop-charge response: {res}')
        return '', f'stop-charge response: {res}'

    @app.callback(
        [
            dash.dependencies.Output(f'{prefix}-latitude-txt', 'children'),
            dash.dependencies.Output(f'{prefix}-longitude-txt', 'children'),
            dash.dependencies.Output(f'{prefix}-car-position-url', 'href'),
            dash.dependencies.Output(f'{prefix}-map', 'figure'),
        ],
        [dash.dependencies.Input(f'{prefix}-interval-component', 'n_intervals')],
        [dash.dependencies.State(f'{prefix}-map', 'figure')],
    )
    def update_position(value, fig):
        lat_text = f'Latitude: {globals.vehicle_pos_num[0]}'
        lon_text = f'Longitude: {globals.vehicle_pos_num[1]}'
        url = f'https://maps.google.com/maps?q={globals.vehicle_pos_num[0]},{globals.vehicle_pos_num[1]}'
        fig = create_vehicle_map()
        return lat_text, lon_text, url, fig
