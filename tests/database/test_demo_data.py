from datetime import date, timedelta

import pytest
import psycopg

from scripts.seed_demo import EXPECTED_COUNTS, seed_demo, validate


def test_demo_has_200_consistent_rows_and_meaningful_extremes(db):
    snapshot = date(2026, 10, 20)
    report = seed_demo(db, snapshot)
    assert report["total_rows"] == 200
    assert report["tables"] == EXPECTED_COUNTS
    assert report["consistency_checks_passed"] == 11
    assert db.execute("SELECT min(duration_min), max(duration_min) FROM movie").fetchone() == (1, 600)
    assert db.execute("SELECT min(duration_min), max(duration_min) FROM episode").fetchone() == (1, 300)
    assert db.execute("SELECT min(rating), max(rating) FROM title_review").fetchone() == (1, 10)
    assert db.execute("SELECT count(*) FROM profile WHERE is_kids").fetchone()[0] == 3
    assert db.execute("SELECT count(*) FROM stream_session WHERE ended_at IS NULL").fetchone()[0] == 6
    assert db.execute("SELECT count(*) FROM account WHERE suspended_at IS NOT NULL").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM watch_history WHERE progress_sec = 0").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM title WHERE imdb_rating > 9 AND imdb_votes < 20").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM title WHERE imdb_id IS NOT NULL").fetchone()[0] == 0


def test_demo_rerun_preserves_ids_hashes_and_snapshot(db):
    snapshot = date(2026, 10, 20)
    seed_demo(db, snapshot)
    before = db.execute("SELECT account_id, email, password_hash FROM account ORDER BY account_id").fetchall()
    report = seed_demo(db, snapshot + timedelta(days=30))
    assert report["action"] == "existing demo retained"
    assert report["as_of"] == snapshot.isoformat()
    assert db.execute("SELECT account_id, email, password_hash FROM account ORDER BY account_id").fetchall() == before


def test_demo_refuses_other_data_without_changing_it(db, sample):
    before = db.execute("SELECT count(*) FROM account").fetchone()
    with pytest.raises(ValueError, match="other data"):
        seed_demo(db, date(2026, 10, 20))
    assert db.execute("SELECT count(*) FROM account").fetchone() == before
    assert db.execute("SELECT count(*) FROM admin_user").fetchone()[0] == 0


def test_demo_progress_violation_is_now_rejected_by_trigger(db):
    snapshot = date(2026, 10, 20)
    seed_demo(db, snapshot)
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute("UPDATE watch_history SET progress_sec = 999999 WHERE watch_id = (SELECT min(watch_id) FROM watch_history)")
