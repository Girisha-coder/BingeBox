"""Commit-time EER participation, including concurrent last-genre removals."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid

import psycopg
import pytest


def test_title_without_genre_rejected_at_commit(database_dsn):
    with psycopg.connect(database_dsn) as connection:
        with pytest.raises(psycopg.errors.CheckViolation, match="at least one genre"):
            with connection.transaction():
                tid = connection.execute("INSERT INTO title(name,release_year,age_rating,title_type) VALUES('No genre',2026,0,'M') RETURNING title_id").fetchone()[0]
                connection.execute("INSERT INTO movie(title_id,duration_min) VALUES(%s,1)", (tid,))
        assert connection.execute("SELECT count(*) FROM title WHERE title_id=%s", (tid,)).fetchone()[0] == 0


def test_last_genre_delete_and_reparent_rejected(db, sample):
    mid, sid = sample["movie"], sample["series"]
    for statement, params in [
        ("DELETE FROM title_genre WHERE title_id=%s", (mid,)),
        ("UPDATE title_genre SET title_id=%s WHERE title_id=%s", (sid, mid)),
    ]:
        # Give reparenting a distinct genre to avoid an unrelated unique violation.
        if statement.startswith("UPDATE"):
            gid = db.execute("INSERT INTO genre(name) VALUES('Distinct') RETURNING genre_id").fetchone()[0]
            db.execute("UPDATE title_genre SET genre_id=%s WHERE title_id=%s", (gid, mid))
        with pytest.raises(psycopg.errors.CheckViolation, match="at least one genre"), db.transaction():
            db.execute(statement, params)
            db.execute("SET CONSTRAINTS ALL IMMEDIATE")
        assert db.execute("SELECT count(*) FROM title_genre WHERE title_id=%s", (mid,)).fetchone()[0] == 1
    with pytest.raises(psycopg.errors.ForeignKeyViolation), db.transaction():
        db.execute("DELETE FROM genre WHERE genre_id IN (SELECT genre_id FROM title_genre WHERE title_id=%s)", (mid,))


def test_genres_can_be_replaced_and_title_deleted_atomically(db, sample):
    mid = sample["movie"]
    gid = db.execute("INSERT INTO genre(name) VALUES('Replacement') RETURNING genre_id").fetchone()[0]
    db.execute("DELETE FROM title_genre WHERE title_id=%s", (mid,))
    db.execute("INSERT INTO title_genre VALUES(%s,%s)", (mid, gid))
    db.execute("SET CONSTRAINTS ALL IMMEDIATE")
    db.execute("SET CONSTRAINTS ALL DEFERRED")
    db.execute("DELETE FROM movie WHERE title_id=%s", (mid,))
    db.execute("DELETE FROM title WHERE title_id=%s", (mid,))
    db.execute("SET CONSTRAINTS ALL IMMEDIATE")


@pytest.mark.parametrize("isolation", ["READ COMMITTED", "REPEATABLE READ"])
def test_concurrent_removals_cannot_leave_title_without_genres(database_dsn, isolation):
    tag = uuid.uuid4().hex[:12]
    with psycopg.connect(database_dsn) as db:
        tid = db.execute("INSERT INTO title(name,release_year,age_rating,title_type) VALUES(%s,2026,0,'M') RETURNING title_id", (tag,)).fetchone()[0]
        db.execute("INSERT INTO movie(title_id,duration_min) VALUES(%s,1)", (tid,))
        genres = [db.execute("INSERT INTO genre(name) VALUES(%s) RETURNING genre_id", (tag + str(i),)).fetchone()[0] for i in range(2)]
        for gid in genres:
            db.execute("INSERT INTO title_genre VALUES(%s,%s)", (tid, gid))
    barrier = Barrier(2)

    def remove(gid):
        try:
            with psycopg.connect(database_dsn) as db:
                db.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
                db.execute("SET LOCAL lock_timeout='5s'")
                db.execute("SET LOCAL statement_timeout='10s'")
                db.execute("DELETE FROM title_genre WHERE title_id=%s AND genre_id=%s", (tid, gid))
                barrier.wait(timeout=10)
            return "committed"
        except (psycopg.errors.CheckViolation, psycopg.errors.SerializationFailure) as error:
            return error.sqlstate

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(remove, genres))
        assert sorted(outcomes) == sorted(["committed", "23514" if isolation == "READ COMMITTED" else "40001"])
        with psycopg.connect(database_dsn) as db:
            assert db.execute("SELECT count(*) FROM title_genre WHERE title_id=%s", (tid,)).fetchone()[0] == 1
    finally:
        with psycopg.connect(database_dsn) as db:
            db.execute("DELETE FROM movie WHERE title_id=%s", (tid,))
            db.execute("DELETE FROM title WHERE title_id=%s", (tid,))
            db.execute("DELETE FROM genre WHERE genre_id=ANY(%s)", (genres,))
