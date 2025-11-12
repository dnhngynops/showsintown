from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import replace
from datetime import date

from .config import Settings
from .pipeline.timeframe import current_week_range
from .pipeline.weekly_report import PipelineResult, run_weekly_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape weekly concert listings into Google Sheets."
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        help="Start date (YYYY-MM-DD). Defaults to current week's Monday.",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        help="End date (YYYY-MM-DD). Defaults to current week's Sunday.",
    )
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=None,
        help="Force headless browser mode.",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Disable headless browser mode.",
    )
    return parser.parse_args()


def log_validation_failures(result: PipelineResult) -> None:
    if not result.invalid:
        return
    for failure in result.invalid:
        logging.warning(
            "Dropped event '%s' at '%s' on %s due to: %s",
            failure.event.event,
            failure.event.venue,
            failure.event.date,
            "; ".join(failure.errors),
        )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()

    try:
        settings = Settings.from_env()
    except RuntimeError as exc:
        logging.error("%s", exc)
        return 1

    if args.headless is not None:
        settings = replace(settings, headless=args.headless)

    start, end = current_week_range()
    if args.start:
        start = args.start
    if args.end:
        end = args.end

    logging.info("Targeting events from %s to %s", start, end)

    result = run_weekly_report(settings=settings, start=start, end=end)

    logging.info(
        "Fetched %d event(s); %d valid; %d new; %d inserted.",
        result.fetched,
        result.valid,
        result.new,
        result.inserted,
    )
    log_validation_failures(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())

