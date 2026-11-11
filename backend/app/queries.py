"""Named, parameterised SQL behind the nine required query categories."""

UP_NEXT = """WITH latest AS (
 SELECT DISTINCT ON(e.series_id) e.series_id,e.season_no,e.episode_no,w.watch_id,w.last_watched_at
 FROM watch_history w JOIN episode e USING(episode_id)
 WHERE w.profile_id=%s AND w.completed ORDER BY e.series_id,w.last_watched_at DESC,w.watch_id DESC)
 SELECT t.title_id,t.name,n.episode_id,n.name AS episode_name,n.season_no,n.episode_no
 FROM latest l JOIN title t ON t.title_id=l.series_id
 JOIN LATERAL(SELECT * FROM episode WHERE series_id=l.series_id AND (season_no,episode_no)>(l.season_no,l.episode_no) ORDER BY season_no,episode_no LIMIT 1)n ON TRUE
 WHERE t.age_rating<=%s ORDER BY l.last_watched_at DESC,l.watch_id DESC"""
TOP_GENRE = """WITH ranked AS(SELECT v.title_id,v.name,v.release_year,v.genres,v.imdb_rating,g.name AS genre,
 row_number() OVER(PARTITION BY g.genre_id ORDER BY v.imdb_rating DESC NULLS LAST,v.title_id) AS rank
 FROM v_title_catalog v JOIN title_genre tg USING(title_id) JOIN genre g USING(genre_id) WHERE v.age_rating<=%s)
 SELECT * FROM ranked WHERE rank<=10 ORDER BY genre,rank"""
RECOMMEND = """WITH watched AS(SELECT DISTINCT coalesce(w.movie_id,e.series_id) AS title_id FROM watch_history w LEFT JOIN episode e USING(episode_id) WHERE w.profile_id=%s)
 SELECT v.title_id,v.name,v.release_year,v.genres,v.imdb_rating,count(*) AS shared_genres
 FROM v_title_catalog v JOIN title_genre g USING(title_id)
 WHERE v.age_rating<=%s AND v.title_id NOT IN(SELECT title_id FROM watched)
 AND g.genre_id IN(SELECT genre_id FROM title_genre WHERE title_id IN(SELECT title_id FROM watched))
 GROUP BY v.title_id,v.name,v.release_year,v.genres,v.imdb_rating ORDER BY shared_genres DESC,v.imdb_rating DESC NULLS LAST,v.title_id LIMIT 12"""
REPORTS = {
    "active-subscriptions": """SELECT p.name,count(s.sub_id)::INT AS accounts FROM plan p LEFT JOIN subscription s ON s.plan_id=p.plan_id AND s.status='active' AND s.start_date<=CURRENT_DATE AND s.end_date>CURRENT_DATE GROUP BY p.plan_id ORDER BY p.monthly_price""",
    "lapsing": """SELECT a.email,p.name AS plan,s.end_date,s.auto_renew FROM subscription s JOIN account a USING(account_id) JOIN plan p USING(plan_id) WHERE s.status='active' AND s.start_date<=CURRENT_DATE AND s.end_date BETWEEN CURRENT_DATE AND CURRENT_DATE+7 ORDER BY s.end_date,a.email""",
    "binge": """SELECT p.profile_id,p.name,w.last_watched_at,count(*)::INT AS completed_episodes FROM watch_history w JOIN profile p USING(profile_id) WHERE w.episode_id IS NOT NULL AND w.completed GROUP BY p.profile_id,w.last_watched_at ORDER BY completed_episodes DESC,p.profile_id,w.last_watched_at DESC""",
    "rating-comparison": """SELECT name,imdb_rating,imdb_votes,user_rating,review_count FROM v_title_catalog WHERE review_count>0 ORDER BY review_count DESC,title_id""",
}
