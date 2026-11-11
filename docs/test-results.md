# Final verification results

## Latest database and submission audit - 21 October 2026

**136 PostgreSQL/API tests passed in 70.08s; all 11 browser journeys passed in 52.0s.** Both suites used temporary databases, which were removed. After tightening the test cookie to include the actual kids flag and adding explicit missing-genre HTTP assertions, the affected **51 tests passed again in 5.16s**. Local Python used the existing Conda `gpu_env`.

The earlier SQL coverage gaps below are now resolved with expected-row, ordering, aggregate and boundary assertions for all nine query categories and four views. The expanded cases include 20-item pagination, intersecting filters, null ratings, literal wildcard search, all five plan limits/quality choices, all age boundaries, calendar-month edges, payment-hook rollback, trailer non-mutation, authentication namespaces and staff restrictions.

Found and fixed: up-next sorting by ID before date; lapsing reports including not-yet-started subscriptions; substring search interpreting `%`, `_` and backslash as patterns; and non-deterministic binge-report date ties. The submission EER's total genre participation is now enforced at commit by an additive migration, with rollback and independent-connection race tests at READ COMMITTED and REPEATABLE READ. Browser W3 now verifies two automatic progress requests 10-15 seconds apart during actual playback.

Source-driven schema checks cover all 18 tables/99 columns, including nullability, identities and explicit defaults; index checks inspect all twelve explicit definitions. [The complete submission audit](submission-coverage.md) maps A1-A8, roles/plans, R1-R13, EER/schema, W1-W3 and explicit source differences. These assertions are not a measured SQL branch-coverage percentage or a production performance claim.

Applied migrations and rebuilt the API container; live website, proxied readiness, direct API readiness and catalogue all returned HTTP 200. [Delivery evidence](evidence/delivery-check.json) confirms the unchanged 840-row/162-title baseline, zero unclassified titles, both deferred genre guards, no remaining temporary databases, 86 retained media files, unchanged source Markdown hash, valid local document links, no Git and no `.venv`.

## Initial delivery evidence - 20 October 2026

Executed locally on **20 October 2026**, using Conda `gpu_env`, PostgreSQL 16.15 in Docker, and Chromium through Playwright. The final source was rebuilt into the running Docker application.

| Check | Result |
| --- | --- |
| PostgreSQL + HTTP integration suite | **64 passed**, 34.93 seconds |
| Browser end-to-end suite | **7 passed**, 19.1 seconds |
| Vite production build | Passed; staff console emitted as a separate lazy-loaded chunk |
| Container builds/startup | PostgreSQL, API and nginx frontend running; database/API health checks passed |
| Initial application dataset | **840 rows**, **162 titles**; 11 semantic consistency checks passed |
| Source-schema correspondence | All **18 tables / 99 columns** match the verified submission |
| Business inventory | 15 named functions, six business triggers, four views and 12 explicit indexes verified; extra integrity machinery documented |
| Generated media | **86 files**, H.264 SD 640×360; every distinct runtime probed; declared/actual duration difference <0.01 second |
| Media size | 630,500,970 bytes total; files shared by matching runtimes |
| Desktop/mobile visual review | Warm minimal desktop and 390-pixel mobile layouts inspected; no horizontal overflow in tested discovery/plans screens |

## Database and HTTP evidence

Tests install all numbered SQL into a new uniquely named test database. Ordinary database tests roll back; committed concurrency/API fixture records are explicitly cleaned within the test database. The runner drops only the database it created.

Coverage includes:

- Exact schema/plan/index correspondence, FK/unique/check constraints, subtype commit-time integrity, cascade behavior and invalid target combinations.
- Deterministic mock/Kaggle loading, repeatability, conflicting-data refusal, row cap and semantic validation.
- Independent-connection races for the final profile slot, final stream slot and first current subscription: exactly one request succeeds.
- Atomic downgrade refusal and successful change, same-device session replacement, calendar-month boundaries, catch-up and idempotent expiry.
- Instrumented payment hook: two missed renewal periods invoke it twice.
- Runtime tolerance, quality selection, age restrictions, progress limits, 90% threshold, replay/resume and movie/series/episode feedback eligibility.
- Password login, signed-cookie tampering, ownership, kids unlock, origin rejection, staff role gates, catalogue CRUD and report queries.
- Real generated video byte ranges: HTTP 206 and requested byte count; revocation rejects later media/progress.
- Stopping an expired but not yet processed stream still releases its slot without accepting unauthorised progress.
- Runtime database role cannot truncate domain tables or create tables. Initial connection ownership and per-user API boundary are documented in [decisions.md](decisions.md).

## Seven browser journeys

The runner creates a separate **840-row** fixture, starts temporary API/web servers on 18001/18081, uses Chromium, saves evidence, then stops the servers and drops the test database.

1. Invalid/expired session cookie still allows account sign-in.
2. Guest search/preview; responsive discovery and plans at 390 pixels; no uncaught JavaScript error in that journey.
3. Play an actual 60-second video, seek to 24 seconds, save, resume, reach ≥90%, and post a visible review.
4. Refuse a third Duo profile and unsafe Basic downgrade, upgrade to Family, add a profile and turn auto-renew off.
5. Hide adult content from kids, refuse incorrect unlock password and accept the correct password.
6. Catalogue staff create/update/delete a genre; billing staff suspend/reinstate an account and switch report types; role-inappropriate tabs are absent.
7. Billing staff process renewals, expire an opted-out account and see its changed state.

Screenshots are in [evidence/](evidence/): [desktop](evidence/desktop-home.png), [mobile](evidence/mobile-home.png), [player](evidence/player.png), [review](evidence/title-review.png), [account](evidence/account.png), and [staff report](evidence/studio-report.png). They show disposable test data, so subscription counts can differ from the unchanged application baseline.

## Reproduction and limits

Use the commands in [README.md](../README.md). [delivery-check.json](evidence/delivery-check.json) records read-only final health, dataset, media, document-link and workspace checks. [media/manifest.json](../media/manifest.json) lists every probed runtime/file size.

These tests establish the scoped local course workflows, not production load capacity, DRM, payment processing, independent security certification or every browser/assistive technology. There is no licensed-film playback claim. YouTube iframe construction/asset validation is implemented, but playback of arbitrary external videos depends on their availability, permissions and network access. No external trailer is invented for the baseline titles.

Full-text/trigram indexes exist and the search paths run; no unsupported claim is made that this small 162-title dataset demonstrates a speed advantage. Source Markdown fidelity was verified separately against all six PDF pages; implementation testing does not replace that transcription audit.


## Stitch-only frontend verification - 21 October 2026

**11 browser journeys passed in 30.7s**, using `gpu_env` and the isolated 840-row database. The test database and temporary servers were removed afterward. The seven original business journeys now run through Stitch; four additional journeys verify cover coverage/uniqueness/loading, featured discovery and keyboard quick look, mobile/reduced-motion/legacy routes, and account/profile/video integration.

All 162 catalogue files match the recorded SHA-256 hashes and have distinct image hashes. Fourteen promotional posters were matched by title/year and poster identity; the remaining 148 covers are illustrative. Metadata matching reached 78 poster candidates, but image-service HTTP 429 responses limited downloads. See [artwork provenance](catalogue-artwork.md).

Production Docker/Vite build passed with 204 modules. Only the web container was rebuilt; the API/database stayed healthy. Live root and catalogue pages were checked in Chrome. The earlier 64 passing backend integration tests remain the backend baseline; this change did not alter backend code or the schema.

Evidence: [Stitch desktop](evidence/stitch-desktop.png), [mobile](evidence/stitch-mobile.png), [full mobile](evidence/stitch-mobile-full.png), [quick look](evidence/stitch-quick-look.png), [verified posters](evidence/verified-posters.png), and the original business-flow screenshots refreshed under [stitch-regression](evidence/stitch-regression/).


## Catalogue page size - 21 October 2026

Changed the catalogue from 18 to 20 titles per page using a single page-size constant for the API limit, page count and Next-button boundary. The 162-title collection has nine pages, with two titles on the final page. Rebuilt the web container and verified the live first page contains titles 1-20 and the next page contains titles 21-40. Both focused guest-discovery/responsive and artwork-loading browser checks passed in 8.8s against a temporary database; it was removed afterward. The preceding complete Stitch suite passed all 11 journeys in 30.7s.


## SQL coverage recheck - 21 October 2026

Reran `scripts/run_checks.py` in the existing `gpu_env`: **64 passed in 39.51s** against a newly created PostgreSQL test database. All numbered SQL installation scripts execute in that database; the fixture drops it afterward. The application database is not used for test mutations.

Coverage includes schema/constraints, data loading, business functions/triggers, transaction rollback, date/progress/runtime boundaries, concurrency and SQL-backed API workflows. This is not proof of exhaustive SQL statement or branch coverage. In particular, `/home` executes up-next, recommendations and top-per-genre queries but currently asserts HTTP success rather than exact expected rows/rankings for each query. The four staff report endpoints likewise have execution checks without full expected-result/boundary assertions. Search/filter combinations are not exhaustively enumerated. No SQL coverage percentage has been measured.
