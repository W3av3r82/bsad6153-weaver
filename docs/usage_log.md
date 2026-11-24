# Usage Log (Weeks 4&ndash;8)

Every time you use your own system for a real decision, add a row using the same columns as
your baseline log. Before the website is available, record the status checks, scripts, or
queries you ran in the "What I used" column. Time yourself so you can compare with your baseline.

| Date | What I was deciding | What I used (site / script / queries) | Time (min) | Did it help? Why or why not? | What I wished I knew | Confidence (1&ndash;5) |
|---|---|---|---|---|---|---|
| 2026-11-23 | Whether to hunt Marquette or Elk City on Thursday morning, November 26 | Ran forecast-freshness checks from db/sync_status.sql and assisted SQL queries in Supabase comparing morning weather and astronomy, the preceding 72-hour precipitation forecast, and weather through Thursday night | 8 min, 41 sec total, with AI assistance (8:16 initial comparison + 0:25 wider forecast check) | Yes; considerably easier. I favored Marquette because lighter wind and slightly colder temperatures suit my hunting style at this point in the season. Compared with my single 14:07 baseline, this trial saved 5:26 (about 38%). | I want a fast, simple snapshot of both locations showing wind, temperature, precipitation, moonrise/moonset, recent precipitation, and incoming weather. The follow-up query added the wider precipitation/weather forecast window; actual rainfall was not verified, and forecasts were sufficient for this planning decision. | 5/5 |

**Notes on anything that went wrong, or that I didn't trust:**

- This was one real planning trial with AI assistance locating and explaining queries and interpreting results. It does not establish independent-use savings, sustained adoption, or better hunting outcomes.
- Accessing the SQL editor and finding the results-limit control required guidance. The first wider-window export was limited to 100 rows; the full results were then obtained.
- The freshness check reported both locations had refreshed about four hours earlier and had forecast coverage beyond November 26. This checks refresh timing and coverage, not forecast accuracy.
- All records in the wider weather query were labeled `fcst`. They described forecast precipitation, not confirmed rainfall observations. I accepted forecasts for this decision.
- The original morning comparison did not include the wider precipitation/weather window. My reported additional time for that follow-up was 25 seconds, included in the 8:41 total.
- The total was above my current five-minute target. More timed real uses are needed; the 14:07 baseline is one observation, not an average.
- I might stop using the system if it takes longer, is difficult to access, produces confusing results, or requires repeated searches on other websites. My planned response is a public website with a simple two-location snapshot and a chatbot; this trial used Supabase queries, not that website.
