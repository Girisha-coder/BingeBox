# BingeBox

BingeBox is a Netflix-style streaming web application built for the **CS F212 Database Systems** project at BITS Pilani, Hyderabad Campus (Group 7, lab section P1). A household **account** subscribes to one of five **plans**; the plan limits how many **profiles** the household can create, how many devices can stream at once and the best video quality. Profiles (adult or kids) browse a catalogue of movies and series, watch videos with resume support, and review titles or rate episodes once they have finished them. Guests get a limited preview, and staff manage the catalogue, subscriptions and reports.

The project's focus is the database: an EER design mapped to **18 relations** in PostgreSQL, with business rules enforced inside the database by constraints, triggers, stored functions and views.

## Team

| Name | ID |
| --- | --- |
| Sai Poojit Baratam | 2024A8PS0494H |
| Girisha | 2024A8PS0497H |
| Puneet Singh | 2024A8PS0507H |
| Vedaang Kharya | 2024A8PS0511H |
| Sanjay Rajkumar | 2024A8PS2044H |

**Submitted version:** Git tag `final`. Its commit hash is recorded on the Demo Sheet.

## Features

- **Accounts and profiles:** sign-up and sign-in, up to the plan's number of profiles, kids profiles limited to age rating 7 with a password needed to leave kids mode.
- **Plans and subscriptions:** subscribe, upgrade or downgrade (refused if the household has too many profiles), auto-renew, staff-run renewals, account suspension. Payments are simulated by a single placeholder function; there is no real billing.
- **Catalogue:** guest preview, full-text and typo-tolerant search, filters for genre, audio and subtitle language, runtime and IMDb rating, title and episode pages, YouTube trailers.
- **Home page:** continue watching, up next, top 10 per genre and genre-based recommendations.
- **Playback:** age, subscription, device-limit and quality checks; resume or start again; progress saved every 10 seconds; completion at 90%. Full videos are labelled placeholder videos generated to each title's exact runtime; no licensed films are included.
- **Reviews and ratings:** allowed only after the profile has finished the movie or episode.
- **Staff Studio:** catalogue staff manage titles, episodes, genres and videos; billing staff run renewals, suspend or reinstate accounts and view four reports; super staff can do everything, including editing plans.

## Technology stack

| Layer | Technology |
| --- | --- |
| Database | PostgreSQL 16 |
| Backend | Python 3.12, FastAPI, psycopg 3 (hand-written SQL, no ORM), uvicorn |
| Frontend | React 19, React Router, Vite |
| Web server | nginx (serves the website and forwards `/api` to the backend) |
| Packaging | Docker and Docker Compose (three containers: `db`, `api`, `web`) |
| Video | ffmpeg (generates the placeholder videos inside the `api` container) |
| Tests | pytest (database and API), Playwright (browser) |

## Database

The database server runs in the `db` container. Its data is kept in the Docker volume `bingebox_postgres_data`, which survives restarts until it is deleted with `docker compose down -v`. The repository holds the scripts that build it.

| File | Contents |
| --- | --- |
| [`db/01_schema.sql`](db/01_schema.sql) | The 18 tables with primary keys, foreign keys, UNIQUE, NOT NULL and CHECK constraints |
| [`db/02_integrity.sql`](db/02_integrity.sql) | Deferred triggers: every title must have its movie or series row (total specialisation) |
| [`db/03_indexes.sql`](db/03_indexes.sql) | 12 indexes, including the partial unique index allowing one current subscription per account |
| [`db/04_seed.sql`](db/04_seed.sql) | The five plans |
| [`db/05_workflows.sql`](db/05_workflows.sql) | 15 business functions (subscription, renewal, suspension, playback) and the business-rule triggers |
| [`db/06_views.sql`](db/06_views.sql) | 4 views: title catalogue, guest catalogue (security view), account status, continue watching |
| [`db/07_permissions.sql`](db/07_permissions.sql) | Restricted role `bingebox_app` used by the backend |
| [`db/08_genre_participation.sql`](db/08_genre_participation.sql) | Deferred triggers: every title must keep at least one genre |
| [`backend/app/queries.py`](backend/app/queries.py) | Up next, top 10 per genre, recommendations and the four staff reports |
| [`backend/app/main.py`](backend/app/main.py) | All API routes and the catalogue search query |
| [`scripts/seed_demo.py`](scripts/seed_demo.py) | 200 fictional demonstration rows (accounts, staff, titles, history, reviews) |
| [`scripts/import_kaggle.py`](scripts/import_kaggle.py) | 640 rows for 150 real Netflix movies from a CC0 Kaggle sample in `data/kaggle/` |
| [`scripts/demo_queries.sql`](scripts/demo_queries.sql) | The five demonstration queries and three DBMS features, ready to run; changes no data (see [Demo queries](#demo-queries)) |

After setup the database holds **840 rows** across the 18 tables. The design, its assumptions and the normalisation are described in the Database Design Document (submitted separately) and in [`docs/normalisation.md`](docs/normalisation.md) and [`docs/decisions.md`](docs/decisions.md). The mid-sem design is in [`docs/reference/`](docs/reference/).

## Setup and run

**Prerequisites:** Docker Desktop (running), Python 3.12 or newer, and Git. Git LFS is not needed. No Docker? See [Running without Docker (Windows)](#running-without-docker-windows).

Windows (PowerShell), from the folder where you want the project:

```powershell
git clone https://github.com/Girisha-coder/BingeBox.git
cd BingeBox
python scripts/configure.py
docker compose up -d --build --wait --wait-timeout 600
python -m venv .venv
.venv\Scripts\python.exe -m pip install "psycopg[binary]==3.3.6"
.venv\Scripts\python.exe scripts\seed_demo.py
.venv\Scripts\python.exe scripts\import_kaggle.py
```

macOS or Linux: the same steps, using `python3` and `.venv/bin/python` instead of `python` and `.venv\Scripts\python.exe`.

What each step does:

1. `configure.py` creates a local `.env` file with a random database password and signing secret. It never overwrites an existing `.env`, and `.env` is never committed.
2. `docker compose up` builds and starts the database, backend and website. On the first start the database runs every SQL file in `db/` in order, creating the tables, rules, views and the five plans.
3. The last four commands create a private Python environment and load the 840 demonstration rows. Both scripts run as single transactions and refuse to mix with unrelated existing data.

Then open **http://localhost:18080**. The backend's interactive API documentation is at http://localhost:18000/docs.

Notes:

- **Dates:** the seed script dates everything relative to the day it runs. Seeded subscriptions last about a month, and one (meera.iyer) deliberately ends the next day to demonstrate expiry. If the data is older, sign in as `billing@staff.bingebox.example` and process renewals through today.
- **Videos:** a title's placeholder video is generated the first time it is played (about 8 seconds for the longest, 600-minute film). To pre-generate all 86 runtimes after loading the data, run `python scripts/prepare_media.py`.
- **Looking inside the database:**

  ```powershell
  docker compose exec db psql -U bingebox -d bingebox
  Get-Content scripts\inspect_demo.sql | docker compose exec -T db psql -U bingebox -d bingebox
  ```

  The first opens an interactive SQL prompt; the second runs a set of read-only example queries. Any database client can also connect to `localhost:15432`, database and user `bingebox`, with the password from `.env`.
- **Stop:** `docker compose down` (keeps the data). **Reset:** `docker compose down -v` (deletes the database; the next `up` rebuilds it from `db/`, after which the data scripts must be run again).
- **Troubleshooting, "container bingebox-api-1 is unhealthy":** this happens when a database volume from an earlier setup is still present. The database keeps the password it was first created with, so it no longer matches a newly created `.env`. Reset the database and load the data again:

  ```powershell
  docker compose down -v
  docker compose up -d --build --wait --wait-timeout 600
  .venv\Scripts\python.exe scripts\seed_demo.py
  .venv\Scripts\python.exe scripts\import_kaggle.py
  ```

## Running without Docker (Windows)

For a computer without Docker. The same database, backend and website run directly on Windows, started by [`scripts/start_local.ps1`](scripts/start_local.ps1). Use a project folder for one method only: the setup points `.env` at the local PostgreSQL port, which the Docker setup would then also try to use.

**1. Install the programs (once).** In any PowerShell window:

```powershell
winget install PostgreSQL.PostgreSQL.16
winget install Python.Python.3.12
winget install Gyan.FFmpeg
winget install OpenJS.NodeJS.LTS
```

Accept the prompts (type `Y` for winget's terms and allow the installers to make changes). The PostgreSQL package installs version 16, the same as in Docker, on port 5432 with the superuser `postgres` and the password `postgres`. Skip any program that is already installed. Afterwards, close and reopen VS Code or the terminal so that the new programs are found.

**2. Download and set up the project (once).** From the folder where you want the project, for example in the VS Code terminal:

```powershell
git clone https://github.com/Girisha-coder/BingeBox.git
cd BingeBox
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1 -Setup
```

`-ExecutionPolicy Bypass` lets Windows run the script without changing any system setting. The script asks once for the `postgres` password (`postgres` after the winget install; nothing is shown while typing). It then creates `.env`, creates the database user and database `bingebox`, runs every SQL file in `db/` in order, installs the Python and website packages, and loads the 840 demonstration rows. Running it again skips the steps already done. If PostgreSQL uses a port other than 5432, add `-DbPort <port>`.

**3. Start BingeBox (every time).**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
```

This starts the backend and the website in the same terminal and opens **http://127.0.0.1:5173**. Use that address exactly, not `localhost`: the backend accepts sign-ins only from the address it was started for. Press **Ctrl+C** to stop both. PostgreSQL keeps running in the background as a Windows service.

The demo logins and the tests below work the same way. If the script reports that port 18000 or 5173 is in use, stop the other program first, for example the Docker version with `docker compose stop`.

**Reset the demo data.** The demo data is dated relative to the day it was loaded (see the dates note under [Setup and run](#setup-and-run)), so reload it shortly before a demonstration. Stop BingeBox with Ctrl+C, then from the project folder:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -U postgres -c "DROP DATABASE bingebox WITH (FORCE)"
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1 -Setup
powershell -ExecutionPolicy Bypass -File scripts\start_local.ps1
```

The first line deletes the database (password `postgres`), the second rebuilds it with fresh demo data, and the third starts BingeBox again.

**SQL prompt and demo queries.** With BingeBox running, open a second terminal in the project folder:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -U postgres -d bingebox
```

Enter the password `postgres`. When the prompt shows `bingebox=#`, type SQL directly, or run the demonstration file with `\i scripts/demo_queries.sql` (see [Demo queries](#demo-queries)). `\q` leaves the prompt. If a different PostgreSQL version is installed, change `16` in the path.

## Demo logins

All demo accounts use the password **`BingeBox-Demo-2026!`**. Tick "Staff account" on the sign-in page for the staff logins.

| Email | Set up to demonstrate |
| --- | --- |
| `dev.menon@bingebox.example` | Basic plan, one profile, no live stream: simplest playback start |
| `meera.iyer@bingebox.example` | Basic plan with a device already streaming: the device limit |
| `kabir.malhotra@bingebox.example` | Duo plan with two profiles: profile limit and refused downgrade |
| `rohan.desai@bingebox.example` | Family plan with an adult and a kids profile (Tara) |
| `vikram.rao@bingebox.example` | Suspended account |
| `ananya.sen@bingebox.example` | Expired subscription |
| `catalogue@staff.bingebox.example` | Catalogue staff |
| `billing@staff.bingebox.example` | Billing staff: renewals, suspension, reports |
| `super@staff.bingebox.example` | Super staff: everything, including plans |

## Workflows

| Workflow | DBMS aspect | What happens | Where |
| --- | --- | --- | --- |
| W1 Subscription lifecycle | Transaction across several tables | Subscribe, change plan (cancel old subscription, end live streams, start new subscription in one transaction), refused downgrade, renewals, suspension | `subscribe`, `change_plan`, `process_renewals`, `suspend_account` in `db/05_workflows.sql`; trigger `profile_limit` |
| W2 Discovery and reports | Complex retrieval | Search and filters, guest preview through a security view, continue watching, up next, top 10 per genre, recommendations, four staff reports | Catalogue query in `backend/app/main.py`; views in `db/06_views.sql`; `backend/app/queries.py` |
| W3 Playback and integrity | Integrity enforcement | Device limit, kids age limit, resume, completion at 90%, reviews only after finishing | `start_session`, `start_playback`, `record_progress` and the triggers `watch_age_check`, `watch_progress`, `review_requires_watch`, `eprating_requires_watch` in `db/05_workflows.sql` |

A step-by-step demonstration script is in [`docs/demo-guide.md`](docs/demo-guide.md).

## Demo queries

[`scripts/demo_queries.sql`](scripts/demo_queries.sql) runs the five SQL queries and the three DBMS features used in the demonstration, plus one index check. Each block names the file and lines where its SQL is written, the backend code that runs it and the screen that shows it. It changes no data: anything that would change data is refused by the database or runs inside `BEGIN ... ROLLBACK`.

| Part | Contents |
| --- | --- |
| Q1 | Staff report of active subscriptions per plan: LEFT JOIN, GROUP BY, COUNT (`backend/app/queries.py` line 22) |
| Q2 | Account status: each account's latest subscription, plan limits and current usage, using correlated subqueries (the query of the view `v_account_status`, `db/06_views.sql` lines 21-26) |
| Q3 | Catalogue details per title: seven joins with SUM, COUNT, ARRAY_AGG and AVG inside subqueries (the query of the view `v_title_catalog`, `db/06_views.sql` lines 1-14) |
| Q4 | Top titles in each genre: CTE and the window function `ROW_NUMBER() OVER (PARTITION BY ...)` (`backend/app/queries.py` lines 11-14) |
| Q5 | Recommendations for one profile: CTE, nested subqueries, GROUP BY (`backend/app/queries.py` lines 15-20) |
| F1 | Trigger `profile_limit` refusing a third profile on the Duo plan |
| F2 | Stored procedure `change_plan` as one transaction: a refused downgrade, then an upgrade undone by ROLLBACK |
| F3 | View `v_guest_catalog`: what a guest sees, compared with the base table |
| Bonus | Partial unique index `subscription_one_current`: a second current subscription is refused |

To run it:

- **With Docker:** `Get-Content scripts\demo_queries.sql | docker compose exec -T db psql -U bingebox -d bingebox`
- **Without Docker:** open the SQL prompt as described in [Running without Docker](#running-without-docker-windows), then `\i scripts/demo_queries.sql`.

## Tests

With the project running, in Docker or locally after `start_local.ps1 -Setup`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install "pytest==9.0.3" "httpx==0.28.1"
.venv\Scripts\python.exe scripts\run_checks.py
```

This runs 136 database and API tests (constraints, triggers, functions, query results, concurrency, roles), each on a temporary database created on the project's PostgreSQL server and dropped afterwards. It never touches the application database.

The 11 browser tests (`scripts/run_browser_checks.py`) additionally need Node.js and ffmpeg on the computer: run `npm ci` and `npx playwright install chromium` in `frontend/` first. See [`docs/test-results.md`](docs/test-results.md).

## Data and media sources

- Real movie metadata: a 150-movie sample of the Kaggle dataset "Netflix Movies and TV Shows" (`shivamb/netflix-shows`, CC0 licence). It has no IMDb ratings, so those columns are empty for these titles. Details in [`docs/data-sources.md`](docs/data-sources.md).
- Fictional demo data: written for this project in `scripts/seed_demo.py`.
- Videos: generated placeholders only. Trailers are YouTube embeds added by catalogue staff (none are included in the initial data).
- Cover art: 14 posters with recorded source pages and 148 illustrative photos; see [`docs/catalogue-artwork.md`](docs/catalogue-artwork.md).

## Individual contributions

The EER model and the mid-sem design were produced jointly by all five members.

| Member | Area of responsibility |
| --- | --- |
| Girisha (2024A8PS0497H) | Catalogue database: `title`, `movie`, `series`, `episode`, `genre` and the linking tables, with their constraints; the specialisation and genre-participation triggers (`02_integrity.sql`, `08_genre_participation.sql`); Kaggle import (`import_kaggle.py`); backend structure, Docker setup and the GitHub repository |
| Sai Poojit Baratam (2024A8PS0494H) | Account and subscription database: `plan`, `admin_user`, `account`, `subscription`, `profile`; the subscription functions (`subscribe`, `change_plan`, `process_renewals`, `suspend_account`, `reinstate_account`) and the `profile_limit` trigger; the one-current-subscription index; Plans and Account pages; workflow W1 |
| Puneet Singh (2024A8PS0507H) | Playback and integrity: `stream_session`, `watch_history`, `media_asset`; the playback functions (`start_session`, `start_playback`, `record_progress`, `end_playback`); the age, progress, video-length and review-eligibility triggers; video streaming and placeholder generation in the backend; the player page; workflow W3 |
| Vedaang Kharya (2024A8PS0511H) | Queries, views and indexes: the four views (`06_views.sql`), the catalogue search query, the home-page queries and staff reports (`queries.py`), the indexes (`03_indexes.sql`); the discovery and search pages; code review, fresh-install testing, README and Demo Sheet; workflow W2 |
| Sanjay Rajkumar (2024A8PS2044H) | Reviews, data and design documentation: `title_review`, `episode_rating`; the restricted database role (`07_permissions.sql`); seed data (`04_seed.sql`, `seed_demo.py`); normalisation analysis and the Database Design Document; staff Studio (`Admin.jsx`); the test suite |

## Use of AI tools

AI tools were used during development, as the course guidelines permit: AI coding assistants to help write and test the application code and documentation, Google Stitch for the visual design (recorded in [`DESIGN.md`](DESIGN.md) and `docs/stitch/`), and Claude for code review and documentation. `AGENTS.md` and `progress.md` are the instruction file and working log of the coding assistant. All design decisions were reviewed by the team, and each member is responsible for explaining the parts listed under their name.

## Scope limits

Payments always succeed through the placeholder function; there is no real billing, DRM or video transcoding. Session dates are stored as DATE (a design choice), so device slots are freed by stopping playback or with "Stop stream" on the Account page rather than by a timeout.

## Further documents

| Document | Purpose |
| --- | --- |
| [`docs/demo-guide.md`](docs/demo-guide.md) | Demonstration steps for W1–W3 and the staff screens |
| [`docs/decisions.md`](docs/decisions.md) | Design decisions and deliberate deviations from the mid-sem design |
| [`docs/normalisation.md`](docs/normalisation.md) | Keys, functional dependencies and normal forms |
| [`docs/requirements-matrix.md`](docs/requirements-matrix.md) | Requirements mapped to database objects and tests |
| [`docs/submission-coverage.md`](docs/submission-coverage.md) | Mid-sem assumptions, roles, plans and workflows checked against the implementation |
| [`docs/data-sources.md`](docs/data-sources.md) | Kaggle source, licence and mapping |
| [`docs/test-results.md`](docs/test-results.md) | Test coverage and limitations |
| [`docs/reference/`](docs/reference/) | The mid-sem submission (PDF and transcription) |
| [`DESIGN.md`](DESIGN.md) | Visual design rules |
