-- Read-only measurements. Run each statement separately in Supabase SQL Editor.
-- Results change with syncs; preserve each measured_at with its result.

-- Q1: Row counts for all seven tables.
SELECT now() AS measured_at, 'locations' AS table_name,
       count(*) AS row_count FROM public.locations
UNION ALL SELECT now(), 'daily_conditions', count(*) FROM public.daily_conditions
UNION ALL SELECT now(), 'hourly_weather', count(*) FROM public.hourly_weather
UNION ALL SELECT now(), 'stations', count(*) FROM public.stations
UNION ALL SELECT now(), 'weather_station_links', count(*) FROM public.weather_station_links
UNION ALL SELECT now(), 'sync_runs', count(*) FROM public.sync_runs
UNION ALL SELECT now(), 'sync_state', count(*) FROM public.sync_state
ORDER BY table_name;

-- Q2: Null counts and denominators; percentage = missing / total_hours * 100.
SELECT now() AS measured_at, source, COUNT(*) AS total_hours,
 COUNT(*) FILTER (WHERE temperature_f IS NULL) AS missing_temperature,
 COUNT(*) FILTER (WHERE wind_speed_mph IS NULL) AS missing_wind_speed,
 COUNT(*) FILTER (WHERE wind_direction_deg IS NULL) AS missing_wind_direction,
 COUNT(*) FILTER (WHERE precipitation_in IS NULL) AS missing_precipitation,
 COUNT(*) FILTER (WHERE precipitation_probability_pct IS NULL) AS missing_precip_probability
FROM public.hourly_weather GROUP BY source ORDER BY source;

-- Q3: Matched future-hour coverage by location, not accuracy.
WITH expected AS (
 SELECT generate_series(
  date_trunc('hour', now()) + interval '1 hour',
  date_trunc('hour', now()) + interval '7 days',
  interval '1 hour') AS hour
)
SELECT now() AS measured_at, l.name AS location,
 COUNT(*) AS expected_hours,
 COUNT(w.weather_id) AS available_forecast_hours,
 COUNT(*) - COUNT(w.weather_id) AS missing_hours,
 ROUND(100.0 * COUNT(w.weather_id) / COUNT(*), 1) AS coverage_pct
FROM public.locations l CROSS JOIN expected e
LEFT JOIN public.hourly_weather w ON w.location_id=l.location_id
 AND w.valid_at=e.hour AND w.source='fcst'
GROUP BY l.location_id,l.name ORDER BY l.name;

-- Q4: Last confirmed live refresh per location, independent of value changes.
SELECT now() AS measured_at, l.name AS location,
 s.last_successful_refresh_at,
 ROUND(EXTRACT(EPOCH FROM (now()-s.last_successful_refresh_at))/3600,2)
 AS hours_since_refresh, s.forecast_through, s.run_id
FROM public.locations l LEFT JOIN public.sync_state s USING (location_id)
ORDER BY l.name;

-- Q5: Duplicate identity groups.
SELECT now() AS measured_at, 'location coordinates' AS check_name,
 COUNT(*) AS duplicate_groups FROM (
 SELECT latitude,longitude FROM public.locations
 GROUP BY latitude,longitude HAVING COUNT(*)>1) d
UNION ALL SELECT now(),'location and day',COUNT(*) FROM (
 SELECT location_id,local_date FROM public.daily_conditions
 GROUP BY location_id,local_date HAVING COUNT(*)>1) d
UNION ALL SELECT now(),'location and exact hour',COUNT(*) FROM (
 SELECT location_id,valid_at FROM public.hourly_weather
 GROUP BY location_id,valid_at HAVING COUNT(*)>1) d
UNION ALL SELECT now(),'station ID',COUNT(*) FROM (
 SELECT station_id FROM public.stations GROUP BY station_id HAVING COUNT(*)>1) d
UNION ALL SELECT now(),'weather and station link',COUNT(*) FROM (
 SELECT weather_id,station_id FROM public.weather_station_links
 GROUP BY weather_id,station_id HAVING COUNT(*)>1) d;

-- Q6: Selected range, category, orphan and date-consistency checks.
-- NULLs do not satisfy these invalid-range predicates; use Q2 for weather NULLs.
SELECT now() AS measured_at,'invalid weather ranges or source' AS check_name,
 COUNT(*) AS issues FROM public.hourly_weather
WHERE wind_speed_mph<0 OR wind_direction_deg NOT BETWEEN 0 AND 360
 OR precipitation_in<0 OR precipitation_probability_pct NOT BETWEEN 0 AND 100
 OR source NOT IN ('obs','fcst')
UNION ALL SELECT now(),'invalid location coordinates',COUNT(*) FROM public.locations
WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180
UNION ALL SELECT now(),'invalid moon phase',COUNT(*) FROM public.daily_conditions
WHERE moon_phase NOT BETWEEN 0 AND 1
UNION ALL SELECT now(),'day missing its location',COUNT(*)
FROM public.daily_conditions d LEFT JOIN public.locations l USING(location_id)
WHERE l.location_id IS NULL
UNION ALL SELECT now(),'hour missing its parent day',COUNT(*)
FROM public.hourly_weather w LEFT JOIN public.daily_conditions d
 ON d.location_id=w.location_id AND d.local_date=w.local_date WHERE d.day_id IS NULL
UNION ALL SELECT now(),'link missing weather or station',COUNT(*)
FROM public.weather_station_links x
LEFT JOIN public.hourly_weather w USING(weather_id)
LEFT JOIN public.stations s USING(station_id)
WHERE w.weather_id IS NULL OR s.station_id IS NULL
UNION ALL SELECT now(),'hour assigned to wrong local date',COUNT(*)
FROM public.hourly_weather w JOIN public.locations l USING(location_id)
WHERE (w.valid_at AT TIME ZONE l.timezone)::date<>w.local_date;

-- Q7: Astronomy NULL counts; denominator is daily records, not distinct dates.
SELECT now() AS measured_at, COUNT(*) AS total_days,
 COUNT(*) FILTER (WHERE sunrise_at IS NULL) AS missing_sunrise,
 COUNT(*) FILTER (WHERE sunset_at IS NULL) AS missing_sunset,
 COUNT(*) FILTER (WHERE moonrise_at IS NULL) AS missing_moonrise,
 COUNT(*) FILTER (WHERE moonset_at IS NULL) AS missing_moonset,
 COUNT(*) FILTER (WHERE moon_phase IS NULL) AS missing_moon_phase
FROM public.daily_conditions;

-- Q8: Identify the daily records with missing moon events.
SELECT now() AS measured_at, l.name AS location, d.local_date,
 d.moonrise_at, d.moonset_at, d.moon_phase
FROM public.daily_conditions d JOIN public.locations l USING(location_id)
WHERE d.moonrise_at IS NULL OR d.moonset_at IS NULL
ORDER BY d.local_date, l.name;

-- Q9: Inspect neighboring dates in local time for the observed missing events.
SELECT l.name AS location, d.local_date,
 d.moonrise_at AT TIME ZONE l.timezone AS moonrise_local,
 d.moonset_at AT TIME ZONE l.timezone AS moonset_local
FROM public.daily_conditions d JOIN public.locations l USING(location_id)
WHERE d.local_date BETWEEN DATE '2026-10-02' AND DATE '2026-10-04'
 OR d.local_date BETWEEN DATE '2026-10-17' AND DATE '2026-10-19'
 OR d.local_date BETWEEN DATE '2026-11-16' AND DATE '2026-11-18'
 OR d.local_date BETWEEN DATE '2026-11-29' AND DATE '2026-12-01'
ORDER BY l.name, d.local_date;

-- Q10: Station metadata completeness and coordinate ranges.
SELECT now() AS measured_at, COUNT(*) AS total_stations,
 COUNT(*) FILTER (WHERE name IS NULL OR btrim(name) = '') AS missing_name,
 COUNT(*) FILTER (WHERE latitude IS NULL) AS missing_latitude,
 COUNT(*) FILTER (WHERE longitude IS NULL) AS missing_longitude,
 COUNT(*) FILTER (WHERE latitude NOT BETWEEN -90 AND 90
  OR longitude NOT BETWEEN -180 AND 180) AS invalid_coordinates
FROM public.stations;

-- Q11: Sync tracking references to locations and runs.
SELECT now() AS measured_at,
 'sync state missing its location' AS check_name, COUNT(*) AS issues
FROM public.sync_state s LEFT JOIN public.locations l
 ON l.location_id = s.location_id
WHERE l.location_id IS NULL
UNION ALL
SELECT now(), 'sync state missing its run', COUNT(*)
FROM public.sync_state s LEFT JOIN public.sync_runs r ON r.run_id = s.run_id
WHERE r.run_id IS NULL;

-- Q12: Same normalized name and exact coordinates under different IDs.
-- Candidate review only; this does not find spelling or coordinate variations.
SELECT now() AS measured_at, 'locations' AS record_type,
 COUNT(*) AS possible_duplicate_groups
FROM (
 SELECT lower(btrim(name)), latitude, longitude
 FROM public.locations
 GROUP BY lower(btrim(name)), latitude, longitude
 HAVING COUNT(DISTINCT location_id) > 1
) AS candidates
UNION ALL
SELECT now(), 'stations', COUNT(*)
FROM (
 SELECT lower(btrim(name)), latitude, longitude
 FROM public.stations
 WHERE name IS NOT NULL AND btrim(name) <> ''
  AND latitude IS NOT NULL AND longitude IS NOT NULL
 GROUP BY lower(btrim(name)), latitude, longitude
 HAVING COUNT(DISTINCT station_id) > 1
) AS candidates;
