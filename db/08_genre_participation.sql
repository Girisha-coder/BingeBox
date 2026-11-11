-- EER Figure 1: every TITLE participates in IN_GENRE.
-- Defer validation so staff can replace the whole genre set atomically.
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM title t WHERE NOT EXISTS
               (SELECT 1 FROM title_genre g WHERE g.title_id=t.title_id)) THEN
        RAISE EXCEPTION 'Assign at least one genre to each existing title before migration.';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION enforce_title_genre() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE target_id INT;
BEGIN
    FOR target_id IN
        SELECT DISTINCT id FROM unnest(ARRAY[
            CASE WHEN TG_OP <> 'INSERT' THEN OLD.title_id END,
            CASE WHEN TG_OP <> 'DELETE' THEN NEW.title_id END
        ]) AS affected(id) WHERE id IS NOT NULL ORDER BY id
    LOOP
        -- Serialize competing removals of different genres on the same title.
        -- A write also prevents write skew under REPEATABLE READ isolation.
        UPDATE title SET name=name WHERE title_id=target_id;
        IF FOUND AND NOT EXISTS (SELECT 1 FROM title_genre WHERE title_id=target_id) THEN
            RAISE EXCEPTION 'A title must have at least one genre.'
                USING ERRCODE='23514', CONSTRAINT='title_requires_genre';
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS title_requires_genre ON title;
CREATE CONSTRAINT TRIGGER title_requires_genre
AFTER INSERT OR UPDATE OF title_id ON title DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_title_genre();

DROP TRIGGER IF EXISTS title_genre_preserves_participation ON title_genre;
CREATE CONSTRAINT TRIGGER title_genre_preserves_participation
AFTER DELETE OR UPDATE ON title_genre DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_title_genre();

GRANT EXECUTE ON FUNCTION enforce_title_genre() TO bingebox_app;
