# Shows In Town Scraper

Weekly automation for collecting Los Angeles concert listings from BoxOfficeTicketSales and pushing them into a Google Sheet.

## Prerequisites

- Python 3.11+
- Google Cloud project with the Google Sheets API enabled
- Service account credential file with **Editor** access to your Google Sheet
- Google Chrome (latest stable)

## First-Time Setup

1. **Create and download service account credentials**
   - Visit [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project (or select an existing one) and enable the **Google Sheets API**.
   - Create a service account, then generate a JSON key.
   - Share your Google Sheet with the service account email (e.g., `service-account-name@project-id.iam.gserviceaccount.com`) and grant **Editor** access.
   - Save the JSON file somewhere secure on your machine.

2. **Install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   - Copy `env.example` to `.env`.
   - Fill in the absolute path to your JSON key and your Google Sheet ID.
   - Update `CACHE_FILE` if you want the persistent cache stored elsewhere.
   - Optionally override the source URL or headless flag.

## Usage

Run the scraper manually:
```bash
python -m src.main
```

The script fetches events for the current week (Monday through Sunday), validates them, filters out anything previously stored in the local cache, then upserts new rows into the `Master` tab of your sheet in the format:

| Venue | Event | Date | Artist |
|-------|-------|------|--------|

## Automation (macOS launchd)

1. Copy the template into your LaunchAgents folder:
   ```bash
   cp launchd/showsintown.plist.example ~/Library/LaunchAgents/com.showsintown.scraper.plist
   ```
2. Edit the new plist so the paths match your setup:
   - `/Users/<you>/Documents/Cursor/showsInTown/.venv/bin/python`
   - `/Users/<you>/Documents/Cursor/showsInTown/.env`
   - `/Users/<you>/Documents/Cursor/showsInTown`
3. Load the job:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.showsintown.scraper.plist
   ```
   The bundled schedule (`StartCalendarInterval`) runs the scraper every Monday at 08:00. To trigger it manually:
   ```bash
   launchctl start com.showsintown.scraper
   ```
4. Logs land in `/tmp/showsintown.out.log` and `/tmp/showsintown.err.log`. Inspect status any time with:
   ```bash
   launchctl print gui/$UID/com.showsintown.scraper
   ```
   If you edit the plist later, remember to `launchctl unload` before reloading it.

## Automation (GitHub Actions)

Deploy the scraper on GitHub’s hosted runners—no servers required.

1. Add the following repository secrets (Settings → Secrets and variables → Actions):
   - `GCP_SERVICE_ACCOUNT_JSON` – full JSON from your Google service account key.
   - `SPREADSHEET_ID` – the Google Sheet ID (from the sheet URL).
   - `SOURCE_URL` – optional; overrides the default Los Angeles concerts listing.
   - `TARGET_VENUES` – optional comma-separated list for venue fallbacks.
2. Commit the workflow at `.github/workflows/scraper.yml` (already present in this repo). It builds the Docker image and runs the scraper every Monday at 16:00 UTC (~08:00 Pacific).
3. Run manually any time from the Actions tab using the “Run workflow” button.

> Adjust the cron expression in the workflow if you need a different day/time.

## Docker

Build a containerised runner (headless Chrome + scraper bundled together):

```bash
docker build -t showsintown-scraper .
```

Run ad-hoc:

```bash
docker run --rm --env-file .env -v "$(pwd)/data:/app/data" showsintown-scraper
```

Or use Docker Compose:

```bash
docker compose run --rm scraper
```

### Scheduling via Docker

On a Linux/Unix host you can add a cron entry:

```
0 8 * * 1 docker run --rm --env-file /path/to/.env -v /path/to/data:/app/data showsintown-scraper
```

For always-on infrastructure (ECS, Kubernetes, GitHub Actions, etc.) trigger `docker run` or `docker compose run scraper` on the cadence you need.

## Project Structure

- `src/events/` – Selenium browser factory, selectors, and scraping logic (`BoxOfficeTicketSalesScraper`).
- `src/events/venues.py` – Supplemental venue fetcher used to guarantee coverage for key venues.
- `src/validation/` – Guards that ensure required fields are present and dates are within the requested window.
- `src/cache/` – JSON-backed event cache so repeat runs skip already-processed listings.
- `src/sheets/` – Google Sheets client wrapper that appends new rows to the `Master` tab.
- `src/pipeline/` – Orchestration utilities (`run_weekly_report`, time window helpers).
- `src/pipeline/cleanup.py` – One-off normalization script for the `Master` sheet.
- `src/canva/` – Placeholder for future Canva automation.
- `src/notifications/` – Placeholder for future reporting/alerting hooks.

## Development Notes

- Selenium uses `webdriver-manager` to auto-install/update ChromeDriver.
- Event parsing selectors live in `src/events/selectors.py`. Adjust them if the upstream site changes markup.
- When tuning selectors or debugging, run the script with `--no-headless` to watch the browser session and inspect elements with DevTools.
- The city scraper now pages through the Fulcrum `es/v2` endpoint, so all weekly listings are pulled (not just the first 50). Only `type="Concerts"` entries are written.
- Venue fallbacks (`TARGET_VENUES` in `.env`) still ensure specific rooms are included every week.
- The event cache defaults to `data/events_cache.json`; delete the file to force a full refresh:
  ```bash
  rm data/events_cache.json
  python -m src.main
  ```
- Normalize legacy rows (date formats, HTML entities, remove opener column) with:
  ```bash
  python -m src.pipeline.cleanup
  ```
- If you need to guarantee certain venues appear each week (e.g., Troubadour, Exchange LA), set `TARGET_VENUES` in `.env`. The pipeline will scrape each venue page directly and merge those events.

## Canva Automation (Roadmap)

- **Spreadsheet-driven:** Continue using the `Master` sheet as the source for Canva “Bulk Create” uploads or copy/paste.
- **API-driven:** Implement a client in `src/canva/client.py` to push grouped events (by venue) directly into a Canva template when the Bulk Create REST API is production-ready.
- **UI automation:** As a fallback, drive the Canva UI headlessly (e.g., Playwright) using the grouped event data for fully automated graphics.

## Troubleshooting

- If the script can't find Chrome, ensure it's installed in `/Applications/Google Chrome.app`.
- For headless execution, toggle the `headless` option in `src/selenium_driver.py`.
- Re-run `pip install -r requirements.txt` after modifying dependencies.

