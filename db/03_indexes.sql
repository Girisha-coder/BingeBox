-- 12 explicitly created indexes, excluding automatic PK/UQ indexes.
CREATE UNIQUE INDEX subscription_one_current ON subscription (account_id)
    WHERE status IN ('active', 'past_due');
CREATE INDEX title_search ON title USING GIN (
    to_tsvector('english', name || ' ' || coalesce(description, ''))
);
CREATE INDEX title_name_trigram ON title USING GIN (name gin_trgm_ops);
CREATE INDEX title_audio_language ON title_audio (language, title_id);
CREATE INDEX title_subtitle_language ON title_subtitle (language, title_id);
CREATE INDEX watch_history_recent ON watch_history (profile_id, last_watched_at DESC, watch_id DESC);
CREATE INDEX stream_session_live ON stream_session (profile_id, session_id) WHERE ended_at IS NULL;
CREATE INDEX subscription_due ON subscription (end_date, account_id) WHERE status = 'active';
CREATE INDEX title_review_title ON title_review (title_id);
CREATE INDEX episode_rating_episode ON episode_rating (episode_id);
CREATE INDEX title_genre_genre ON title_genre (genre_id, title_id);
CREATE INDEX subscription_account_history ON subscription (account_id, start_date DESC, sub_id DESC);
