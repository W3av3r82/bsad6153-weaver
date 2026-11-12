-- Milestone 2: review before running against Supabase.
-- US units: Fahrenheit, miles per hour, inches, and degrees from north.
-- Plain CREATE statements deliberately report an error if tables already exist.
BEGIN;

CREATE TABLE public.locations (
    location_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL CHECK (btrim(name) <> ''),
    latitude numeric NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude numeric NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    timezone text NOT NULL CHECK (btrim(timezone) <> ''),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (latitude, longitude)
);

CREATE TABLE public.daily_conditions (
    day_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id bigint NOT NULL REFERENCES public.locations(location_id),
    local_date date NOT NULL,
    sunrise_at timestamptz,
    sunset_at timestamptz,
    moonrise_at timestamptz,
    moonset_at timestamptz,
    moon_phase numeric CHECK (moon_phase BETWEEN 0 AND 1),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (location_id, local_date)
);

CREATE TABLE public.hourly_weather (
    weather_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id bigint NOT NULL,
    local_date date NOT NULL,
    valid_at timestamptz NOT NULL,
    source text NOT NULL CHECK (source IN ('obs', 'fcst')),
    temperature_f numeric,
    wind_direction_deg numeric CHECK (wind_direction_deg BETWEEN 0 AND 360),
    wind_speed_mph numeric CHECK (wind_speed_mph >= 0),
    precipitation_probability_pct numeric
        CHECK (precipitation_probability_pct BETWEEN 0 AND 100),
    precipitation_in numeric CHECK (precipitation_in >= 0),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (location_id, local_date)
        REFERENCES public.daily_conditions(location_id, local_date),
    UNIQUE (location_id, valid_at)
);

CREATE TABLE public.stations (
    station_id text PRIMARY KEY CHECK (btrim(station_id) <> ''),
    name text,
    latitude numeric CHECK (latitude BETWEEN -90 AND 90),
    longitude numeric CHECK (longitude BETWEEN -180 AND 180),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.weather_station_links (
    weather_id bigint NOT NULL REFERENCES public.hourly_weather(weather_id),
    station_id text NOT NULL REFERENCES public.stations(station_id),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (weather_id, station_id)
);

-- Defaults set audit timestamps on insert only. Milestone 3 updates must
-- explicitly advance last_updated_at when stored values change.
COMMIT;
