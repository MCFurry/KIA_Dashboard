import json
import os
from datetime import datetime, timedelta

import plotly.graph_objs as go
from dash import Input, Output, State, callback_context, dcc, html
from hyundai_kia_connect_api import ClimateRequestOptions

import globals

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
START_HOUR = 6
END_HOUR = 23
SLOT_MINUTES = 15
SCHEDULE_FILE = 'scheduled_slots.json'


def generate_time_slots(start_hour, end_hour, slot_minutes):
    slots = []
    t = datetime(2000, 1, 1, start_hour, 0)
    end = datetime(2000, 1, 1, end_hour, 0)
    while t < end:
        slots.append(t.strftime('%H:%M'))
        t += timedelta(minutes=slot_minutes)
    return slots


TIME_SLOTS = generate_time_slots(START_HOUR, END_HOUR, SLOT_MINUTES)


def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_schedule(slots):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(slots, f)


def make_figure(scheduled_slots):
    z = []
    for t in TIME_SLOTS:
        row = []
        for d in DAYS:
            row.append(1 if (d, t) in scheduled_slots else 0)
        z.append(row)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=DAYS,
            y=TIME_SLOTS,
            colorscale=[[0, 'white'], [1, 'lightblue']],
            showscale=False,
            hoverongaps=False,
        )
    )
    # Add grid lines as shapes
    shapes = []
    n_cols = len(DAYS)
    n_rows = len(TIME_SLOTS)
    for i in range(n_cols + 1):
        x0 = i - 0.5
        x1 = i - 0.5
        shapes.append(
            dict(
                type='line',
                xref='x',
                yref='paper',
                x0=x0,
                y0=0,
                x1=x1,
                y1=1,
                line=dict(color='black', width=1),
            )
        )
    for j in range(n_rows + 1):
        y0 = j - 0.5
        y1 = j - 0.5
        shapes.append(
            dict(
                type='line',
                xref='paper',
                yref='y',
                x0=0,
                y0=y0,
                x1=1,
                y1=y1,
                line=dict(color='black', width=1),
            )
        )
    fig.update_layout(
        title='Click a timeslot to schedule climate control',
        xaxis_title='',
        yaxis_title='Time',
        margin=dict(l=40, r=40, t=40, b=40),
        clickmode='event+select',
        yaxis_autorange='reversed',
        height=1200,
        xaxis=dict(
            tickmode='array',
            tickvals=DAYS,
            ticktext=[f'<b>{d}</b>' for d in DAYS],
            side='top',
            ticks='outside',
            tickfont=dict(size=14, family='Arial', color='black'),
            range=[-0.5, n_cols - 0.5],
            constrain='domain',
            fixedrange=True,
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=TIME_SLOTS,
            showgrid=False,
            ticks='outside',
            tickfont=dict(size=10, family='Arial', color='black'),
            range=[-0.5, n_rows - 0.5],
            constrain='domain',
            fixedrange=True,
        ),
        shapes=shapes,
    )
    return fig


def get_calendar_layout(prefix='calendar'):
    return html.Div(
        [
            dcc.Location(id=f'{prefix}-url', refresh=False),
            dcc.Graph(id=f'{prefix}-graph', config={'displayModeBar': False}),
            dcc.Store(id=f'{prefix}-scheduled-slots'),
            html.Div(id=f'{prefix}-action-output', style={'marginTop': 20}),
        ]
    )


def register_calendar_callbacks(app, prefix='calendar'):
    @app.callback(
        Output(f'{prefix}-graph', 'figure'),
        Output(f'{prefix}-scheduled-slots', 'data'),
        Output(f'{prefix}-action-output', 'children'),
        [Input(f'{prefix}-url', 'pathname'), Input(f'{prefix}-graph', 'clickData')],
        State(f'{prefix}-scheduled-slots', 'data'),
    )
    def unified_callback(pathname, clickData, scheduled_slots):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]['prop_id'].startswith(f'{prefix}-url'):
            slots = load_schedule()
            scheduled_set = set(tuple(x) for x in slots)
            fig = make_figure(scheduled_set)
            return fig, slots, ''
        if scheduled_slots is None:
            scheduled_slots = []
        scheduled_set = set(tuple(x) for x in scheduled_slots)
        msg = ''
        changed = False
        if clickData and 'points' in clickData:
            pt = clickData['points'][0]
            day = pt['x']
            time_label = pt['y']
            slot = (day, time_label)
            if slot not in scheduled_set:
                scheduled_set.add(slot)
                msg = f'Action scheduled for {day} at {time_label}.'
                print(msg)
                changed = True
            else:
                scheduled_set.remove(slot)
                msg = f'Action unscheduled for {day} at {time_label}.'
                print(msg)
                changed = True
        slots_list = list(scheduled_set)
        if changed:
            save_schedule(slots_list)
        fig = make_figure(scheduled_set)
        return fig, slots_list, msg


def calendar_background_scheduler():
    from datetime import datetime

    last_triggered = set()
    import time as time_mod

    while True:
        now = datetime.now()
        # Round down to nearest 15 minutes
        minute = (now.minute // 15) * 15
        current_time = now.replace(minute=minute, second=0, microsecond=0)
        time_label = current_time.strftime('%H:%M')
        day_label = now.strftime('%A')
        slots = load_schedule()
        # Each slot is (day, time_label)
        for slot in slots:
            if tuple(slot) == (day_label, time_label):
                # Only print once per slot per time
                if (day_label, time_label) not in last_triggered:
                    try:
                        res = globals.vm.start_climate(
                            vehicle_id=globals.vehicle_id,
                            options=ClimateRequestOptions(
                                set_temp=20.5, duration=15, defrost=True
                            ),
                        )
                    except Exception as e:
                        res = f'Error starting climate control: {e}'
                    print(f'Airco response: {res}')
                    last_triggered.add((day_label, time_label))
        # Clean up last_triggered for slots that are no longer current
        last_triggered = {
            (d, t) for (d, t) in last_triggered if t == time_label and d == day_label
        }
        time_mod.sleep(30)
