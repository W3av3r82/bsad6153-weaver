# Weather database design — Milestone 2

Draft for student review. This document and `db/schema.sql` describe the
proposed design; they do not prove that tables have been created or populated.
Based on the saved collection described in `docs/data_dictionary.md`.

```mermaid
erDiagram
    locations ||--o{ daily_conditions : has
    daily_conditions ||--o{ hourly_weather : contains
    hourly_weather ||--o{ weather_station_links : has
    stations ||--o{ weather_station_links : contributes_to

    locations {
        bigint location_id PK
        text name
        numeric latitude UK
        numeric longitude UK
        text timezone
    }
    daily_conditions {
        bigint day_id PK
        bigint location_id FK
        date local_date
        timestamptz sunrise_at
        timestamptz sunset_at
        timestamptz moonrise_at
        timestamptz moonset_at
        numeric moon_phase
    }
    hourly_weather {
        bigint weather_id PK
        bigint location_id FK
        date local_date FK
        timestamptz valid_at
        text source
        numeric temperature_f
        numeric wind_direction_deg
        numeric wind_speed_mph
        numeric precipitation_probability_pct
        numeric precipitation_in
    }
    stations {
        text station_id PK
        text name
        numeric latitude
        numeric longitude
    }
    weather_station_links {
        bigint weather_id PK, FK
        text station_id PK, FK
    }
```

All five tables also contain `first_seen_at` and `last_updated_at`, both
`timestamptz NOT NULL DEFAULT now()`. They are omitted from the diagram for
readability. Diagram uniqueness markers on location coordinates refer to the
**pair**, not to either coordinate independently.

## What one row means

- **locations:** One requested weather location, with resolved coordinates and
  its IANA timezone. Marquette is the requested place, not a weather station.
- **daily_conditions:** One local calendar day at one location, with daily
  astronomy. `(location_id, local_date)` is unique; missing moon events stay null.
- **hourly_weather:** One absolute hour at one location, represented by the
  current stored observation or forecast. `(location_id, valid_at)` is unique.
- **stations:** One provider weather station. Its text station ID is the natural
  primary key, which also guarantees uniqueness without a redundant constraint.
- **weather_station_links:** One association between an hour and a listed
  contributing station. Its two-column primary key prevents repeated links.

## Relationships and a debated design choice

One location has many days, and one day contains many hourly records. The hour's
`(location_id, local_date)` foreign key references that exact location/day pair;
therefore an hour cannot reference a nonexistent day. The loader must derive
`local_date` in the location's timezone and check it against the parent day.

We considered storing one station ID on each hour, but the API can list multiple
stations for one hour. A linking table preserves that many-to-many relationship
without duplicating weather measurements. Forecast hours can have **zero** station
links; absence does not mean those forecasts should be discarded.

## Time, units, and missing data

Convert hourly epoch timestamps to timezone-aware instants for `valid_at`.
Use the location's timezone for local calendar dates and local sunrise/sunset
values, preferring supplied epoch fields where available. PostgreSQL
`timestamptz` stores an instant; the location's timezone is stored separately.
Repeated local clock hours during daylight saving time remain distinct.

Measurements use the collection's US units: degrees Fahrenheit, miles per hour,
and inches. Wind direction is the direction wind comes **from**, in degrees.
The loader must verify units rather than silently mix unit systems.

Checks enforce coordinate ranges, nonnegative wind/precipitation, percentages
from 0 to 100, and moon phase from 0 to 1. Missing measurements remain SQL NULL,
not zero. Source categories are currently restricted to the verified `obs` and
`fcst` values; unexpected categories must be reported for review, not relabeled.
Historical precipitation probability is not the original forecast probability.

## Duplicate prevention and audit limitations

Milestone 2 loading will use the unique keys with `ON CONFLICT DO NOTHING`.
This stores one version per location/hour, not a forecast-revision archive.
If both an observation and forecast exist for the same hour in the input, the
loader should prefer the observation deterministically. Milestone 3 must define
updates for refreshed forecasts and their replacement by observations.

Audit timestamps mean **first database insertion** and **last stored update**;
they do not establish API retrieval time or forecast issue time. Defaults only
initialize them; later update code must advance `last_updated_at` explicitly.
Daily astronomy likewise represents a single stored version for the location/day.

## Applying the design

The SQL wraps table creation in a transaction so an error does not leave a
partially created design. It contains no DROP statements or passwords. Do not
run it until reviewed. Applying it creates tables; it does not load weather,
create access roles, or implement scheduled syncing.

## Access roles

### app_reader — verified November 16, 2026

`db/roles.sql` creates a login without administrative powers and grants SELECT
on the five data tables. The password was set separately in Supabase, not in
this repository. Its Session pooler URI is stored privately as
`APP_DATABASE_URL` in ignored `.env`; the administrative `DATABASE_URL` stays
separate. Access to `sync_runs` must be granted when that table is created.

Before running the test, the student predicted: “select should succeed,
however delete and write should be denied!” The observed result matched.

Commands run from the project folder:

```bash
.venv/bin/python scripts/check_db.py --app
.venv/bin/python scripts/check_permissions.py
```

The connection check reported:

```text
[ok] Connected using APP_DATABASE_URL
     Database user: app_reader
```

The student supplied the following permission-test output:

```text
[ok] Database user: app_reader
SQL: SELECT count(*) FROM public.hourly_weather
[ok] SELECT succeeded: 1129 hourly records
SQL: DELETE FROM public.hourly_weather WHERE FALSE
[ok] DELETE: permission denied (SQLSTATE 42501)
SQL: INSERT INTO public.locations (name, latitude, longitude, timezone) SELECT 'permission_test', 0, 0, 'UTC' WHERE FALSE
[ok] INSERT: permission denied (SQLSTATE 42501)
PASS: read allowed; INSERT and DELETE denied.
No test changes committed. This checks the named tables/operations only.
```

`WHERE FALSE` targets zero rows even if permissions are unexpectedly broad;
the checker additionally rolls back after each statement. These tests establish
SELECT on hourly weather, DELETE denial on hourly weather, and INSERT denial
on locations. They do not independently test every operation on every table.

### Remaining Part A checks

- Student confirmed Enable Data API is off on November 16, 2026.
- After adding `sync_runs`, grant SELECT to `app_reader` and verify that access.
