# Data-quality report — Milestone 3

**Draft, partial evidence.** Results below were run by the student in Supabase
and supplied in this chat. They were not independently re-executed by the
assistant. Corresponding read-only statements are Q1–Q12 in
[`db/quality_checks.sql`](../db/quality_checks.sql). Each timestamp belongs to
its own measurement; the results are not one simultaneous database snapshot.
UTC is six hours ahead of Central Standard Time on these dates.

## Row counts — Q1
Measured **2026-11-18 01:36:47.729753+00** (November 17, 7:36 p.m. CST).

| Table | Rows at the stated timestamp |
|---|---:|
| daily_conditions | 79 |
| hourly_weather | 1,857 |
| locations | 2 |
| stations | 9 |
| sync_runs | 9 |
| sync_state | 2 |
| weather_station_links | 4,720 |

These are dated counts, not current totals or permanent expectations.

## Important-field null rates — Q2
Measured **2026-11-18 01:40:02.265038+00** (November 17, 7:40 p.m. CST).

| Source | Hours | Missing temperature | Missing wind speed | Missing wind direction | Missing precipitation | Missing precipitation probability |
|---|---:|---:|---:|---:|---:|---:|
| fcst | 801 | 0 | 0 | 0 | 0 | 0 |
| obs | 1,056 | 0 | 0 | 0 | 0 | 0 |

For each listed field and source, null rate = missing count / total hours ×
100 = **0% at the stated timestamp**. This establishes completeness of these
fields, not accuracy. Astronomy and station metadata were measured separately
below.

## Astronomy completeness and calendar boundaries — Q7–Q9

Q7 measured **2026-11-22 02:28:18.519499+00** (November 21, 8:28 p.m. CST).
Across **87 location-day records**, sunrise, sunset, and moon phase each had
**0 missing values (0%)**. Moonrise and moonset each had **4 missing values
(4/87, approximately 4.60%)**. These are eight different affected records,
not four records missing both events.

Q8 measured **2026-11-22 02:30:16.270008+00**. Both towns had the same pattern:
moonrise absent on **October 3 and November 30, 2026**, and moonset absent on
**October 18 and November 17, 2026**. No difference between towns was observed
for these missing-event dates; this does not establish equal astronomy accuracy.

The student suggested that the events might fall on neighboring calendar days.
Q9's 24 returned rows support that interpretation in all eight cases. The
student supplied those results during this session; Q9 did not include a
measurement timestamp, so no exact execution time is claimed.

| Missing event/date | Elk City: previous event → next event (local time) | Marquette: previous event → next event (local time) |
|---|---|---|
| Moonrise, Oct 3 | Oct 2 23:26:29 → Oct 4 00:36:51 | Oct 2 23:29:44 → Oct 4 00:40:40 |
| Moonset, Oct 18 | Oct 17 23:39:37 → Oct 19 00:39:58 | Oct 17 23:43:20 → Oct 19 00:44:26 |
| Moonset, Nov 17 | Nov 16 23:30:38 → Nov 18 00:31:04 | Nov 16 23:36:25 → Nov 18 00:37:46 |
| Moonrise, Nov 30 | Nov 29 22:54:27 → Dec 1 00:02:55 | Nov 29 23:00:34 → Dec 1 00:09:50 |

[Visual Crossing's official field documentation](https://www.visualcrossing.com/resources/documentation/weather-data/weather-data-documentation/)
explains that a moon event can be empty when it does not occur within the local
calendar day. The neighboring stored times are consistent with that documented
case, rather than evidence of a collection failure. They are not an independent
astronomical calculation. Preserve these NULLs; do not substitute zero, midnight,
or the prior day's event. A display should distinguish a documented no-event
case from an unexplained unavailable value rather than assuming every NULL
has this cause. No stored values were changed by this investigation.

## Fairness check: comparable location coverage — Q3 and Q4
Measured **2026-11-19 02:10:44.154559+00** (November 18, 8:10 p.m. CST).
Q3 compares the same next 168 absolute hourly timestamps at both places,
starting at the next whole hour: 2026-11-19 03:00 UTC through
2026-11-26 02:00 UTC, inclusive.

| Location | Expected hours | Available forecast hours | Missing | Coverage |
|---|---:|---:|---:|---:|
| Elk City, KS | 168 | 168 | 0 | 100.0% |
| Marquette, KS | 168 | 168 | 0 | 100.0% |

Freshness measured separately at **2026-11-19 02:13:27.580502+00**
(November 18, 8:13 p.m. CST): both locations had their last live refresh at
**2026-11-19 00:02:16.146259+00**, were **2.19 hours** old, referenced
**Run 11**, and showed forecast coverage through **2026-12-03 05:00:00+00**.

**Interpretation:** no location coverage or refresh-age disparity was found in
these measurements. A hypothetical missing-hour gap could bias a chatbot if
it treated unknown precipitation as zero and favored the less complete town;
that gap was **not** observed here. Equal coverage and age do not establish
equal accuracy. Town forecasts cannot establish wind shelter or conditions at
a particular stand; a chatbot could mislead a hunter by treating town-level
values as exact site measurements. It should compare matched time windows,
disclose freshness and missingness, ask for site context, and avoid claiming
one town offers better deer encounters based solely on forecast coverage.

This is a limited check of two places and one future window, not proof that
the system is fair for every place, time period, user, or hunting style.

## Duplicate identities — Q5
Measured **2026-11-19 02:16:33.173601+00** (November 18, 8:16 p.m. CST).

| Duplicate grouping | Duplicate groups at stated timestamp |
|---|---:|
| Location coordinate pair | 0 |
| Location and local day | 0 |
| Location and absolute hourly timestamp | 0 |
| Provider station ID | 0 |
| Weather ID and station ID link | 0 |

Unique/primary-key constraints prevent these duplicates. Q12 below separately
checks candidates under different IDs. Neither check rules out alternate place
names or near-identical coordinates. Do not deduplicate repeated local clock hours:
daylight-saving transitions can give them different absolute timestamps.

### Same entity under different IDs — Q12

Measured **2026-11-22 02:44:38.466572+00** (November 21, 8:44 p.m. CST).
The student supplied **0 possible duplicate groups for locations** and
**0 for stations**. The query groups records by trimmed, lowercase name and
exact latitude/longitude, looking for more than one distinct ID. Station
candidates require nonblank names and populated coordinates; Q10 separately
found no missing values in those fields at its measurement time.

This is a narrow candidate check, not proof of real-world uniqueness. Spelling
variants, different names, and small coordinate differences can evade it;
different stations may also legitimately be colocated. No records were merged
or deleted. Retain provider station IDs and review ambiguous future matches
before making any identity changes.

## Anomalies and orphans — Q6
Measured **2026-11-19 02:20:32.538606+00** (November 18, 8:20 p.m. CST).

| Check | Issues at stated timestamp |
|---|---:|
| Invalid weather ranges or source | 0 |
| Invalid location coordinates | 0 |
| Invalid moon phase | 0 |
| Day missing its location | 0 |
| Hour missing its parent day | 0 |
| Link missing weather or station | 0 |
| Hour assigned to wrong local date | 0 |

Ranges checked: nonnegative wind speed/precipitation, wind direction 0–360,
precipitation probability 0–100, obs/fcst categories, coordinate bounds, and
moon phase 0–1. Foreign keys reject absent parents; validation checks hourly
timestamps against the location's timezone. Missing values are distinct from
invalid ranges. These checks do not measure forecast accuracy, all metadata
ranges, or all sync-state relationships.

## Station metadata — Q10

Measured **2026-11-22 02:37:11.720252+00** (November 21, 8:37 p.m. CST).
The student supplied results for **9 stations**: **0** missing or blank names,
**0** missing latitudes, **0** missing longitudes, and **0** invalid coordinate
pairs. Each missing-field rate is **0/9 = 0%**. Valid coordinate bounds are
latitude −90 to 90 and longitude −180 to 180. These checks establish
completeness and valid ranges, not independently verified station positions
or descriptive usefulness of station names.

## Sync tracking relationships — Q11

Measured **2026-11-22 02:39:55.658722+00** (November 21, 8:39 p.m. CST).
The student supplied **0** sync-state records missing their referenced location
and **0** missing their referenced run. This checks existence of referenced
records, not whether a run succeeded, whether every location has sync state,
or whether a refresh is recent enough for a hunting decision.

## Cleaning and preservation decisions

- Retain raw responses in ignored local storage; do not modify original JSON.
- Exclude elapsed forecast-response hours without source labels rather than
  inventing a forecast/observation label. Run 3's saved responses had **40 such
  hours and 680 labeled forecasts**, as verified during the November 16 session;
  this raw-file diagnostic is not a SQL measurement of the current database.
- Reject future unlabeled hours, unexpected source categories, out-of-range
  values, and invalid parent references before committing weather changes.
- Preserve legitimate missing values as NULL, not zero. Missing forecast
  station links do not imply missing weather; station absence is allowed.
- Keep historical observations separate from forecasts and protect observations
  against forecast overwrites. Historical precipitation probability is not the
  original issued forecast probability.
- Leave correctly ranged values unchanged even when surprising. No weather
  values were altered merely to improve the quality report's results.

## Lineage, freshness target, and ownership

Visual Crossing → raw forecast JSON → validation/transformation in
`ingest/sync.py` → transactional Supabase upserts → read-only reports/future
application. Location/day/hour identities connect daily astronomy and weather;
historical station links preserve provider station IDs. Raw files on Actions
runners are temporary, so they are not a durable revision archive.

Refreshes are scheduled at **11:17 and 23:17 UTC**, approximately every 12 hours.
With prompt successful runs, retrieval age is normally about 12 hours or less
plus execution time. There is **no finite worst-case freshness guarantee**:
delays or repeated failures can leave the last successful data indefinitely old.
Display the last successful live refresh and age, check requested-window
coverage, and disclose stale/incomplete inputs. Forecast target time and row
update time must not be substituted for retrieval time. Recent retrieval does
not establish forecast accuracy. See the data dictionary for the fuller path.

Joshua Weaver owns maintenance, failure review, credential protection, and
approval of changes. Visual Crossing supplies weather predictions; the user
retains the hunting decision. Reviewed Git commits/PRs track implementation
changes; this report preserves dated measurements rather than rewriting old
results to look current.

### Documentation change log

- **November 21, 2026:** added the astronomy NULL/calendar-boundary investigation,
  station metadata checks, sync reference checks, lineage, freshness limits,
  and confirmed ownership, plus the same-entity/different-ID candidate check.
  Supporting SQL is Q7–Q12. No database values were
  changed by these read-only checks.

## Remaining work before claiming Parts E–H complete

- Station metadata nulls/ranges and sync-state reference checks are documented
  above with their measured timestamps; broader accuracy is not established.
- Review the completed golden/reference comparisons, two deliberate tests, and
  dated scheduled-run evidence in `docs/sync_tests.md` for final consistency.
- Complete final review, GitHub publication, and the Milestone 3 screencast.
