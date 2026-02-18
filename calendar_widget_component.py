import json
import os
from datetime import datetime, timedelta
import pytz
import plotly.graph_objs as go
from dash import callback_context, Input, Output, State, dcc, html
from hyundai_kia_connect_api import ClimateRequestOptions
import time as time_mod

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


def make_figure(scheduled_slots, prefix, timezone_store=None):
    z = []
    tz_store = timezone_store if timezone_store else 'UTC'
    user_timezone = tz_store if tz_store else 'UTC'
    tz = pytz.timezone(user_timezone)
    # Convert all slots to user's local time for display
    display_slots = []
    for slot in scheduled_slots:
        if len(slot) == 3:
            day, time_label, slot_tz = slot
            slot_tz_obj = pytz.timezone(slot_tz)
            # Find the weekday index for the scheduled day
            try:
                day_idx = DAYS.index(day)
            except ValueError:
                day_idx = 0
            # Use a reference Monday of this week, then add day_idx days
            now = datetime.now()
            ref_monday = now - timedelta(days=now.weekday())
            slot_date = ref_monday + timedelta(days=day_idx)
            slot_local = slot_tz_obj.localize(datetime(slot_date.year, slot_date.month, slot_date.day, int(time_label[:2]), int(time_label[3:]), 0, 0))
            slot_user = slot_local.astimezone(tz)
            # Use the user's local weekday and time
            display_slots.append((slot_user.strftime('%A'), slot_user.strftime('%H:%M')))
        else:
            display_slots.append((slot[0], slot[1]))
    for t in TIME_SLOTS:
        row = []
        for d in DAYS:
            row.append(1 if any(ds[0] == d and ds[1] == t for ds in display_slots) else 0)
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
            dcc.Store(id=f'{prefix}-timezone-store'),
            html.Div(id=f'{prefix}-action-output', style={'marginTop': 20}),
        ]
    )


def register_calendar_callbacks(app, prefix='calendar'):
    # Clientside callback to detect browser timezone
    app.clientside_callback(
        '''
        function(n) {
            var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            console.log('Detected browser timezone:', tz);
            return tz;
        }
        ''' ,
        Output(f'{prefix}-timezone-store', 'data'),
        Input(f'{prefix}-url', 'pathname')
    )
    @app.callback(
        Output(f'{prefix}-graph', 'figure'),
        Output(f'{prefix}-scheduled-slots', 'data'),
        Output(f'{prefix}-action-output', 'children'),
        [Input(f'{prefix}-url', 'pathname'), Input(f'{prefix}-graph', 'clickData')],
        [State(f'{prefix}-scheduled-slots', 'data'), State(f'{prefix}-timezone-store', 'data')],
    )
    def unified_callback(pathname, clickData, scheduled_slots, timezone_store):
        ctx = callback_context
        if not ctx.triggered or ctx.triggered[0]['prop_id'].startswith(f'{prefix}-url'):
            slots = load_schedule()
            scheduled_set = set(tuple(x) for x in slots)
            fig = make_figure(scheduled_set, prefix, timezone_store)
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
            # Try to get timezone from dcc.Store
            try:
                tz_store = callback_context.states.get(f'{prefix}-timezone-store.data', 'UTC')
            except Exception:
                tz_store = 'UTC'
            user_timezone = tz_store if tz_store else 'UTC'
            slot = (day, time_label, user_timezone)
            if slot not in scheduled_set:
                scheduled_set.add(slot)
                msg = f'Action scheduled for {day} at {time_label} ({user_timezone}).'
                print(msg)
                changed = True
            else:
                scheduled_set.remove(slot)
                msg = f'Action unscheduled for {day} at {time_label} ({user_timezone}).'
                print(msg)
                changed = True
        slots_list = list(scheduled_set)
        if changed:
            save_schedule(slots_list)
        fig = make_figure(scheduled_set, prefix, timezone_store)
        return fig, slots_list, msg


def calendar_background_scheduler():
    last_triggered = set()

    while True:
        now_utc = datetime.now(pytz.UTC).replace(second=0, microsecond=0)
        slots = load_schedule()
        # Each slot is (day, time_label, timezone)
        for slot in slots:
            if len(slot) == 3:
                day_label, time_label, tz_name = slot
                try:
                    tz = pytz.timezone(tz_name)
                except Exception:
                    tz = pytz.UTC
                # Build local time for today
                local_now = datetime.now(tz)
                # Find the next occurrence of the scheduled day
                # If today is the scheduled day, check time
                if local_now.strftime('%A') == day_label:
                    # Build scheduled local datetime
                    scheduled_local = tz.localize(datetime(local_now.year, local_now.month, local_now.day,
                                                          int(time_label[:2]), int(time_label[3:]), 0, 0))
                    scheduled_utc = scheduled_local.astimezone(pytz.UTC)
                    # If now_utc matches scheduled_utc (rounded to nearest 15 min)
                    minute = (now_utc.minute // 15) * 15
                    current_utc = now_utc.replace(minute=minute)
                    if scheduled_utc.replace(second=0, microsecond=0) == current_utc:
                        # Only print once per slot per time
                        if (day_label, time_label, tz_name) not in last_triggered:
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
                            last_triggered.add((day_label, time_label, tz_name))
        # Clean up last_triggered for slots that are no longer current
        last_triggered = {
            (d, t, tz) for (d, t, tz) in last_triggered if (d, t, tz) in [(slot[0], slot[1], slot[2]) for slot in slots]
        }
        time_mod.sleep(30)
