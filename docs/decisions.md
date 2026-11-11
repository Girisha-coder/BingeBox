# Implementation decisions

The original submission is preserved unchanged in `reference/`. These decisions resolve its open choices without expanding the project into a production streaming platform.

## Workspace and architecture

- Non-Git directory; existing Conda `gpu_env` for local Python; no `.venv`.
- PostgreSQL 16, FastAPI/psycopg 3 raw parameterised SQL, React/Vite/React Router. Docker Compose serves all three tiers; nginx proxies `/api` on the website’s origin.
- Preserve all 18 tables and 99 columns. Do not add billing, heartbeat, device, provenance or media-delivery tables.
- Five seed plans retain the source limits/prices. Seed scripts insert missing plans without overwriting staff edits.
- Twelve indexes means **explicit indexes**, excluding automatic primary/unique indexes. Actual small-data query plans can prefer sequential scans.

## Transaction and integrity policies

| Topic | Implemented decision |
| --- | --- |
| Period dates | Start inclusive, end exclusive. Calendar-month increments clamp to the last valid date. Subsequent extensions start at the previous end date; no billing-anchor column exists. |
| Renewal | Catch up every missed month through the selected date, invoking the payment hook each time. Successful renewal retains streams; opted-out expiry closes them. Processing the same date again is idempotent. Suspended accounts retain their subscription/renewal preference; suspension independently blocks playback. |
| Plan change | Validate profile count first, then atomically cancel old current subscription, close streams and start the new plan. A failure rolls everything back. No proration is modelled. |
| Plan editing | Refuse profile/stream/quality reductions while current subscriptions reference the plan. Price/name changes remain permitted. Historical joins show current plan metadata because source schema has no price snapshot. |
| Profile limit | Use the latest subscription’s plan, even after expiry. Require a subscription before creating the first profile. Playback still requires an active, date-valid period. |
| Shared limits | Profile, subscription, stream, plan-change and suspension writers coordinate using ACCOUNT row locks. Independent-connection tests exercise competing requests. |
| Completion | Progress is bounded by runtime; ≥90% sets completion. Moving backward can make that attempt incomplete again. Previous completed attempts still establish review eligibility. |
| Resume/replay | Resume latest unfinished attempt for that exact profile/item; explicit Start again creates a new attempt. IDs break DATE ties. Continue watching shows the latest attempt per item. |
| Series feedback | Complete at least one episode to review its series; complete the exact episode to rate that episode. Composite primary keys enforce one feedback row per profile/item. |
| Total specialisation | Three additional deferred constraint triggers enforce exactly one matching MOVIE/SERIES subtype at commit. Composite FKs alone did not enforce total participation. |
| Total genre participation | EER Figure 1 requires every title to have a genre. Two deferred triggers validate new titles and genre-link removal/reassignment at commit, permitting atomic replacement. The helper writes the parent row without changing its values to serialize competing removals, including protection against REPEATABLE READ write skew. Existing unclassified rows make migration fail; no categories are fabricated. |
| Parent edits | Title age increases conflicting with history are rejected by an extra trigger. API rejects runtime/episode-parent changes once media/history exists, profile age reductions conflicting with history, and title/episode deletion with history. |

## Authentication and media

- Salted scrypt password hashes. Accounts and staff are distinct identities; API responses never expose hashes.
- HMAC-signed, expiring HttpOnly/SameSite=Lax cookies. Role and profile ownership checks run server-side. The selected kids identity cannot use account-management endpoints until the account password is re-entered.
- Unsafe requests reject a foreign Origin. Local HTTP uses non-Secure cookies; `COOKIE_SECURE=true` is available for a separately configured HTTPS deployment. No public deployment is included.
- Database calls switch to `bingebox_app`, a NOLOGIN role without schema creation, truncation or table ownership. The connection is initially established by the local database owner. This is a local course deployment, not an independently credentialled least-privilege production setup; API ownership/role checks remain the per-user security boundary. Raw owner SQL is administrative access.
- A browser tab’s opaque UUID is retained in session storage and recorded in `device_name`. Same household/token replaces its previous stream; independent tabs get separate tokens. Device identity is demonstrative, not tamper-proof DRM.
- There is no idle-session expiry: DATE fields cannot measure precise heartbeats. Explicit stop, best-effort page-exit cleanup, same-device replacement, account device management and staff lifecycle actions release slots.
- Media URLs are signed and bound to account, profile, session, watch target and selected asset. Each media request and progress write checks current authorisation. Revocation stops later requests/progress; already-buffered bytes cannot be recalled. API/media access logging is disabled so tokens are not written to access logs.
- Runtime-matched, original SD placeholders are generated and cached by duration, including for Kaggle metadata without MEDIA_ASSET rows. This virtual fallback preserves the accepted 840-row baseline; it is explicitly labelled. Existing seed asset paths are treated as placeholder metadata rather than claims that real films exist.
- Full-file admin entries require a path inside `media/` and ffprobe duration matching. The database also enforces runtime ±60 seconds. Placeholder entries must be SD. Trailers use validated YouTube IDs; iframe playback depends on the external video’s availability/embedding permission.
- Payments are a successful `confirm_payment()` stub, exactly as scoped. No card details are collected.

## Data and design

- The user accepted **840 initial rows**: a 200-row fictional snapshot including plans, plus 640 related rows for 150 real Kaggle movies. The loader has a 1,000-row import cap. Normal user activity is not artificially capped.
- Kaggle replaces the source’s proposed IMDb ingestion by explicit user approval. Original identifiers, ratings, votes, audio/subtitle languages and episode details are not fabricated where absent. Data source/licence/sample hash and limitations are in [data-sources.md](data-sources.md).
- Seeders construct a deterministic historical fixture in one validated transaction. They insert through tables with triggers installed; they do not pretend that backdated states arose from live API activity. Lifecycle behavior is separately tested through functions and HTTP.
- The final user decision is to retain only the Stitch interface. It uses the independently generated and approved obsidian/indigo palette, local Syne/Plus Jakarta Sans fonts, real-data discovery and accessible motion. Earlier design experiments are retired; saved URLs normalize to the main routes. [DESIGN.md](../DESIGN.md) records the current rules.
- Catalogue artwork is a local presentation asset and does not add database rows or modify the submitted schema. Official posters are matched by title/year and poster identity; distinct illustrative fallbacks cover unverified or unavailable downloads. Source attribution and matching evidence are retained.
- Executable retrieval SQL lives in API query functions/module rather than a redundant `db/queries.sql` copy.
- Up-next ordering uses last-watched DATE first and watch ID for same-day ties. Lapsing reports include started active periods ending today through seven days ahead, including due-today rows awaiting renewal processing; future-start periods are excluded. Binge reports count completed episode attempts, including replays, and use date descending as the final tie-breaker. Search treats user-entered `%`, `_` and backslashes literally in substring matching.

See [normalisation.md](normalisation.md) for fixed discriminator, nullable-key and stored-completion qualifications. See [requirements-matrix.md](requirements-matrix.md) for exact business-object coverage and extra integrity machinery.
