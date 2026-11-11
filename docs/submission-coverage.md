# Submission coverage audit

Audited 21 October 2026 against the complete [six-page submission](reference/BingeBox_MidSem_Submission.md), including its assumptions, role restrictions, EER diagram, relational schema and application workflows. The reference transcription is unchanged. This document distinguishes implemented requirements from source qualifications and data-loading deviations; it does not claim exhaustive SQL branch coverage.

## Assumptions A1-A8

| Source | Implementation and verification | Qualification |
| --- | --- | --- |
| A1 Household login, hashes, separate staff, unstored guests | ACCOUNT/PROFILE ownership; salted scrypt hashes; separate staff authentication. `test_assumption_a1_password_hashes_staff_namespace_and_no_guest_storage` checks hashes, salts, namespace separation, blocked staff signup and unchanged account count after guest requests. | Household membership is an account ownership model, not real-world identity verification. |
| A2 Simulated payments, one month, dated renewals and expiry | Calendar-month subscription periods; selectable renewal date; opted-out expiry stops streams. Tests cover leap/non-leap January, year rollover, missed months, repeat runs, payment-hook calls and successful renewal retaining streams. | Payments deliberately remain a successful stub. End dates are exclusive. A2/R9 govern expiry; W1's broad wording does not mean a successful renewal disconnects viewers. |
| A3 Immediate plan change | Old subscription is cancelled, new period starts on the chosen current date; history retained; streams closed atomically. Tests verify start dates, profile-cap refusal and rollback of all changes when the payment hook fails. | No proration, as documented in the project decisions. |
| A4 Progress, 90%, stream lifetime, DATE/ID ordering | Player throttles regular reports to ten seconds and also saves on pause/stop. Browser W3 checks two automatic reports 10-15 seconds apart during actual video playback. SQL tests check the 90% boundary, bounded progress, explicit stop, same-device replacement, resume and continue/up-next ordering by date then ID. | Browser event delivery can be delayed in suspended/background tabs. DATE fields cannot implement a precise idle timeout; no timeout is claimed. |
| A5 Age codes and kids limit | CHECK domains use 0/7/13/16/18; kids maximum is 7. Parameterized tests cover each boundary, equal-age acceptance and next-higher refusal; HTTP/browser tests cover direct access and kids account-page protection. | No invented granular age taxonomy. |
| A6 Free trailers, no slot/history | Guest, account without selected profile and kids identities can retrieve the trailer reference; tests assert no account, profile, watch or stream records are added. Full playback still requires a selected authorized profile. | YouTube iframe construction and ID validation are implemented. External availability/embedding permission is not guaranteed; the baseline has no fabricated trailer associations. |
| A7 Permitted full media or equal-runtime SD placeholders | Best permitted quality and SD fallback are tested for all five plans. Existing media evidence probes 86 distinct runtimes, including the 600-minute extreme. API validates local file containment and duration; SQL validates ownership and runtime tolerance. | No licensed films are bundled. Original placeholders are labelled. Rights clearance is a human prerequisite for adding a real film, not something SQL can establish. |
| A8 Ratings 1-10 and reference metadata | Viewer title/episode ratings have 1-10 constraints, watched-only eligibility and unique profile/item keys. Query tests verify rating averages, counts, rounding and NULL IMDb values. | User-approved Kaggle metadata replaces the proposed IMDb import. Missing IMDb identifiers, votes, ratings and episode data remain absent. Fictional demo data is identified separately. See [data provenance](data-sources.md). |

Detailed executable assumption cases are in [test_submission_assumptions.py](../tests/database/test_submission_assumptions.py); authentication, role restrictions and transactional HTTP tests are in [test_journeys.py](../tests/test_journeys.py).

## Roles, plans and business rules

All four user categories have implemented paths: guest previews; account subscription/profile/device management; standard/kids playback and feedback; catalogue/billing/super staff permissions. Tests reject full guest playback, watching without a profile, unauthorized account ownership, kids account access and staff role violations. Staff tests also assert that hashes are absent from responses and that history, feedback and manual subscription-extension endpoints are unavailable.

All five source plan rows are compared exactly by name, price, profile cap, stream cap and quality. Each plan is also exercised through actual subscription/playback functions, including extra-profile/extra-device refusal, same-device replacement at capacity and best-file selection.

Every business rule **R1-R13** has an implementation and executed assertion. The [requirements matrix](requirements-matrix.md) maps each rule; [workflow tests](../tests/database/test_workflows.py), [schema tests](../tests/database/test_schema.py), assumption tests and HTTP journeys cover success, refusal, rollback and competing-account-slot requests. R13 includes subscription starts, plan changes and each caught-up renewal period.

## EER, relational schema and normalization

| Submission material | Implementation and evidence |
| --- | --- |
| 13 entity types, 15 relationships, 18 mapped relations | Existing schema maps weak entities with owner/partial-key uniqueness, M:N relationships with junction keys and languages with owner/value keys. WATCH_EVENT maps to WATCH_HISTORY. Subscription periods remain separate historical rows. |
| Disjoint and total TITLE specialization | Composite foreign keys, fixed discriminators and three deferred subtype triggers. Tests cover orphan parent creation, wrong subtype, moving/removing a subtype and valid transactional creation/deletion. |
| Total TITLE participation in IN_GENRE | Added `08_genre_participation.sql`: new titles must have a genre at commit; removing or moving the last link is rejected; replacing the set and deleting the whole title remain valid. Independent-connection tests cover competing removals at READ COMMITTED and REPEATABLE READ. The API rejects an empty genre set and rolls back other edits in that request. |
| Exactly 18 relations and 99 source columns | Automated comparison parses section 5 and checks every name, order and PostgreSQL type. Additional source-driven assertions check all 99 columns' nullability, identity declarations and explicit defaults. No base columns or tables were added. |
| Keys, domains and cross-table rules | Tests exercise current-subscription uniqueness, profile/episode composite uniqueness, target exclusivity, age/kids bounds, rating bounds, dates, suspension metadata, nullable media uniqueness, duration tolerances, eligibility and cascades. Source CHECK/PK/FK structure is retained. |
| Source section 6 normalization claims | [Relation-by-relation analysis](normalisation.md) explains fixed-discriminator dependencies, nullable keys and stored derived completion. The source's blanket BCNF/no-derived-data/all-INT-identity statements are qualified, not silently repeated as proven facts. |

The migration validates existing titles before installation and refuses any unclassified rows instead of inventing genre assignments. It adds one integrity helper and two deferred triggers; the original six named business triggers and fifteen business functions remain. Total custom-object counts therefore exceed the source's shorthand inventory. The unchanged twelve explicit indexes exclude automatic PK/UQ indexes.

## Application requirements and all nine query categories

React/Vite/React Router, FastAPI/psycopg 3, PostgreSQL 16 and Docker Compose match the three-tier design. Workflow functions run inside connection transactions; SQL values are bound and dynamic resource identifiers are whitelisted. The existing deployment and isolated browser journeys exercise W1 subscription lifecycle, W2 discovery/reporting and W3 actual playback, including the three specified limit demonstrations.

| Query/category | Result-level evidence added |
| --- | --- |
| Browse/filter | Genre/audio/subtitle intersections; runtime/rating edges and missing ratings; movie/series runtime; age-filtered totals; empty/out-of-range results; invalid requests; stable 20/20/2 pagination with no duplicates or missing IDs. |
| Search | Full-text description/stemming, title substring, typo matching, case/whitespace, quotes, injection-shaped input and literal `%`, `_` and backslash handling. |
| Up next | Latest completed episode, season transitions/gaps, finished series, incomplete attempts, profile/age isolation and date-before-ID ordering. |
| Top ten per genre | Independent ten-item partitions, tied ratings, NULL ordering, age filtering before ranking and titles in multiple genres. |
| Recommendations | Shared-genre counts, deduplication across repeated watches, watched movies/series excluded, profile/age isolation, ties/NULL ratings and twelve-result limit. |
| Active subscriptions per plan | All plans including zero counts; start-inclusive/end-exclusive boundaries; future, expired, cancelled and past-due exclusion. |
| Lapsing subscriptions | Started active subscriptions ending today through day seven inclusive; later, past, future-start and inactive records excluded; both renewal choices retained; deterministic email ties. |
| Binge report | Completed episode attempts per profile/date, including replay attempts; exact 90% edge; movies/incomplete attempts excluded; deterministic date ties. This is not a count of distinct episodes. |
| Rating comparison | Exact viewer counts, averages/rounding, NULL IMDb values, exclusion of titles without reviews and deterministic ordering. |

[Query-result tests](../tests/database/test_query_results.py) also assert the four views: aggregate joins must not multiply reviews, episodes, genres or languages; guest projection must exclude protected fields; account status must choose the correct subscription and count live streams; continue watching must reflect latest attempts and replays. [Catalogue API tests](../tests/database/test_catalogue_queries.py) execute actual endpoint SQL through the application database role and assert IDs, counts and home-row payloads.

Queries defensively tested against temporary unclassified titles run inside rollback-only transactions. These intermediate fixtures cannot be committed under the new genre constraint. Committed HTTP fixtures and browser data satisfy the full constraint set.

Index tests inspect the actual PostgreSQL definitions for all twelve explicit indexes, including GIN expression/trigram operator class, column ordering and partial predicates. This is functional/schema evidence, not a performance benchmark on the small catalogue.

Supporting CRUD exists for profiles, feedback, renewal preferences, titles, episodes, genres, trailers/videos and plans, with suspension/reinstatement. Automated evidence exercises representative CRUD and the eligibility/role/parent-edit restrictions; it does not enumerate every possible API field combination.

## Explicit source differences and verification limits

1. Kaggle instead of IMDb is the user's accepted data-source change. The retained 840-row baseline includes 200 fictional rows and 640 additional catalogue/relationship rows for 150 real films.
2. The deterministic historical seeder inserts table rows with integrity triggers installed rather than constructing the entire backdated snapshot through live workflow functions. This differs from section 7's proposed loading path. Actual lifecycle behavior is independently tested through functions and HTTP; the seed is not presented as a replay of real user activity.
3. Retrieval SQL lives in `backend/app/queries.py` and endpoint functions; installation SQL is split into numbered scripts rather than the submission's single schema/query filenames.
4. Extra integrity helpers/triggers implement constraints that the source's named objects alone could not enforce. Base tables, columns, business function names and views remain as submitted.
5. Normalization claims and renewal/device ambiguities are resolved in [decisions](decisions.md) and the normalization analysis. External YouTube playback, licensed-film rights, real payments, production load capacity and exhaustive SQL branch coverage are outside the verified claim.

See [test results](test-results.md) for the final executed counts and [completed workflow](COMPLETED_WORKFLOW.md) for reproduction commands. No unresolved core database implementation gap from this audit is intentionally deferred; the differences above remain visible rather than being labelled exact source compliance.
