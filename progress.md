# BingeBox progress

**Status: complete within the submitted course-project scope.** Last frontend verification: 21 October 2026.

| Step | Completed work | Evidence |
| --- | --- | --- |
| 1 — Source documents | Full six-page PDF transcription, diagram asset/transcription and implementation workflow | Source verification appendix; 18 tables / 99 columns checked |
| 2 — Workspace | Dedicated non-Git directory; existing `gpu_env`; no `.venv` | Project instructions and delivery audit |
| 3 — Foundation | PostgreSQL 16 schema, structural constraints, subtype integrity, 12 explicit indexes, five plans and Docker API | Schema integration tests and restart persistence check |
| 4 — Data | 200 fictional rows plus bounded Kaggle metadata → 840 rows, 162 titles | Import provenance, source hash, 11 semantic checks |
| 5 — Workflows | 15 business functions, six business triggers, lifecycle, playback, completion/feedback rules and locking | Boundary/rollback and independent-connection race tests |
| 6 — Retrieval/auth | Four views, nine query categories, account/staff login, ownership, roles and kids protection | HTTP integration tests and requirements matrix |
| 7 — Media | Protected seekable video, same-runtime SD placeholders, progress/resume/replay | 86 files ffprobe-verified; HTTP 206 and real browser playback |
| 8 — Interface | Guest, viewer, profile, account, player and staff screens | Vite production build and eleven browser journeys |
| 9 — Final design | User-selected Stitch-only interface; obsidian/indigo palette, accessible motion and 162 distinct covers | DESIGN.md, desktop/mobile screenshots |
| 10 — Handover | Completed workflow, demo guide, decisions, normalisation, requirements matrix and final evidence | README links and delivery audit |

Latest integration suite: **136 passed** (70.08s). Latest browser suite: **11 passed** (52.0s), including actual automatic progress-save cadence. The application baseline remains **840 rows** because tests use their own databases. Docker serves the application at **http://localhost:18080**.

The user’s constraints are retained: no Git repository, no `.venv`, existing Conda environment, bounded realistic data and original project scope. Simulated payments, labelled placeholder films and DATE-only session behavior are explicit scope decisions. No remaining planned implementation milestone is open; ordinary future user activity and optional permitted-media additions are not part of the initial dataset verification.

See [test results](docs/test-results.md), [completed workflow](docs/COMPLETED_WORKFLOW.md), [requirements matrix](docs/requirements-matrix.md) and [demo guide](docs/demo-guide.md).

## Database gaps and complete submission audit - 21 October 2026

Completed the follow-up against every source section, including A1-A8 and EER participation. Added expected-result tests for all nine query categories/four views, filters/pagination, plan and age boundaries, payment/renewal behavior, role restrictions and source-driven schema/index checks. Fixed up-next chronology, future-start lapsing results, literal wildcard search and binge date ties. Added deferred enforcement of at least one genre per title, including concurrent-removal protection without changing the 18-table/99-column schema.

Verification: **136 integration tests passed in 70.08s; all 11 browser journeys passed in 52.0s**, including automatic 10-15-second progress reports. A final affected-test rerun passed **51 tests in 5.16s** after improving the kids-cookie fixture and missing-genre HTTP assertion. Applied the migration, rebuilt the API and verified live health/catalogue. Delivery audit confirms 840 rows, 162 titles, no genre omissions, no leftover test databases, unchanged reference Markdown and preserved workspace constraints.

The [submission coverage audit](docs/submission-coverage.md) records each requirement and evidence, plus the accepted Kaggle substitution, historical-seeder difference and source normalization/device/renewal qualifications. The earlier execution-only SQL gaps recorded below are historical and closed by this work; exhaustive SQL branch coverage is not claimed.

## Separate palette page — 20 October 2026

Completed the requested black (`#000000`), white (`#FFFFFF`) and indigo (`#2C3480`) version at `http://localhost:18080/black-white/`. All app routes retain the alternate prefix. The original warm version at `/` and its stylesheet are preserved; both versions share the existing application data.

Validation: production Vite build passed; only the web container was rebuilt. Read-only Playwright checks passed for exact computed palette colors, alternate Plans navigation and direct reload, title and login routes, 390px mobile overflow, return to the original theme and original Plans navigation, with no JavaScript page errors. Desktop and mobile screenshots were visually inspected: [desktop](docs/evidence/black-white-home.png), [mobile](docs/evidence/black-white-mobile.png). No database mutations were performed for these checks. Earlier integration-suite results above remain the backend baseline; this palette change used focused frontend verification.

## Independent Stitch design exploration — 21 October 2026

Called the configured Stitch MCP through JSON-RPC, created a private project, and generated a fresh desktop concept from a requirements-only brief. No existing layouts, code, screenshots or design references were supplied. Saved the screenshot, HTML, full explanation, submitted prompts and responses under `docs/stitch`. The user approved the first concept's broader dark blue/indigo palette. Inspected the generated HTML: hover/press feedback and a basic overlay exist, while scroll choreography remains proposed. A refinement call for scope corrections and working scroll motion returned service unavailable. See [reviewed ideas](docs/stitch/reviewed-ideas.md) for precise limitations and follow-up ideas. Both running frontend versions and the database remain unchanged.

## Additional reference-inspired version — 21 October 2026

Completed `/cinematic/` from the user's separate Bingwatch URL. Added a full-width photographic hero, locally bundled fonts/WebP assets, real-data featured selector, image cards, horizontal account discovery rows, scroll depth, viewport reveals, hover/focus feedback and reduced-motion support. Existing workflows run under the new namespace; no unsupported watchlist, fake match percentages or media-quality claims were added. `/` and `/black-white/` remain intact. The Stitch concept and palette approval remain separate saved artifacts.

Validation: production build passed; **3 focused Playwright journeys passed in 8.7s** against an isolated 840-row fixture, then the temporary database and servers were removed. Checks cover guest search, hero selection, deep links/reload, original theme isolation, 320/390/768px layouts, reduced motion, keyboard navigation, login, profile selection and actual video playback/save. Desktop/mobile screenshots were visually inspected. Only the web container is rebuilt for delivery; the application database is unchanged by these tests.


## Stitch-only delivery and distinct covers - 21 October 2026

The latest user decision supersedes preservation of earlier variants: Stitch is now the sole interface at http://localhost:18080. Saved `/stitch/`, `/black-white/` and `/cinematic/` URLs normalize to the equivalent root route, retaining query strings and fragments. Retired components, theme styles, image assets and unused font packages were removed from the application; historical design records remain under docs.

Implemented the independently generated Stitch layout with real catalogue metadata, explicit spotlight selection, a native quick-look dialog with focus containment/restoration, passive native-scroll depth, viewport reveals and reduced-motion support. Existing profiles, account, kids, subscription, playback, review and staff workflows are retained.

Replaced repeating catalogue artwork with 162 stable local covers: 14 title/year-verified promotional posters and 148 distinct illustrative covers. The 150 real titles were checked; repeated HTTP 429 responses prevented completing poster downloads, so unavailable downloads retain labelled fallbacks. Verified every cover hash and unique assignment; recorded sources, matching evidence and limitations in docs/catalogue-artwork.md. Existing successful poster writes were recovered after stopping the rate-limited download; subsequent downloads checkpoint metadata immediately.

Validation: production Docker/Vite build passed; **all 11 Playwright journeys passed in 30.7s** against an isolated 840-row PostgreSQL fixture, which was removed afterward. Coverage includes every artwork hash, image loading, search, quick look/focus, saved URLs/deep reload, 320/390/768px widths, reduced motion, profiles/kids, subscriptions, account stream cleanup, actual playback/save/resume/completion/review and staff CRUD/renewal/report flows. Test locators and account setup were corrected for featured headings and state changes made by earlier test journeys; no backend change was required. Earlier 64-test backend baseline remains unchanged.

Rebuilt only the web container. Live UI was inspected at the main URL and catalogue section; API/database containers remain healthy. Desktop/mobile and verified-poster contact sheets were visually inspected. No application database records were changed by this work. No outstanding scoped work remains.


## Catalogue page size - 21 October 2026

Changed the catalogue from 18 to 20 titles per page using a single page-size constant for the API limit, page count and Next-button boundary. The 162-title collection has nine pages, with two titles on the final page. Rebuilt the web container and verified the live first page contains titles 1-20 and the next page contains titles 21-40. Both focused guest-discovery/responsive and artwork-loading browser checks passed in 8.8s against a temporary database; it was removed afterward. The preceding complete Stitch suite passed all 11 journeys in 30.7s.


## SQL coverage recheck - 21 October 2026

Reran `scripts/run_checks.py` in the existing `gpu_env`: **64 passed in 39.51s** against a newly created PostgreSQL test database. All numbered SQL installation scripts execute in that database; the fixture drops it afterward. The application database is not used for test mutations.

Coverage includes schema/constraints, data loading, business functions/triggers, transaction rollback, date/progress/runtime boundaries, concurrency and SQL-backed API workflows. This is not proof of exhaustive SQL statement or branch coverage. In particular, `/home` executes up-next, recommendations and top-per-genre queries but currently asserts HTTP success rather than exact expected rows/rankings for each query. The four staff report endpoints likewise have execution checks without full expected-result/boundary assertions. Search/filter combinations are not exhaustively enumerated. No SQL coverage percentage has been measured.

## Published to GitHub � 11 November 2026

Initialised a Git repository and pushed 305 files to https://github.com/Girisha-coder/BingeBox. The .mp4 placeholder video files (601 MB) are excluded via .gitignore. A .env.example template is included; the real .env with secrets remains local only.
