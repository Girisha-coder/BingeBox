# Keys, dependencies and normalisation

This analysis qualifies the blanket BCNF statement in the original submission. It distinguishes relational dependencies from cross-table validation and stored computed state.

| Relation | Candidate key / main dependency | Assessment under declared business dependencies |
| --- | --- | --- |
| PLAN | `plan_id`; unique `name` → price and limits | BCNF |
| ADMIN_USER | `admin_id`; unique `email` → other attributes | BCNF |
| ACCOUNT | `account_id`; unique `email`; non-null unique phone values identify an account | BCNF for key-based dependencies; nullable phone is not a universal classical candidate key |
| SUBSCRIPTION | `sub_id` → account, plan, period, status and renewal choice | BCNF; a conditional current-account uniqueness rule is not a key for the whole history |
| PROFILE | `profile_id`; `(account_id,name)` → remaining attributes | BCNF |
| STREAM_SESSION | `session_id` → profile, device and dates | BCNF; account ID is obtained through PROFILE, not repeated |
| TITLE | `title_id` → remaining attributes; non-null IMDb ID identifies a title | BCNF for the stated entity dependencies; nullable IDs require the same qualification as phone |
| MOVIE | `title_id` → runtime; `title_type` is always M | Remove the fixed discriminator and the relation is BCNF. Literally, the non-key dependency ∅ → fixed `title_type` prevents an unqualified BCNF claim. The constant supports the composite FK. |
| SERIES | `title_id` → status; `title_type` is always S | Same fixed-discriminator qualification as MOVIE |
| EPISODE | `episode_id`; `(series_id,season_no,episode_no)` → remaining attributes | BCNF |
| GENRE | `genre_id`; unique `name` | BCNF; its key is SMALLINT, not INT |
| TITLE_GENRE | `(title_id,genre_id)` | All-key relation, BCNF |
| TITLE_AUDIO | `(title_id,language)` | All-key relation, BCNF |
| TITLE_SUBTITLE | `(title_id,language)` | All-key relation, BCNF |
| MEDIA_ASSET | `asset_id`; null-aware unique tuple `(asset_kind,title_id,movie_id,episode_id,quality)` | Key-based dependencies are normalised. Exact-one-target and conditional null patterns are integrity rules; classical BCNF reasoning alone does not describe SQL null semantics. Duration is separately checked against a parent runtime. |
| WATCH_HISTORY | `watch_id` → profile, target, dates, progress and completion | Completion is deliberately stored derived state: for a fixed item runtime, target plus progress determines completion. Do not claim strict BCNF/no derived data without this exception. The trigger maintains the stored value. |
| TITLE_REVIEW | `(profile_id,title_id)` → rating, review text and dates | BCNF |
| EPISODE_RATING | `(profile_id,episode_id)` → rating and date | BCNF |

All domain columns are scalar. Multi-valued genres and languages are represented by rows in separate relations; arrays appearing in catalogue views are presentation aggregates, not denormalised base columns. Average ratings, series runtime and live-session counts are computed in views/queries.

Foreign keys alone enforce references, not total subtype participation. The deferred subtype checks test final transaction state. Runtime/age guards prevent ordinary catalogue edits from invalidating histories; additional runtime/profile edit restrictions are enforced by the API. Owner-level SQL access remains an administrative trust boundary.

No schema columns were added to conceal these qualifications. `WATCH_EVENT` in the conceptual diagram maps to relational `WATCH_HISTORY`. Historical subscription prices are not snapshotted because the submitted schema stores only a plan reference; changing a plan price changes its displayed price in historical joins.
