from __future__ import annotations

import logging
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials

from ..events.models import EventRecord

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
MASTER_TAB_NAME = "Master"
HEADER = ["Venue", "Event", "Date", "Artist"]


class SheetsClient:
    def __init__(self, spreadsheet_id: str, service_account_file: str) -> None:
        credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
        self._client = gspread.authorize(credentials)
        self._spreadsheet = self._client.open_by_key(spreadsheet_id)

    def ensure_header(self) -> None:
        worksheet = self._get_master_worksheet()
        existing = worksheet.row_values(1)
        if existing[: len(HEADER)] != HEADER:
            worksheet.update(f"A1:{chr(64 + len(HEADER))}1", [HEADER])
        if worksheet.col_count > len(HEADER):
            worksheet.resize(rows=worksheet.row_count, cols=len(HEADER))

    def fetch_rows(self) -> list[list[str]]:
        worksheet = self._get_master_worksheet()
        return worksheet.get_all_values()

    def overwrite_rows(self, rows: list[list[str]]) -> None:
        worksheet = self._get_master_worksheet()
        worksheet.clear()
        if rows:
            worksheet.update("A1", rows)
        self.ensure_header()

    def upsert_events(self, events: Iterable[EventRecord]) -> int:
        worksheet = self._get_master_worksheet()
        self.ensure_header()

        existing_rows = worksheet.get_all_records()
        existing_keys = {
            (row.get("Venue", ""), row.get("Event", ""), row.get("Date", ""))
            for row in existing_rows
        }

        new_rows = []
        for event in events:
            key = (event.venue, event.event, event.date.strftime("%Y-%m-%d"))
            if key not in existing_keys:
                new_rows.append(event.to_sheet_row())
                existing_keys.add(key)

        if not new_rows:
            logger.info("No new events to append to the sheet.")
            return 0

        worksheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        logger.info("Appended %d new row(s) to %s", len(new_rows), MASTER_TAB_NAME)
        return len(new_rows)

    def _get_master_worksheet(self):
        try:
            return self._spreadsheet.worksheet(MASTER_TAB_NAME)
        except gspread.WorksheetNotFound as exc:
            raise RuntimeError(
                f"Worksheet '{MASTER_TAB_NAME}' not found. Please create it manually."
            ) from exc

