# Demo data and source provenance

Loaded on 20 October 2026. The database contains **840 rows across 18 tables**, below the requested 1,000-row limit.

## Fictional demo snapshot: 200 rows

The original 200-row snapshot includes five existing source plans and 195 new fictional rows. People, staff accounts, titles, activity and review text are synthetic. Email addresses use the reserved `.example` domain; phone numbers are intentionally absent. Passwords are stored as individually salted scrypt hashes of the public demo password `BingeBox-Demo-2026!`.

Account examples include `aarav.sharma@bingebox.example` (Student), `meera.iyer@bingebox.example` (Basic, auto-renew off, near expiry), `rohan.desai@bingebox.example` (Family with two kids profiles), and `vikram.rao@bingebox.example` (suspended Duo account). Account and staff login is implemented; see the [demo guide](demo-guide.md).

| Case | Example or behaviour |
| --- | --- |
| Regular values | Most fictional movies run 82–143 minutes; typical user ratings are 6–9 |
| Low runtime boundary | `A Minute of Rain`: 1 minute |
| High runtime boundary | `The Long Winter Archive`: 600-minute experimental archive |
| Episode boundaries | `Field Note: One Minute` and a 300-minute extended testimony episode |
| Low rating outlier | `Midnight Signal`: synthetic IMDb-style rating 2.3; one user review rates it 1 |
| High user rating | `Paper Lanterns`: user review rated 10 |
| Small-sample outlier | `After the Flood`: synthetic reference score 9.7 with only 18 votes |
| Completion boundary | Exactly 90%, one second below 90%, 100%, zero progress and nearly finished attempts |
| Rewatch | A completed `The Last Local` attempt followed by an unfinished replay for the same profile |
| Account lifecycle | Active, expired and cancelled subscriptions; prior plan history; one suspended account |
| Access limits | Three kids profiles; one standard profile capped at age 13; Basic, Duo, Premium and Family stream patterns |
| Missing data | Optional phone fields and IMDb IDs left null |

The 12 fictional titles have mock reference scores/vote counts to exercise the schema; those numbers are **not actual IMDb data**. The imported real titles have no fabricated IMDb values.

There are 21 full-video asset rows for the nine fictional movies and 12 episodes. They describe SD placeholders of matching duration and retain their original `mock/...mp4` metadata paths. Playback now resolves placeholder entries to generated files under `media/placeholder/{runtime_sec}.mp4`; imported titles without asset rows use the same explicitly labelled fallback. All 86 distinct movie/episode runtimes have generated, probed files. No licensed videos or trailers were downloaded; the initial 840-row dataset remains unchanged.

## Kaggle metadata: 150 real movies

Source: [Netflix Movies and TV Shows by Shivam Bansal](https://www.kaggle.com/datasets/shivamb/netflix-shows), dataset slug `shivamb/netflix-shows`. Kaggle's public dataset-list API reported **CC0: Public Domain** and a last update of **27 September 2021**. The exact retrieval time, archive hash and retained-sample hash are saved in [source.json](../data/kaggle/source.json).

The archive was fetched from Kaggle directly. Only the first 1,000 source records were considered; 150 valid movie records were retained in [netflix_movies_sample.csv](../data/kaggle/netflix_movies_sample.csv). The complete archive was not saved. Selection retains the shortest/longest runtimes, earliest/latest release years, available maturity-label diversity and a deterministic random remainder. This is a deliberately varied test sample, not a population-representative catalogue sample.

The selected real movies span **1959–2021**, with runtimes **12–273 minutes**. Ten maturity categories are represented. The source is historical metadata and does not establish current Netflix availability or rights to stream any title.

### Mapping into BingeBox

| Source field | Stored use |
| --- | --- |
| `title` | `TITLE.name`, preserved |
| `release_year` | `TITLE.release_year` |
| `description` | `TITLE.description`, preserved |
| `duration` | Minutes parsed into `MOVIE.duration_min`; invalid/missing runtimes excluded |
| `rating` | Conservative mapping to allowed `TITLE.age_rating` values |
| `listed_in` | Normalised genre labels and `TITLE_GENRE` links |
| `show_id` | Retained in CSV and the source-ID → title-ID mapping; not put in `imdb_id` |
| `director`, `cast`, `country`, `date_added` | Retained in CSV; the submission has no corresponding columns |
| Not supplied: original language | `Unknown`; no inference from country |
| Not supplied: IMDb identifier/rating/votes | NULL |
| Not supplied: audio/subtitle languages or video rights | No fabricated language rows or media assets |

Maturity mapping: G/TV-G/TV-Y → 0; PG/TV-Y7/TV-Y7-FV → 7; PG-13/TV-PG → 13; TV-14 → 16; R/TV-MA/NC-17/NR/UR or missing → 18. This is an application access policy, not an official recertification.

Genre normalisation is explicit in `scripts/import_kaggle.py`, for example Dramas → Drama, Comedies → Comedy, Documentaries → Documentary and Children & Family Movies → Family. Original values remain in the CSV. No series were imported because the dataset does not provide the episode-level information required by this project.

The import created **640 relational rows**: 150 titles, 150 movies, 15 new genres and 325 genre links. The [import report](../data/kaggle/import-report.json) records the exact source IDs and database IDs.

## Final row distribution

| Table | Demo snapshot | Kaggle additions | Final |
| --- | ---: | ---: | ---: |
| PLAN | 5 | 0 | 5 |
| ADMIN_USER | 3 | 0 | 3 |
| ACCOUNT | 12 | 0 | 12 |
| SUBSCRIPTION | 16 | 0 | 16 |
| PROFILE | 18 | 0 | 18 |
| STREAM_SESSION | 8 | 0 | 8 |
| TITLE | 12 | 150 | 162 |
| MOVIE | 9 | 150 | 159 |
| SERIES | 3 | 0 | 3 |
| EPISODE | 12 | 0 | 12 |
| GENRE | 6 | 15 | 21 |
| TITLE_GENRE | 18 | 325 | 343 |
| TITLE_AUDIO | 15 | 0 | 15 |
| TITLE_SUBTITLE | 10 | 0 | 10 |
| MEDIA_ASSET | 21 | 0 | 21 |
| WATCH_HISTORY | 23 | 0 | 23 |
| TITLE_REVIEW | 6 | 0 | 6 |
| EPISODE_RATING | 3 | 0 | 3 |
| **Total** | **200** | **640** | **840** |

## Repeatability and validation

```powershell
conda run -n gpu_env python scripts/seed_demo.py --as-of 2026-10-20
conda run -n gpu_env python scripts/import_kaggle.py
conda run -n gpu_env python scripts/seed_demo.py --check-only
conda run -n gpu_env python scripts/run_checks.py
```

Both insertion paths use transactions. Repeating the same import retains matching rows and does not duplicate data. Conflicting existing records are refused, and an import that would exceed 1,000 total rows rolls back. No force-reset/delete option is provided.

Eleven semantic checks cover profile limits, live-session eligibility/limits, progress/completion, age restrictions, subscription periods, suspension dates, asset durations, review/rating eligibility and signup dates. Integration tests also verify the source hash, row cap, retained source IDs, unknown metadata and unchanged identifiers/password hashes on rerun.

The sample is anchored to 20 October 2026. Re-running the seeder preserves that snapshot date rather than silently advancing account histories. Future lifecycle tests should use explicit dates.
