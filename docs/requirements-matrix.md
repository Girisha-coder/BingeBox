# Requirements and implementation evidence

The implementation preserves all **18 relations and 99 source columns**. Automated schema comparison reads the verified submission and compares names, order and PostgreSQL types. The deployment retains 12 explicitly declared indexes; indexes automatically backing primary/unique constraints are additional.

The [complete submission audit](submission-coverage.md) additionally maps **A1-A8**, roles, plans, the EER diagram, all 99 columns' nullability/defaults/identities, W1-W3 and source qualifications. Exact query results and filter boundaries are asserted in `test_query_results.py` and `test_catalogue_queries.py`.

| Rule | Implemented enforcement | Evidence |
| --- | --- | --- |
| R1 One current subscription | Partial unique index; account lock in subscription functions | Schema uniqueness test; concurrent subscription test |
| R2 Profile cap and unique names | `profile_limit` trigger locks account and counts profiles; unique key | Boundary tests; independent-connection last-slot race; browser third-profile refusal |
| R3 Stream cap, active period, unsuspended | `start_session` locks account, replaces same-device session, checks current plan and live count | Concurrent last-stream race; API second-device rejection; suspension revocation |
| R4 Age limit, kids ≤7 | Profile CHECK; `watch_age_check`; catalogue and media age gates | SQL age test; API direct URL rejection; kids browser journey |
| R5 One target and bounded progress | CHECK plus `watch_progress`; completion recomputed at ≥90% | Invalid-target tests; 5399/5400 boundary for 6000 seconds; seek/resume browser test |
| R6 Watched-only, unique feedback | Two eligibility triggers; composite primary keys | SQL movie/series/episode tests; API review upsert/delete; browser completed review |
| R7 Exactly one subtype; unique episode | Composite FKs, fixed discriminators, three deferred integrity triggers; episode unique constraint | Commit-time orphan, wrong subtype, subtype move/delete and season tests |
| R8 Asset ownership and duration | Target CHECKs, null-aware uniqueness and `asset_duration`; local file probing in API | SQL exact targets, 60/61-second tolerance; media manifest; HTTP range test |
| R9 Renewal/expiry closes expired streams | `process_renewals`, ordered account locks, calendar-month catch-up | Month-end and repeat-run tests; browser expiry of opted-out account |
| R10 Refused unsafe downgrade | Count validation before cancelling subscription; one transaction | SQL rollback assertion; browser refusal, successful upgrade |
| R11 Billing/super suspension | API identity/role gate plus `require_admin_role`; recorded admin and stream closure | SQL catalogue-role rejection; HTTP role tests; staff browser journey |
| R12 Preview-only guests | `v_guest_catalog` projection for listing and details | HTTP forbidden-field assertions and guest browser preview |
| R13 Payment hook | Starts and each renewal period invoke `confirm_payment` | Instrumented hook asserts two missed-period calls; subscription tests |

## Object inventory

- **15 business functions**, with the exact names in the source: `subscribe`, `change_plan`, `process_renewals`, `confirm_payment`, `start_session`, `start_playback`, `record_progress`, `end_playback`, `suspend_account`, `reinstate_account`, `current_plan`, `item_age_rating`, `item_runtime_sec`, `quality_rank`, `require_admin_role`.
- **Six named business triggers**: `profile_limit`, `watch_age_check`, `watch_progress`, `asset_duration`, `review_requires_watch`, `eprating_requires_watch`.
- **Four views**: `v_title_catalog`, `v_guest_catalog`, `v_account_status`, `v_continue_watching`.
- **12 explicit indexes**, including the current-subscription partial unique index, expression full-text GIN and name trigram GIN.
- Additional implementation machinery: six business-trigger helper functions; one title-age guard function/trigger; one subtype-integrity helper with three deferred triggers; one genre-participation helper with two deferred triggers. Therefore total custom functions/triggers exceed the source’s shorthand counts. Extension-owned `pg_trgm` functions are separate again.

## Nine query categories

| Category | Location / interface |
| --- | --- |
| Browse/filter | `catalog()` in `backend/app/main.py`; Discover filters |
| Search | Same endpoint: full-text expression, `ILIKE` substring and trigram similarity |
| Up next | `UP_NEXT` in `backend/app/queries.py`; next season/episode via LATERAL |
| Top ten per genre | `TOP_GENRE`; `row_number` partitioned by genre |
| Recommendations | `RECOMMEND`; watched-title CTE and shared genres, excludes watched titles |
| Active subscriptions per plan | `REPORTS['active-subscriptions']`; staff reports |
| Lapsing subscriptions | `REPORTS['lapsing']`; next seven days |
| Binge report | `REPORTS['binge']`; completed episode attempts per profile/date |
| Rating comparison | `REPORTS['rating-comparison']`; IMDb beside viewer aggregates |

The executable queries live beside their API callers instead of a separate `db/queries.sql`. Parameters are bound; the small set of dynamic table/column identifiers is explicitly whitelisted. On this small dataset PostgreSQL may reasonably choose sequential scans; merely creating a GIN index is not a benchmark claim.
