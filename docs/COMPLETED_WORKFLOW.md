# BingeBox: complete workflow from start to finish

This document records the work actually performed, complements the original source workflow, and provides a repeatable handover. The source proposal is in [BingeBox_Project_Workflow.md](reference/BingeBox_Project_Workflow.md).

Latest follow-up, 21 October 2026: the [complete submission audit](submission-coverage.md) checks A1-A8, R1-R13, roles/plans, EER/schema and W1-W3. Added exact SQL result assertions and fixed chronology, lapsing-period eligibility, literal search characters and report ties. Added commit-time genre participation with concurrent-removal tests. The full integration suite now has **136 passing tests**; all **11 browser journeys pass**, including automatic progress-save cadence. Applied `08_genre_participation.sql` through `scripts/migrate.py`, rebuilt the API and reran `scripts/verify_delivery.py`; the 840-row baseline and source documents remain intact. Source differences are explicit in the audit, not hidden by a blanket compliance claim.

## 1. Recover and verify the source

1. Locate `BingeBox_MidSem_Submission.pdf`; inspect all six pages.
2. Extract text, reconstruct tables and preserve headings, page order, footers, mathematical operators and identifiers.
3. Render/check the EER diagram and retain it as an image with a searchable transcription.
4. Compare source text tokens and all schema rows. Verify 18 relations, 99 columns, R1–R13, A1–A8, W1–W3, named functions/triggers/views and index categories.
5. Produce the full [Markdown transcription](reference/BingeBox_MidSem_Submission.md), with a verification appendix distinguishing source claims from verified implementation facts.

## 2. Establish the working directory

1. Create `C:\ACC\DL\BingeBox` without Git.
2. Copy reference documents under `docs/reference/`; keep them unchanged.
3. Use `gpu_env` for local Python. Record workspace restrictions in `AGENTS.md`.
4. Record source ambiguities in [decisions.md](decisions.md); keep milestone evidence in [progress.md](../progress.md).

## 3. Build the database foundation

1. Implement all source columns, types, defaults, keys, checks and delete behavior in `db/01_schema.sql`.
2. Add deferred subtype completeness enforcement in `02_integrity.sql`.
3. Declare 12 explicit indexes in `03_indexes.sql` and five repeatable seed plans in `04_seed.sql`.
4. Configure Docker PostgreSQL 16 and the initial FastAPI health/plan endpoints. Generate local secrets without printing or overwriting them.
5. Start Docker; test real PostgreSQL in disposable databases. Verify data survives container restart.

## 4. Load realistic, bounded data

1. Construct a coherent 200-row fictional snapshot: households, plans, profiles, dated subscriptions, devices, titles, episodes, watch attempts and eligible feedback.
2. Include typical values and valid extremes: 1/600-minute movies, 1/300-minute episodes, ratings 1/10, partial/complete/repeated watches, kids, suspended/expired accounts and 90% completion boundaries.
3. Verify the public Kaggle source’s CC0 metadata licence, inspect a maximum 1,000-row source window and retain 150 movies deterministically.
4. Preserve unknown fields as unknown, map maturity conservatively, store provenance outside the domain schema, and enforce an import row cap.
5. Verify **840 rows**, **162 titles**, source hashes, repeatability and 11 dataset consistency checks. Keep source/import reports under `data/kaggle/`.

## 5. Implement transactional business rules

1. Implement all 15 named functions and six business triggers in `05_workflows.sql`.
2. Coordinate account-level profile/stream/subscription limits with row locks. Make plan changes atomic and refusals non-destructive.
3. Implement calendar-month renewal/catch-up, payment-hook calls, expiry, suspension and reinstatement.
4. Enforce target, age, duration, progress, completion and feedback eligibility. Add guards for parent edits that would invalidate child records.
5. Test boundary values, rollback, same-device replacement and competing last-slot requests through independent database connections.

## 6. Add views, queries and access control

1. Build four views in `06_views.sql`; aggregate catalogue details without adding denormalised base columns.
2. Implement the nine retrieval/report categories: browsing, search, up next, top ten per genre, recommendations and four staff reports.
3. Add the runtime database role in `07_permissions.sql`, signed session cookies, scrypt passwords, profile ownership, staff role gates and kids-mode unlock.
4. Apply additive migrations to the existing application; retain its 840-row snapshot.

## 7. Deliver playable media

1. Generate original H.264, 640×360 SD placeholders, visibly labelled and exactly matched to item runtime.
2. Cache files by runtime; use a virtual fallback for imported metadata without inserting asset rows.
3. Implement protected, seekable byte-range delivery and signed playback context. Check authorisation on media/progress calls.
4. Save progress every ten seconds, on pause and on explicit close. Resume unfinished attempts; support replay and completion-dependent feedback.
5. Prewarm/probe every distinct runtime using `scripts/prepare_media.py`; retain `media/manifest.json`.
6. Support appropriate YouTube trailer IDs and administrator-provided permitted local MP4s. Do not bundle copyrighted films or invent trailer associations.

## 8. Build and refine the interface

1. Implement guest discovery, filters, previews, plans and login/signup.
2. Implement profile selection/management, home rows, full title/episode pages, player, feedback and account/device management.
3. Implement role-aware Studio catalogue CRUD, plans, renewals, suspension and reports.
4. Implement the selected Stitch design with locally hosted Syne/Plus Jakarta Sans, obsidian surfaces and indigo accents. Earlier warm, monochrome and reference-inspired experiments are retired; saved variant URLs normalize to the main application. Preserve the independent requirements-only Stitch brief under `docs/stitch`.
5. Assign each of the 162 catalogue titles a persistent, unique cover. Verify promotional posters by title, release year and poster identity; retain labelled illustrative covers when a verified download is unavailable. Store source and hash evidence in `docs/evidence/catalogue-art-manifest.json`.
6. Integrate quick-look keyboard behavior, featured selection, native scroll depth and section reveals. Respect reduced motion. Recheck all original viewing/account/staff journeys against the isolated browser database.
5. Verify desktop/mobile layouts and form/accessibility behavior; preserve all project features during the restyle.

## 9. Verify end to end

1. Run `python scripts/run_checks.py` from `gpu_env`. The runner creates and drops only its own uniquely named PostgreSQL test database and redacts generated secrets from diagnostic output.
2. Run `npm run build` in `frontend/` to verify a production build.
3. Run `python scripts/run_browser_checks.py`: seed an isolated 840-row database, launch temporary API/web servers, drive real Chromium through the UI, save screenshots, and stop/remove the test resources.
4. Exercise guest/mobile discovery; actual video seek/save/resume/completion/review; profile cap and downgrade refusal; successful upgrade and auto-renew; kids unlock; staff CRUD, suspension, reports and renewal expiry.
5. Verify application health, baseline counts, generated media and source/document links separately. Record the exact final results in [test-results.md](test-results.md).

## 10. Package and hand over

1. Keep the project running at [localhost:18080](http://localhost:18080).
2. Deliver source files, verified source Markdown, this completed workflow, [requirements matrix](requirements-matrix.md), [normalisation analysis](normalisation.md), [demo guide](demo-guide.md), data provenance and verification evidence.
3. Retain the accepted initial dataset. Interactive user activity may subsequently increase row counts.
4. State scope accurately: simulated payments and labelled placeholder films, no public deployment, DRM or precise idle timeout.

## Fresh-start commands

From the project directory, with Docker Desktop running:

```powershell
conda activate gpu_env
python scripts/configure.py
docker compose up -d --build --wait --wait-timeout 240
python scripts/migrate.py
# Only for an empty application database:
python scripts/seed_demo.py
python scripts/import_kaggle.py
python scripts/prepare_media.py
python scripts/run_checks.py
cd frontend
npm ci
npx playwright install chromium
npm run build
cd ..
python scripts/run_browser_checks.py
```

For an already-populated workspace, skip the two loading commands. Stop with `docker compose stop`; resume with `docker compose start --wait`. Keep the PostgreSQL volume. Never reset live data to run tests or apply an additive migration.
