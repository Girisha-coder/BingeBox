CREATE OR REPLACE VIEW v_title_catalog AS
SELECT t.*, coalesce(m.duration_min,ep.runtime_min,0)::INT AS runtime_min,
 coalesce(ep.season_count,0)::INT AS season_count,coalesce(ep.episode_count,0)::INT AS episode_count,
 coalesce(g.genres,ARRAY[]::VARCHAR[]) AS genres,coalesce(a.languages,ARRAY[]::VARCHAR[]) AS audio_languages,
 coalesce(st.languages,ARRAY[]::VARCHAR[]) AS subtitle_languages,
 r.user_rating,coalesce(r.review_count,0)::INT AS review_count,
 tr.source_ref AS trailer_ref,tr.provider AS trailer_provider
FROM title t LEFT JOIN movie m USING(title_id)
LEFT JOIN LATERAL(SELECT sum(duration_min) AS runtime_min,count(DISTINCT season_no) AS season_count,count(*) AS episode_count FROM episode WHERE series_id=t.title_id) ep ON TRUE
LEFT JOIN LATERAL(SELECT array_agg(name ORDER BY name) AS genres FROM genre JOIN title_genre USING(genre_id) WHERE title_id=t.title_id) g ON TRUE
LEFT JOIN LATERAL(SELECT array_agg(language ORDER BY language) AS languages FROM title_audio WHERE title_id=t.title_id) a ON TRUE
LEFT JOIN LATERAL(SELECT array_agg(language ORDER BY language) AS languages FROM title_subtitle WHERE title_id=t.title_id) st ON TRUE
LEFT JOIN LATERAL(SELECT round(avg(rating),1) AS user_rating,count(*) AS review_count FROM title_review WHERE title_id=t.title_id) r ON TRUE
LEFT JOIN LATERAL(SELECT source_ref,provider FROM media_asset WHERE title_id=t.title_id AND asset_kind='trailer' ORDER BY asset_id LIMIT 1) tr ON TRUE;

CREATE OR REPLACE VIEW v_guest_catalog AS
SELECT title_id,name,release_year,title_type,genres,audio_languages,imdb_rating,season_count,
 left(coalesce(description,''),90) AS teaser,trailer_ref,trailer_provider
FROM v_title_catalog;

CREATE OR REPLACE VIEW v_account_status AS
SELECT a.account_id,a.email,a.suspended_at,s.sub_id,s.status,s.start_date,s.end_date,s.auto_renew,
 p.plan_id,p.name AS plan_name,p.max_profiles,p.max_streams,p.max_quality,p.monthly_price,
 (SELECT count(*)::INT FROM profile WHERE account_id=a.account_id) AS profile_count,
 (SELECT count(*)::INT FROM stream_session ss JOIN profile pr USING(profile_id) WHERE pr.account_id=a.account_id AND ss.ended_at IS NULL) AS live_streams
FROM account a LEFT JOIN LATERAL(SELECT * FROM subscription WHERE account_id=a.account_id ORDER BY start_date DESC,sub_id DESC LIMIT 1) s ON TRUE LEFT JOIN plan p USING(plan_id);

CREATE OR REPLACE VIEW v_continue_watching AS
WITH ranked AS(SELECT w.*,row_number() OVER(PARTITION BY profile_id,movie_id,episode_id ORDER BY last_watched_at DESC,watch_id DESC) AS ordinal FROM watch_history w)
SELECT w.watch_id,w.profile_id,w.movie_id,w.episode_id,w.progress_sec,w.last_watched_at,
 coalesce(w.movie_id,e.series_id) AS title_id,t.name,t.age_rating,e.name AS episode_name,
 item_runtime_sec(w.movie_id,w.episode_id) AS runtime_sec
FROM ranked w LEFT JOIN episode e USING(episode_id) JOIN title t ON t.title_id=coalesce(w.movie_id,e.series_id)
JOIN profile p USING(profile_id) WHERE ordinal=1 AND NOT completed AND progress_sec>0 AND t.age_rating<=p.max_age_rating;
