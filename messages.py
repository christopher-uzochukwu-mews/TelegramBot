"""Format schedule events into Telegram messages."""
from datetime import date, timedelta
from typing import Any

from briefing import get_assignment_briefing
from schedule_loader import (
    format_date_for_display,
    get_events_on,
    get_events_this_week,
    get_next_assignments,
)

TYPE_EMOJI = {
    "assignment": "📋",
    "class": "📅",
    "quiz": "📝",
    "exam": "🎓",
    "discussion": "💬",
    "presentation": "📢",
}

def _emoji(ev: dict) -> str:
    return TYPE_EMOJI.get(ev.get("type", "assignment"), "📌")

def format_event_short(ev: dict) -> str:
    """One line: emoji, course, title, time."""
    e = _emoji(ev)
    course = ev.get("course", "")
    title = ev.get("title", "")
    time_note = ev.get("time_note", "")
    part = f"{e} *{course}* – {title}"
    if time_note:
        part += f" ({time_note})"
    return part

def format_today_message(schedule: list[dict], from_date: date | None = None) -> str:
    """What's due or happening today."""
    from_date = from_date or date.today()
    events = get_events_on(schedule, from_date)
    day_str = format_date_for_display(from_date)
    if not events:
        return f"✨ *Today ({day_str})*\n\nNothing due today – you're clear!"
    lines = [f"📆 *Today: {day_str}*\n"]
    for ev in events:
        lines.append(format_event_short(ev))
    return "\n".join(lines)

def format_tomorrow_message(schedule: list[dict], from_date: date | None = None) -> str:
    from schedule_loader import get_events_tomorrow
    tomorrow = (from_date or date.today()) + timedelta(days=1)
    events = get_events_tomorrow(schedule, from_date)
    day_str = format_date_for_display(tomorrow)
    if not events:
        return f"✨ *Tomorrow ({day_str})*\n\nNo deadlines or classes – you're clear!"
    lines = [f"📆 *Tomorrow: {day_str}*\n"]
    for ev in events:
        lines.append(format_event_short(ev))
    return "\n".join(lines)

def format_week_message(schedule: list[dict], from_date: date | None = None) -> str:
    events = get_events_this_week(schedule, from_date)
    if not events:
        return "This week: no events in the schedule. Enjoy the breather!"
    # Group by date
    by_date: dict[str, list[dict]] = {}
    for ev in events:
        d = ev.get("date", "")
        by_date.setdefault(d, []).append(ev)
    lines = ["📅 *This week*\n"]
    for d in sorted(by_date.keys()):
        try:
            dt = date.fromisoformat(d)
            lines.append(f"\n*{format_date_for_display(dt)}*")
        except ValueError:
            lines.append(f"\n*{d}*")
        for ev in by_date[d]:
            lines.append(format_event_short(ev))
    return "\n".join(lines)

def format_next_assignment_message(schedule: list[dict], from_date: date | None = None) -> str:
    """Message for the closest assignment(s) due (same day), with notes when available."""
    events = get_next_assignments(schedule, from_date)
    if not events:
        return "📋 *Next assignment*\n\nNo upcoming assignments in the schedule."
    d = date.fromisoformat(events[0]["date"])
    day_str = format_date_for_display(d)
    lines = [f"📋 *Closest assignment(s) due: {day_str}*\n"]
    for ev in events:
        briefing = get_assignment_briefing(ev)
        lines.append(format_event_with_briefing(ev, briefing))
    return "\n".join(lines)

def format_event_with_briefing(ev: dict, briefing: str | None) -> str:
    """Full block for one event: title + optional AI briefing."""
    head = format_event_short(ev)
    if briefing:
        return f"{head}\n\n_{briefing}_"
    return head
