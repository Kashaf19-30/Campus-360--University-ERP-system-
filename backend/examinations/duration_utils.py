"""Parse unlock / edit-window duration from API payloads (hours, minutes, or both)."""
from __future__ import annotations

from datetime import timedelta


def parse_unlock_duration(data, *, default_hours: int = 0, default_minutes: int = 0) -> timedelta:
    """
    Accept hours and/or minutes. At least one must be > 0; otherwise defaults apply.
    Examples: {hours: 2}, {minutes: 30}, {hours: 1, minutes: 15}
    """
    raw_hours = data.get('hours')
    raw_minutes = data.get('minutes')

    def _coerce(raw):
        if raw in (None, ''):
            return None
        val = int(raw)
        return None if val == 0 else val

    hours = _coerce(raw_hours)
    minutes = _coerce(raw_minutes)

    if hours is None and minutes is None:
        hours = default_hours
        minutes = default_minutes
    else:
        hours = hours or 0
        minutes = minutes or 0

    if hours == 0 and minutes == 0:
        raise ValueError('Unlock duration must include hours and/or minutes greater than zero.')

    return timedelta(hours=hours, minutes=minutes)


def format_unlock_duration(delta: timedelta) -> str:
    total_minutes = int(delta.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    parts = []
    if hours:
        parts.append(f'{hours} hour{"s" if hours != 1 else ""}')
    if minutes:
        parts.append(f'{minutes} minute{"s" if minutes != 1 else ""}')
    return ' '.join(parts) if parts else '0 minutes'
