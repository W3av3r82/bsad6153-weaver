-- Milestone 3: run as the database owner after reviewing this file.
-- No passwords belong in this file or Git history.
-- Set the app_reader password privately in Supabase, then store its Session
-- pooler connection in .env as APP_DATABASE_URL.
-- This script creates a NEW role; if it already exists, stop and inspect it.

BEGIN;

CREATE ROLE app_reader LOGIN
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;

GRANT USAGE ON SCHEMA public TO app_reader;

-- Explicitly grant only SELECT on the project's data tables.
REVOKE ALL PRIVILEGES ON TABLE
    public.locations,
    public.daily_conditions,
    public.hourly_weather,
    public.stations,
    public.weather_station_links
FROM app_reader;

GRANT SELECT ON TABLE
    public.locations,
    public.daily_conditions,
    public.hourly_weather,
    public.stations,
    public.weather_station_links
TO app_reader;

-- No INSERT, UPDATE, DELETE, TRUNCATE, sequence, or table-creation grants.
-- PostgreSQL PUBLIC grants apply to all roles, even with NOINHERIT.
-- Verify effective permissions using the actual app_reader connection;
-- do not assume these grants alone prove read-only access.
-- Part C: db/sync_schema.sql grants SELECT on sync_runs and sync_state.
-- After those tables exist, run the following separately (not this CREATE ROLE again):
-- GRANT SELECT ON public.sync_runs, public.sync_state TO app_reader;

COMMIT;
