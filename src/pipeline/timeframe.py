from __future__ import annotations

from datetime import date, datetime, timedelta


def current_week_range(reference: date | None = None) -> tuple[date, date]:
    ref = reference or datetime.today().date()
    start = ref - timedelta(days=ref.weekday())
    end = start + timedelta(days=6)
    return start, end

