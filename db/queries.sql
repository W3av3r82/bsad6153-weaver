-- Milestone 2 business queries: read-only SELECT statements.
-- Fixed historical demonstration window, not a live hunting recommendation.
-- Baseline motivation: quick snapshots across multiple days/times and places.
-- Dataset currently contains only Marquette and Elk City, Kansas.
-- Future added locations will also appear unless a location filter is added.
-- US units: Fahrenheit, mph, inches. Wind direction is where wind comes FROM.
-- SUM/AVG ignore NULLs; counts show hours, not measurement completeness.
-- Student-run results in Supabase: Q1=44, Q2=96, Q3=44, Q4=44, Q5=88 rows.
-- Count agreement is a structural check, not proof of meteorological accuracy.

-- Question 1: How did daily temperature, wind speed, and precipitation
-- compare between Marquette and Elk City on October 1-22?
-- Student's surprising finding: The timing of wind increases relative to
-- rainfall differed. Both places had rain on October 1, with stronger winds
-- in Marquette. Elk City's winds increased on October 2 without recorded rain.
-- Hourly follow-up: Elk City had 16.4 mph wind and zero precipitation at 03:00
-- on October 2, versus Marquette's 9.1 mph and zero precipitation then.
-- Marquette did record 0.003 inches at midnight October 2; do not call that
-- entire day dry. These results alone do not prove a front or its direction.
SELECT
    l.name AS location,
    w.local_date AS day,
    COUNT(*) AS hours_recorded,
    ROUND(AVG(w.temperature_f), 1) AS avg_temperature_f,
    ROUND(AVG(w.wind_speed_mph), 1) AS avg_wind_mph,
    ROUND(SUM(w.precipitation_in), 3) AS total_precipitation_inches
FROM public.hourly_weather AS w
JOIN public.locations AS l ON w.location_id = l.location_id
WHERE w.source = 'obs'
  AND w.local_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-22'
GROUP BY l.name, w.local_date
ORDER BY w.local_date, l.name;

-- Question 2: When did wind and precipitation change in each location
-- on October 1-2?
SELECT
    w.valid_at AT TIME ZONE l.timezone AS local_time,
    l.name AS location,
    w.wind_speed_mph,
    w.wind_direction_deg,
    w.precipitation_in,
    w.temperature_f
FROM public.hourly_weather AS w
JOIN public.locations AS l ON w.location_id = l.location_id
WHERE w.source = 'obs'
  AND w.local_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-02'
ORDER BY w.valid_at, l.name;

-- Question 3: What were conditions in the first hourly record at or
-- after sunrise in each location? This is not an exact sunrise measurement.
SELECT DISTINCT ON (l.location_id, d.local_date)
    l.name AS location,
    d.local_date AS day,
    d.sunrise_at AT TIME ZONE l.timezone AS sunrise_local,
    w.valid_at AT TIME ZONE l.timezone AS weather_time_local,
    w.temperature_f,
    w.wind_speed_mph,
    w.wind_direction_deg,
    w.precipitation_in,
    d.moon_phase
FROM public.locations AS l
JOIN public.daily_conditions AS d ON d.location_id = l.location_id
JOIN public.hourly_weather AS w
    ON w.location_id = d.location_id
   AND w.local_date = d.local_date
WHERE w.source = 'obs'
  AND d.local_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-22'
  AND w.valid_at >= d.sunrise_at
  AND w.valid_at < d.sunrise_at + INTERVAL '1 hour'
ORDER BY l.location_id, d.local_date, w.valid_at;

-- Question 4: What were conditions in the last hourly record at or
-- before sunset? This is not an exact sunset measurement.
SELECT DISTINCT ON (d.local_date, l.location_id)
    l.name AS location,
    d.local_date AS day,
    d.sunset_at AT TIME ZONE l.timezone AS sunset_local,
    w.valid_at AT TIME ZONE l.timezone AS weather_time_local,
    w.temperature_f,
    w.wind_speed_mph,
    w.wind_direction_deg,
    w.precipitation_in,
    d.moon_phase
FROM public.locations AS l
JOIN public.daily_conditions AS d ON d.location_id = l.location_id
JOIN public.hourly_weather AS w
    ON w.location_id = d.location_id
   AND w.local_date = d.local_date
WHERE w.source = 'obs'
  AND d.local_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-22'
  AND w.valid_at <= d.sunset_at
  AND w.valid_at > d.sunset_at - INTERVAL '1 hour'
ORDER BY d.local_date, l.location_id, w.valid_at DESC;

-- Question 5: How did conditions near sunrise and sunset compare
-- at both locations? CASE labels the morning and evening records.
SELECT
    l.name AS location,
    d.local_date AS day,
    CASE
        WHEN w.valid_at >= d.sunrise_at
         AND w.valid_at < d.sunrise_at + INTERVAL '1 hour'
        THEN 'Morning'
        ELSE 'Evening'
    END AS period,
    w.valid_at AT TIME ZONE l.timezone AS weather_time_local,
    w.temperature_f,
    w.wind_speed_mph,
    w.wind_direction_deg,
    w.precipitation_in,
    d.moon_phase
FROM public.locations AS l
JOIN public.daily_conditions AS d ON d.location_id = l.location_id
JOIN public.hourly_weather AS w
    ON w.location_id = d.location_id
   AND w.local_date = d.local_date
WHERE w.source = 'obs'
  AND d.local_date BETWEEN DATE '2026-10-01' AND DATE '2026-10-22'
  AND (
      (w.valid_at >= d.sunrise_at
       AND w.valid_at < d.sunrise_at + INTERVAL '1 hour')
      OR
      (w.valid_at <= d.sunset_at
       AND w.valid_at > d.sunset_at - INTERVAL '1 hour')
  )
ORDER BY d.local_date, l.name, w.valid_at;
