"""Refresh the current forecast window for two Kansas towns.

Default: explain the plan without reading credentials or making connections.
Apply only after review: .venv/bin/python -B ingest/sync.py --apply
Run offline payload replay: --apply --replay-dir PATH (never a scheduled success).
DATABASE_URL and VISUAL_CROSSING_API_KEY come from environment first, then .env.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import os
import shutil
from pathlib import Path
import tempfile
from urllib.parse import quote

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
import requests
from dotenv import dotenv_values

from fetch import ENDPOINT, ELEMENTS, get_response
from load import prepare, DataValidationError, instant

ROOT = Path(__file__).resolve().parents[1]
TOWNS = ('Marquette,KS,US', 'Elk City,KS,US')
LOCK_ID = 6153003
# Two forecast requests normally cost 2 units. At most 4 attempts per town.
# Reserve one unit for each attempt, including uncertain timeout costs.
RUN_BUDGET = 8


class SyncValidationError(ValueError):
    """Only fixed, developer-written messages may be supplied here."""


def safe_error(error, stage):
    # Arbitrary ValueError/HTTP/DB messages may include credentials. Never echo.
    reason = str(error) if isinstance(error, (SyncValidationError, DataValidationError)) else type(error).__name__
    return f'{stage}: {reason}'


def upsert(conn, table, keys, values):
    """Fixed caller-selected identifiers, bound values; update only differences.

    The sync advisory lock serializes this pipeline. RETURNING distinguishes a
    changed row from a no-op. Existence is read first to classify insert/update.
    """
    names = list(values)
    key_names = list(keys)
    where = sql.SQL(' AND ').join(sql.SQL('{} = %s').format(sql.Identifier(k))
                                  for k in key_names)
    existed = conn.execute(sql.SQL('SELECT 1 FROM public.{} WHERE {}').format(
        sql.Identifier(table), where), tuple(keys.values())).fetchone() is not None
    changes = [n for n in names if n not in keys]
    query = sql.SQL('INSERT INTO public.{} ({}) VALUES ({}) ON CONFLICT ({}) ').format(
        sql.Identifier(table),
        sql.SQL(',').join(map(sql.Identifier, names)),
        sql.SQL(',').join(sql.Placeholder() for _ in names),
        sql.SQL(',').join(map(sql.Identifier, key_names)))
    if changes:
        assignments = sql.SQL(',').join(sql.SQL('{}=EXCLUDED.{}').format(
            sql.Identifier(n), sql.Identifier(n)) for n in changes)
        different = sql.SQL(' OR ').join(sql.SQL('{}.{} IS DISTINCT FROM EXCLUDED.{}').format(
            sql.Identifier(table), sql.Identifier(n), sql.Identifier(n)) for n in changes)
        query += sql.SQL('DO UPDATE SET {}, last_updated_at=now() WHERE ({})').format(
            assignments, different)
        # A current forecast must never replace an actual observation.
        if table == 'hourly_weather':
            query += sql.SQL(" AND NOT (hourly_weather.source='obs' AND EXCLUDED.source='fcst')")
    else:
        query += sql.SQL('DO NOTHING')
    query += sql.SQL(' RETURNING 1')
    changed = conn.execute(query, tuple(values.values())).fetchone() is not None
    return 'updated' if changed and existed else 'inserted' if changed else 'unchanged'


def write_data(conn, data):
    counts = Counter()
    ids = {}
    for loc, row in data['locations'].items():
        values = dict(zip(('name','latitude','longitude','timezone'), row))
        counts['locations_' + upsert(conn, 'locations',
            dict(zip(('latitude','longitude'),loc)), values)] += 1
        ids[loc] = conn.execute('SELECT location_id FROM public.locations WHERE latitude=%s AND longitude=%s',loc).fetchone()[0]
    for (loc, day), row in data['daily_conditions'].items():
        keys = dict(location_id=ids[loc], local_date=day)
        values = {**keys, **dict(zip(('sunrise_at','sunset_at','moonrise_at','moonset_at','moon_phase'),row))}
        counts['days_' + upsert(conn,'daily_conditions',keys,values)] += 1
    for sid, row in data['stations'].items():
        values = dict(zip(('station_id','name','latitude','longitude'),row))
        counts['stations_' + upsert(conn,'stations',dict(station_id=sid),values)] += 1
    through = {}
    for (loc, when), (row, station_ids) in data['hourly_weather'].items():
        keys = dict(location_id=ids[loc],valid_at=when)
        values = dict(location_id=ids[loc], **dict(zip(('local_date','valid_at','source',
            'temperature_f','wind_direction_deg','wind_speed_mph',
            'precipitation_probability_pct','precipitation_in'),row)))
        outcome = upsert(conn,'hourly_weather',keys,values)
        counts[outcome] += 1
        weather_id, stored_source = conn.execute('SELECT weather_id,source FROM public.hourly_weather WHERE location_id=%s AND valid_at=%s',
            (ids[loc],when)).fetchone()
        if stored_source == row[2]:
            old = {r[0] for r in conn.execute('SELECT station_id FROM public.weather_station_links WHERE weather_id=%s',(weather_id,))}
            for sid in old - station_ids:
                conn.execute('DELETE FROM public.weather_station_links WHERE weather_id=%s AND station_id=%s',(weather_id,sid))
                counts['links_deleted'] += 1
            for sid in station_ids - old:
                conn.execute('INSERT INTO public.weather_station_links (weather_id,station_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(weather_id,sid))
                counts['links_inserted'] += 1
        through[ids[loc]] = max(through.get(ids[loc],when),when)
    return counts, through


def fetch_forecasts(key, directory, progress=None):
    if not key:
        raise SyncValidationError('API key is missing')
    spent = Decimal(0)
    reserved = 0
    for i, town in enumerate(TOWNS):
        with requests.Session() as session:
            response, attempts = get_response(session,
                ENDPOINT + '/' + quote(town,safe=''),
                {'key':key, 'unitGroup':'us', 'include':'days,hours,fcst',
                 'elements':ELEMENTS, 'contentType':'json'}, 1, RUN_BUDGET-reserved)
        reserved += attempts
        if progress is not None:
            progress["attempts"] = reserved
        if response is None:
            raise RuntimeError('Forecast request failed after bounded retries')
        payload = response.json()
        cost = Decimal(str(payload.get('queryCost')))
        if not cost.is_finite() or cost < 0 or cost > 1:
            raise SyncValidationError('Unexpected forecast queryCost; stop for account review')
        spent += cost
        if progress is not None:
            progress["query_cost"] = spent
        if not payload.get('days') or not any(d.get('hours') for d in payload['days']):
            raise SyncValidationError('Empty forecast response')
        # Save only response JSON, never request URLs/parameters or the API key.
        serialized = json.dumps(payload)
        if key in serialized:
            raise SyncValidationError('Response unexpectedly contains API key; not saved')
        Path(directory,f'{i}.json').write_text(serialized)
        if progress is not None:
            progress['response_hours'] = progress.get('response_hours', 0) + sum(
                len(d.get('hours') or []) for d in payload['days'])
    return spent, reserved


def prepare_forecasts(directory):
    """Filter only missing-source elapsed hours; preserve original snapshots.

    Snapshot file mtime is used as the conservative capture-time boundary.
    Future unlabeled hours or any unexpected nonempty label stop validation.
    No hour is relabeled as a forecast.
    """
    omitted = 0
    with tempfile.TemporaryDirectory() as filtered:
        for index, path in enumerate(sorted(Path(directory).glob('*.json'))):
            payload = json.loads(path.read_text())
            captured = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            for day in payload['days']:
                retained = []
                for hour in day['hours']:
                    if hour.get('source') == 'fcst':
                        retained.append(hour)
                    elif hour.get('source') is None and instant(hour['datetimeEpoch']) < captured:
                        omitted += 1
                    else:
                        raise SyncValidationError('Future unlabeled hour or unexpected source; review required')
                day['hours'] = retained
            Path(filtered, f'{index}.json').write_text(json.dumps(payload))
        data, counts = prepare(Path(filtered))
    if not data['hourly_weather']:
        raise SyncValidationError('No explicitly labeled forecast hours remain')
    print(f'Excluded elapsed hours without source: {omitted}; labeled forecast hours: {len(data["hourly_weather"])}')
    return data, counts, omitted


def run(url, key, trigger, replay=None):
    run_id = None
    lock = False
    fetched = 0
    cost = Decimal(0)
    attempts = 0
    progress = {}
    stage = 'start and concurrency check'
    with psycopg.connect(url,connect_timeout=10,autocommit=True) as conn:
        conn.execute("SET statement_timeout = '30s'")
        conn.execute("SET lock_timeout = '5s'")
        run_id = conn.execute('''INSERT INTO public.sync_runs (status,trigger,error_message,details)
            VALUES ('failed',%s,'Run in progress or interrupted',%s) RETURNING run_id''',
            (trigger,Jsonb({'mode':'replay' if replay else 'live'}))).fetchone()[0]
        try:
            lock = conn.execute('SELECT pg_try_advisory_lock(%s)',(LOCK_ID,)).fetchone()[0]
            if not lock:
                raise RuntimeError('Another sync is running')
            with tempfile.TemporaryDirectory() as directory:
                if replay:
                    stage = 'validate replay files'
                    data, _, omitted = prepare_forecasts(Path(replay))
                else:
                    stage = 'request forecasts and check allowance'
                    cost, attempts = fetch_forecasts(key,directory,progress)
                    stage = 'retain responses in ignored local storage'
                    saved = ROOT / 'data' / 'raw' / 'sync_forecasts' / f'run_{run_id}'
                    saved.mkdir(parents=True, exist_ok=False)
                    for response_path in Path(directory).glob('*.json'):
                        shutil.copyfile(response_path, saved / response_path.name)
                    print(f'Saved forecast responses locally: data/raw/sync_forecasts/run_{run_id}')
                    stage = 'validate forecast fields, timestamps, and station links' 
                    data, _, omitted = prepare_forecasts(saved)
                    stage = 'verify returned location count'
                    if len(data['locations']) != 2:
                        raise SyncValidationError('Expected two distinct locations')
                    now = datetime.now(timezone.utc)
                    stage = 'match forecast locations to stored coordinates'
                    for loc in data['locations'].values():
                        stored = conn.execute('SELECT 1 FROM public.locations WHERE latitude=%s AND longitude=%s',
                            (loc[1],loc[2])).fetchone()
                        if stored is None:
                            raise SyncValidationError('API resolved an unexpected location; review before insertion')
                    stage = 'verify forecast source labels'
                    for (loc, when), (values, _) in data['hourly_weather'].items():
                        if values[2] != 'fcst':
                            raise SyncValidationError('Forecast-only request returned a non-forecast hour')
                    stage = 'verify upcoming forecast coverage'
                    if max(k[1] for k in data['hourly_weather']) <= now:
                        raise SyncValidationError('No upcoming forecast hours returned')
                fetched = len(data['hourly_weather'])
                stage = 'save weather, bookmarks, and success log'
                with conn.transaction():
                    counts, through = write_data(conn,data)
                    if not replay:
                        for location_id, end in through.items():
                            conn.execute('''INSERT INTO public.sync_state
                                (location_id,last_successful_refresh_at,forecast_through,run_id)
                                VALUES (%s,now(),%s,%s) ON CONFLICT (location_id) DO UPDATE SET
                                last_successful_refresh_at=EXCLUDED.last_successful_refresh_at,
                                forecast_through=EXCLUDED.forecast_through,run_id=EXCLUDED.run_id,
                                last_updated_at=now()''',(location_id,end,run_id))
                    conn.execute('''UPDATE public.sync_runs SET finished_at=now(),status='success',
                        records_fetched=%s,records_inserted=%s,records_updated=%s,
                        query_cost=%s,error_message=NULL,details=%s,last_updated_at=now()
                        WHERE run_id=%s''',(fetched,counts['inserted'],counts['updated'],cost,
                        Jsonb({'mode':'replay' if replay else 'live','attempts':attempts,
                               'entities':dict(counts), 'excluded_elapsed_unlabeled_hours':omitted}),run_id))
            print(f"Run {run_id}: success; hourly fetched={fetched}, inserted={counts['inserted']}, updated={counts['updated']}; queryCost={cost}")
            return 0
        except Exception as error:
            # Never record provider body, URL, credentials, or arbitrary exception text.
            conn.execute('''UPDATE public.sync_runs SET finished_at=now(),status='failed',
                records_fetched=%s,query_cost=%s,error_message=%s,last_updated_at=now()
                WHERE run_id=%s''',(fetched or progress.get('response_hours',0),progress.get('query_cost',cost),safe_error(error,stage),run_id))
            print(f'Run {run_id}: FAILED; {safe_error(error,stage)}; data transaction not confirmed.')
            return 1
        finally:
            if lock:
                conn.execute('SELECT pg_advisory_unlock(%s)',(LOCK_ID,))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--trigger',choices=('manual','schedule'),default='manual')
    parser.add_argument('--replay-dir',type=Path)
    parser.add_argument('--validate-dir',type=Path,help='Validate saved forecast files offline only')
    args = parser.parse_args()
    if args.validate_dir:
        if args.apply:
            parser.error('--validate-dir cannot be combined with --apply')
        data, _, omitted = prepare_forecasts(args.validate_dir)
        print('OFFLINE ONLY: no credentials read or connections made.')
        return 0
    if args.replay_dir and args.trigger == 'schedule':
        parser.error('Replay is manual-only; cannot count as scheduled live sync')
    if not args.apply:
        print('PREVIEW: two towns; current available forecast window; days,hours,fcst; US units.')
        print('Normally 2 allowance units per refresh; max 8 request attempts total.')
        print('Refresh the full forecast window because existing predictions change.')
        print('No credentials read, API calls, database connections, or writes.')
        return 0
    config = {**dotenv_values(ROOT/'.env'), **os.environ}
    url = config.get('DATABASE_URL')
    key = config.get('VISUAL_CROSSING_API_KEY')
    if not url:
        print('FAILED: DATABASE_URL missing; cannot connect or write a sync_runs row.')
        return 1
    if not key and not args.replay_dir:
        # Run logging still works: request fails and is logged without a real key.
        key = ''
    try:
        return run(url,key,args.trigger,args.replay_dir)
    except Exception as error:
        print(f'FAILED ({type(error).__name__}); logging unavailable or completion unconfirmed. No credentials displayed.')
        return 1


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,format='%(levelname)s: %(message)s')
    raise SystemExit(main())
