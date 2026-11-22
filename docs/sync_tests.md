# Sync verification and failure tests — Milestone 3

Draft evidence log. This document records results the student supplied and
verified in GitHub/Supabase; it does not claim the assistant independently ran
these database tests. Forecast counts describe hours, not station/link totals.

## Nightly scheduled-run check — November 19, 2026

The student opened the [Actions run list](https://github.com/W3av3r82/bsad6153-weaver/actions)
and provided a screenshot showing seven successful workflows: one manual run
and six explicitly marked **Scheduled**, all on `main`. No failed workflow
was visible among these seven entries.

| Workflow run number | Event | Displayed start time (CST) | Result |
|---|---|---|---|
| 1 | Manual | November 16, 9:05 p.m. | Success; excluded from scheduled evidence |
| 2 | Schedule | November 17, 6:02 a.m. | Success |
| 3 | Schedule | November 17, 6:00 p.m. | Success |
| 4 | Schedule | November 18, 6:12 a.m. | Success |
| 5 | Schedule | November 18, 6:02 p.m. | Success |
| 6 | Schedule | November 19, 6:12 a.m. | Success |
| 7 | Schedule | November 19, 5:56 p.m. | Success |

Times are the displayed minute-resolution times, not exact API timestamps.
The first-to-last scheduled start span is approximately **59 hours 54 minutes**.
Thus the observed evidence meets at least three successful scheduled runs
spread over at least 48 hours. Manual runs are not counted. The actual start
times demonstrate that GitHub may delay the nominal cron times.

### Latest run cross-check

- [GitHub workflow run 7](https://github.com/W3av3r82/bsad6153-weaver/actions/runs/44641803356)
- [Sync job log](https://github.com/W3av3r82/bsad6153-weaver/actions/runs/44641803356/job/135974438521)
- GitHub event: schedule; result: success.
- Database `sync_runs` ID: **13**. GitHub run numbers and database run IDs are
  different numbering systems and should not be confused.

The student supplied this job output:

```text
Excluded elapsed hours without source: 34; labeled forecast hours: 686
Run 13: success; hourly fetched=686, inserted=0, updated=686; queryCost=2
```

The student then checked Supabase's `sync_runs` table and confirmed Run 13 had
`status=success`, `records_inserted=0`, `records_updated=686`, and
`trigger=schedule`. Weather records can change in only one field and still
count as updated; these totals do not measure magnitude or forecast accuracy.
No prospective prediction was recorded for this unattended run, and none is
invented afterward.

### Warning observed

GitHub showed a Node.js 20 deprecation warning for `actions/checkout@v4` and
`actions/setup-python@v5`, noting execution under Node.js 24. The run succeeded.
Helper-version maintenance remains a follow-up; no workflow upgrade was made
as part of this check.

## Earlier test evidence

The coaching session already recorded these student-run outcomes:

- Saved-response Run 4: 680 inserted, 0 updated, no API usage.
- Identical saved-response Run 5: 0 inserted, 0 updated, no API usage; student
  confirmed the matching finished/success rows in Supabase. This is evidence
  for the rerun test, not a scheduled live refresh.
- Live Run 6: 0 inserted, 382 updated, queryCost=2; student confirmed database
  counts. Prediction was few changes and nearly zero inserts; updates exceeded
  that expectation. Differences alone do not measure weather-change magnitude.
- Manual Actions test/database Run 7: 0 inserted, 514 updated, queryCost=2;
  student confirmed matching database row and manual trigger.

Exact dated run-row evidence and commands for the two deliberate tests are
documented below. Other outcomes here remain limited to the evidence supplied.
The early validation failures revealed elapsed hourly entries without source
labels; their handling was corrected without inventing forecast labels.

## Final review remaining

- Review the two deliberate tests documented below: unchanged-file replay
  (Run 5) and bad credentials (Run 18). Retain the distinction between the
  student's original prediction and evidence verified later.
- The golden-question baseline and later comparison are documented below;
  the comparison includes four additional successful scheduled syncs.
- Complete final evidence review and the Milestone 3 screencast. Schedule
  evidence alone does not complete the milestone.


## Golden-question baseline — November 19, 2026

Before this test the student predicted successful results without data gaps,
while acknowledging that gaps would not be surprising. The student ran:

```bash
.venv/bin/python -B evals/check_reference.py --hunt-date 2026-11-22 --run
```

The checker confirmed `app_reader` and read-only transactions. All **11**
reference queries succeeded with nonempty outputs. Q01–Q11 row counts were
**8, 10, 2, 2, 8, 2, 8, 4, 8, 2, 8**, respectively. Q12–Q15 were
`should_decline`, with no SQL executed; this does not test a future chatbot's
actual refusals or recommendation quality.

Baseline timestamp: **2026-11-20T02:22:13.174791+00:00**, equivalent to
**November 19, 2026, 8:22 p.m. CST**. Explicit hunt date: **November 22, 2026**.
The local ignored snapshot is
`data/raw/evals/reference_20261120T022213_174791Z.json`; it is not committed.
The assistant inspected that file locally with the student's approval, making
no new database connection or API request.

### Actual completeness and interpretation

- Q03: each town had **72 expected and 72 available hours**, with **0 missing
  hours and 0 missing precipitation amounts**, at the baseline timestamp.
  All **72 hours per town were labeled forecast**, and none were observations.
  The NULL observed totals mean there were no observed records in this window,
  not zero observed rainfall. Predicted totals must not be described as measured
  rainfall, particularly for hours already elapsed at evaluation time.
- Q10: each town had **4 expected and 4 available morning hourly timestamps**,
  **0 missing hours**, and **0 incomplete measurement rows**, at the baseline.
- Q04: sunrise, sunset, moonrise, moonset, and phase were all populated for
  both towns on the specified date, at the baseline.
- Q06: both towns' last live refresh was
  **2026-11-19T23:56:54.389254+00:00**, database Run **13**. Both were about
  **2.42 hours old** at the baseline timestamp.

The no-gap prediction matches the specific completeness checks, but does not
establish that every desired input is available or up to date. Generic morning
SQL uses **sunrise to noon**, not the student's full preferred window beginning
30 minutes before sunrise. Event-relative rainfall boundaries are approximate
because data is hourly. The saved set is a reproducible baseline with these
limits, not a claim that the entire recommendation workflow is complete.

### Later-check procedure (completed November 21 below)

The baseline recorded successful scheduled database run IDs **8–13**.
The comparison must happen after **at least two additional scheduled syncs
that started after this baseline**, using the same hunt date and unchanged
question definitions. Existing successes before the baseline do not count.

```bash
.venv/bin/python -B evals/check_reference.py --run --compare data/raw/evals/reference_20261120T022213_174791Z.json
```

Do not run that command as evidence of the required later check until the two
additional scheduled syncs have occurred. Review which substantive forecast
answers changed; a change in freshness age alone does not prove forecast
measurements changed. If questions or windows are revised, establish a new
baseline and wait for its additional scheduled syncs rather than comparing
unlike tests.


## Second golden-question check — November 21, 2026

Prediction recorded before execution: the student expected some weather answers
to change and all reference queries to pass.

Command run by the student:

```bash
.venv/bin/python -B evals/check_reference.py --run --compare data/raw/evals/reference_20261120T022213_174791Z.json
```

Later snapshot: `data/raw/evals/reference_20261122T021334_187882Z.json`, measured
**2026-11-22T02:13:34.187882+00:00** (November 21, 2026, 8:13 p.m. CST).
Both snapshots use hunt date **November 22, 2026** and unchanged question
definitions. The checker connected as `app_reader` in read-only transactions.
All **11 reference queries passed with nonempty results** again. The four
should-decline entries executed no SQL and remain future chatbot behavior tests.

The saved comparison confirmed **four** additional successful live scheduled
runs started after the baseline: database run IDs **14, 15, 16, 17**. This meets
the requirement to repeat the reference check after at least two more scheduled
syncs; it is separate from the already demonstrated 48-hour schedule span.

Changed answers: **Q01, Q02, Q03, Q05, Q06, Q07, Q08, Q09, Q11**.
Unchanged answers: **Q04** (astronomy) and **Q10** (coverage).
Q06 freshness changes are not themselves proof of changed weather, so the
following matched location/hour comparison establishes substantive changes.

### Example for the screencast: same location and target hour

Elk City, Kansas; **November 22, 2026 at 8:00 a.m. local time**:

| Forecast field | Baseline: Nov 19, 8:22 p.m. CST | Later: Nov 21, 8:13 p.m. CST |
|---|---:|---:|
| Temperature (F) — Q09 | 43.8 | 45.2 |
| Wind speed (mph) — Q11 | 20.0 | 22.1 |
| Wind direction, degrees FROM — Q11 | 351.0 | 352.0 |

These are revised predictions, not actual observations or a measurement of
forecast accuracy. The student's prediction of passing queries and changed
weather answers was supported by the saved results.

### Limitations remain

The generic morning window still starts at sunrise, rather than 30 minutes
before it. Both rainfall-window answers still contain forecasts only, with no
observed rainfall records in that window; elapsed forecast values must not be
presented as measured rainfall. A query returning rows is not proof that the
future chatbot correctly asks follow-ups, declines unsupported claims, or makes
reliable recommendations. Those need later evaluation.

The assistant inspected the two saved local snapshots with permission; this
inspection used no additional database query or weather API request.

## Deliberate bad-credentials test — November 21, 2026

Before running, the student predicted: “with a fake API key it will fail.”
The expected behavior was a logged failure with zero weather inserts or updates.
From the project folder, the student ran:

```bash
VISUAL_CROSSING_API_KEY=invalid-test-key .venv/bin/python -B ingest/sync.py --apply
```

The fake value overrides the API key for this command only; the saved `.env`
and GitHub Actions secrets were not changed. An earlier attempt outside the
project folder could not find Python and did not execute the sync; it is not
counted as the credentials test.

Actual Terminal output:

```text
ERROR: HTTP 401: not retried (check key, access, or parameters)
Run 18: FAILED; request forecasts and check allowance: RuntimeError; data transaction not confirmed.
```

The student checked Supabase's `sync_runs` table and confirmed:

| Field | Run 18 evidence |
|---|---|
| Started at (UTC) | 2026-11-22 02:22:39.503678+00 |
| Finished at (UTC) | 2026-11-22 02:22:41.369667+00 |
| Status | failed |
| records_inserted | 0 |
| records_updated | 0 |

This occurred November 21 at approximately 8:22 p.m. CST. The API rejected
the fake key with HTTP 401, and the script stopped without retrying that
authentication error. The logged failure and zero write counts support the
student's prediction. The failure happened during fetching, before the weather
write transaction. No independent before/after comparison of every weather row
was performed; the evidence is the Terminal output and student-verified log row.

## Unchanged-data rerun test — Run 5

Before the repeated replay, the student predicted no new inserts because the
same saved data was being used. This test checks that identical input does not
create duplicate rows or unnecessarily update existing weather records.
The student ran the same command used for the preceding replay:

```bash
.venv/bin/python -B ingest/sync.py --apply --replay-dir data/raw/sync_forecasts/run_3
```

Run 4 had inserted 680 hourly records. The repeated input produced this output:

```text
Run 5: success; hourly fetched=680, inserted=0, updated=0; queryCost=0
```

The student subsequently supplied the exact Supabase row for Run 5:

| Field | Verified value |
|---|---|
| Started at (UTC) | 2026-11-17 02:18:44.792401+00 |
| Finished at (UTC) | 2026-11-17 02:18:44.892448+00 |
| Status / trigger / mode | success / manual / replay |
| records_fetched | 680 |
| records_inserted / records_updated | 0 / 0 |
| Hourly records unchanged | 680 |
| Days / locations unchanged | 30 / 2 |
| API attempts / query_cost | 0 / 0 |
| error_message | null |

The run occurred November 16, 2026 at approximately 8:18 p.m. CST; the row was
verified later during evidence review. Its details also report 40 excluded
elapsed unlabeled hours. The results support the original no-insert prediction
and demonstrate an unchanged replay for this saved input. This does not test
every possible duplicate input or independently verify audit timestamps on
every weather row. Together with Run 18's bad-credentials test, this supplies
two distinct deliberate test cases.
