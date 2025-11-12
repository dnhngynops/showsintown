from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ..events.models import EventRecord


class EventCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, str] = {}
        self.load()

    @staticmethod
    def _key(event: EventRecord) -> str:
        return "|".join(
            [
                event.venue.casefold(),
                event.event.casefold(),
                event.date.isoformat(),
            ]
        )

    def load(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True), encoding="utf-8")

    def filter_new(self, events: Iterable[EventRecord]) -> list[EventRecord]:
        new_events: list[EventRecord] = []
        for event in events:
            key = self._key(event)
            if key not in self._data:
                new_events.append(event)
        return new_events

    def record_events(self, events: Iterable[EventRecord]) -> None:
        for event in events:
            key = self._key(event)
            self._data[key] = event.date.isoformat()
        self.save()

