from datetime import datetime, timedelta, time as dtime, timedelta
from dateutil import tz

def grab_events(api, days: int = 7):
    cal = api.calendar

    local_tz = tz.tzlocal()
    start = datetime.now(local_tz)
    end = start + timedelta(days=days)

    # Variant A (some pyicloud versions)
    if hasattr(cal, "events"):
        return cal.events(from_dt=start, to_dt=end)

    # Variant B (your version most likely)
    if hasattr(cal, "get_events"):
        # as_objs=False tends to return dicts (easier to handle)
        return cal.get_events(from_dt=start, to_dt=end, period="week", as_objs=False)

    raise AttributeError("This pyicloud CalendarService has neither .events() nor .get_events().")

def date_array_to_dt(arr, tzinfo):
    # arr like [20260206, 2026, 2, 6, 13, 0, 780]
    return datetime(arr[1], arr[2], arr[3], arr[4], arr[5], tzinfo=tzinfo)

def events_to_busy_intervals(events: list[dict]) -> list[tuple[datetime, datetime]]:
    local_tz = tz.tzlocal()
    busy = []

    for e in events:
        if e.get("allDay"):
            # optional: skip all-day events so they don't block study time
            continue

        start_arr = e.get("localStartDate") or e.get("startDate")
        end_arr = e.get("localEndDate") or e.get("endDate")
        if not start_arr or not end_arr:
            continue

        start_dt = date_array_to_dt(start_arr, local_tz)
        end_dt = date_array_to_dt(end_arr, local_tz)

        busy.append((start_dt, end_dt))

    busy.sort(key=lambda x: x[0])
    return busy

def build_sleep_intervals(
    days: int = 7,
    sleep_start: dtime = dtime(22, 00),
    sleep_end: dtime = dtime(6, 00),
    days_off = None
):
    """
    Returns a list of (start_dt, end_dt) intervals for sleep for the next N days.
    Handles sleep that crosses midnight (most common case).
    """
    local_tz = tz.tzlocal()
    now = datetime.now(local_tz)
    intervals = []

    if days_off is None:
        days_off = set()

    for i in range(days):
        day = (now + timedelta(days=i)).date()

        weekday_name = day.strftime("%a")  # 'Mon', 'Tue', etc.

        if weekday_name in days_off:
            off_start = datetime(day.year, day.month, day.day, 0, 0, tzinfo=local_tz)
            off_end = off_start + timedelta(days=1)
            intervals.append((off_start, off_end))
            continue

        start_dt = datetime(day.year, day.month, day.day,
                            sleep_start.hour, sleep_start.minute, tzinfo=local_tz)

        # if sleep_end is "earlier" than sleep_start, it ends next day
        end_day = day if sleep_end > sleep_start else (day + timedelta(days=1))
        end_dt = datetime(end_day.year, end_day.month, end_day.day,
                          sleep_end.hour, sleep_end.minute, tzinfo=local_tz)

        intervals.append((start_dt, end_dt))

    return intervals

def merge_intervals(intervals):
    if not intervals:
        return []

    intervals = sorted(intervals, key=lambda x: x[0])
    merged = [list(intervals[0])]

    for s, e in intervals[1:]:
        if s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    return [(s, e) for s, e in merged]
