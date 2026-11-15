-- BingeBox demo: 5 SQL queries and 3 DBMS features, ready to run in psql.
-- Without Docker: in a terminal in the project folder, open the SQL prompt (password: postgres)
--     & "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -U postgres -d bingebox
--   then, at the bingebox=# prompt, run the whole file with   \i scripts/demo_queries.sql
--   or paste one block at a time.
-- With Docker, from the project folder:
--     Get-Content scripts\demo_queries.sql | docker compose exec -T db psql -U bingebox -d bingebox
-- Nothing here changes the demo data: every statement that would change data runs inside BEGIN ... ROLLBACK
-- or is refused by the database.
--
-- Each block says where its SQL comes from:
--   Defined in : the file and lines where the SQL text (or database object) is written
--   Run by     : the backend code that sends it to the database, and the API address
--   Shown in   : the website screen, and the frontend code that calls that API address
-- To jump to a line in VS Code: press Ctrl+P, type e.g.  backend/app/queries.py:22  and press Enter.
-- Line numbers refer to the submitted version of the repository.

\pset pager off

-- =====================================================================================
-- Q1  Active subscriptions per plan                     SQL: LEFT JOIN + GROUP BY + COUNT
--     Defined in : backend/app/queries.py line 22, REPORTS["active-subscriptions"]
--     Run by     : backend/app/main.py lines 749-755, GET /api/admin/reports/active-subscriptions
--     Shown in   : Studio -> Reports (billing/super staff); frontend/src/Admin.jsx lines 508 and 538-539
-- =====================================================================================
\echo '=== Q1  Active subscriptions per plan ==='
SELECT p.name, count(s.sub_id)::INT AS accounts
FROM plan p
LEFT JOIN subscription s
       ON s.plan_id = p.plan_id AND s.status = 'active'
      AND s.start_date <= CURRENT_DATE AND s.end_date > CURRENT_DATE
GROUP BY p.plan_id
ORDER BY p.monthly_price;

-- =====================================================================================
-- Q2  Account status: latest subscription, plan limits and current usage per account
--     SQL: JOINs + correlated subqueries (COUNT of profiles and of live streams in the SELECT list,
--          latest subscription through a LATERAL subquery) + a derived table (subquery in FROM)
--     Defined in : db/06_views.sql lines 21-26, the query of the view v_account_status
--     Run by     : backend/app/main.py line 299, GET /api/account (the signed-in account),
--                  and line 718, GET /api/admin/accounts (line 713, the staff account list)
--     Shown in   : Account page, frontend/src/main.jsx line 1143; Studio -> Accounts,
--                  frontend/src/Admin.jsx line 403
--     The inner query is the view's definition, unchanged; the outer SELECT only picks columns.
-- =====================================================================================
\echo '=== Q2  Account status ==='
SELECT email, plan_name, status, end_date, profile_count, max_profiles, live_streams, max_streams
FROM (
    SELECT a.account_id, a.email, a.suspended_at, s.sub_id, s.status, s.start_date, s.end_date, s.auto_renew,
           p.plan_id, p.name AS plan_name, p.max_profiles, p.max_streams, p.max_quality, p.monthly_price,
           (SELECT count(*)::INT FROM profile WHERE account_id = a.account_id) AS profile_count,
           (SELECT count(*)::INT FROM stream_session ss JOIN profile pr USING (profile_id)
             WHERE pr.account_id = a.account_id AND ss.ended_at IS NULL) AS live_streams
    FROM account a
    LEFT JOIN LATERAL (SELECT * FROM subscription WHERE account_id = a.account_id
                       ORDER BY start_date DESC, sub_id DESC LIMIT 1) s ON TRUE
    LEFT JOIN plan p USING (plan_id)
) AS account_status
ORDER BY account_id;

-- =====================================================================================
-- Q3  Catalogue details per title: runtime, seasons, episodes, genres, languages, ratings
--     SQL: 7 JOINs + aggregation inside correlated (LATERAL) subqueries:
--          SUM, COUNT(DISTINCT ...), COUNT, ARRAY_AGG, AVG
--     Defined in : db/06_views.sql lines 1-14, the query of the view v_title_catalog
--     Run by     : backend/app/main.py lines 401 and 405 (catalogue search, GET /api/catalog),
--                  line 445 (title page, GET /api/catalog/{title_id}); Q4 and Q5 also read this view
--     Shown in   : Browse/search page, frontend/src/main.jsx line 265; title page, main.jsx line 850
--     The inner query is the view's definition, unchanged; the outer SELECT picks columns and
--     keeps the 12 fictional titles (9 movies, 3 series) so that the output fits the screen.
-- =====================================================================================
\echo '=== Q3  Catalogue details per title ==='
SELECT title_id, name, title_type, runtime_min, season_count, episode_count,
       genres, audio_languages, user_rating, review_count
FROM (
    SELECT t.*, coalesce(m.duration_min, ep.runtime_min, 0)::INT AS runtime_min,
           coalesce(ep.season_count, 0)::INT AS season_count, coalesce(ep.episode_count, 0)::INT AS episode_count,
           coalesce(g.genres, ARRAY[]::VARCHAR[]) AS genres, coalesce(a.languages, ARRAY[]::VARCHAR[]) AS audio_languages,
           coalesce(st.languages, ARRAY[]::VARCHAR[]) AS subtitle_languages,
           r.user_rating, coalesce(r.review_count, 0)::INT AS review_count,
           tr.source_ref AS trailer_ref, tr.provider AS trailer_provider
    FROM title t LEFT JOIN movie m USING (title_id)
    LEFT JOIN LATERAL (SELECT sum(duration_min) AS runtime_min, count(DISTINCT season_no) AS season_count,
                              count(*) AS episode_count
                       FROM episode WHERE series_id = t.title_id) ep ON TRUE
    LEFT JOIN LATERAL (SELECT array_agg(name ORDER BY name) AS genres
                       FROM genre JOIN title_genre USING (genre_id) WHERE title_id = t.title_id) g ON TRUE
    LEFT JOIN LATERAL (SELECT array_agg(language ORDER BY language) AS languages
                       FROM title_audio WHERE title_id = t.title_id) a ON TRUE
    LEFT JOIN LATERAL (SELECT array_agg(language ORDER BY language) AS languages
                       FROM title_subtitle WHERE title_id = t.title_id) st ON TRUE
    LEFT JOIN LATERAL (SELECT round(avg(rating), 1) AS user_rating, count(*) AS review_count
                       FROM title_review WHERE title_id = t.title_id) r ON TRUE
    LEFT JOIN LATERAL (SELECT source_ref, provider FROM media_asset
                       WHERE title_id = t.title_id AND asset_kind = 'trailer'
                       ORDER BY asset_id LIMIT 1) tr ON TRUE
) AS catalogue
WHERE title_id <= 12
ORDER BY title_id;

-- =====================================================================================
-- Q4  Top titles in each genre
--     SQL: CTE (WITH) + window function ROW_NUMBER() OVER (PARTITION BY genre ORDER BY rating)
--          + JOINs (catalogue view, title_genre, genre)
--     Defined in : backend/app/queries.py lines 11-14, TOP_GENRE
--     Run by     : backend/app/main.py line 480, inside GET /api/home (line 467)
--     Shown in   : Home page rows "Top 10 in <genre>"; frontend/src/main.jsx lines 421 and 456
--     The backend fills %s with the profile's age limit (18 here). The app keeps the top 10 of
--     every genre; to fit the screen, the outer WHERE below keeps the top 3 of three genres.
-- =====================================================================================
\echo '=== Q4  Top titles in each genre ==='
WITH ranked AS (
    SELECT v.title_id, v.name, v.release_year, v.genres, v.imdb_rating, g.name AS genre,
           row_number() OVER (PARTITION BY g.genre_id
                              ORDER BY v.imdb_rating DESC NULLS LAST, v.title_id) AS rank
    FROM v_title_catalog v
    JOIN title_genre tg USING (title_id)
    JOIN genre g USING (genre_id)
    WHERE v.age_rating <= 18)
SELECT genre, rank, name, release_year, imdb_rating
FROM ranked
WHERE rank <= 3 AND genre IN ('Comedy', 'Drama', 'Thriller')
ORDER BY genre, rank;

-- =====================================================================================
-- Q5  "Recommended for you" for Kabir's profile
--     SQL: CTE (WITH) + nested subqueries (IN, NOT IN) + JOIN + GROUP BY + COUNT
--     Defined in : backend/app/queries.py lines 15-20, RECOMMEND
--     Run by     : backend/app/main.py line 479, inside GET /api/home (line 467)
--     Shown in   : Home page of profile "Kabir" (kabir.malhotra); frontend/src/main.jsx line 417
--     The backend fills the two %s with the profile id and its age limit; here psql does it.
-- =====================================================================================
\echo '=== Q5  Recommendations for profile Kabir ==='
SELECT p.profile_id AS pid, p.max_age_rating AS age
FROM profile p JOIN account a USING (account_id)
WHERE a.email = 'kabir.malhotra@bingebox.example' AND p.name = 'Kabir' \gset
\echo 'What Kabir has watched (the genres the recommendations are based on):'
SELECT DISTINCT t.name, g.name AS genre
FROM watch_history w
LEFT JOIN episode e USING (episode_id)
JOIN title t ON t.title_id = coalesce(w.movie_id, e.series_id)
JOIN title_genre tg ON tg.title_id = t.title_id
JOIN genre g USING (genre_id)
WHERE w.profile_id = :pid
ORDER BY 1, 2;
\echo 'Recommendations:'
WITH watched AS (
    SELECT DISTINCT coalesce(w.movie_id, e.series_id) AS title_id
    FROM watch_history w LEFT JOIN episode e USING (episode_id)
    WHERE w.profile_id = :pid)
SELECT v.title_id, v.name, v.release_year, v.genres, v.imdb_rating, count(*) AS shared_genres
FROM v_title_catalog v JOIN title_genre g USING (title_id)
WHERE v.age_rating <= :age
  AND v.title_id NOT IN (SELECT title_id FROM watched)
  AND g.genre_id IN (SELECT genre_id FROM title_genre WHERE title_id IN (SELECT title_id FROM watched))
GROUP BY v.title_id, v.name, v.release_year, v.genres, v.imdb_rating
ORDER BY shared_genres DESC, v.imdb_rating DESC NULLS LAST, v.title_id
LIMIT 12;

-- =====================================================================================
-- F1  TRIGGER profile_limit
--     Defined in : db/05_workflows.sql lines 88-97 (trigger function enforce_profile_limit)
--                  and line 132 (CREATE TRIGGER profile_limit)
--     Fired by   : backend/app/main.py line 212, the INSERT INTO profile in POST /api/profiles (line 205)
--     Shown in   : kabir.malhotra -> Profiles -> add a third profile -> refused;
--                  frontend/src/main.jsx lines 701 and 757
--     Before a profile is inserted, the trigger counts the account's profiles and
--     refuses the row if the plan's max_profiles is reached.
-- =====================================================================================
\echo '=== F1  Trigger profile_limit ==='
SELECT email, plan_name, max_profiles, profile_count
FROM v_account_status WHERE email = 'kabir.malhotra@bingebox.example';
BEGIN;
INSERT INTO profile (account_id, name)
SELECT account_id, 'Third' FROM account WHERE email = 'kabir.malhotra@bingebox.example';
ROLLBACK;

-- =====================================================================================
-- F2  STORED PROCEDURE + TRANSACTION change_plan
--     Defined in : db/05_workflows.sql lines 43-52 (it calls subscribe, lines 29-42)
--     Called by  : backend/app/main.py line 326, SELECT change_plan(...) in POST /api/account/change-plan (line 321)
--     Shown in   : kabir.malhotra -> Plans -> Basic (refused), Family (succeeds); frontend/src/main.jsx line 625
--     One call = one transaction: lock the account, check the profile count, cancel the
--     old subscription, end live streams, create the new subscription. All or nothing.
-- =====================================================================================
\echo '=== F2  Stored procedure + transaction change_plan ==='
\echo 'Kabir''s subscriptions now:'
SELECT s.sub_id, pl.name AS plan, s.status, s.start_date, s.end_date
FROM subscription s JOIN plan pl USING (plan_id) JOIN account a USING (account_id)
WHERE a.email = 'kabir.malhotra@bingebox.example' ORDER BY s.sub_id;

\echo 'Downgrade to Basic: refused, so nothing at all changes:'
SELECT change_plan(account_id, (SELECT plan_id FROM plan WHERE name = 'Basic'))
FROM account WHERE email = 'kabir.malhotra@bingebox.example';

\echo 'Upgrade to Family inside a transaction (old row cancelled + new row created together):'
BEGIN;
SELECT change_plan(account_id, (SELECT plan_id FROM plan WHERE name = 'Family')) AS new_sub_id
FROM account WHERE email = 'kabir.malhotra@bingebox.example';
SELECT s.sub_id, pl.name AS plan, s.status, s.start_date, s.end_date
FROM subscription s JOIN plan pl USING (plan_id) JOIN account a USING (account_id)
WHERE a.email = 'kabir.malhotra@bingebox.example' ORDER BY s.sub_id;
ROLLBACK;
\echo 'After ROLLBACK every change is undone together:'
SELECT s.sub_id, pl.name AS plan, s.status, s.start_date, s.end_date
FROM subscription s JOIN plan pl USING (plan_id) JOIN account a USING (account_id)
WHERE a.email = 'kabir.malhotra@bingebox.example' ORDER BY s.sub_id;

-- =====================================================================================
-- F3  VIEW v_guest_catalog
--     Defined in : db/06_views.sql lines 16-19 (built on the view v_title_catalog, lines 1-14)
--     Read by    : backend/app/main.py line 460, in GET /api/catalog/{title_id} (line 439) for guests;
--                  also joined into the catalogue search at line 401
--     Shown in   : open a title while signed out -> preview only
--     Guests are served this view, which exposes only a 90-character teaser instead of the
--     full description.
-- =====================================================================================
\echo '=== F3  View v_guest_catalog ==='
\echo 'Full row in the base table:'
SELECT title_id, name, length(description) AS description_length, description
FROM title WHERE name = 'Monsoon Letters';
\echo 'What a guest gets through the view:'
SELECT title_id, name, genres, length(teaser) AS teaser_length, teaser
FROM v_guest_catalog WHERE name = 'Monsoon Letters';

-- =====================================================================================
-- Bonus  PARTIAL UNIQUE INDEX subscription_one_current
--     Defined in : db/03_indexes.sql lines 2-3
--     Checked    : on every insert into subscription, e.g. by subscribe() in db/05_workflows.sql line 29
--     At most one current ('active' or 'past_due') subscription per account.
-- =====================================================================================
\echo '=== Bonus  Index subscription_one_current ==='
BEGIN;
INSERT INTO subscription (account_id, plan_id, start_date, end_date)
SELECT account_id, (SELECT plan_id FROM plan WHERE name = 'Basic'), CURRENT_DATE, CURRENT_DATE + 30
FROM account WHERE email = 'kabir.malhotra@bingebox.example';
ROLLBACK;
