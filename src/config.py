from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from a .env file if present."""
    env_file = os.getenv("ENV_FILE", ".env")
    env_path = Path(env_file)
    if env_path.is_file():
        load_dotenv(env_path)
    else:
        # Fallback: load .env in current working directory if ENV_FILE is missing
        default_path = Path(".env")
        if default_path.is_file():
            load_dotenv(default_path)


@dataclass(frozen=True)
class Settings:
    source_url: str
    spreadsheet_id: str
    service_account_file: Path
    cache_file: Path
    headless: bool = True
    timeout: int = 20
    target_venues: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        load_environment()

        source_url = os.getenv(
            "SOURCE_URL",
            "https://www.boxofficeticketsales.com/los-angeles/ca?type=Concerts",
        )
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        cache_file = os.getenv("CACHE_FILE", "data/events_cache.json")
        headless = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
        target_venues_raw = os.getenv(
            "TARGET_VENUES", "Troubadour,Exchange LA,SoFi Stadium"
        )
        target_venues = tuple(
            venue.strip()
            for venue in target_venues_raw.split(",")
            if venue.strip()
        )

        missing = [
            name
            for name, value in {
                "SPREADSHEET_ID": spreadsheet_id,
                "GOOGLE_SERVICE_ACCOUNT_FILE": service_account_file,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"Missing required environment variable(s): {', '.join(missing)}"
            )

        return cls(
            source_url=source_url,
            spreadsheet_id=spreadsheet_id,
            service_account_file=Path(service_account_file).expanduser().resolve(),
            cache_file=Path(cache_file).expanduser().resolve(),
            headless=headless,
            target_venues=target_venues,
        )

