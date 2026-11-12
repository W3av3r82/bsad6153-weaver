"""Load saved US-unit Visual Crossing files. Preview is the safe default.

    .venv/bin/python -B ingest/load.py
    .venv/bin/python -B ingest/load.py --apply   # writes to DATABASE_URL

No API requests. Review before applying. Existing rows are never updated.
"""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TABLES = ('locations', 'daily_conditions', 'hourly_weather', 'stations',
          'weather_station_links')


def number(value, low=None, high=None):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError('Boolean supplied for a numeric field')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('Invalid numeric field') from None
    if not result.is_finite() or (low is not None and result < low) or (
            high is not None and result > high):
        raise ValueError('Numeric field outside its valid range')
    return result


def instant(epoch):
    if isinstance(epoch, bool) or not isinstance(epoch, int):
        raise ValueError('Missing or invalid integer epoch timestamp')
    return datetime.fromtimestamp(epoch, timezone.utc)


def astronomy(day, field, local_date, tz):
    epoch = day.get(field + 'Epoch')
    if epoch is not None:
        return instant(epoch)
    clock = day.get(field)
    if clock is None:
        return None
    return datetime.fromisoformat(f'{local_date}T{clock}').replace(tzinfo=tz)


def prepare(directory):
    """Validate every file before any DB connection; deduplicate by entity keys.

    These are the US-unit files produced by this project's fetch.py. Raw API
    payloads do not identify their units, so do not mix in other downloads.
    Invalid structure/values stop the whole load rather than silently lose rows.
    """
    data = {name: {} for name in TABLES}
    counts = Counter()
    files = sorted(directory.glob('*.json'))
    if not files:
        raise ValueError('No saved JSON files found')
    for path in files:
        try:
            payload = json.loads(path.read_text())
            latitude = number(payload['latitude'], -90, 90)
            longitude = number(payload['longitude'], -180, 180)
            if latitude is None or longitude is None:
                raise ValueError('Location coordinates are required')
            loc = (latitude, longitude)
            tz = ZoneInfo(payload['timezone'])
            name = payload['resolvedAddress']
            if not isinstance(name, str) or not name.strip():
                raise ValueError('Location name is required')
            location = (name, latitude, longitude, payload['timezone'])
            if loc in data['locations'] and data['locations'][loc] != location:
                raise ValueError('Conflicting location metadata')
            data['locations'][loc] = location
            for sid, station in (payload.get('stations') or {}).items():
                if not isinstance(sid, str) or not sid.strip() or station.get('id') != sid:
                    raise ValueError('Invalid or inconsistent station ID')
                data['stations'].setdefault(sid, (sid, station.get('name'),
                    number(station.get('latitude'), -90, 90),
                    number(station.get('longitude'), -180, 180)))
            for day in payload['days']:
                local_date = date.fromisoformat(day['datetime'])
                day_key = (loc, local_date)
                daily = tuple(astronomy(day, field, local_date, tz)
                    for field in ('sunrise', 'sunset', 'moonrise', 'moonset')) + (
                    number(day.get('moonphase'), 0, 1),)
                # Contradictory day records need a deliberate policy, not file ordering.
                if day_key in data['daily_conditions'] and data['daily_conditions'][day_key] != daily:
                    raise ValueError('Conflicting daily astronomy')
                data['daily_conditions'][day_key] = daily
                for hour in day['hours']:
                    when = instant(hour['datetimeEpoch'])
                    if when.astimezone(tz).date() != local_date:
                        raise ValueError('Hour does not belong to its stated local day')
                    source = hour.get('source')
                    if source not in ('obs', 'fcst'):
                        raise ValueError('Unrecognized weather source; review required')
                    values = (local_date, when, source,
                        number(hour.get('temp')),
                        number(hour.get('winddir'), 0, 360),
                        number(hour.get('windspeed'), 0),
                        number(hour.get('precipprob'), 0, 100),
                        number(hour.get('precip'), 0))
                    ids = hour.get('stations') or []
                    if not isinstance(ids, list) or any(
                            not isinstance(s, str) or not s.strip() for s in ids):
                        raise ValueError('Invalid hourly station list')
                    candidate = (values, frozenset(ids))
                    key = (loc, when)
                    existing = data['hourly_weather'].get(key)
                    counts['input_hours'] += 1
                    if existing is not None:
                        counts['duplicate_input_hours'] += 1
                        if existing[0][2] == source:
                            if existing != candidate:
                                raise ValueError('Conflicting same-source weather revisions')
                            continue
                        if source == 'fcst':
                            continue  # Prefer observed weather over forecast in the input.
                    data['hourly_weather'][key] = candidate
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError, OSError) as error:
            raise ValueError(f'{path.name}: invalid or conflicting data ({type(error).__name__})') from None
    for key, (values, ids) in data['hourly_weather'].items():
        for sid in ids:
            if sid not in data['stations']:
                raise ValueError('Station reference has no metadata; load stopped')
            data['weather_station_links'][(key, sid)] = None
        counts['missing_measurements'] += sum(v is None for v in values[3:])
        counts[values[2]] += 1
    counts['files'] = len(files)
    return data, counts


def apply(data, url):
    """One atomic transaction; values always use psycopg %s placeholders."""
    import psycopg
    inserted = Counter()
    # Fixed SQL identifiers only; no data is interpolated into SQL strings.
    with psycopg.connect(url, connect_timeout=10) as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '5s'")
        location_ids = {}
        for key, values in data['locations'].items():
            row = conn.execute('''INSERT INTO public.locations
                (name, latitude, longitude, timezone) VALUES (%s,%s,%s,%s)
                ON CONFLICT (latitude, longitude) DO NOTHING RETURNING location_id''', values).fetchone()
            inserted['locations'] += row is not None
            location_ids[key] = row[0] if row else conn.execute('''SELECT location_id
                FROM public.locations WHERE latitude=%s AND longitude=%s''', key).fetchone()[0]
        for (loc, day), values in data['daily_conditions'].items():
            row = conn.execute('''INSERT INTO public.daily_conditions
                (location_id,local_date,sunrise_at,sunset_at,moonrise_at,moonset_at,moon_phase)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (location_id,local_date) DO NOTHING RETURNING day_id''',
                (location_ids[loc], day, *values)).fetchone()
            inserted['daily_conditions'] += row is not None
        for values in data['stations'].values():
            row = conn.execute('''INSERT INTO public.stations
                (station_id,name,latitude,longitude) VALUES (%s,%s,%s,%s)
                ON CONFLICT (station_id) DO NOTHING RETURNING station_id''', values).fetchone()
            inserted['stations'] += row is not None
        weather_ids = {}
        for key, (values, ids) in data['hourly_weather'].items():
            loc, when = key
            row = conn.execute('''INSERT INTO public.hourly_weather
                (location_id,local_date,valid_at,source,temperature_f,wind_direction_deg,
                 wind_speed_mph,precipitation_probability_pct,precipitation_in)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (location_id,valid_at) DO NOTHING RETURNING weather_id''',
                (location_ids[loc], *values)).fetchone()
            inserted['hourly_weather'] += row is not None
            # Do not modify links of an existing weather row: it may represent
            # an earlier forecast/observation than the selected input version.
            if row:
                weather_ids[key] = row[0]
        for key, sid in data['weather_station_links']:
            if key not in weather_ids:
                continue
            row = conn.execute('''INSERT INTO public.weather_station_links
                (weather_id,station_id) VALUES (%s,%s)
                ON CONFLICT (weather_id,station_id) DO NOTHING RETURNING weather_id''',
                (weather_ids[key], sid)).fetchone()
            inserted['weather_station_links'] += row is not None
        # Exiting the context commits only after all records succeed.
    return inserted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write to Supabase; default is preview only')
    args = parser.parse_args()
    try:
        data, counts = prepare(ROOT / 'data/raw/visual_crossing')
    except Exception as error:
        print(f'Validation failed ({type(error).__name__}). No database connection made.')
        if isinstance(error, ValueError):
            print(str(error))
        return 1
    print('Validated US-unit saved files:', counts['files'])
    for table in TABLES:
        print(f'  {table}: {len(data[table])} prepared records')
    print(f"  Observations: {counts['obs']}; saved forecasts: {counts['fcst']}")
    print(f"  Duplicate input hours: {counts['duplicate_input_hours']}; missing measurements: {counts['missing_measurements']}")
    print('Saved forecasts are snapshots, not current forecasts.')
    if len(data['hourly_weather']) < 500:
        print('Stopped: fewer than 500 distinct hourly records.')
        return 1
    if not args.apply:
        print('PREVIEW ONLY: no .env read, no database connection, no writes.')
        return 0
    from dotenv import dotenv_values
    # Read the owner connection privately; never print it or DB exception text.
    url = dotenv_values(ROOT / '.env').get('DATABASE_URL')
    if not url:
        print('DATABASE_URL is missing or empty. No database connection made.')
        return 1
    try:
        inserted = apply(data, url)
    except Exception as error:
        print(f'Load failed ({type(error).__name__}); transaction was not confirmed. No success claimed.')
        print('Details withheld to protect credentials; inspect the failure privately before retrying.')
        return 1
    print('COMMITTED: newly inserted rows (existing rows and their links left unchanged):')
    for table in TABLES:
        print(f'  {table}: {inserted[table]} inserted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
