# BingeBox

**A subscription video-streaming platform**, built as the full-stack database project for the DBMS course at BITS Pilani, Hyderabad Campus (Group 7).

BingeBox works like a small Netflix:
- **Accounts and profiles:** a household account holds several viewer profiles, including kids profiles.
- **Plans:** the subscription plan decides how many profiles the account may create, how many devices can stream at the same time, and the best video quality.
- **Playback:** trailers play from YouTube, and full movies and episodes play in the browser.
- **Progress:** the player saves your position, which powers watch history, resume and "continue watching".
- **Catalogue:** it can be searched (typo-tolerant) and filtered by genre, audio or subtitle language, runtime and rating.

The main goal of the project is the **relational database design**. Most of the business rules are enforced by PostgreSQL itself, through keys, CHECK constraints, triggers and stored functions, not just by the application.

---

## Team (Group 7)

| Name | ID number |
|---|---|
| Sai Poojit Baratam | 2024A8PS0494H |
| Girisha | 2024A8PS0497H |
| Puneet Singh | 2024A8PS0507H |
| Vedaang Kharya | 2024A8PS0511H |
| Sanjay Rajkumar | 2024A8PS2044H |

---

## Users

| User | What they can do |
|---|---|
| **Guest** (not logged in) | Browse and search the catalogue, see a short preview card for each title, watch trailers, view the plans |
| **Account holder** | Subscribe and change plan, turn auto-renew on or off, create and delete profiles, see which devices are streaming |
| **Profile** (standard or kids) | Watch full movies and episodes, resume, continue watching, review movies and series, rate individual episodes. Kids profiles only see content rated 7+ or below. |
| **Admin** (catalogue, billing, super) | Manage titles, episodes, genres, trailers and videos; run subscription renewals for a chosen date; suspend accounts; manage plans |

## Plans

| Plan | Profiles | Devices at once | Best quality | Price / month |
|---|---|---|---|---|
| Student | 1 | 1 | HD | ₹99 |
| Basic | 1 | 1 | HD | ₹199 |
| Duo | 2 | 2 | HD | ₹349 |
| Premium | 1 | 3 | 4K | ₹499 |
| Family | 4 | 4 | 4K | ₹649 |

Plans are rows in the database, so prices and limits can be changed without touching the schema. Payments are **out of scope for now**: subscribing activates a plan straight away. Every subscription start and renewal goes through a single payment hook, `confirm_payment()`, so real payments can be added later without changing any existing table.

---

## Database design

18 relations in PostgreSQL 16:

| Area | Relations |
|---|---|
| Accounts and subscriptions | `plan`, `admin_user`, `account`, `subscription`, `profile`, `stream_session` |
| Catalogue | `title`, `movie`, `series`, `episode`, `genre`, `title_genre`, `title_audio`, `title_subtitle`, `media_asset` |
| Viewer activity | `watch_history`, `title_review`, `episode_rating` |

Main design features:
- **EER modelling:**
  - **specialisation:** TITLE → MOVIE | SERIES, disjoint and total
  - **weak entities:** PROFILE, EPISODE
  - **multivalued attributes:** audio and subtitle languages
  - **M:N relationships with attributes:** reviews, episode ratings
- **Normalised to BCNF,** with the important design decisions justified in the report.
- **Data types:** limited to `INT`, `SMALLINT`, `DECIMAL`, `VARCHAR`, `BOOLEAN` and `DATE`.
- **Integrity enforced in the database:**
  - primary keys, foreign keys, UNIQUE, NOT NULL and CHECK constraints
  - partial unique indexes, e.g. one current subscription per account
  - **triggers** for the profile limit, age limits, progress ≤ runtime, "review only after watching", and video length matching runtime
- **Stored functions** for every multi-table workflow, each running in a single transaction with row locking: subscribe, change plan, renewals, start/record/end playback, suspend and reinstate an account.
- **Views:** catalogue, guest preview, account status, continue watching.
- **Indexes:** a GIN full-text index and a trigram (`pg_trgm`) index for search.

The full design (EER diagram, relational schema, constraints, normalisation and workflows) is in the mid-semester report.

---

## Main workflows

1. **Subscription lifecycle:** subscribe, change plan (a downgrade is refused if the account has too many profiles), and run renewals for a date. Auto-renew extends a subscription; otherwise it expires and its streams stop.
2. **Discover and search:** full-text, typo-tolerant search; browse filters; home rows (continue watching, up next, top 10 per genre, "because you watched"); title pages with trailer and ratings.
3. **Playback under plan limits:** pressing play checks the age limit, the subscription, account suspension and free device slots, then picks the best video the plan allows and resumes from the saved position. It is refused, for example, for a third device on a Duo plan, an 18+ title on a kids profile, or a third profile on a Duo plan.

---

## Technology stack

| Tier | Choice |
|---|---|
| Database | PostgreSQL 16 (PL/pgSQL, `pg_trgm`) |
| Back end | Python, FastAPI, psycopg 3, using hand-written SQL (no ORM) |
| Front end | React (Vite), React Router |
| Video | YouTube IFrame API for trailers; HTML5 video for full content and placeholders |
| Data | IMDb non-commercial datasets for titles, episodes and ratings; synthetic users and activity |
| Packaging | Docker Compose |

Full-length videos are used only where they are legally free (Creative Commons or public domain). Every other title plays a generated placeholder video of the same length.

---

## Repository structure (planned)

```
BingeBox/
├── db/
│   ├── schema.sql        # tables, constraints, triggers, functions, views, indexes
│   ├── seed_plans.sql    # the five subscription plans
│   └── queries.sql       # browse, search, recommendations and report queries
├── backend/              # FastAPI application
├── frontend/             # React application
├── data/                 # data loader scripts
├── docs/                 # mid-semester report and EER diagram
└── docker-compose.yml
```

## Getting started (database)

Requires PostgreSQL 16.

```bash
createdb bingebox
psql -d bingebox -f db/schema.sql
psql -d bingebox -f db/seed_plans.sql
```

Setup steps for the back end and front end will be added as they are built.

---

## Progress

- [x] Requirements, users, plans and business rules
- [x] EER model, relational schema, normalisation (mid-semester report)
- [x] Database schema with constraints, triggers, functions and views
- [ ] Data loader (IMDb import, synthetic users and activity)
- [ ] REST API
- [ ] React front end
- [ ] Final report and demo
