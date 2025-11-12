from __future__ import annotations

"""
Canva automation placeholder.

Two potential implementation paths:

1. Bulk Create CSV upload
   - Export curated rows from Google Sheets.
   - Use the Canva Bulk Create REST endpoint (currently in beta) to inject rows into
     named placeholders within a template.

2. Headless browser automation
   - Drive the Canva UI (Selenium/Playwright) to duplicate a template, paste data,
     and export frames.

Once a direction is chosen, mirror the Sheets client pattern with a dedicated
client class that exposes a `publish(events_by_venue)` method.
"""

from collections import defaultdict
from typing import Iterable

from ..events.models import EventRecord


def group_events_by_venue(events: Iterable[EventRecord]) -> dict[str, list[EventRecord]]:
    grouped: dict[str, list[EventRecord]] = defaultdict(list)
    for event in events:
        grouped[event.venue].append(event)
    return dict(grouped)

