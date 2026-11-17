-- Milestone 3 additive migration. Review before applying as database owner.
-- Run once. Existing weather tables and records are preserved.
BEGIN;
CREATE TABLE public.sync_runs (
    run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    records_fetched integer NOT NULL DEFAULT 0 CHECK (records_fetched >= 0),
    records_inserted integer NOT NULL DEFAULT 0 CHECK (records_inserted >= 0),
    records_updated integer NOT NULL DEFAULT 0 CHECK (records_updated >= 0),
    error_message text,
    trigger text NOT NULL CHECK (trigger IN ('schedule', 'manual')),
    query_cost numeric NOT NULL DEFAULT 0 CHECK (query_cost >= 0),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now()
);
-- A pending run uses status=failed and finished_at=NULL until completion.
-- A killed process therefore cannot leave a falsely successful log row.
CREATE TABLE public.sync_state (
    location_id bigint PRIMARY KEY REFERENCES public.locations(location_id),
    last_successful_refresh_at timestamptz NOT NULL,
    forecast_through timestamptz NOT NULL,
    run_id bigint NOT NULL REFERENCES public.sync_runs(run_id),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_updated_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT ON public.sync_runs, public.sync_state TO app_reader;
COMMIT;
