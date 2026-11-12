"""Fetch Visual Crossing weather in date batches; never connect to a database.

Preview first (no network request):
    .venv/bin/python ingest/fetch.py --start 2026-10-01 --end 2026-10-22 --dry-run

Remove --dry-run only after reviewing the request plan and account allowance.
Existing successful responses are reused unless --refresh is explicitly given.
"""

import argparse
import hashlib
import json
import logging
import math
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import dotenv_values
from email.utils import parsedate_to_datetime

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
# Astronomy belongs to daily records; individual hours may omit these fields.
ELEMENTS = (
    "datetime,datetimeEpoch,temp,tempmin,tempmax,winddir,windspeed,"
    "precipprob,precip,sunrise,sunset,moonphase,moonriseEpoch,moonsetEpoch,"
    "source,stations"
)
REQUIRED_HOUR_FIELDS = ("datetimeEpoch", "temp", "winddir", "windspeed", "precip")
REQUEST_PAUSE_SECONDS = 1  # Our precaution, not a provider-published per-second limit.
MAX_ATTEMPTS = 4
LOG = logging.getLogger("fetch")


def date_batches(start, end, size):
    """Both API dates are inclusive; advance to the following calendar day."""
    while start <= end:
        last = min(start + timedelta(days=size - 1), end)
        yield start, last
        start = last + timedelta(days=1)


def retry_delay(response, attempt):
    """Honor Retry-After (seconds or HTTP date), otherwise use 2, 4, 8 seconds."""
    header = response.headers.get("Retry-After") if response is not None else None
    if header:
        try:
            delay = float(header)
        except ValueError:
            try:
                when = parsedate_to_datetime(header)
                delay = (when - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                delay = -1
        if math.isfinite(delay) and delay >= 0:
            return delay
    return 2 ** attempt


def get_response(session, url, params, estimated_cost, remaining_budget):
    """Return (response, attempts); stop after bounded retries without leaking URLs."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Check every attempt, including retries after uncertain timeout costs.
        if estimated_cost * attempt > remaining_budget:
            LOG.error("Another attempt would exceed the run budget; stopping")
            return None, attempt - 1
        # This pause also applies to retries. Never send simultaneous requests.
        time.sleep(REQUEST_PAUSE_SECONDS)
        response = None
        try:
            response = session.get(url, params=params, timeout=(10, 45))
        except (requests.Timeout, requests.ConnectionError):
            LOG.warning("Network failure on attempt %s/%s", attempt, MAX_ATTEMPTS)
        except requests.RequestException:
            LOG.error("Request failed; URL and exception text withheld to protect the key")
            return None, attempt
        else:
            if response.status_code == 200:
                return response, attempt
            if response.status_code != 429 and not 500 <= response.status_code <= 599:
                LOG.error("HTTP %s: not retried (check key, access, or parameters)", response.status_code)
                return None, attempt
            LOG.warning("HTTP %s on attempt %s/%s", response.status_code, attempt, MAX_ATTEMPTS)
        if attempt < MAX_ATTEMPTS:
            delay = retry_delay(response, attempt)
            # A quota reset could be hours away: stop rather than ignore its wait.
            if delay > 120:
                LOG.error("Retry-After requires %.0f seconds; stopping for a later run", delay)
                return None, attempt
            LOG.info("Backing off for %.1f seconds", delay)
            time.sleep(delay)
    LOG.error("Retry limit reached; a daily quota requires waiting for its reset")
    return None, MAX_ATTEMPTS


def inspect_payload(payload, hourly_records, station_ids):
    """Count real, uniquely timestamped hours and report missing fields."""
    if not isinstance(payload, dict) or not isinstance(payload.get("days"), list):
        raise ValueError("Response must contain a days list")
    if any(not isinstance(day, dict) for day in payload["days"]):
        raise ValueError("Day entries must be objects")
    location = (payload.get("latitude"), payload.get("longitude"))
    missing = malformed = duplicate = 0
    referenced = set()
    for day in payload["days"]:
        hours = day.get("hours")
        if not isinstance(hours, list):
            LOG.warning("Day %s has no hourly list", day.get("datetime", "unknown"))
            continue
        for hour in hours:
            if not isinstance(hour, dict) or hour.get("datetimeEpoch") is None:
                malformed += 1
                continue
            identity = (*location, hour["datetimeEpoch"])
            if identity in hourly_records:
                duplicate += 1
            hourly_records.add(identity)
            missing += sum(hour.get(field) is None for field in REQUIRED_HOUR_FIELDS)
            for station in hour.get("stations") or []:
                if isinstance(station, str):
                    referenced.add(station)
    stations = payload.get("stations") or {}
    if not isinstance(stations, dict):
        LOG.warning("Station metadata is not an object")
        stations = {}
    station_ids.update(station for station, details in stations.items() if isinstance(details, dict))
    unresolved = referenced - set(stations)
    LOG.info("Missing core field values=%s; skipped malformed hours=%s; duplicate hours=%s; unresolved station references=%s", missing, malformed, duplicate, len(unresolved))
    return missing, malformed, duplicate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--location", default="Marquette,KS,US")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--batch-days", type=int, default=2)
    parser.add_argument("--budget", type=int, default=600, help="Conservative allowance for this run, not account balance")
    parser.add_argument("--forecast-days", type=int, default=0, help="Optional upcoming complete days, 0 to 14")
    parser.add_argument("--minimum-records", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="Fetch again instead of reusing local responses; uses allowance")
    args = parser.parse_args()
    if args.end < args.start or not 1 <= args.batch_days <= 10:
        parser.error("Dates must be ordered and batch-days must be between 1 and 10")
    if not 0 <= args.forecast_days <= 14 or not 1 <= args.budget <= 1000 or args.minimum_records < 1:
        parser.error("forecast-days must be 0..14, budget 1..1000, and minimum-records positive")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # Calendar date is derived from Kansas time, not the computer's timezone.
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/Chicago")).date()
    if args.end >= today:
        parser.error("Historical end must be before today in Kansas")
    jobs = [("history", first, last) for first, last in date_batches(args.start, args.end, args.batch_days)]
    if args.forecast_days:
        jobs.append(("forecast", today + timedelta(days=1), today + timedelta(days=args.forecast_days)))
    LOG.info("Location=%s; %s request batches; run budget=%s", args.location, len(jobs), args.budget)
    for kind, first, last in jobs:
        LOG.info("Plan: %s %s through %s (inclusive)", kind, first, last)
    if args.dry_run:
        LOG.info("DRY RUN: no key read, no requests sent, and no files written")
        return 0

    # Authentication: read only the named key; never log params or full URLs.
    key = dotenv_values(ROOT / ".env").get("VISUAL_CROSSING_API_KEY")
    if not key:
        LOG.error("VISUAL_CROSSING_API_KEY is missing or blank in .env")
        return 1
    raw_dir = ROOT / "data" / "raw" / "visual_crossing"
    raw_dir.mkdir(parents=True, exist_ok=True)
    location_tag = hashlib.sha256(args.location.encode()).hexdigest()[:12]
    hourly_records, station_ids = set(), set()
    successful = cached = failed = spent = reserved = 0
    quality = [0, 0, 0]
    session = requests.Session()
    for kind, first, last in jobs:
        path = raw_dir / f"{location_tag}_{kind}_{first}_{last}.json"
        payload = None
        if path.exists() and not args.refresh:
            try:
                payload = json.loads(path.read_text())
                counts = inspect_payload(payload, hourly_records, station_ids)
                quality = [a + b for a, b in zip(quality, counts)]
            except (ValueError, OSError):
                LOG.error("Invalid local response %s; retained for inspection", path.name)
                failed += 1
                continue
            cached += 1
            LOG.info("Reused %s; no API request made (forecast may be stale)", path.name)
            continue
        # DST can make a local day 25 hours; reserve 25 rather than 24.
        estimate = (last - first).days * 25 + 25 if kind == "history" else 1
        if reserved + estimate > args.budget:
            LOG.error("Run budget would be exceeded; remaining batches were not requested")
            failed += len(jobs) - successful - cached - failed
            break
        url = f"{ENDPOINT}/{quote(args.location, safe='')}/{first}/{last}"
        params = {"key": key, "unitGroup": "us", "include": "days,hours", "elements": ELEMENTS, "contentType": "json"}
        response, attempts = get_response(
            session, url, params, estimate, args.budget - reserved
        )
        # Reserve attempted calls conservatively, including uncertain timeout costs.
        reserved += estimate * attempts
        if response is None:
            failed += 1
            LOG.error("Stopped after failed batch %s to %s; prior files remain saved", first, last)
            break
        try:
            payload = response.json()
            counts = inspect_payload(payload, hourly_records, station_ids)
        except (ValueError, TypeError):
            LOG.error("Invalid JSON or missing response structure; batch not saved")
            failed += 1
            continue
        quality = [a + b for a, b in zip(quality, counts)]
        cost = payload.get("queryCost")
        if isinstance(cost, (int, float)) and cost >= 0:
            spent += cost
        else:
            LOG.warning("queryCost absent; use account usage page to verify allowance")
        # Save the unmodified API payload, not the request URL or its secret key.
        try:
            path.write_text(json.dumps(payload, indent=2) + "\n")
        except OSError:
            LOG.error("Could not save %s; stopping", path.name)
            failed += 1
            break
        successful += 1
        LOG.info("Saved %s; reported queryCost=%s", path.name, cost)
    session.close()
    LOG.info("SUMMARY: downloaded=%s; reused=%s; failed=%s; unique hourly weather records=%s; related station records=%s; reported new queryCost=%s; conservative reserved allowance=%s; missing values=%s; skipped hours=%s; duplicates=%s", successful, cached, failed, len(hourly_records), len(station_ids), spent, reserved, *quality)
    LOG.info("This run does not know other account usage today; check your account dashboard")
    if len(hourly_records) < args.minimum_records or not station_ids or failed:
        LOG.error("Target not met: need at least %s unique hours, related stations, and no failed batches", args.minimum_records)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
