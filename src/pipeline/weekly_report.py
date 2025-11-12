from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from ..cache.storage import EventCache
from ..config import Settings
from ..events.browser import create_driver
from ..events.scraper import BoxOfficeTicketSalesScraper
from ..events.venues import fetch_target_venues
from ..sheets.client import SheetsClient
from ..validation.events import ValidationResult, filter_valid_events

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    fetched: int
    valid: int
    new: int
    inserted: int
    invalid: list[ValidationResult]


def run_weekly_report(settings: Settings, start: date, end: date) -> PipelineResult:
    driver = create_driver(headless=settings.headless)
    try:
        scraper = BoxOfficeTicketSalesScraper(
            driver=driver,
            source_url=settings.source_url,
            timeout=settings.timeout,
        )
        raw_events = scraper.collect_week_events(start, end)
    finally:
        driver.quit()

    valid_events, invalid_results = filter_valid_events(raw_events, start, end)

    if settings.target_venues:
        logger.info(
            "Fetching supplemental events for venues: %s",
            ", ".join(settings.target_venues),
        )
        supplemental = fetch_target_venues(settings.target_venues, start, end)
        if supplemental:
            logger.info("Retrieved %d supplemental venue event(s)", len(supplemental))
            valid_events.extend(supplemental)

    cache = EventCache(settings.cache_file)
    new_events = cache.filter_new(valid_events)

    inserted = 0
    if new_events:
        sheets = SheetsClient(
            spreadsheet_id=settings.spreadsheet_id,
            service_account_file=str(settings.service_account_file),
        )
        inserted = sheets.upsert_events(new_events)
        cache.record_events(new_events)
    else:
        logger.info("No new events to insert after cache filtering.")

    return PipelineResult(
        fetched=len(raw_events),
        valid=len(valid_events),
        new=len(new_events),
        inserted=inserted,
        invalid=invalid_results,
    )

