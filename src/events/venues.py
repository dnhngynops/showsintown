from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Iterable

import pendulum
import requests

from .models import EventRecord

logger = logging.getLogger(__name__)

ES_REQUEST_PATTERN = re.compile(r"esRequest\s*=\s*(\{.*?\});", re.DOTALL)

# Explicit slug overrides when naive slugification would fail.
VENUE_SLUG_OVERRIDES: dict[str, str] = {
    "Exchange LA": "exchange-la",
    "SoFi Stadium": "sofi-stadium",
    "Troubadour": "troubadour",
}


def _slugify(name: str) -> str:
    if not name:
        raise ValueError("Venue name is required to derive slug.")

    if name in VENUE_SLUG_OVERRIDES:
        return VENUE_SLUG_OVERRIDES[name]

    slug = name.lower()
    slug = re.sub(r"&", " and ", slug)
    slug = re.sub(r"[()'’]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def _extract_es_request(html: str) -> dict:
    match = ES_REQUEST_PATTERN.search(html)
    if not match:
        raise ValueError("esRequest JSON block not found on venue page.")
    block = match.group(1)
    return json.loads(block)


def fetch_venue_events(
    venue_name: str,
    start: date,
    end: date,
    session: requests.Session | None = None,
) -> list[EventRecord]:
    slug = _slugify(venue_name)
    url = f"https://www.boxofficeticketsales.com/venues/{slug}"

    client = session or requests.Session()
    logger.debug("Fetching venue page for %s (%s)", venue_name, url)

    response = client.get(url, timeout=20)
    response.raise_for_status()

    es_request = _extract_es_request(response.text)
    data = es_request.get("data", {}).get("data", [])

    events: list[EventRecord] = []
    for entry in data:
        if (entry.get("type") or "").lower() != "concerts":
            continue

        when = entry.get("datetime_local")
        if not when:
            continue
        try:
            parsed = pendulum.parse(when)
        except pendulum.parsing.exceptions.ParserError:
            logger.warning("Could not parse datetime %r for venue %s", when, venue_name)
            continue

        event_date = parsed.date()
        if not (start <= event_date <= end):
            continue

        venue = entry.get("venue", {}).get("name", venue_name)
        title = entry.get("title") or entry.get("event") or venue_name

        events.append(
            EventRecord(
                venue=venue,
                event=title,
                date=event_date,
                artist=title,
            )
        )

    logger.info("Fetched %d event(s) for venue %s", len(events), venue_name)
    return events


def fetch_target_venues(
    venues: Iterable[str],
    start: date,
    end: date,
    session: requests.Session | None = None,
) -> list[EventRecord]:
    client = session or requests.Session()
    collected: list[EventRecord] = []
    for venue in venues:
        try:
            collected.extend(fetch_venue_events(venue, start, end, session=client))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to fetch venue %s: %s", venue, exc)
    return collected

