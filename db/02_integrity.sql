-- Additional enforcement for R7, absent from the submission's FK-only design.
-- Deferral permits parent and child creation/deletion within one transaction.
CREATE FUNCTION enforce_title_subtype() RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
    target_id INT;
    target_type VARCHAR(1);
BEGIN
    -- Check both ends of a subtype key update, not only the new parent.
    FOR target_id IN
        SELECT DISTINCT id
        FROM unnest(ARRAY[
            CASE WHEN TG_OP <> 'INSERT' THEN OLD.title_id END,
            CASE WHEN TG_OP <> 'DELETE' THEN NEW.title_id END
        ]) AS affected(id)
        WHERE id IS NOT NULL
    LOOP
        SELECT title_type INTO target_type FROM title WHERE title_id = target_id FOR UPDATE;
        IF NOT FOUND THEN
            CONTINUE;
        END IF;
        IF (target_type = 'M' AND NOT EXISTS (SELECT 1 FROM movie WHERE title_id = target_id))
            OR (target_type = 'S' AND NOT EXISTS (SELECT 1 FROM series WHERE title_id = target_id)) THEN
            RAISE EXCEPTION 'A title must have its matching movie or series row.'
                USING ERRCODE = '23514', CONSTRAINT = 'title_requires_subtype';
        END IF;
    END LOOP;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER title_requires_subtype
AFTER INSERT OR UPDATE ON title DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_title_subtype();

CREATE CONSTRAINT TRIGGER movie_preserves_subtype
AFTER DELETE OR UPDATE ON movie DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_title_subtype();

CREATE CONSTRAINT TRIGGER series_preserves_subtype
AFTER DELETE OR UPDATE ON series DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_title_subtype();
