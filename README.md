# BSAD 6153 Project: &lt;your project name&gt;

**Student:** Joshua Weaver
**My decision:** Which day and hunting location in Kansas should I prioritize for whitetail hunting based on wind, temperature, precipitation, lunar cycle, sunrise/sunset, and moonrise/moonset?
**Website:** &lt;your domain, from Week 4&gt;

**Data source:** Visual Crossing Timeline Weather API.

**Initial verification:** Successfully retrieved one daily forecast for Marquette, Kansas. Database design and scheduled syncing are not implemented yet.

This repository is one complete AI system, built over eight weeks: a real API, synced on a schedule into a
PostgreSQL database, shown on a public website, with a chatbot and an agent that answer and act from your
own data. You build it with an AI coding agent, and you read and verify everything it writes.

---

## Setting up your computer (Week 1 Setup)

You need a **Windows 10/11 or macOS computer where you can install software**, Git, Python 3.12, and your AI
coding agent (Claude Code, Codex, Antigravity, or Copilot). Let your agent help with the installs, but read
every command before you approve it, and keep auto-approve off.

1. **Clone this repository** into a short folder path that isn't synced by OneDrive or Dropbox, for example
   `C:\dev\bsad6153` on Windows or `~/dev/bsad6153` on macOS.
2. **Create and activate a virtual environment** from the project folder:

   | | Windows (PowerShell) | macOS (Terminal) |
   |---|---|---|
   | Create | `py -3.12 -m venv .venv` | `python3.12 -m venv .venv` |
   | Activate | `.venv\Scripts\Activate.ps1` | `source .venv/bin/activate` |

   You'll see `(.venv)` at the start of your prompt when it's active. Activate it every time you open a new terminal.
3. **Install the packages:** `pip install -r requirements.txt`
4. **Create your secrets file:** copy `.env.example` to `.env`, and put a fake value on the `TEST_SECRET=` line.
5. **Check everything:** `python scripts/check_setup.py` should end with `Setup OK`.
6. **Try the website:** `streamlit run app/streamlit_app.py` opens it in your browser. Press Ctrl+C to stop it.

### Working with your AI agent

- **You approve every command.** Read it first, and if you don't understand it, ask the agent what it does.
- **Ask for a plan before code:** "Before writing anything, tell me your plan."
- **Never paste a real key into the chat,** and never ask the agent to print your `.env` file.
- **The agent never gets the owner database password or deploy tokens.** That's how agents delete databases.
- **Record what you directed, read, verified, and decided** in each pull request's AI review log.

---

## Project layout

| Folder | What goes there | When |
|---|---|---|
| `ingest/` | Fetch, load, and sync code | Weeks 1&ndash;3 |
| `db/` | `schema.sql`, `roles.sql`, `queries.sql` | Weeks 2&ndash;6 |
| `docs/` | Data dictionary, logs, reports (see `docs/README.md`) | Every week |
| `evals/` | Golden questions and evaluation runs | Weeks 3&ndash;7 |
| `app/` | Your website (Streamlit) | Weeks 4&ndash;6 |
| `examples/` | A reference tool-using chatbot loop | Week 5 |
| `scripts/` | Setup and database checks | Weeks 0&ndash;2 |
| `data/sample/` | A small sample of raw API data (large downloads go in `data/raw/`, which Git ignores) | Week 1 |

## Secrets: where each one lives

| Secret | On your computer | On Render (website) | In GitHub Actions (sync) |
|---|---|---|---|
| `DATABASE_URL` (owner) | `.env` | **never** | Actions secret |
| `APP_DATABASE_URL` (read-only) | `.env` | environment setting | if your checks need it |
| `AGENT_DATABASE_URL` | `.env` | environment setting | no |
| LLM key, `APP_PASSWORD` | `.env` | environment setting | no |
| Data API key | `.env` | no | Actions secret |

`.env.example` lists the names only. If a secret ever leaks, revoke or rotate it first, then tell the instructor.

---

## Deploying on Render (Week 4)

1. Claim your free domain through the GitHub Student Developer Pack.
2. In Render, choose **New &gt; Blueprint**, pick this repository, and enter each secret when asked.
   (`render.yaml` describes the service.) Or create a **Web Service** by hand with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `streamlit run app/streamlit_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   - Environment variables: `PYTHON_VERSION=3.12.4`, `APP_DATABASE_URL`, and later your LLM key and `APP_PASSWORD`
3. Under **Settings &gt; Custom Domains**, add your domain, then add the DNS records Render shows you at your
   registrar. Ask your agent to explain each record before you add it. HTTPS turns on automatically.
4. Free services sleep when idle and take about a minute to wake. Say so on your site.

---

## Troubleshooting

- **`pip install` fails with "No such file or directory" on Windows:** the folder path is too long. Move the
  project to a short path such as `C:\dev\bsad6153` and recreate `.venv`.
- **PowerShell says running scripts is disabled when you activate:** use Command Prompt instead and run
  `.venv\Scripts\activate.bat`, or ask the instructor. Don't change system security settings without asking.
- **`python` opens the Microsoft Store or isn't found:** use `py -3.12` on Windows or `python3.12` on macOS.
- **The database check can't connect:** use Supabase's Session pooler string, check the password, and check
  that your Supabase project isn't paused.

---

## Project Proposal

My project will support a recurring decision: which day and Kansas location should I prioritize for whitetail hunting? I want to compare wind, temperature, precipitation, sunrise/sunset, and lunar information in one place. These conditions will inform my planning rather than serve as a guaranteed prediction of deer encounters.

My primary source is the Visual Crossing Timeline Weather API. It provides historical and forecast weather, daily astronomy information, and related weather-station records. The initial collection contains 528 historical hourly records, 73 forecast hourly records, and four unique stations for Marquette, Kansas. Open-Meteo is my backup for weather information if Visual Crossing becomes unavailable. Switching would require adapting its fields and checking which astronomy features and station relationships are unavailable.

Today, I consult several weather applications, a lunar-cycle website, and a sunrise/sunset website. My baseline log records one decision that took 14 minutes and 7 seconds. Switching websites and repeating location searches makes comparisons time-consuming. I want the system to provide a clear view of my preferred locations, dates, and conditions. I will compare later decision times with my baseline rather than assume the system saves time.

By Week 6, my proposed agent would prepare and save a side-by-side scouting brief for locations and dates I explicitly select. It would combine relevant conditions, identify missing or stale information, and explain comparisons. I would make the final scouting choice; the agent would not assume my location or schedule.

Risks include daily API limits, disabled or expired credentials, increasing data volume, changing forecasts, missing fields, and confusing historical observations with predictions. Daylight-saving changes also require careful timestamp handling. The current fetcher protects credentials, waits between requests, retries temporary failures, and reports results. Future syncing will need explicit freshness tracking. Storage, public display, attribution, and sample-sharing practices must follow applicable terms and instructor guidance.

## How to run this project

Run these commands from the repository folder after completing the Python 3.12,
virtual environment, package installation, and `.env` setup above. Store your real
weather key only in `.env` as `VISUAL_CROSSING_API_KEY`; `.env.example` contains
only the blank variable name.

### 1. Run the offline checks

```bash
.venv/bin/python -B ingest/test_fetch.py
```

These four tests simulate API responses and waits. They do not read the API key,
contact Visual Crossing, or use API allowance. Successful output ends with `OK`.

### 2. Preview the download plan

```bash
.venv/bin/python -B ingest/fetch.py \
  --start 2026-10-01 \
  --end 2026-10-22 \
  --batch-days 1 \
  --forecast-days 3 \
  --minimum-records 500 \
  --budget 600 \
  --dry-run
```

This previews inclusive one-day historical batches for Marquette, Kansas, plus
three upcoming complete forecast days. Forecast dates are calculated when the
script runs, using `America/Chicago`. Dry-run mode reads no key, sends no API
requests, and writes no files.

### 3. Retrieve the data after checking your account allowance

```bash
.venv/bin/python -B ingest/fetch.py \
  --start 2026-10-01 \
  --end 2026-10-22 \
  --batch-days 1 \
  --forecast-days 3 \
  --minimum-records 500 \
  --budget 600
```

Unlike the preview, this command can use API allowance and writes responses to
`data/raw/visual_crossing/`. The `--budget` is a conservative allowance cap for
this run, including retries; it is not a dollar amount or an account-balance
check. Other account activity is not included, so inspect your provider usage
page before making live requests.

The summary reports downloaded and reused files, failures, distinct hourly
records, station records, missing core values, and reported `queryCost`.
The verified October 29, 2026 collection contained 528 historical hours,
73 forecast hours, and four unique stations. Future forecast counts and values
can differ, including around daylight-saving changes. Resource counts and the
provider's allowance accounting are different measurements.

### Saved files and refresh behavior

- `data/raw/` is ignored by Git. Full downloaded responses stay local.
- Matching saved responses are reused by default. A repeated command may be a
  cache-reuse run rather than a new API download; a saved forecast can be stale.
- Adding `--refresh` requests matching batches again and overwrites their saved
  files. It uses allowance and does not preserve the previous forecast version.
  Do not add it without checking the account's remaining allowance.
- Network timeouts, HTTP 429, and server errors have bounded retries. A persistent
  error or insufficient budget stops the affected download and is reported;
  already saved responses remain available.
- Read `docs/data_dictionary.md` for field meanings, relationships, null values,
  and the distinction between forecasts and historical observations.

Database loading and scheduled syncing are not implemented yet. For a
screencast, show whether each response was freshly downloaded or reused; do not
present cached results as evidence of a new live request. Keep `.env` and your
API key off-screen.

## Credits

[Weather Data Provided by Visual Crossing](https://www.visualcrossing.com/).
Weather and astronomy data are retrieved through the
[Visual Crossing Timeline Weather API](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/).
See `docs/data_dictionary.md` for source details and data-use notes.
