# BingeBox

A complete local DBMS course application: PostgreSQL 16, FastAPI with psycopg 3 and hand-written SQL, and React/Vite with React Router. This directory is **not a Git repository**. Local Python commands use the existing Conda **`gpu_env`**; no `.venv` is used.

Open **[BingeBox](http://localhost:18080)**. API documentation: [localhost:18000/docs](http://localhost:18000/docs).

**Stitch is the only interface**, using the approved obsidian, white and indigo design. Saved `/stitch/`, `/black-white/` and `/cinematic/` links normalize to the corresponding main route. The catalogue uses verified posters where obtainable and distinct, labelled illustrative covers otherwise. See [artwork provenance](docs/catalogue-artwork.md).

## Run

With Docker Desktop running, use PowerShell in this directory:

```powershell
conda activate gpu_env
python scripts/configure.py
docker compose up -d --build --wait --wait-timeout 240
python scripts/migrate.py
```

The configuration script preserves the database password and adds an authentication secret if missing. PostgreSQL persists in a named volume. The website, API and database bind to localhost only. Database connection: `127.0.0.1:15432`, database/user `bingebox`, password in the local `.env` file.

The current database already contains **840 rows across 18 tables**, including **162 titles**. The baseline combines 200 fictional demo rows with 640 additional rows representing 150 real Kaggle movies and their relationships. Ordinary use adds watch sessions, reviews and subscriptions; 840 is the initial dataset size, not a permanent application limit.

To populate a **new empty database** after startup:

```powershell
python scripts/seed_demo.py
python scripts/import_kaggle.py
python scripts/prepare_media.py
```

The retained CSV is used without another download. The seeder anchors a new snapshot to today; this workspace’s original snapshot is 20 October 2026. Seed/import scripts retain matching data, refuse conflicting data and never reset an existing application. Do not rerun baseline count validation after deliberately adding user activity and expect the original counts to remain unchanged.

## Demo logins

All fictional demo accounts use **`BingeBox-Demo-2026!`**. Select “Staff account” on the sign-in form for staff logins.

| Email | Demonstration |
| --- | --- |
| `dev.menon@bingebox.example` | Basic plan, one profile, no initial live stream; easy playback starting point |
| `meera.iyer@bingebox.example` | Basic plan with an existing live device; stop it in Account to play |
| `kabir.malhotra@bingebox.example` | Duo with two profiles; demonstrate profile cap and refused downgrade |
| `rohan.desai@bingebox.example` | Family with adult and kids profiles |
| `vikram.rao@bingebox.example` | Suspended account |
| `ananya.sen@bingebox.example` | Expired subscription |
| `catalogue@staff.bingebox.example` | Catalogue, episode, genre, trailer and video management |
| `billing@staff.bingebox.example` | Renewals, suspension/reinstatement and reports |
| `super@staff.bingebox.example` | All staff functions, including plans |

Existing seeded subscriptions can become past their end dates. Billing staff can process renewals through today. Opted-out subscriptions expire; their account holders can choose a new plan. The demo password is deliberately public; the generated database/authentication secrets are not.

## Implemented scope

- Account/staff authentication, profile selection, profile CRUD, password-protected exit from kids mode, ownership and role checks.
- Plans, simulated payment hook, subscriptions, atomic plan changes, automatic renewal preference, staff renewal processing, suspension and reinstatement.
- Guest previews; full-text/fuzzy search; genre, audio, subtitle, runtime and IMDb filters; pagination; title/episode details and YouTube trailer embedding.
- Continue watching, up next, top ten per genre, and recommendations based on watched genres.
- Playback with subscription/age/device/quality checks; HTML5 seeking, resume/replay, progress and completion; eligible reviews and episode ratings.
- Staff CRUD for titles, episodes, genres, video assets and plans; four reporting screens.
- Stitch interface with featured-title selection, accessible quick look, native scroll depth, viewport reveals, hover/focus feedback and reduced-motion support. Project rules are in [DESIGN.md](DESIGN.md).

Full videos are **generated, visibly labelled SD placeholders**, matched to each movie or episode runtime. Kaggle metadata does not include film rights. Files are generated on demand; `prepare_media.py` prewarms and probes all distinct runtimes. The longest is 600 minutes. No licensed films are bundled. Promotional posters retain their original rights; source pages are recorded in the artwork manifest. Trailer management accepts YouTube IDs; the initial dataset has no invented trailer associations. A catalogue administrator can add an appropriate trailer or a permitted MP4 placed under `media/`.

Payments always succeed through the course’s stub. There is no real billing, DRM, content transcoding pipeline or idle-session timeout. DATE-only source columns are preserved. These are scope boundaries, not unfinished integrations.

## Verification

```powershell
conda run --no-capture-output -n gpu_env python scripts/run_checks.py
cd frontend
npm ci
npx playwright install chromium
npm run build
cd ..
conda run --no-capture-output -n gpu_env python scripts/run_browser_checks.py
```

Python tests use a uniquely named temporary PostgreSQL database. Browser tests create their own 840-row database and temporary API/frontend servers on ports 18001/18081, then remove them. They never reset or mutate the application database. Local Python runs in `gpu_env`; the Docker API has its own container interpreter. [Test evidence](docs/test-results.md) explains coverage and limitations.

## Operations and documents

```powershell
docker compose ps
docker compose stop
docker compose start --wait
```

Keep the PostgreSQL volume when stopping or rebuilding. Numbered SQL installs a fresh database; `scripts/migrate.py` applies the additive workflow/view/permission/integrity scripts to an existing foundation. No database reset is needed. Titles must have at least one genre; the migration refuses existing unclassified titles rather than assigning invented categories.

| File | Purpose |
| --- | --- |
| [Verified PDF transcription](docs/reference/BingeBox_MidSem_Submission.md) | Complete source content, diagram and fidelity appendix |
| [Original implementation workflow](docs/reference/BingeBox_Project_Workflow.md) | Source-to-project implementation plan |
| [Completed workflow](docs/COMPLETED_WORKFLOW.md) | Actual start-to-finish process and rerun commands |
| [Demo walkthrough](docs/demo-guide.md) | W1–W3 and staff demonstration steps |
| [Requirements matrix](docs/requirements-matrix.md) | R1–R13, object counts and evidence |
| [Complete submission audit](docs/submission-coverage.md) | A1–A8, roles, plans, EER/schema, W1–W3 and explicit source differences |
| [Decisions](docs/decisions.md) | Resolved source ambiguities and deliberate deviations |
| [Normalisation analysis](docs/normalisation.md) | Keys, dependencies and source qualifications |
| [Data provenance](docs/data-sources.md) | Kaggle source, licence, sample, mapping and limitations |
| [Progress](progress.md) | Implementation milestones |
| `db/01_schema.sql`–`db/07_permissions.sql` | Schema, indexes, seed plans, business functions, triggers, views and role |
| `backend/app/` | API, authentication, connections and named reporting queries |
| `frontend/src/` | Viewing interface, player, account pages and lazy-loaded staff console |
| `media/manifest.json` | Generated-media duration and codec verification |
| `docs/evidence/` | Browser screenshots and verification artifacts |

The original PDF and verified Markdown remain unchanged in `docs/reference/`. The root workspace also retains the two originally requested Markdown files.
