"""Date-window helpers for RO App endpoints with bounded query periods."""
from __future__ import annotations

from datetime import date, timedelta


def build_date_windows(date_from: str, date_to: str, max_days: int = 92) -> list[tuple[date, date]]:
    """Split an inclusive ISO date range into contiguous windows of at most max_days."""
    if max_days < 1:
        raise ValueError("max_days must be at least 1")

    start = date.fromisoformat(date_from)
    end = date.fromisoformat(date_to)
    if end < start:
        raise ValueError("date_to must be on or after date_from")

    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + timedelta(days=max_days - 1), end)
        windows.append((cursor, window_end))
        cursor = window_end + timedelta(days=1)
    return windows
