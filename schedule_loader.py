"""Load and query MBA schedule."""
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

def load_schedule(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_events_on(schedule: list[dict], d: date) -> list[dict]:
    """Return events on exactly this date (date string YYYY-MM-DD)."""
    ds = d.strftime("%Y-%m-%d")
    return [e for e in schedule if e.get("date") == ds]

def get_events_tomorrow(schedule: list[dict], from_date: date | None = None) -> list[dict]:
    from_date = from_date or date.today()
    tomorrow = from_date + timedelta(days=1)
    return get_events_on(schedule, tomorrow)

def get_events_this_week(schedule: list[dict], from_date: date | None = None) -> list[dict]:
    """Events in the calendar week (Mon–Sun) that contains today."""
    from_date = from_date or date.today()
    # Monday = 0, Sunday = 6
    start = from_date - timedelta(days=from_date.weekday())
    end = start + timedelta(days=6)
    result = []
    for e in schedule:
        try:
            ed = date.fromisoformat(e["date"])
        except (KeyError, ValueError):
            continue
        if start <= ed <= end:
            result.append(e)
    result.sort(key=lambda x: (x["date"], x.get("course", ""), x.get("title", "")))
    return result

def get_next_assignments(schedule: list[dict], from_date: date | None = None) -> list[dict]:
    """Assignments due on the nearest future date (today or later). Returns all assignments on that date."""
    from_date = from_date or date.today()
    assignments = []
    for e in schedule:
        if e.get("type") != "assignment":
            continue
        try:
            ed = date.fromisoformat(e["date"])
        except (KeyError, ValueError):
            continue
        if ed >= from_date:
            assignments.append(e)
    if not assignments:
        return []
    assignments.sort(key=lambda x: (x["date"], x.get("course", ""), x.get("title", "")))
    first_date = assignments[0]["date"]
    return [e for e in assignments if e["date"] == first_date]

def format_date_for_display(d: date) -> str:
    return d.strftime("%A, %B %d")
