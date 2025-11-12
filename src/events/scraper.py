from __future__ import annotations

import copy
import html
import json
import logging
import re
import time
from datetime import date
from typing import Iterable

import pendulum
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .models import EventRecord
from .parsers import parse_event_date, scrub
from .selectors import (
    EVENT_DATE_MONTH_DAY,
    EVENT_DATE_TIME,
    EVENT_LOCATION,
    EVENT_ROW,
    EVENT_TITLE,
)

logger = logging.getLogger(__name__)

ES_REQUEST_PATTERN = re.compile(r"var\s+esRequest\s*=\s*(\{.*?\});", re.DOTALL)
API_ENDPOINT = "https://www.boxofficeticketsales.com/es/v2"


class BoxOfficeTicketSalesScraper:
    def __init__(self, driver: WebDriver, source_url: str, timeout: int = 20) -> None:
        self.driver = driver
        self.source_url = source_url
        self.timeout = timeout

    def _load_all_events(self) -> None:
        max_rounds = 15
        unchanged_rounds = 0
        previous_count = 0

        while unchanged_rounds < max_rounds:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            current_count = len(self.driver.find_elements(By.CSS_SELECTOR, EVENT_ROW))
            if current_count == previous_count:
                unchanged_rounds += 1
            else:
                previous_count = current_count
                unchanged_rounds = 0

    def _iter_event_elements(self) -> Iterable:
        return self.driver.find_elements(By.CSS_SELECTOR, EVENT_ROW)

    def load_page(self) -> None:
        logger.info("Navigating to %s", self.source_url)
        self.driver.get(self.source_url)
        WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, EVENT_ROW))
        )
        self._load_all_events()

    def collect_week_events(self, start: date, end: date) -> list[EventRecord]:
        self.load_page()
        try:
            es_request = self._extract_es_request()
            listings = self._fetch_listings(es_request)
            records = self._build_records_from_listings(listings, start, end)
            logger.info(
                "Collected %d event(s) for the target week via API", len(records)
            )
            return records
        except Exception as exc:  # noqa: BLE001
            logger.exception("API pagination failed, falling back to DOM parsing: %s", exc)
            return self._collect_from_dom(start, end)

    @staticmethod
    def _safe_text(node, selector: str) -> str:
        try:
            return scrub(node.find_element(By.CSS_SELECTOR, selector).text)
        except Exception:
            return ""

    @staticmethod
    def _extract_year(node) -> str | None:
        href = node.get_attribute("href") or ""
        match = re.search(r"-(\d{2})-(\d{2})-(\d{4})(?:-|$)", href)
        if match:
            return match.group(3)
        return None

    def _extract_es_request(self) -> dict:
        html_source = self.driver.page_source
        match = ES_REQUEST_PATTERN.search(html_source)
        if not match:
            raise RuntimeError("esRequest block not found in page source.")
        return json.loads(match.group(1))

    def _fetch_listings(self, es_request: dict) -> list[dict]:
        per_page = es_request.get("perPage") or 50
        if per_page <= 0:
            per_page = 50

        base_payload = {
            "draw": (es_request.get("draw") or 0) + 1,
            "page": 1,
            "start": 0,
            "perPage": per_page,
            "view": copy.deepcopy(es_request.get("view", {})),
            "static": copy.deepcopy(es_request.get("search", {}).get("static", {})),
            "preset": copy.deepcopy(es_request.get("search", {}).get("preset", {})),
            "selected": copy.deepcopy(es_request.get("search", {}).get("selected", {})),
        }

        session = requests.Session()
        results: list[dict] = []
        records_filtered = (
            es_request.get("data", {}).get("recordsFiltered")
            or es_request.get("data", {}).get("recordsTotal")
            or 0
        )

        page = 1
        draw = base_payload["draw"]

        while True:
            payload = copy.deepcopy(base_payload)
            payload.update(
                {
                    "page": page,
                    "start": (page - 1) * per_page,
                    "draw": draw,
                }
            )

            response = session.post(
                API_ENDPOINT, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            body = response.json()
            listings = body.get("data") or []
            if not listings:
                break

            results.extend(listings)
            records_filtered = body.get("recordsFiltered", records_filtered) or records_filtered

            if records_filtered and len(results) >= records_filtered:
                break

            page += 1
            draw += 1

            if page > 50:  # safety guard
                logger.warning("Stopping pagination after 50 pages to avoid runaway loop.")
                break

        return results

    def _build_records_from_listings(
        self, listings: Iterable[dict], start: date, end: date
    ) -> list[EventRecord]:
        records: list[EventRecord] = []
        seen: set[tuple[str, str, date]] = set()

        for listing in listings:
            if (listing.get("type") or "").lower() != "concerts":
                continue
            when = listing.get("datetime_local")
            if not when:
                continue

            try:
                event_date = pendulum.parse(when).date()
            except pendulum.parsing.exceptions.ParserError as exc:
                logger.warning("Could not parse datetime %r: %s", when, exc)
                continue

            if not (start <= event_date <= end):
                continue

            venue_name = listing.get("venue", {}).get("name") or ""
            title = listing.get("title") or listing.get("event") or ""
            title = html.unescape(title).strip()
            venue_name = html.unescape(venue_name).strip()

            performers = listing.get("performers") or []
            artist = performers[0].get("name") if performers else title
            artist = html.unescape(artist or "").strip()

            key = (venue_name.casefold(), title.casefold(), event_date)
            if key in seen:
                continue
            seen.add(key)

            records.append(
                EventRecord(
                    venue=venue_name,
                    event=title,
                    date=event_date,
                    artist=artist,
                )
            )

        return records

    def _collect_from_dom(self, start: date, end: date) -> list[EventRecord]:
        records: list[EventRecord] = []

        for node in self._iter_event_elements():
            title = self._safe_text(node, EVENT_TITLE)
            if not title:
                continue

            location = self._safe_text(node, EVENT_LOCATION)
            venue = location.split(",")[0] if location else ""
            month_day = self._safe_text(node, EVENT_DATE_MONTH_DAY)
            time_text = self._safe_text(node, EVENT_DATE_TIME)
            year = self._extract_year(node)

            event_date = parse_event_date(month_day, time_text, year)
            if not event_date:
                continue

            if start <= event_date <= end:
                records.append(
                    EventRecord(
                        venue=venue,
                        event=title,
                        date=event_date,
                        artist=title,
                    )
                )

        logger.info(
            "Collected %d event(s) for the target week via DOM fallback", len(records)
        )
        return records

