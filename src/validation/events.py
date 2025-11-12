from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ..events.models import EventRecord


@dataclass(slots=True)
class ValidationResult:
    event: EventRecord
    is_valid: bool
    errors: list[str]


REQUIRED_FIELDS = ("venue", "event", "artist")


def validate_event(event: EventRecord, start: date, end: date) -> ValidationResult:
    errors: list[str] = []

    for field_name in REQUIRED_FIELDS:
        value = getattr(event, field_name)
        if isinstance(value, str):
            value = value.strip()
        if not value:
            errors.append(f"{field_name.title()} is required.")

    if event.date < start or event.date > end:
        errors.append("Event date is outside the requested range.")

    return ValidationResult(event=event, is_valid=not errors, errors=errors)


def filter_valid_events(
    events: Iterable[EventRecord], start: date, end: date
) -> tuple[list[EventRecord], list[ValidationResult]]:
    valid: list[EventRecord] = []
    failures: list[ValidationResult] = []

    for event in events:
        result = validate_event(event, start, end)
        if result.is_valid:
            valid.append(result.event)
        else:
            failures.append(result)

    return valid, failures

