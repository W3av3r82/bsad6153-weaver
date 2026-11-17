-- Latest confirmed live refresh, not a replay or only a changed measurement.
SELECT max(finished_at) AS last_successful_live_refresh,
       now() - max(finished_at) AS time_since_refresh
FROM public.sync_runs
WHERE status='success' AND details->>'mode'='live';

-- What changed in the last seven days? Counts here are HOURLY records.
SELECT run_id, started_at, finished_at, status, trigger,
       records_fetched, records_inserted, records_updated, query_cost,
       error_message, details
FROM public.sync_runs
WHERE started_at >= now() - INTERVAL '7 days'
ORDER BY started_at DESC;

-- Per-location refresh bookmarks and forecast coverage.
SELECT l.name, s.last_successful_refresh_at, s.forecast_through,
       now() - s.last_successful_refresh_at AS age
FROM public.locations l
LEFT JOIN public.sync_state s USING (location_id)
ORDER BY l.name;
