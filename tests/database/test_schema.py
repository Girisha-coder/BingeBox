from pathlib import Path
import re

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]


def rejects(db, error, statement, parameters=()):
    with pytest.raises(error), db.transaction():
        db.execute(statement, parameters)


def test_schema_matches_all_source_columns(db):
    reference = (ROOT / "docs/reference/BingeBox_MidSem_Submission.md").read_text(encoding="utf-8")
    section = reference.split("### 5. Relational schema and integrity constraints")[1].split("### 6.")[0]
    expected = {}
    for name, body in re.findall(r"#### ([A-Z_]+)\n(.*?)(?=\n#### |\Z)", section, re.S):
        expected[name.lower()] = [
            (column, data_type.lower().replace(" ", ""))
            for column, data_type in re.findall(r"^\| ([a-z_]+) \| ([A-Z0-9(),]+) \|", body, re.M)
        ]
    rows = db.execute(
        """SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod)
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           JOIN pg_attribute a ON a.attrelid = c.oid
           WHERE n.nspname = 'public' AND c.relkind = 'r'
             AND a.attnum > 0 AND NOT a.attisdropped
           ORDER BY c.relname, a.attnum"""
    ).fetchall()
    actual = {}
    for table, column, data_type in rows:
        data_type = data_type.replace("character varying", "varchar").replace("integer", "int").replace("numeric", "decimal")
        actual.setdefault(table, []).append((column, data_type.replace(" ", "")))
    assert len(expected) == 18
    assert sum(map(len, expected.values())) == 99
    assert actual == expected
    assert db.execute("SHOW server_version_num").fetchone()[0].startswith("16")


def test_seed_exact_values_and_repeatability(db):
    expected = [("Student", 99, 1, 1, "HD"), ("Basic", 199, 1, 1, "HD"),
                ("Duo", 349, 2, 2, "HD"), ("Premium", 499, 1, 3, "4K"),
                ("Family", 649, 4, 4, "4K")]
    query = "SELECT name, monthly_price, max_profiles, max_streams, max_quality FROM plan ORDER BY monthly_price"
    assert db.execute(query).fetchall() == expected
    db.execute((ROOT / "db/04_seed.sql").read_text(encoding="utf-8"))
    assert db.execute(query).fetchall() == expected
    db.execute("UPDATE plan SET monthly_price = 100 WHERE name = 'Student'")
    db.execute((ROOT / "db/04_seed.sql").read_text(encoding="utf-8"))
    assert db.execute("SELECT monthly_price FROM plan WHERE name = 'Student'").fetchone()[0] == 100


def test_source_nullability_defaults_and_identity_columns(db):
    reference = (ROOT / "docs/reference/BingeBox_MidSem_Submission.md").read_text(encoding="utf-8")
    section = reference.split("### 5. Relational schema and integrity constraints")[1].split("### 6.")[0]
    actual = {
        (table, column): (not_null, identity, default)
        for table, column, not_null, identity, default in db.execute(
            """SELECT c.relname,a.attname,a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid)
               FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
               JOIN pg_attribute a ON a.attrelid=c.oid
               LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
               WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped"""
        )
    }
    checked = 0
    for table, body in re.findall(r"#### ([A-Z_]+)\n(.*?)(?=\n#### |\Z)", section, re.S):
        for column, constraints in re.findall(r"^\| ([a-z_]+) \| [A-Z0-9(),]+ \| (.*?) \|$", body, re.M):
            not_null, identity, default = actual[table.lower(), column]
            assert not_null == bool(re.search(r"\b(?:PK|NN)\b", constraints)), (table, column)
            assert bool(identity) == ("auto-increment" in constraints), (table, column)
            match = re.search(r"\bDEF ('[^']*'|\w+)", constraints)
            if match:
                expected = match.group(1).strip("'").lower()
                normalized = default.split("::")[0].strip("'").lower().replace("current_date", "today")
                assert normalized == expected, (table, column, default)
            checked += 1
    assert checked == 99


@pytest.mark.parametrize("field,value", [("monthly_price", -1), ("max_profiles", 0),
                                          ("max_streams", 11), ("max_quality", "8K")])
def test_plan_domains(db, field, value):
    from psycopg import sql
    rejects(db, psycopg.errors.CheckViolation,
            sql.SQL("UPDATE plan SET {} = %s WHERE name = 'Basic'").format(sql.Identifier(field)), (value,))


def test_only_one_current_subscription(db, sample):
    db.execute('DELETE FROM subscription WHERE account_id=%s', (sample['account'],))
    statement = """INSERT INTO subscription (account_id, plan_id, start_date, end_date, status)
                   VALUES (%s, %s, DATE '2026-10-01', DATE '2026-11-01', %s)"""
    db.execute(statement, (sample["account"], sample["plan"], "active"))
    rejects(db, psycopg.errors.UniqueViolation, statement, (sample["account"], sample["plan"], "past_due"))
    db.execute(statement, (sample["account"], sample["plan"], "expired"))
    db.execute(statement, (sample["account"], sample["plan"], "cancelled"))


def test_subscription_and_session_date_bounds(db, sample):
    rejects(db, psycopg.errors.CheckViolation,
            """INSERT INTO subscription (account_id, plan_id, start_date, end_date)
               VALUES (%s, %s, '2026-11-01', '2026-10-01')""", (sample["account"], sample["plan"]))
    rejects(db, psycopg.errors.CheckViolation,
            """INSERT INTO stream_session (profile_id, device_type, device_name, started_at, ended_at)
               VALUES (%s, 'web', 'Browser', '2026-11-01', '2026-10-01')""", (sample["profile"],))


def test_kids_bound_and_profile_name_uniqueness(db, sample):
    statement = "INSERT INTO profile (account_id, name, is_kids, max_age_rating) VALUES (%s, %s, TRUE, %s)"
    db.execute(statement, (sample["account"], "Kids", 7))
    rejects(db, psycopg.errors.CheckViolation, statement, (sample["account"], "Older", 13))
    rejects(db, psycopg.errors.UniqueViolation, statement, (sample["account"], "Kids", 7))


def test_suspension_metadata_pair(db, sample):
    rejects(db, psycopg.errors.CheckViolation,
            "UPDATE account SET suspended_at = CURRENT_DATE WHERE account_id = %s", (sample["account"],))
    admin = db.execute("""INSERT INTO admin_user (email, password_hash, full_name, role)
                        VALUES ('billing@example.test', 'test-only', 'Billing', 'billing') RETURNING admin_id""").fetchone()[0]
    db.execute("UPDATE account SET suspended_at = CURRENT_DATE, suspended_by_admin = %s WHERE account_id = %s",
               (admin, sample["account"]))
    rejects(db, psycopg.errors.CheckViolation,
            "UPDATE account SET suspended_at = NULL WHERE account_id = %s", (sample["account"],))


@pytest.mark.parametrize("email", ["invalid", "two@@example.com", "space @example.com"])
def test_email_format(db, email):
    rejects(db, psycopg.errors.CheckViolation,
            "INSERT INTO account (email, password_hash) VALUES (%s, 'test-only')", (email,))


def test_missing_subtype_rejected_at_transaction_commit(database_dsn):
    with psycopg.connect(database_dsn) as connection:
        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.transaction():
                connection.execute("""INSERT INTO title (name, release_year, age_rating, title_type)
                                    VALUES ('Orphan', 2026, 0, 'M')""")
        assert connection.execute("SELECT count(*) FROM title WHERE name = 'Orphan'").fetchone()[0] == 0


def test_valid_movie_and_series_deferred_checks(db, sample):
    db.execute("SET CONSTRAINTS ALL IMMEDIATE")
    assert db.execute("SELECT count(*) FROM title").fetchone()[0] == 2


def test_wrong_subtype_is_rejected(db, sample):
    rejects(db, psycopg.errors.ForeignKeyViolation,
            "INSERT INTO movie (title_id, duration_min) VALUES (%s, 10)", (sample["series"],))


@pytest.mark.parametrize("kind", ["movie", "series"])
def test_deleting_only_subtype_is_rejected(db, sample, kind):
    from psycopg import sql
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute(sql.SQL("DELETE FROM {} WHERE title_id = %s").format(sql.Identifier(kind)), (sample[kind],))
        db.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_subtype_key_move_cannot_orphan_old_parent(db, sample):
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        new_id = db.execute("""INSERT INTO title (name, release_year, age_rating, title_type)
                               VALUES ('New parent', 2026, 0, 'M') RETURNING title_id""").fetchone()[0]
        db.execute("UPDATE movie SET title_id = %s WHERE title_id = %s", (new_id, sample["movie"]))
        db.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_parent_and_child_can_be_deleted_together(db, sample):
    db.execute("DELETE FROM movie WHERE title_id = %s", (sample["movie"],))
    db.execute("DELETE FROM title WHERE title_id = %s", (sample["movie"],))
    db.execute("SET CONSTRAINTS ALL IMMEDIATE")


def test_episode_number_unique_within_series_and_season(db, sample):
    statement = "INSERT INTO episode (series_id, season_no, episode_no, name, duration_min) VALUES (%s, %s, 1, 'Episode', 30)"
    rejects(db, psycopg.errors.UniqueViolation, statement, (sample["series"], 1))
    db.execute(statement, (sample["series"], 2))


@pytest.mark.parametrize("language", ["", " ", "\t\n"])
def test_blank_languages_rejected(db, sample, language):
    rejects(db, psycopg.errors.CheckViolation,
            "INSERT INTO title_audio VALUES (%s, %s)", (sample["movie"], language))


@pytest.mark.parametrize("targets", [(False, False), (True, True)])
def test_watch_requires_exactly_one_target(db, sample, targets):
    rejects(db, psycopg.errors.CheckViolation,
            "INSERT INTO watch_history (profile_id, movie_id, episode_id) VALUES (%s, %s, %s)",
            (sample["profile"], sample["movie"] if targets[0] else None, sample["episode"] if targets[1] else None))


@pytest.mark.parametrize("kind,title,movie,episode", [
    ("full", False, False, False), ("full", False, True, True), ("full", True, True, False),
    ("trailer", False, True, False), ("trailer", True, True, False),
])
def test_invalid_asset_targets(db, sample, kind, title, movie, episode):
    rejects(db, psycopg.errors.CheckViolation,
            """INSERT INTO media_asset (asset_kind, title_id, movie_id, episode_id, provider, source_ref, duration_sec)
               VALUES (%s, %s, %s, %s, 'file', 'test.mp4', 10)""",
            (kind, sample["movie"] if title else None, sample["movie"] if movie else None,
             sample["episode"] if episode else None))


def test_asset_uniqueness_treats_null_targets_as_equal(db, sample):
    statement = """INSERT INTO media_asset (asset_kind, movie_id, provider, source_ref, duration_sec, quality)
                   VALUES ('full', %s, 'file', 'test.mp4', 6000, %s)"""
    db.execute(statement, (sample["movie"], "SD"))
    rejects(db, psycopg.errors.UniqueViolation, statement, (sample["movie"], "SD"))
    db.execute(statement, (sample["movie"], "HD"))


def test_trailer_length_and_placeholder_rules(db, sample):
    statement = """INSERT INTO media_asset (asset_kind, title_id, provider, source_ref, duration_sec, is_placeholder)
                   VALUES ('trailer', %s, 'youtube', 'example', %s, %s)"""
    db.execute(statement, (sample["movie"], 900, False))
    rejects(db, psycopg.errors.CheckViolation, statement, (sample["movie"], 901, False))
    rejects(db, psycopg.errors.CheckViolation, statement, (sample["movie"], 60, True))


def test_feedback_range_and_unique_profile_item(db, sample):
    db.execute('INSERT INTO watch_history(profile_id,movie_id,progress_sec) VALUES(%s,%s,6000)', (sample['profile'],sample['movie']))
    statement = "INSERT INTO title_review (profile_id, title_id, rating) VALUES (%s, %s, %s)"
    for bad_rating in (0, 11):
        rejects(db, psycopg.errors.CheckViolation, statement, (sample["profile"], sample["movie"], bad_rating))
    db.execute(statement, (sample["profile"], sample["movie"], 10))
    rejects(db, psycopg.errors.UniqueViolation, statement, (sample["profile"], sample["movie"], 1))


def test_account_cascade_deletes_dependent_data(db, sample):
    db.execute("INSERT INTO watch_history (profile_id, movie_id) VALUES (%s, %s)", (sample["profile"], sample["movie"]))
    db.execute("DELETE FROM account WHERE account_id = %s", (sample["account"],))
    assert db.execute("SELECT count(*) FROM profile").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM watch_history").fetchone()[0] == 0


def test_explicit_index_inventory(db):
    count = db.execute("""SELECT count(*) FROM pg_index i
                          JOIN pg_class t ON t.oid = i.indrelid
                          JOIN pg_namespace n ON n.oid = t.relnamespace
                          LEFT JOIN pg_constraint c ON c.conindid = i.indexrelid
                          WHERE n.nspname = 'public' AND c.oid IS NULL""").fetchone()[0]
    assert count == 12


def test_index_definitions_support_submission_lookup_categories(db):
    indexes = dict(db.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public'").fetchall())
    expected = {
        "subscription_one_current": ("UNIQUE", "(account_id)", "WHERE", "'active'", "'past_due'"),
        "title_search": ("USING gin", "to_tsvector", "'english'", "name", "description"),
        "title_name_trigram": ("USING gin", "name gin_trgm_ops"),
        "title_audio_language": ("(language, title_id)",),
        "title_subtitle_language": ("(language, title_id)",),
        "watch_history_recent": ("(profile_id, last_watched_at DESC, watch_id DESC)",),
        "stream_session_live": ("(profile_id, session_id)", "WHERE (ended_at IS NULL)"),
        "subscription_due": ("(end_date, account_id)", "WHERE", "'active'"),
        "title_review_title": ("(title_id)",),
        "episode_rating_episode": ("(episode_id)",),
        "title_genre_genre": ("(genre_id, title_id)",),
        "subscription_account_history": ("(account_id, start_date DESC, sub_id DESC)",),
    }
    for name, parts in expected.items():
        assert all(part in indexes[name] for part in parts), (name, indexes[name])
