from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class EventRecord:
    venue: str
    event: str
    date: date
    artist: str

    def to_sheet_row(self) -> list[str]:
        return [
            self.venue,
            self.event,
            self.date.strftime("%Y-%m-%d"),
            self.artist,
        ]

