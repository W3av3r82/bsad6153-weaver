# Running decision questions

These are project questions discussed with the student, not baseline-log entries
or a personal AI review log. The baseline motivation is a quick view of weather,
astronomy, and multiple locations without repeatedly switching websites.

## Queried in Milestone 2

The student ran these read-only queries in Supabase. SQL is in
`db/queries.sql`; row counts were checked against the loaded date/location coverage.

| ID | Question | Observed result count |
|---|---|---|
| Q1 | How did daily temperature, wind speed, and precipitation compare between Marquette and Elk City on October 1-22, 2026? | 44 |
| Q2 | When did wind and precipitation change at each location on October 1-2? | 96 |
| Q3 | What were conditions in the first hourly record at or after sunrise? | 44 |
| Q4 | What were conditions in the last hourly record at or before sunset? | 44 |
| Q5 | How did morning and evening conditions compare at both locations? | 88 |

## Finding the student identified as surprising

The student identified the timing of wind increases relative to rainfall:
both locations had rain on October 1, with stronger winds in Marquette;
Elk City's winds increased on October 2 without recorded precipitation.
The displayed hourly follow-up showed Elk City at 16.4 mph and Marquette at
9.1 mph at 03:00 on October 2, with zero precipitation at both then.
Marquette recorded 0.003 inches at midnight October 2, so do not call that
whole day dry. The finding and limits are also noted above Q1 in the SQL.

## Questions not established by the current data

- Was a weather front responsible, and which direction did it travel?
  The student raised a possible west-to-east front. The two-location weather
  comparison does not prove a front or travel direction; weather maps and
  additional evidence would be needed.
- Which location and time should I prioritize for a future hunting trip?
  Historical October records and saved forecast snapshots cannot answer a
  current planning question. Refreshed forecasts and the student's explicit
  location/time preferences are needed.
- Do these conditions predict deer encounters at a particular hunting spot?
  Weather and astronomy alone do not establish that relationship. There are
  no deer-encounter records or verified outcome model in this dataset.

## Limits and next milestone

Hourly records near sunrise/sunset are not exact event-time measurements.
The matching comparison uses observations from October 1-22, 2026; it excludes
Marquette's extra saved forecasts. Missing measurements must remain unknown.
Keep adding genuine questions as they arise. In Milestone 3, expand this list
into the required golden-question set, including questions the system must
acknowledge it cannot answer. These five queries are not that finished set.
