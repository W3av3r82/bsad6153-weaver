# Data dictionary - Visual Crossing scouting project

Draft for student review. Documentation and local data were checked on October 29, 2026.
This is a data reference, not a personal baseline log or AI review log.

## 1. Source and access

- API: Visual Crossing Timeline Weather API.
- Base URL: `https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/`
- Endpoint used: `GET /timeline/{location}/{start_date}/{end_date}`.
- Location used: `Marquette,KS,US`, resolved to latitude 38.5529, longitude -97.8339, timezone `America/Chicago`.
- Output: JSON, with daily and hourly sections (`include=days,hours`) and `unitGroup=us`.
- Authentication used by this project: read `VISUAL_CROSSING_API_KEY` from the local `.env` file and send it as the `key` query parameter. Never save or print the key, full request URL, or request parameters in logs.
- Documentation nuance: the Timeline page describes supported anonymous requests while its parameter list labels `key` required. This project deliberately uses authenticated requests under the student's account.

Official references:

- [Timeline endpoint, parameters, response structure, and error codes](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/)
- [Weather fields, units, and meanings](https://www.visualcrossing.com/resources/documentation/weather-data/weather-data-documentation/)
- [Sunrise, sunset, and lunar fields](https://www.visualcrossing.com/resources/documentation/weather-api/how-to-include-sunrise-sunset-and-moon-phase-data-into-your-api-requests/)
- [Plan limits](https://www.visualcrossing.com/weather-data-pricing/)
- [How allowance records are counted](https://www.visualcrossing.com/resources/documentation/weather-data/what-exactly-is-a-weather-record/)
- [License terms](https://www.visualcrossing.com/weather-service-terms/)
- [Free-plan permitted uses](https://www.visualcrossing.com/resources/documentation/what-can-i-do-with-the-visual-crossing-weather-free-plan/)

## 2. What one record means

| Resource | Plain-English meaning |
|---|---|
| Hourly weather (main resource) | Conditions for one requested location during one hour, labeled by source as historical observations or forecasts. This is not an individual deer sighting or a guarantee of conditions at an exact hunting spot. |
| Weather station (related resource) | A station identifier and descriptive metadata, such as its name and coordinates. Historical weather records contain identifiers linking to station metadata. A listed station is not necessarily the requested scouting location. |
| Daily weather and astronomy | A location's calendar day, containing daily summaries and sunrise, sunset, and lunar information. Hourly weather objects are nested under that day. |
| Location metadata | The resolved location, coordinates, and timezone attached to a response. The same location is repeated in multiple downloaded responses. |

The downloaded data already contains these resources and links. Database tables and loading have not been implemented.

## 3. Verified collection

- Historical dates: October 1-22, 2026, inclusive: **528 hourly records**, all with `source=obs`.
- Forecast dates: October 30-November 1, 2026: **73 hourly records**, all with `source=fcst`.
- Total: **601 distinct location/timestamp pairs** across 25 calendar days.
- Related resources: **4 unique station identifiers**: `QNRK1`, `KSLN`, `KEWK`, and `KHUT`.
- The 22 historical responses contain 88 repeated station-metadata objects in total; these are not 88 different stations.
- Storage: 23 raw JSON responses under `data/raw/visual_crossing/`, which Git ignores. No database exists yet.
- One-day live test: 24 hours and 4 station records; reported `queryCost=24`.
- Full run: 22 new downloads and 1 reused response; reported additional `queryCost=505`. Together, these two runs reported 529 allowance units, excluding any other account activity.
- The inspected core hourly fields had no missing values. Forecast station links and some daily moon events were missing; a core-field check is not a completeness check for all fields.

These counts describe the saved snapshot, not a promise about future responses.

## 4. Twenty important fields

Paths below describe nested JSON. Examples are from inspected responses; they are not necessarily from the same date or object. `number` includes integer and decimal JSON values. No missing value observed does not guarantee a field will always be available.

| Field/path | Type | Example | Meaning | Can it be missing? |
|---|---|---|---|---|
| `resolvedAddress` | text | `Marquette, KS, United States` | Location label returned by geocoding. | None missing in these responses; validate future responses. |
| Location/station `latitude` | number | `38.5529` (location); `38.144` (station) | North-south position in decimal degrees; interpret in the containing object. | None missing in the inspected location/station objects; validate. |
| Location/station `longitude` | number | `-97.8339` (location); `-98.478` (station) | East-west position in decimal degrees; negative here means west. | None missing in the inspected location/station objects; validate. |
| `timezone` | text | `America/Chicago` | Timezone used to interpret local dates and clock times. | None missing here; required to interpret local times safely. |
| `days[].datetime` | date text | `2026-10-30` | Local calendar day containing its hourly records. | None missing here; invalid/missing dates need handling. |
| `days[].hours[].datetimeEpoch` | integer | `1790830800` | Absolute instant in UNIX seconds; avoids ambiguity when clock time repeats. | None missing here; the fetcher skips hours lacking this field. |
| `days[].hours[].temp` | number | `73.6` | Temperature in degrees Fahrenheit for this request's U.S. units. | None missing here; future values may be null or absent. |
| `days[].hours[].winddir` | number | `169.0` | Compass direction the wind comes from, in degrees. | None missing here; treat unavailable values as unknown. |
| `days[].hours[].windspeed` | number | `12.0` | Wind speed in miles per hour. | None missing here; not interchangeable with a gust field. |
| `days[].hours[].precipprob` | number | `11.0` (forecast) | Precipitation chance, percent. Historical values are not the forecast originally issued for that hour. | None missing here; forecast and history have different interpretations. |
| `days[].hours[].precip` | number | `0.0` | Liquid-equivalent precipitation amount, inches; recorded historically or predicted for forecasts. | None missing here; unknown must not be changed to zero. |
| `days[].hours[].source` | text | `obs` or `fcst` | Provenance category. Our snapshot contains observations and forecasts. | None missing here; do not infer solely from the filename. |
| `days[].hours[].stations` | list of text IDs, or null | `["QNRK1", "KSLN", "KEWK", "KHUT"]` | Links to station metadata associated with historical weather. | Null in all 73 forecast hours; populated in all 528 historical hours. |
| `days[].sunrise` | time text | `07:56:00` | Local sunrise time for the day. | Present in all 25 days; absent from every inspected hour. |
| `days[].sunset` | time text | `18:33:32` | Local sunset time for the day. | Present in all 25 days; daily context is needed. |
| `days[].moonphase` | number | `0.66` | Position in the lunar cycle: 0 is new moon and 0.5 is full moon. | Present in all 25 days; absent from every inspected hour. |
| `days[].moonriseEpoch` | integer | `1793417489` | Moonrise instant in UNIX seconds, convertible to local time. | Absent on 1 of the 25 days; the event may not occur within that local day. |
| `days[].moonsetEpoch` | integer | `1793383963` | Moonset instant in UNIX seconds, convertible to local time. | Absent on 1 of the 25 days; do not substitute zero. |
| `stations.{station_id}.id` | text | `QNRK1` | Station identifier, also represented by the enclosing dictionary key. | Present in inspected station objects; preserve as text. |
| `stations.{station_id}.name` | text | `STAFFORD KS US` | Provider's station label; some labels are only codes, such as `KHUT`. | Present here; labels need not be descriptive or unique. |

Additional interpretation notes:

- Hourly `datetime` is a local clock label, such as `01:00:00`; it is not a safe identifier by itself.
- The documented historical precipitation probability can be 0 or 100 based on whether precipitation occurred. It must not be treated as the original predicted probability when evaluating forecast accuracy.
- Forecast precipitation chance and forecast amount are different quantities. A zero amount does not guarantee a zero chance of rain.
- The four station metadata fields `distance`, `useCount`, `quality`, and `contribution` are retained in raw files. We have not verified the full semantics of the latter three and do not use their zero values to infer station reliability or contribution. Distance describes a station relative to a requested location, not a permanent station-only property.
- Missing core values are reported, not silently imputed. Missing astronomy or station values can be legitimate. Field absence, JSON null, and numeric zero remain distinguishable in raw JSON.

## 5. Identifiers and relationships

The API does not provide a universal ID for each location-hour object. The fetcher counts unique records using **resolved latitude + longitude + `datetimeEpoch`**. Coordinates describe the requested location, not the station. The hash in a raw filename identifies the query's location text for caching; it is not a provider-issued station or weather ID.

Proposed database relationships, to be finalized with the database assignment:

- A stable local `location_id` connects one location to many dated weather records.
- A location/day identity connects daily astronomy to that day's hours.
- Station ID identifies a station independently of repeated copies of its metadata.
- Historical weather has a list of station IDs: many weather records can reference the same station, and one weather record can reference multiple stations. A linking table would preserve this many-to-many relationship.
- Keep `source` and collection provenance. If forecast revisions are retained, an additional retrieval/run identifier is needed; location/time alone cannot distinguish multiple predictions for the same future hour.

No primary keys, foreign keys, or linking tables have been created yet. These are design proposals, not implemented guarantees.

## 6. Update behavior and finding new data

Forecast values can change before their target hour. New historical hours become available as time advances; older historical values may also be corrected. We have not verified a fixed refresh interval and do not promise one.

Current fetch behavior:

- Request inclusive date ranges in nonoverlapping batches; continue from the day after each batch's end. This is date batching, not page-number or cursor pagination.
- Reuse an existing matching JSON file by default. A reused forecast can therefore be stale.
- `--refresh` explicitly downloads matching batches again and overwrites their cached files; it uses allowance and does not preserve the previous forecast version.
- The payload is saved as returned. The current fetcher does not persist an explicit retrieval timestamp or a sync cursor, so raw weather timestamps must not be presented as forecast issue times.

Proposed later sync behavior: track the last successfully processed absolute timestamp, fetch new hours plus an overlap for corrections, and upsert on stable record identities. Refresh the upcoming forecast window separately. Record retrieval time and source; decide whether to keep revisions before claiming forecast-accuracy comparisons. This is not implemented in Milestone 1.

## 7. Limits, waiting, and failure handling

The checked Free plan lists 1,000 allowance records per day and one concurrent request. Historical hourly accounting normally uses one unit per hour; a current forecast for one location is accounted differently. Count returned hourly resources separately from the API's `queryCost`.

The script sends requests sequentially, pauses one second before each attempt, retries 429/5xx and network timeouts with bounded backoff, and honors a usable `Retry-After`. These implementation choices do not imply a provider-published one-request-per-second rule. Its conservative default run budget is 600 and includes retry attempts; it does not know other account usage. Persistent limits cause a reported stop, not unlimited retrying.

Four offline tests passed: 429 then success, repeated 429 stopping at four attempts, timeout then success, and a budget preventing a retry. These simulated tests complement the successful live downloads; we did not intentionally exhaust the real account allowance.

## 8. Verified data surprises and consequences

1. **A day can contain 25 hourly records.** November 1, 2026 has two `01:00:00` forecast entries. Their epoch timestamps differ by 3,600 seconds. Retain both; do not deduplicate on local clock text.
2. **Forecast station links are null.** All 73 forecast hours lack populated station lists, while all 528 historical hours have them. Station joins must allow forecasts without station links.
3. **Astronomy is daily, not hourly, in this response.** Sunrise and lunar fields are absent from the 601 hour objects. Use daily records rather than calling every hourly absence a failed observation.
4. **Some moon events are absent.** One daily moonrise field and one moonset field are omitted. Provider documentation explains that an event may not happen within a particular local calendar day; unknown or inapplicable is not zero.
5. **Repeated station metadata is not a new station.** The 88 metadata objects across historical files reduce to four station IDs. Deduplicate station entities by ID and preserve their weather links separately.
6. **Listed stations can have zero-valued metadata.** The inspected `QNRK1` metadata includes `useCount=0` and `contribution=0.0`. These meanings need further verification before interpretation.

## 9. Data-use ethics check

### What do the terms allow and forbid?

The checked terms permit storage and condition public display and commercial use on the applicable license. The Free plan requires attribution. Use a nearby linked credit such as [Weather Data Provided by Visual Crossing](https://www.visualcrossing.com/). Raw downloadable redistribution is restricted; the assignment's public-sample treatment is deferred to instructor feedback. Keep full raw responses in ignored local storage in the meantime.

### Does the data describe identifiable people, and did they expect this use?

The inspected records describe weather, a town, and stations rather than individual people. Exact private scouting coordinates or personal baseline entries could become sensitive if combined with the weather later; those are separate from the public town-level response inspected here.

### What is the worst realistic harm from leakage or misinterpretation?

Leaking the API key could permit unauthorized account use. Misreading forecast data as observations, confusing units, or losing the repeated daylight-saving hour could produce misleading scouting recommendations; exact private location data could also expose a hunting spot if added later.

### Who should read or change the records?

Proposed roles: the student and authorized ingestion process may update stored data; the public application should have read-only access to appropriate display/derived information, with no access to secrets or personal logs. Administrative changes should stay under the student's control. These permissions have not yet been implemented because there is no database.
