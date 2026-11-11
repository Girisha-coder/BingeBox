"""Integration tests use a new database, never the application's live data."""

import os
from pathlib import Path
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def database_dsn():
    admin_dsn = os.environ.get("TEST_ADMIN_DSN")
    if not admin_dsn:
        pytest.fail("Use python scripts/run_checks.py with the project database running.")
    name = "bingebox_test_" + uuid.uuid4().hex
    dsn = make_conninfo(admin_dsn, dbname=name)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(dsn) as connection:
                for path in sorted((ROOT / "db").glob("*.sql")):
                    connection.execute(path.read_text(encoding="utf-8"))
            yield dsn
        finally:
            # The only database this fixture may remove is the one it created.
            assert name.startswith("bingebox_test_") and len(name) == 46
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def db(database_dsn):
    connection = psycopg.connect(database_dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def sample(db):
    account_id = db.execute(
        "INSERT INTO account (email, password_hash) VALUES (%s, %s) RETURNING account_id",
        ("household@example.test", "test-fixture-only"),
    ).fetchone()[0]
    db.execute("SELECT subscribe(%s,(SELECT plan_id FROM plan WHERE name='Family'))", (account_id,))
    profile_id = db.execute(
        "INSERT INTO profile (account_id, name) VALUES (%s, %s) RETURNING profile_id",
        (account_id, "Viewer"),
    ).fetchone()[0]
    movie_id = db.execute(
        """INSERT INTO title (name, release_year, age_rating, title_type)
           VALUES ('Example movie', 2026, 7, 'M') RETURNING title_id"""
    ).fetchone()[0]
    db.execute("INSERT INTO movie (title_id, duration_min) VALUES (%s, 100)", (movie_id,))
    series_id = db.execute(
        """INSERT INTO title (name, release_year, age_rating, title_type)
           VALUES ('Example series', 2026, 13, 'S') RETURNING title_id"""
    ).fetchone()[0]
    db.execute("INSERT INTO series (title_id, series_status) VALUES (%s, 'ongoing')", (series_id,))
    genre = db.execute("INSERT INTO genre(name) VALUES('Sample genre') RETURNING genre_id").fetchone()[0]
    db.execute("INSERT INTO title_genre VALUES(%s,%s),(%s,%s)", (movie_id, genre, series_id, genre))
    episode_id = db.execute(
        """INSERT INTO episode (series_id, season_no, episode_no, name, duration_min)
           VALUES (%s, 1, 1, 'Pilot', 30) RETURNING episode_id""", (series_id,)
    ).fetchone()[0]
    plan_id = db.execute("SELECT plan_id FROM plan WHERE name = 'Basic'").fetchone()[0]
    return dict(account=account_id, profile=profile_id, movie=movie_id,
                series=series_id, episode=episode_id, plan=plan_id)
