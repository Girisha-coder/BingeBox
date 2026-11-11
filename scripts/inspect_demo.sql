-- Read-only examples for the loaded fictional + Kaggle dataset.
-- Password hashes and connection credentials are intentionally not selected.

SELECT 'accounts' AS entity, count(*) AS rows FROM account
UNION ALL SELECT 'profiles', count(*) FROM profile
UNION ALL SELECT 'titles', count(*) FROM title
UNION ALL SELECT 'movies', count(*) FROM movie
UNION ALL SELECT 'series', count(*) FROM series
UNION ALL SELECT 'episodes', count(*) FROM episode
UNION ALL SELECT 'watch attempts', count(*) FROM watch_history;

SELECT status, auto_renew, count(*) AS subscriptions
FROM subscription GROUP BY status, auto_renew ORDER BY status, auto_renew;

SELECT t.name, t.release_year, m.duration_min, t.age_rating, t.imdb_rating
FROM title t JOIN movie m USING (title_id)
ORDER BY m.duration_min, t.name LIMIT 8;

SELECT t.name, t.release_year, m.duration_min, t.age_rating, t.imdb_rating
FROM title t JOIN movie m USING (title_id)
ORDER BY m.duration_min DESC, t.name LIMIT 8;

SELECT a.email, p.name AS profile, p.is_kids, t.name AS title,
       w.progress_sec, coalesce(m.duration_min, e.duration_min) * 60 AS runtime_sec,
       w.completed, w.last_watched_at
FROM watch_history w JOIN profile p USING (profile_id)
JOIN account a USING (account_id)
LEFT JOIN movie m ON m.title_id = w.movie_id
LEFT JOIN episode e USING (episode_id)
JOIN title t ON t.title_id = coalesce(w.movie_id, e.series_id)
ORDER BY w.last_watched_at DESC, w.watch_id DESC;

SELECT t.name, r.rating, r.review_text
FROM title_review r JOIN title t USING (title_id)
ORDER BY r.rating, t.name;
