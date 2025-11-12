from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import pendulum

logger = logging.getLogger(__name__)


def parse_event_date(
    month_day: Optional[str],
    time_text: Optional[str],
    year: Optional[str],
) -> date | None:
    if not month_day:
        return None

    pieces = [month_day.strip()]
    if year:
        pieces.append(year.strip())
    if time_text:
        pieces.append(time_text.strip())

    candidate = " ".join(pieces)
    try:
        parsed = pendulum.parse(candidate, strict=False)
        return parsed.date()
    except (pendulum.parsing.exceptions.ParserError, TypeError, ValueError) as exc:
        logger.warning("Could not parse date components %r: %s", candidate, exc)
        return None


def scrub(text: str | None) -> str:
    return text.strip() if text else ""

