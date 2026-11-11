DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='bingebox_app') THEN CREATE ROLE bingebox_app NOLOGIN; END IF; END $$;
GRANT USAGE ON SCHEMA public TO bingebox_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO bingebox_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO bingebox_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO bingebox_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
-- The HTTP connection SET ROLEs to this non-login role; it cannot create/drop/truncate tables.
