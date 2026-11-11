-- Additive/repeatable migration. All shared-limit writers lock ACCOUNT first.
CREATE OR REPLACE FUNCTION current_plan(a INT, on_date DATE DEFAULT CURRENT_DATE) RETURNS plan
LANGUAGE sql STABLE AS $$
 SELECT p.* FROM subscription s JOIN plan p USING(plan_id)
 WHERE s.account_id=a AND s.status='active' AND s.start_date<=on_date AND s.end_date>on_date
 ORDER BY s.sub_id DESC LIMIT 1
$$;
CREATE OR REPLACE FUNCTION quality_rank(q VARCHAR) RETURNS INT LANGUAGE sql IMMUTABLE AS $$
 SELECT CASE q WHEN 'SD' THEN 1 WHEN 'HD' THEN 2 WHEN '4K' THEN 3 ELSE 0 END
$$;
CREATE OR REPLACE FUNCTION item_runtime_sec(m INT, e INT) RETURNS INT LANGUAGE sql STABLE AS $$
 SELECT CASE WHEN m IS NOT NULL AND e IS NULL THEN (SELECT duration_min*60 FROM movie WHERE title_id=m)
 WHEN e IS NOT NULL AND m IS NULL THEN (SELECT duration_min*60 FROM episode WHERE episode_id=e) END
$$;
CREATE OR REPLACE FUNCTION item_age_rating(m INT,e INT) RETURNS INT LANGUAGE sql STABLE AS $$
 SELECT age_rating::INT FROM title WHERE title_id=coalesce(m,(SELECT series_id FROM episode WHERE episode_id=e))
$$;
CREATE OR REPLACE FUNCTION require_admin_role(admin INT, roles VARCHAR[]) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM admin_user WHERE admin_id=admin AND (role='super' OR role=ANY(roles))) THEN
 RAISE EXCEPTION 'This action requires an authorised staff role.' USING ERRCODE='42501'; END IF;
END $$;
CREATE OR REPLACE FUNCTION confirm_payment(a INT,p INT) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM account WHERE account_id=a) OR NOT EXISTS(SELECT 1 FROM plan WHERE plan_id=p) THEN
 RAISE EXCEPTION 'Account or plan does not exist.' USING ERRCODE='23514'; END IF;
 RETURN TRUE; -- Course scope: payments always succeed. All period starts call this hook.
END $$;
CREATE OR REPLACE FUNCTION subscribe(a INT,p INT,on_date DATE DEFAULT CURRENT_DATE) RETURNS INT LANGUAGE plpgsql AS $$
DECLARE result INT;
BEGIN
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 IF NOT FOUND OR EXISTS(SELECT 1 FROM account WHERE account_id=a AND suspended_at IS NOT NULL) THEN
 RAISE EXCEPTION 'Account is unavailable or suspended.' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM subscription WHERE account_id=a AND status IN('active','past_due')) THEN
 RAISE EXCEPTION 'A current subscription already exists. Change plan instead.' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM profile WHERE account_id=a)>(SELECT max_profiles FROM plan WHERE plan_id=p) THEN
 RAISE EXCEPTION 'Remove extra profiles before selecting this plan.' USING ERRCODE='23514'; END IF;
 PERFORM confirm_payment(a,p);
 INSERT INTO subscription(account_id,plan_id,start_date,end_date) VALUES(a,p,on_date,(on_date+INTERVAL '1 month')::DATE) RETURNING sub_id INTO result;
 RETURN result;
END $$;
CREATE OR REPLACE FUNCTION change_plan(a INT,p INT,on_date DATE DEFAULT CURRENT_DATE) RETURNS INT LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM plan WHERE plan_id=p) THEN RAISE EXCEPTION 'Plan not found.' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM profile WHERE account_id=a)>(SELECT max_profiles FROM plan WHERE plan_id=p) THEN
 RAISE EXCEPTION 'Remove extra profiles before downgrading.' USING ERRCODE='23514'; END IF;
 UPDATE subscription SET status='cancelled' WHERE account_id=a AND status IN('active','past_due');
 UPDATE stream_session SET ended_at=greatest(on_date,started_at) WHERE ended_at IS NULL AND profile_id IN(SELECT profile_id FROM profile WHERE account_id=a);
 RETURN subscribe(a,p,on_date);
END $$;
CREATE OR REPLACE FUNCTION process_renewals(admin INT,on_date DATE) RETURNS JSONB LANGUAGE plpgsql AS $$
DECLARE a INT; s subscription; renews INT:=0; expires INT:=0;
BEGIN
 PERFORM require_admin_role(admin,ARRAY['billing']::VARCHAR[]);
 FOR a IN SELECT account_id FROM account ORDER BY account_id LOOP
  PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
  FOR s IN SELECT * FROM subscription WHERE account_id=a AND status='active' AND end_date<=on_date ORDER BY sub_id LOOP
   IF s.auto_renew THEN
    WHILE s.end_date<=on_date LOOP
     PERFORM confirm_payment(a,s.plan_id);
     s.end_date:=(s.end_date+INTERVAL '1 month')::DATE; renews:=renews+1;
    END LOOP;
    UPDATE subscription SET end_date=s.end_date WHERE sub_id=s.sub_id;
   ELSE
    UPDATE subscription SET status='expired' WHERE sub_id=s.sub_id; expires:=expires+1;
    UPDATE stream_session SET ended_at=greatest(on_date,started_at) WHERE ended_at IS NULL AND profile_id IN(SELECT profile_id FROM profile WHERE account_id=a);
   END IF;
  END LOOP;
 END LOOP;
 RETURN jsonb_build_object('renewed_periods',renews,'expired',expires);
END $$;
CREATE OR REPLACE FUNCTION suspend_account(admin INT,a INT,on_date DATE DEFAULT CURRENT_DATE) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
 PERFORM require_admin_role(admin,ARRAY['billing']::VARCHAR[]);
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 UPDATE account SET suspended_at=on_date,suspended_by_admin=admin WHERE account_id=a;
 UPDATE stream_session SET ended_at=greatest(on_date,started_at) WHERE ended_at IS NULL AND profile_id IN(SELECT profile_id FROM profile WHERE account_id=a);
END $$;
CREATE OR REPLACE FUNCTION reinstate_account(admin INT,a INT) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
 PERFORM require_admin_role(admin,ARRAY['billing']::VARCHAR[]);
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 UPDATE account SET suspended_at=NULL,suspended_by_admin=NULL WHERE account_id=a;
END $$;

CREATE OR REPLACE FUNCTION enforce_profile_limit() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE lim INT;
BEGIN
 PERFORM 1 FROM account WHERE account_id IN(NEW.account_id,CASE WHEN TG_OP='UPDATE' THEN OLD.account_id END) ORDER BY account_id FOR UPDATE;
 SELECT p.max_profiles INTO lim FROM subscription s JOIN plan p USING(plan_id) WHERE s.account_id=NEW.account_id ORDER BY s.start_date DESC,s.sub_id DESC LIMIT 1;
 IF lim IS NULL THEN RAISE EXCEPTION 'Subscribe before creating profiles.' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM profile WHERE account_id=NEW.account_id AND profile_id<>NEW.profile_id)>=lim THEN
 RAISE EXCEPTION 'Your plan has no free profile slots.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION enforce_watch_age() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF item_age_rating(NEW.movie_id,NEW.episode_id)>(SELECT max_age_rating FROM profile WHERE profile_id=NEW.profile_id) THEN
 RAISE EXCEPTION 'This title is above the profile age limit.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION enforce_watch_progress() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE runtime INT;
BEGIN
 runtime:=item_runtime_sec(NEW.movie_id,NEW.episode_id);
 IF runtime IS NULL THEN RAISE EXCEPTION 'Choose exactly one valid movie or episode.' USING ERRCODE='23514'; END IF;
 IF NEW.progress_sec<0 OR NEW.progress_sec>runtime THEN RAISE EXCEPTION 'Progress must be within the video runtime.' USING ERRCODE='23514'; END IF;
 NEW.completed:=NEW.progress_sec::BIGINT*10>=runtime::BIGINT*9;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION enforce_asset_duration() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.asset_kind='full' AND abs(NEW.duration_sec-item_runtime_sec(NEW.movie_id,NEW.episode_id))>60 THEN
 RAISE EXCEPTION 'Full video duration must match its runtime within 60 seconds.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION enforce_review_watch() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM watch_history w LEFT JOIN episode e USING(episode_id) WHERE w.profile_id=NEW.profile_id AND w.completed AND coalesce(w.movie_id,e.series_id)=NEW.title_id) THEN
 RAISE EXCEPTION 'Complete this movie or an episode of this series before reviewing.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION enforce_episode_watch() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM watch_history WHERE profile_id=NEW.profile_id AND episode_id=NEW.episode_id AND completed) THEN
 RAISE EXCEPTION 'Complete this episode before rating it.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS profile_limit ON profile;
CREATE TRIGGER profile_limit BEFORE INSERT OR UPDATE ON profile FOR EACH ROW EXECUTE FUNCTION enforce_profile_limit();
DROP TRIGGER IF EXISTS watch_age_check ON watch_history;
CREATE TRIGGER watch_age_check BEFORE INSERT OR UPDATE ON watch_history FOR EACH ROW EXECUTE FUNCTION enforce_watch_age();
DROP TRIGGER IF EXISTS watch_progress ON watch_history;
CREATE TRIGGER watch_progress BEFORE INSERT OR UPDATE ON watch_history FOR EACH ROW EXECUTE FUNCTION enforce_watch_progress();
DROP TRIGGER IF EXISTS asset_duration ON media_asset;
CREATE TRIGGER asset_duration BEFORE INSERT OR UPDATE ON media_asset FOR EACH ROW EXECUTE FUNCTION enforce_asset_duration();
DROP TRIGGER IF EXISTS review_requires_watch ON title_review;
CREATE TRIGGER review_requires_watch BEFORE INSERT OR UPDATE ON title_review FOR EACH ROW EXECUTE FUNCTION enforce_review_watch();
DROP TRIGGER IF EXISTS eprating_requires_watch ON episode_rating;
CREATE TRIGGER eprating_requires_watch BEFORE INSERT OR UPDATE ON episode_rating FOR EACH ROW EXECUTE FUNCTION enforce_episode_watch();

CREATE OR REPLACE FUNCTION start_session(pr INT,device VARCHAR,kind VARCHAR DEFAULT 'web') RETURNS INT LANGUAGE plpgsql AS $$
DECLARE a INT; p plan; result INT;
BEGIN
 SELECT account_id INTO a FROM profile WHERE profile_id=pr;
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 p:=current_plan(a);
 IF p.plan_id IS NULL OR EXISTS(SELECT 1 FROM account WHERE account_id=a AND suspended_at IS NOT NULL) THEN
 RAISE EXCEPTION 'An active subscription and an unsuspended account are required.' USING ERRCODE='23514'; END IF;
 UPDATE stream_session SET ended_at=greatest(CURRENT_DATE,started_at) WHERE ended_at IS NULL AND device_name=device AND profile_id IN(SELECT profile_id FROM profile WHERE account_id=a);
 IF (SELECT count(*) FROM stream_session WHERE ended_at IS NULL AND profile_id IN(SELECT profile_id FROM profile WHERE account_id=a))>=p.max_streams THEN
 RAISE EXCEPTION 'All device slots are in use. Stop another stream first.' USING ERRCODE='23514'; END IF;
 INSERT INTO stream_session(profile_id,device_type,device_name) VALUES(pr,kind,device) RETURNING session_id INTO result;
 RETURN result;
END $$;
CREATE OR REPLACE FUNCTION start_playback(pr INT,m INT,e INT,device VARCHAR,replay BOOLEAN DEFAULT FALSE,kind VARCHAR DEFAULT 'web') RETURNS JSONB LANGUAGE plpgsql AS $$
DECLARE s INT; w watch_history; asset media_asset; p plan; runtime INT;
BEGIN
 IF num_nonnulls(m,e)<>1 OR item_runtime_sec(m,e) IS NULL THEN RAISE EXCEPTION 'Choose exactly one valid movie or episode.' USING ERRCODE='23514'; END IF;
 IF item_age_rating(m,e)>(SELECT max_age_rating FROM profile WHERE profile_id=pr) THEN RAISE EXCEPTION 'This title is above the profile age limit.' USING ERRCODE='23514'; END IF;
 s:=start_session(pr,device,kind);
 p:=current_plan((SELECT account_id FROM profile WHERE profile_id=pr));
 runtime:=item_runtime_sec(m,e);
 IF NOT replay THEN SELECT * INTO w FROM watch_history WHERE profile_id=pr AND movie_id IS NOT DISTINCT FROM m AND episode_id IS NOT DISTINCT FROM e AND NOT completed ORDER BY last_watched_at DESC,watch_id DESC LIMIT 1; END IF;
 IF w.watch_id IS NULL THEN INSERT INTO watch_history(profile_id,movie_id,episode_id) VALUES(pr,m,e) RETURNING * INTO w; END IF;
 SELECT * INTO asset FROM media_asset WHERE asset_kind='full' AND movie_id IS NOT DISTINCT FROM m AND episode_id IS NOT DISTINCT FROM e AND quality_rank(quality)<=quality_rank(p.max_quality) ORDER BY quality_rank(quality) DESC,asset_id LIMIT 1;
 RETURN jsonb_build_object('session_id',s,'watch_id',w.watch_id,'movie_id',m,'episode_id',e,'runtime_sec',runtime,'progress_sec',w.progress_sec,'asset_id',asset.asset_id,'quality',coalesce(asset.quality,'SD'),'is_placeholder',coalesce(asset.is_placeholder,TRUE),'source_ref',asset.source_ref);
END $$;
CREATE OR REPLACE FUNCTION record_progress(s INT,w INT,pos INT) RETURNS watch_history LANGUAGE plpgsql AS $$
DECLARE a INT; pr INT; result watch_history;
BEGIN
 SELECT p.account_id,p.profile_id INTO a,pr FROM stream_session ss JOIN profile p USING(profile_id) WHERE session_id=s;
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 IF NOT EXISTS(SELECT 1 FROM stream_session WHERE session_id=s AND ended_at IS NULL) OR (current_plan(a)).plan_id IS NULL OR EXISTS(SELECT 1 FROM account WHERE account_id=a AND suspended_at IS NOT NULL) THEN
 RAISE EXCEPTION 'Playback is no longer authorised. Return to your account.' USING ERRCODE='23514'; END IF;
 UPDATE watch_history SET progress_sec=pos,last_watched_at=CURRENT_DATE WHERE watch_id=w AND profile_id=pr RETURNING * INTO result;
 IF NOT FOUND THEN RAISE EXCEPTION 'Watch record does not belong to this session.' USING ERRCODE='23514'; END IF;
 RETURN result;
END $$;
CREATE OR REPLACE FUNCTION end_playback(s INT,w INT DEFAULT NULL,pos INT DEFAULT NULL) RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE a INT;
BEGIN
 SELECT account_id INTO a FROM profile WHERE profile_id=(SELECT profile_id FROM stream_session WHERE session_id=s);
 PERFORM 1 FROM account WHERE account_id=a FOR UPDATE;
 IF w IS NOT NULL AND pos IS NOT NULL AND EXISTS(SELECT 1 FROM stream_session WHERE session_id=s AND ended_at IS NULL) THEN PERFORM record_progress(s,w,pos); END IF;
 UPDATE stream_session SET ended_at=greatest(CURRENT_DATE,started_at) WHERE session_id=s AND ended_at IS NULL;
END $$;

-- Protect parent edits that could silently invalidate existing children.
CREATE OR REPLACE FUNCTION guard_catalog_edit() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='title' AND NEW.age_rating<>OLD.age_rating AND EXISTS(
 SELECT 1 FROM watch_history w JOIN profile p USING(profile_id) LEFT JOIN episode e USING(episode_id)
 WHERE coalesce(w.movie_id,e.series_id)=NEW.title_id AND p.max_age_rating<NEW.age_rating) THEN
 RAISE EXCEPTION 'This age change conflicts with existing watch history.' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS title_age_guard ON title;
CREATE TRIGGER title_age_guard BEFORE UPDATE ON title FOR EACH ROW EXECUTE FUNCTION guard_catalog_edit();
-- Runtime edits are rejected by the catalogue API once history or assets reference the item.
-- Profile age changes are similarly checked by the API before the UPDATE.
