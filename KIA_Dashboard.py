#!/usr/bin/python3

from threading import Thread

import dash
from dash import dcc, html
from flask import Flask

import globals
from calendar_widget_component import (
    calendar_background_scheduler,
    get_calendar_layout,
    register_calendar_callbacks,
)
from main_widget_components import get_main_layout, register_main_callbacks
from rest_updater import rest_updater

server = Flask(__name__)

############################## Create Dash app ##############################
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/',
    external_stylesheets=external_stylesheets,
    prevent_initial_callbacks='initial_duplicate',
)
app.title = f'{globals.LICENSE_PLATE} car status'

# auth = dash_auth.BasicAuth(
#     app,
#     VALID_USERNAME_PASSWORD_PAIRS
# )

# Layout
app.layout = html.Div(
    [
        dcc.Tabs(
            [
                dcc.Tab(label='Home', children=[get_main_layout(prefix='main')]),
                dcc.Tab(
                    label='Climate Control Schedule',
                    children=[get_calendar_layout(prefix='calendar')],
                ),
            ]
        )
    ]
)

register_main_callbacks(app, prefix='main')
register_calendar_callbacks(app, prefix='calendar')


############################## Create Flask app ##############################
@server.route('/')
def my_dash_app():
    return app.index()


if __name__ == '__main__':
    rest_thread = Thread(target=rest_updater, daemon=True)
    rest_thread.start()
    calendar_thread = Thread(target=calendar_background_scheduler, daemon=True)
    calendar_thread.start()

    server.run(host='0.0.0.0', port=8080, threaded=True, debug=False)
