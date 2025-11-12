from __future__ import annotations

import argparse
import logging
from html import unescape
from typing import Iterable

import pendulum

from ..config import Settings
from ..sheets.client import HEADER, SheetsClient

logger = logging.getLogger(__name__)


def _sanitize_row(row: list[str]) -> list[str]:
    padded = row + [""] * max(0, len(HEADER) - len(row))
    trimmed = padded[: len(HEADER)]

    sanitized = [unescape(cell).strip() for cell in trimmed]

    date_value = sanitized[2]
    if date_value:
        try:
            parsed = pendulum.parse(date_value, strict=False)
            sanitized[2] = parsed.to_date_string()
        except (pendulum.parsing.exceptions.ParserError, ValueError, TypeError) as exc:
            logger.warning("Could not normalize date %r: %s", date_value, exc)
    return sanitized


def normalize_master_sheet(settings: Settings) -> int:
    client = SheetsClient(settings.spreadsheet_id, str(settings.service_account_file))
    rows = client.fetch_rows()
    if not rows:
        client.ensure_header()
        return 0

    header, *data_rows = rows
    normalized = [_sanitize_row(row) for row in data_rows]
    client.overwrite_rows([HEADER] + normalized)
    logger.info("Normalized %d existing row(s) in the Master sheet.", len(normalized))
    return len(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize existing rows in the Master sheet (dates, HTML entities, remove openers)."
    )
    parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        settings = Settings.from_env()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    normalize_master_sheet(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

