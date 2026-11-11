# BingeBox: complete project workflow

This is a start-to-finish implementation and submission plan derived from [BingeBox_MidSem_Submission.pdf](BingeBox_MidSem_Submission.pdf), dated 11 October 2026. Use the [verified Markdown transcription](BingeBox_MidSem_Submission.md) for the full schema and original requirements.

**Status:** This document describes work to perform and evidence to collect. It is not a claim that the application has been implemented or tested. The linked GitHub repository was not inspected for this document. Proposed paths, endpoints, policies and acceptance tests below are implementation recommendations; the PDF does not specify all of them. No deadline, team allocation or fixed development duration is assumed.

## 1. Define the finish line

Deliver a working three-tier application: React (Vite) and React Router → FastAPI with psycopg 3 and parameterised SQL → PostgreSQL 16. Package the services with Docker Compose. Demonstrate actual browser playback, database-enforced business rules, useful retrieval queries and reproducible setup.

The original scope includes:

- Guest catalogue previews, filtering, typo-tolerant search, trailers, plans and sign-up.
- Household accounts, separate staff logins, viewer profiles and kids restrictions.
- Five plans, subscriptions, immediate plan changes, auto-renew, date-driven renewal runs, suspension and reinstatement.
- Profile-based full playback, device limits, quality selection, saved progress, resume, continue watching and up next.
- Catalogue management, IMDb reference data, user title reviews and episode ratings.
- Database evidence: 18 relations, six named triggers, 15 named functions, four views and the stated 12-index target.
- Nine query categories: browse/filter, up next, top 10 per genre, recommendations, search, active subscriptions per plan, lapsing subscriptions, binge report and rating comparison.

Payments are a successful stub behind `confirm_payment()`. Student eligibility checks are outside the original scope. Use only suitably licensed full video assets; use same-length SD placeholders for other titles. Do not make an external payment integration a prerequisite for finishing this project.

**Done when:** a fresh checkout can start the system, load reproducible demo data, pass the rule tests, run W1–W3 through the UI, and provide matching SQL, documentation and demonstration evidence.

## 2. Resolve the design gaps before implementation

Record decisions in a short `docs/decisions.md`. These suggested defaults complete underspecified parts of the PDF; adopt or replace them deliberately.

| Question | Recommended decision | Why it must be explicit |
| --- | --- | --- |
| TITLE total specialisation | Create TITLE and exactly one subtype in one transaction. If the requirement must hold for all permitted SQL writers, add deferred constraint enforcement or an equivalent restricted write design. | The displayed subtype foreign keys enforce valid references; they do not force every parent TITLE to acquire a subtype. |
| Successful renewal and streams | Preserve streams after a successful renewal; close streams on expiry or suspension. | A2/R9 and the wording of W1 differ in clarity. |
| What counts as watching a series? | For this course implementation, allow a series review after completing at least one of its episodes; state this in the UI and report. | R6 does not define series-review eligibility. |
| Resume versus replay | Resume the latest unfinished attempt; create a new WATCH_HISTORY record for an explicit replay after completion. | WATCH_EVENT allows repeated attempts, and eligibility must survive later replays. |
| Completion | Use `progress_sec >= 0.9 * item_runtime_sec(...)` for the current attempt; any completed attempt can establish review eligibility. | A4 specifies a 90% threshold. Seeking back and replaying must have predictable effects. |
| Subscription dates | Use a documented half-open interval, start date inclusive and end date exclusive; add one calendar month with a documented month-end rule. | DATE has no time-of-day precision; “one month” is not always 30 days. |
| Missed renewals | Bring each due auto-renew subscription forward until its end date is after the requested processing date, calling the payment hook for each period. | A late run and a repeated run must not produce inconsistent periods. |
| Lower stream/quality limits on plan change | Refuse changes with too many profiles as R10 requires. For an accepted change, close existing sessions and require playback to restart under the new limits. | The source specifies profile-limit rejection but not handling of existing streams. |
| Device identity | Specify a stable browser/device token and its mapping. If keeping the exact 18-table schema, document how the token is encoded within the available session fields and its limitations; otherwise record a schema revision. | Display labels alone can collide and do not establish device identity. |
| Abrupt browser exit | Support explicit stop and replacement by the same device. Document that reliable idle expiry requires a design extension beyond the DATE-only model. | The PDF does not provide timestamp/heartbeat fields. |
| Editing an in-use plan | For the initial project, reject reductions that invalidate existing profiles or sessions, or handle all affected accounts transactionally under a documented policy. | Limits are read from PLAN; editing a plan can invalidate accounts without a `change_plan()` call. |
| Past-due status | Retain it in the schema, but do not invent payment-failure behaviour while the payment hook always succeeds. Treat only active subscriptions as playback-eligible. | The schema allows `past_due`; payment failure is outside the described demo. |
| Privileged account pages | Require account-holder authentication for billing, profile-limit changes and exiting kids restrictions. | A profile selector alone should not grant account-management privileges. |

Keep the conceptual-to-relational mapping `WATCH_EVENT → WATCH_HISTORY` explicit. Qualify the original blanket BCNF, “all keys are INT” and “no stored derived data” statements as described in the transcription's verification appendix.

**Exit check:** every open decision has an agreed policy and a corresponding acceptance test. If implementation changes the original schema/object counts, update the final report rather than retaining stale counts.

## 3. Establish the repository and reproducible environment

Start by inspecting the existing repository before creating files. Preserve working code and adapt this proposed layout to it:

```text
BingeBox/
  README.md
  .env.example
  compose.yaml
  db/
    schema.sql
    functions.sql
    triggers.sql
    views.sql
    indexes.sql
    queries.sql
    seed.sql
  backend/
    app/
    tests/
  frontend/
    src/
  scripts/
    import_imdb.py
    seed_demo.py
    prepare_media.py
  tests/
    database/
    concurrency/
    e2e/
  media/
  docs/
    decisions.md
    eer-diagram.*
    test-results.md
    demo-script.md
    data-sources.md
```

1. Inspect repository instructions and existing setup; record the implementation baseline.
2. Pin compatible dependencies and lockfiles around the source's PostgreSQL 16, FastAPI/psycopg 3, React/Vite stack. Do not change the architecture merely to adopt newer tools.
3. Define database, API and frontend services, a persistent database volume, media location, service configuration and health checks.
4. Put example configuration in `.env.example`; keep actual credentials out of tracked files.
5. Define a deterministic schema installation order: extension/schema, tables, functions, triggers, views, indexes and seed data, adjusting for actual dependencies.
6. Make database initialization safe to rerun or document migrations separately. Do not depend on an initialization script silently rerunning against an existing volume.
7. Document one startup command, such as `docker compose up --build`, after the Compose file actually supports it. Add exact import, test and seed commands to the README once those entry points exist.
8. Assign an owner and reviewer for database, API, frontend, data/media and integration work. Coordinate around agreed contracts before splitting implementation.

**Exit check:** the services start from a clean development environment, the API can reach the database, the frontend can reach the API, and a persistent volume survives a normal restart.

## 4. Implement and verify the relational model

Use section 5 of the transcription as the column-level specification. Build in dependency order:

| Batch | Relations | Main checks |
| --- | --- | --- |
| Independent entities | PLAN, ADMIN_USER, GENRE, TITLE | Identity/primary keys, unique identifiers, domains and defaults |
| Account and catalogue subtypes | ACCOUNT, MOVIE, SERIES | Suspension metadata pair; composite subtype foreign keys and discriminators |
| Dependent entities | SUBSCRIPTION, PROFILE, EPISODE | Current subscription uniqueness, profile names, episode numbering, DATE and rating limits |
| Language and genre mappings | TITLE_GENRE, TITLE_AUDIO, TITLE_SUBTITLE | Composite keys, nonblank languages, intended delete actions |
| Assets and playback | MEDIA_ASSET, STREAM_SESSION, WATCH_HISTORY | Exact-one-target checks, asset uniqueness, session dates, progress defaults |
| Reviews and ratings | TITLE_REVIEW, EPISODE_RATING | One row per profile/item; user ratings 1–10 |

For every relation, verify column names, types, nullability, defaults, keys, CHECKs, references and ON DELETE actions against the submission. Do not add CASCADE to foreign keys where the source does not specify it without recording that decision.

Use a partial unique index for current subscriptions (`active` or `past_due`). Preserve the media uniqueness rule across `(asset_kind, title_id, movie_id, episode_id, quality)` with the specified null handling. PostgreSQL 16 supports `UNIQUE NULLS NOT DISTINCT`; ordinary UNIQUE treats null values differently. CHECK conditions also need explicit null handling where a null result would otherwise pass. See [PostgreSQL 16 constraints](https://www.postgresql.org/docs/16/ddl-constraints.html).

Treat “exactly one target” as an explicit rule for WATCH_HISTORY and full MEDIA_ASSET rows. A trailer must have only its title target; a full asset must not retain a title target as well as its movie/episode target.

Test total specialisation separately from disjointness. A successful MOVIE insert with a matching TITLE does not prove that orphan TITLE rows are impossible.

**Exit check:** all 18 relations exist; valid examples insert successfully; invalid domains, duplicate keys, conflicting targets and missing references are rejected. Export the actual catalogue as evidence and compare it to the documentation.

## 5. Implement the six named triggers

| Trigger | Required responsibility | Important negative/boundary tests |
| --- | --- | --- |
| `profile_limit` | Prevent profiles exceeding the account plan limit | Third Duo profile; concurrent final-slot inserts; account transfer on update |
| `watch_age_check` | Reject watch targets above the profile's age limit | Kids profile at rating 7 succeeds; rating 13 fails; movie and episode paths |
| `watch_progress` | Keep progress within runtime and apply the completion policy | Negative progress, runtime + 1, just below 90%, at 90%, backward seeking |
| `asset_duration` | Validate full-file length against item runtime within ±60 seconds | Difference of 60 versus 61 seconds; minute-to-second conversion; trailer path |
| `review_requires_watch` | Require qualifying watch history before a title review | Unwatched movie, incomplete attempt, completed movie, agreed series policy |
| `eprating_requires_watch` | Require a completed watch of the exact episode | Different episode, different profile, incomplete watch, completed watch |

Specify INSERT and UPDATE coverage as appropriate. Check changes to parent data too: changing a runtime or age rating can invalidate existing dependent rows even if no child trigger fires. Define a rejection or coordinated-update policy for those admin operations.

For profile limits, use the same account-level coordination protocol as subscription changes. A trigger that only counts current rows can let two concurrent requests each see one free slot.

**Exit check:** direct SQL tests demonstrate rule enforcement, including updates and concurrent writes. Any additional trigger needed to close a design gap is documented and included in the revised count.

## 6. Implement the 15 database functions

Build helpers first, lifecycle/admin functions second, playback last. Choose and document actual signatures; the PDF supplies function names, not full parameter or return contracts.

| Function | Behaviour and result to define |
| --- | --- |
| `current_plan` | Resolve an account's playback-eligible current plan, limits and quality; specify no-plan behaviour |
| `item_age_rating` | Resolve movie age rating or an episode's parent-title age rating |
| `item_runtime_sec` | Resolve duration and convert stored minutes to seconds |
| `quality_rank` | Order SD < HD < 4K consistently |
| `require_admin_role` | Check the authenticated staff identity against allowed roles |
| `confirm_payment` | Successful stub called once per subscription start or renewal period |
| `subscribe` | Validate plan/account, coordinate writes, call payment hook, create the one-month subscription |
| `change_plan` | Validate profile count; cancel the old subscription and start the new one atomically; apply session policy |
| `process_renewals` | Process due subscriptions for a supplied date, renew or expire and close expired accounts' sessions |
| `suspend_account` | Require billing/super role; record admin and date; end live sessions atomically |
| `reinstate_account` | Require authorised staff; clear suspension metadata without manufacturing a valid subscription |
| `start_session` | Check subscription/suspension/device identity and available stream slots; create or replace the device session |
| `start_playback` | Check account/profile/item, select permitted media, coordinate session start and resume/new watch attempt |
| `record_progress` | Verify ownership and live session; persist bounded progress and completion; reject revoked playback |
| `end_playback` | Save final valid progress if supplied and mark the session ended; define repeated-stop behaviour |

Each mutating workflow must commit or roll back as a unit. Lock the relevant ACCOUNT row before checking shared limits and keep the lock until the write completes. All paths that can alter those limits or eligibility must follow the same protocol. This applies to profile creation, subscription changes, starts, suspension and renewal, not only the happy-path player request. PostgreSQL row locks last until transaction end, and consistent lock ordering helps avoid deadlocks; see [PostgreSQL 16 explicit locking](https://www.postgresql.org/docs/16/explicit-locking.html).

Avoid holding locks while doing network or video-file work. The current payment hook is local; a future external payment integration will need its own failure and retry design.

For repeated requests, define safe outcomes: retries must not create a second active subscription, duplicate a renewal period or consume an extra device slot. Test transaction rollback after an intermediate failure, not just successful results.

**Exit check:** every named function has success, rejection and relevant retry tests. Two independent database connections cannot exceed one Basic stream or the final available profile slot.

## 7. Build views, retrieval queries and indexes

| View | Output contract |
| --- | --- |
| `v_title_catalog` | Title metadata plus computed runtime, genres, rating aggregates and trailer availability |
| `v_guest_catalog` | Only the preview fields allowed by section 1: name, year, genres, audio languages, IMDb rating, short teaser and season count; retain identifiers needed for navigation |
| `v_account_status` | Account/subscription status, plan and limits needed by account workflows |
| `v_continue_watching` | Latest eligible unfinished attempt per profile/item, with deterministic DATE/id ordering |

Implement the nine planned query categories in `db/queries.sql`. For each query, document inputs, access scope, returned columns and ordering:

1. **Browse/filter:** genre, audio/subtitle language, runtime and rating, with pagination.
2. **Up next:** next episode by season number then episode number, including season transitions.
3. **Top 10 per genre:** rank within each genre using a window function and an explicit tie-breaker.
4. **Recommendations:** a transparent because-you-watched rule, such as shared genres; document exclusions.
5. **Search:** full-text title/description matching plus a `pg_trgm` typo-tolerant path and stable ordering.
6. **Active subscriptions per plan:** grouped counts with a defined date/status interpretation.
7. **Lapsing subscriptions:** subscriptions due within a chosen date window, including auto-renew state.
8. **Binge report:** define the metric, such as completed episodes per profile/day; DATE-only data cannot prove uninterrupted viewing sessions.
9. **Rating comparison:** keep IMDb reference ratings distinct from BingeBox user averages and vote counts.

Use CTEs, window functions and LATERAL joins where they make the requested query clearer. Avoid duplicate title rows when joining genres, languages, episodes and reviews; aggregate or isolate each multivalued source appropriately.

Create an index inventory recording name, table, expression/columns, predicate, purpose and supporting query. Cover the source's full-text GIN, title-name trigram, language, watch-history recency, live-session, due-subscription, review/rating and genre lookup categories. Clarify whether the stated 12 excludes indexes automatically created for primary/unique constraints; the PDF does not enumerate all 12 definitions.

Collect query plans on representative data and record observed results. Do not invent a latency target or add redundant indexes solely to reach a count.

**Exit check:** all four views and nine query categories return correct results for empty data, multiple genres/languages, ties, null ratings and repeat watches; guest results contain no full descriptions, episode lists or reviews.

## 8. Prepare catalogue data, media and deterministic fixtures

1. Load the five source plans exactly: Student (1 profile/1 stream/HD/₹99), Basic (1/1/HD/₹199), Duo (2/2/HD/₹349), Premium (1/3/4K/₹499) and Family (4/4/4K/₹649).
2. Select a manageable IMDb subset with both movies and multi-season series. Record input files, acquisition date, provenance and applicable terms in `docs/data-sources.md`.
3. Parse source identifiers, missing values, title types, episode parent links and ratings. Report rejected/skipped records rather than silently inventing data.
4. Import parent titles before subtypes and episodes. Use deterministic upserts or an explicitly isolated rebuild process so reruns do not duplicate catalogue entries.
5. Handle missing runtime, language, description and age-classification data deliberately. IMDb data is not guaranteed to supply every application field; mark curated/synthetic additions and their source.
6. Add genres, audio languages and subtitle languages as separate rows. Metadata should describe the actual playable sample; do not imply that subtitle metadata alone provides subtitle tracks.
7. Add valid YouTube trailer references; trailers must not create sessions or watch history.
8. Prepare permitted full videos and SD placeholders. Verify actual duration against metadata, browser playback and the ±60-second constraint; placeholder generation should target the full specified runtime.
9. If claiming HD/4K selection, supply distinct valid quality assets for representative demo items. A quality label alone does not establish actual resolution.
10. Seed accounts, kids/standard profiles, subscriptions, reviews and watch activity through the intended functions/validated write paths. Store only password hashes and clearly label demo credentials.

Include fixtures for every plan, each staff role, an expired account, an auto-renew account, a suspended account, partial and completed watches, one title without real video, and titles on either side of the kids age boundary.

**Exit check:** loading twice has the documented outcome; imported counts and rejects are reported; all demo media play and their metadata match the files.

## 9. Implement the FastAPI layer

Define request/response contracts and consistent error codes before frontend integration. The following routes are proposed examples, not routes quoted from the PDF:

| API area | Example routes / operations | Enforcement |
| --- | --- | --- |
| Authentication | `POST /auth/signup`, `/auth/login`, `/auth/logout`; separate staff login | Password hashing, account/staff separation, safe credential handling |
| Guest discovery | `GET /catalog`, `/catalog/{id}/preview`, `/plans` | Preview projection only; validated filters and pagination |
| Account/profile | `GET/POST /profiles`, `PATCH/DELETE /profiles/{id}`, account status, live devices | Authenticated account ownership and privileged-account checks |
| Subscription | Subscribe, change plan, toggle auto-renew | One transactional lifecycle operation; no client-supplied authority |
| Profile discovery | Title detail, episodes, home rows, recommendations | Profile ownership and age policy |
| Playback | `POST /playback/start`, `/playback/{session_id}/progress`, `/playback/{session_id}/stop` | Account/profile/session ownership, live eligibility and database constraints |
| Feedback | Create/update/delete title reviews and episode ratings | Viewer ownership, watch eligibility, composite-key uniqueness |
| Staff catalogue | Manage titles, episodes, genres, languages and media | Catalogue/super authorisation |
| Staff billing | Renewals, suspend/reinstate, billing reports | Billing/super authorisation |
| Staff plans | Plan management | Super authorisation and policy for affected subscribers |

Use parameterised SQL through psycopg 3. Bind identity from authenticated server context rather than trusting request-supplied account/profile/admin identifiers. Every referenced profile, watch row and session must be checked against that context.

Return user-facing messages for expected database rejections, such as device limit, kids restriction or invalid downgrade. Roll back failed transactions before reusing a connection. Do not expose SQL statements, hashes or database internals in responses.

Full media delivery must honour playback authorisation. Protect file access as well as the start endpoint; a publicly reusable file URL would bypass subscription and age checks. Browser seeking and resumed playback must work with the chosen delivery path. On suspension/expiry, revoke further media access and stop the player when the server reports revocation; already buffered bytes cannot be retroactively withdrawn.

Staff actions must use the authenticated staff identity. A database function taking an arbitrary `admin_id` is insufficient if an untrusted client can choose it.

**Exit check:** API tests cover every role, ownership across two households, input validation, error rollback and media access before the UI is treated as complete.

## 10. Implement the React application

Build in this order so each stage has usable backend contracts:

1. **Guest flow:** catalogue, filters, typo search, title preview, trailer, plans and sign-up/login.
2. **Account setup:** subscription, profile creation/rename/delete, Who's watching, kids profile configuration and protected account pages.
3. **Profile home:** continue watching, up next, top 10 per genre and because-you-watched rows.
4. **Title detail:** complete description, trailer, episode list, IMDb and user ratings, review controls.
5. **Player:** start authorisation, selected media quality, resume position, progress reporting every 10–15 seconds, stop/final progress and error recovery.
6. **Account management:** plan change, auto-renew, subscription status and live devices.
7. **Staff console:** role-appropriate catalogue, billing, suspension/reinstatement and plan tools.

Show loading, empty and rejected states. Preserve active profile context across navigation, clear it appropriately at logout, and avoid letting a kids viewer reach privileged account actions through a direct route.

For the player, restore the saved position after media metadata is available, prevent duplicate progress timers, stop timers on navigation, and handle rejected progress after revocation. Explicit stop should release the slot; same-device replacement must use the agreed identity rule. Do not promise reliable close-tab cleanup without a server-side timeout mechanism.

Provide separate trailer and full-play actions. Clearly label placeholder videos. If a plan permits 4K but only SD exists, report the actual chosen quality.

**Exit check:** each role can complete its permitted journey through the UI; direct API attempts still enforce the same restrictions.

## 11. Integrate the three assessed workflows

### W1: subscription lifecycle

1. Sign up an account and choose a plan.
2. Call `subscribe()` through the API; verify exactly one current subscription and payment-hook use.
3. Create profiles within its limit.
4. Change plan; verify atomic cancellation/new subscription and the selected active-session policy.
5. Attempt a downgrade with too many profiles; verify rejection leaves the original subscription intact.
6. Toggle auto-renew and run renewals for a controlled date as authorised staff.
7. Show one successful renewal and one expiry; verify expired streams end and repeated processing does not double-renew.
8. Suspend an account; verify recorded admin/date, ended sessions and rejected future playback. Reinstate without bypassing subscription validity.

### W2: discover and search

1. Browse as a guest and inspect the actual API response for preview-only fields.
2. Search an exact term, a description term and a typo.
3. Combine genre, language, runtime and rating filters; check pagination and empty results.
4. Enter a profile and display full title information, episode order and user ratings.
5. Watch part of an item; show continue watching and accurate resume.
6. Complete an episode; show up next, including a season boundary.
7. Demonstrate top 10 per genre, because-you-watched and the three administrative report categories.
8. Explain a representative query and its plan using actual seeded data.

### W3: playback under plan limits

1. Play a trailer as a guest; verify no session or history row is created.
2. Start full playback as a valid profile; verify age, subscription, suspension, device slot and media quality checks.
3. Report progress at the specified interval; verify history, 90% completion and saved resume position.
4. Stop and confirm the slot is released.
5. Attempt a second distinct device on Basic; show the clear limit error.
6. Attempt an 18+ title from a kids profile; show rejection before media delivery.
7. Attempt a third profile on Duo; show the profile-limit error.
8. Start two distinct devices concurrently on an empty Basic account; demonstrate that only one succeeds.

**Exit check:** capture UI results and relevant before/after database rows for each workflow. A screenshot alone is not proof of transaction or concurrency correctness.

## 12. Run the acceptance and regression checks

The following matrix connects every original business rule to observable evidence:

| Rule | Test | Expected result |
| --- | --- | --- |
| R1 | Two current subscriptions, including concurrent attempts | At most one active/past_due row per account |
| R2 | Duplicate name; profile limit; simultaneous final-slot inserts | Duplicates/overflow rejected without losing valid rows |
| R3 | No subscription, expired, suspended, or excess device | Full playback rejected; concurrent starts respect the limit |
| R4 | Kids rating 7 and 13; standard profile with lower custom limit | Boundary obeyed for movies and episodes |
| R5 | Both/neither target; negative or over-runtime progress | Invalid rows rejected; valid runtime boundary accepted |
| R6 | Unwatched review/rating; completed watch; duplicate pair | Eligibility enforced; updates change one existing record |
| R7 | Wrong subtype; missing subtype; duplicate episode number | Disjointness, totality and numbering enforced by the final design |
| R8 | Wrong asset target; duplicate quality; duration tolerance | Invalid ownership/duplicates rejected; ±60 accepted, ±61 rejected |
| R9 | Due auto-renew on/off; missed run; repeated same-date run | Correct renewal/expiry, expired streams closed, no double processing |
| R10 | Downgrade below profile count | Entire operation rejected; existing subscription retained |
| R11 | Catalogue admin versus billing/super suspension | Unauthorised request rejected; authorised admin recorded and streams ended |
| R12 | Guest response and direct detail/media requests | Only allowed preview/trailer access |
| R13 | Subscribe, change-plan start and renewal periods | Every new subscription period uses the payment hook exactly as specified |

Also verify:

- Cross-household access attempts for profile, session, progress, reviews and account data.
- All five plan combinations, especially Premium's one profile but three simultaneous devices.
- Exact 90% completion, 1–10 user-rating boundaries, 0–10 imported-rating schema range and absent IMDb ratings.
- Replays, repeated progress/stop requests, missing assets, fallback quality and trailer exclusion from history.
- Month ends, leap-year dates, same-day ordering by record id and renewal rollback.
- Parent runtime/age edits, plan edits, referenced-row deletion and documented cascade behaviour.
- Fresh-database install, seed rerun, normal restart, persistence and backup/restore in an isolated test environment.

Use real PostgreSQL for SQL/trigger/concurrency tests, API integration tests for access control and transaction errors, and browser end-to-end tests or recorded manual checks for the player/UI. Run concurrent cases with independent connections and coordinated starts, not two sequential calls.

Record command, environment, fixture version, expected outcome, observed result and evidence in `docs/test-results.md`. Fix failures, rerun affected checks and relevant regression cases, then update the evidence. Do not record unexecuted cases as passed.

## 13. Prepare the final submission and demonstration

1. Compare the actual database catalogue to the schema document. Update column definitions, constraints, trigger/function/view/index inventories and object counts.
2. Reconcile the EER figure with the relational model, including weak-entity mappings, specialisation, languages and WATCH_EVENT/WATCH_HISTORY naming.
3. Provide a relation-by-relation normalisation argument with candidate keys and dependencies; disclose deliberate physical redundancy rather than asserting BCNF without analysis.
4. Finish the README with prerequisites, configuration, exact startup/import/test commands, demo credentials, data provenance and known limitations.
5. Include the SQL files, import/seed scripts, permitted media or reproducible preparation instructions, tests and test evidence.
6. Prepare a concise demonstration script following W1 → W2 → W3, with deterministic fixtures and dates. Rehearse resetting only the disposable demo environment.
7. Explain the payment stub, placeholder videos, DATE-only recency and the chosen stale-session limitation. Ensure UI labels and report claims agree.
8. Start from a fresh checkout and isolated empty database; execute the documented setup without undocumented manual edits.
9. Freeze a tested revision or release tag and record it in the report. Verify repository links and required course upload formats before submission.
10. Keep a recoverable copy of the final artefacts and demo data; perform one last playback and concurrency smoke check on the submission environment.

**Final deliverables checklist:**

- [ ] Source repository at a reproducible tested revision.
- [ ] One-command Compose startup plus exact documented data-loading steps.
- [ ] Schema, functions, triggers, views, indexes and nine query categories.
- [ ] Deterministic sample data, provenance and playable permitted media/placeholders.
- [ ] Working guest, account, profile, kids and staff flows.
- [ ] W1, W2 and W3 demonstrated with database evidence.
- [ ] R1–R13 checked; concurrency, access control and rollback verified.
- [ ] Updated EER/schema/normalisation documentation and accurate object counts.
- [ ] README, decision log, test results, demo script and explicit limitations.
- [ ] Final report and any course-required presentation/video/upload completed.

## 14. Suggested milestone order

| Milestone | Work | Completion evidence |
| --- | --- | --- |
| M1: agreed design | Sections 1–2 | Scope and decision log |
| M2: reproducible foundation | Sections 3–4 | Fresh setup and schema checks |
| M3: database workflows | Sections 5–7 | Trigger/function/concurrency tests and query outputs |
| M4: usable data and API | Sections 8–9 | Repeatable fixtures, playable samples, API tests |
| M5: complete application | Sections 10–11 | Working UI journeys W1–W3 |
| M6: verified submission | Sections 12–13 | Passing evidence, fresh-checkout rehearsal and final artefacts |

Data preparation can start once the schema contract is agreed, and frontend work can start against agreed API contracts. Complete integration at each milestone so database, backend, UI and documentation do not diverge.
