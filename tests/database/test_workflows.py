from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import uuid
import psycopg
import pytest


def reject(db, statement, args=()):
    with pytest.raises(psycopg.errors.CheckViolation), db.transaction():
        db.execute(statement, args)


def test_business_inventory_and_runtime_role(db):
    names = "subscribe change_plan process_renewals confirm_payment start_session start_playback record_progress end_playback suspend_account reinstate_account current_plan item_age_rating item_runtime_sec quality_rank require_admin_role".split()
    assert (
        db.execute(
            "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace=n.oid WHERE n.nspname='public' AND p.proname=ANY(%s)",
            (names,),
        ).fetchone()[0]
        == 15
    )
    assert (
        db.execute(
            "SELECT count(*) FROM information_schema.views WHERE table_schema='public'"
        ).fetchone()[0]
        == 4
    )
    assert (
        db.execute(
            "SELECT count(*) FROM pg_trigger WHERE tgname=ANY(%s)",
            (
                "profile_limit watch_age_check watch_progress asset_duration review_requires_watch eprating_requires_watch".split(),
            ),
        ).fetchone()[0]
        == 6
    )
    db.execute("SET ROLE bingebox_app")
    assert db.execute("SELECT current_user").fetchone()[0] == "bingebox_app"
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute("TRUNCATE account CASCADE")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute("CREATE TABLE forbidden(id INT)")


def test_playback_resume_replay_progress_and_review_threshold(db, sample):
    s = sample

    def play(replay=False):
        return db.execute(
            "SELECT start_playback(%s,%s,NULL,'device-one',%s)",
            (s["profile"], s["movie"], replay),
        ).fetchone()[0]

    first = play()
    assert first["is_placeholder"] and first["quality"] == "SD"
    reject(
        db,
        "SELECT record_progress(%s,%s,6001)",
        (first["session_id"], first["watch_id"]),
    )
    reject(
        db,
        "INSERT INTO title_review(profile_id,title_id,rating) VALUES(%s,%s,8)",
        (s["profile"], s["movie"]),
    )
    db.execute(
        "SELECT record_progress(%s,%s,5399)", (first["session_id"], first["watch_id"])
    )
    assert not db.execute(
        "SELECT completed FROM watch_history WHERE watch_id=%s", (first["watch_id"],)
    ).fetchone()[0]
    resumed = play()
    assert resumed["watch_id"] == first["watch_id"] and resumed["progress_sec"] == 5399
    assert (
        db.execute(
            "SELECT count(*) FROM stream_session WHERE ended_at IS NULL"
        ).fetchone()[0]
        == 1
    )
    db.execute(
        "SELECT record_progress(%s,%s,5400)",
        (resumed["session_id"], resumed["watch_id"]),
    )
    db.execute(
        "INSERT INTO title_review(profile_id,title_id,rating) VALUES(%s,%s,8)",
        (s["profile"], s["movie"]),
    )
    replay = play(True)
    assert replay["watch_id"] != first["watch_id"] and replay["progress_sec"] == 0
    db.execute(
        "SELECT end_playback(%s,%s,123)", (replay["session_id"], replay["watch_id"])
    )
    db.execute("SELECT end_playback(%s)", (replay["session_id"],))
    reject(
        db,
        "SELECT record_progress(%s,%s,200)",
        (replay["session_id"], replay["watch_id"]),
    )
    assert (
        db.execute(
            "SELECT progress_sec FROM v_continue_watching WHERE profile_id=%s",
            (s["profile"],),
        ).fetchone()[0]
        == 123
    )


def test_kids_age_and_episode_eligibility(db, sample):
    s = sample
    db.execute(
        "UPDATE profile SET max_age_rating=7,is_kids=TRUE WHERE profile_id=%s",
        (s["profile"],),
    )
    reject(
        db,
        "SELECT start_playback(%s,NULL,%s,'kids-device')",
        (s["profile"], s["episode"]),
    )
    reject(
        db,
        "INSERT INTO episode_rating(profile_id,episode_id,rating) VALUES(%s,%s,8)",
        (s["profile"], s["episode"]),
    )
    db.execute(
        "UPDATE profile SET max_age_rating=18,is_kids=FALSE WHERE profile_id=%s",
        (s["profile"],),
    )
    p = db.execute(
        "SELECT start_playback(%s,NULL,%s,'adult-device')", (s["profile"], s["episode"])
    ).fetchone()[0]
    db.execute("SELECT record_progress(%s,%s,1620)", (p["session_id"], p["watch_id"]))
    db.execute(
        "INSERT INTO episode_rating(profile_id,episode_id,rating) VALUES(%s,%s,8)",
        (s["profile"], s["episode"]),
    )
    db.execute(
        "INSERT INTO title_review(profile_id,title_id,rating) VALUES(%s,%s,9)",
        (s["profile"], s["series"]),
    )


def test_asset_tolerance_and_quality_selection(db, sample):
    s = sample
    db.execute("SELECT change_plan(%s,%s)", (s["account"], s["plan"]))
    for quality in ["SD", "HD", "4K"]:
        db.execute(
            "INSERT INTO media_asset(asset_kind,movie_id,provider,source_ref,quality,duration_sec) VALUES('full',%s,'file','test.mp4',%s,6060)",
            (s["movie"], quality),
        )
    p = db.execute(
        "SELECT start_playback(%s,%s,NULL,'browser-one')", (s["profile"], s["movie"])
    ).fetchone()[0]
    assert p["quality"] == "HD" and not p["is_placeholder"]
    reject(
        db, "UPDATE media_asset SET duration_sec=6061 WHERE movie_id=%s", (s["movie"],)
    )


def test_downgrade_rolls_back_then_closes_sessions(db, sample):
    s = sample
    db.execute(
        "INSERT INTO profile(account_id,name) VALUES(%s,'Second')", (s["account"],)
    )
    p = db.execute(
        "SELECT start_session(%s,'browser-one')", (s["profile"],)
    ).fetchone()[0]
    reject(db, "SELECT change_plan(%s,%s)", (s["account"], s["plan"]))
    assert (
        db.execute("SELECT (current_plan(%s)).name", (s["account"],)).fetchone()[0]
        == "Family"
    )
    assert (
        db.execute(
            "SELECT ended_at FROM stream_session WHERE session_id=%s", (p,)
        ).fetchone()[0]
        is None
    )
    db.execute(
        "DELETE FROM profile WHERE account_id=%s AND profile_id<>%s",
        (s["account"], s["profile"]),
    )
    db.execute("SELECT change_plan(%s,%s)", (s["account"], s["plan"]))
    assert (
        db.execute(
            "SELECT ended_at FROM stream_session WHERE session_id=%s", (p,)
        ).fetchone()[0]
        is not None
    )


def test_renewal_month_edges_expiry_and_hook(db, sample):
    s = sample
    admin = db.execute(
        "INSERT INTO admin_user(email,password_hash,full_name,role) VALUES('renewal@example.test','test','Renewal','billing') RETURNING admin_id"
    ).fetchone()[0]
    db.execute("DELETE FROM subscription WHERE account_id=%s", (s["account"],))
    db.execute("SELECT subscribe(%s,%s,'2026-01-31')", (s["account"], s["plan"]))
    assert db.execute(
        "SELECT end_date FROM subscription WHERE account_id=%s", (s["account"],)
    ).fetchone()[0] == date(2026, 2, 28)
    # Instrument the designated payment hook inside this rolled-back test transaction.
    db.execute("CREATE TEMP TABLE payment_calls(a INT,p INT)")
    db.execute(
        "CREATE OR REPLACE FUNCTION confirm_payment(a INT,p INT) RETURNS BOOLEAN LANGUAGE plpgsql AS $$ BEGIN INSERT INTO payment_calls VALUES(a,p); RETURN TRUE; END $$"
    )
    result = db.execute(
        "SELECT process_renewals(%s,'2026-04-01')", (admin,)
    ).fetchone()[0]
    assert result == {"renewed_periods": 2, "expired": 0}
    assert db.execute("SELECT count(*) FROM payment_calls").fetchone()[0] == 2
    assert db.execute(
        "SELECT end_date FROM subscription WHERE account_id=%s", (s["account"],)
    ).fetchone()[0] == date(2026, 4, 28)
    db.execute(
        "UPDATE subscription SET auto_renew=FALSE WHERE account_id=%s", (s["account"],)
    )
    db.execute(
        "INSERT INTO stream_session(profile_id,device_type,device_name) VALUES(%s,'web','fixture')",
        (s["profile"],),
    )
    result = db.execute(
        "SELECT process_renewals(%s,'2026-05-01')", (admin,)
    ).fetchone()[0]
    assert result["expired"] == 1
    assert (
        db.execute(
            "SELECT count(*) FROM stream_session WHERE ended_at IS NULL"
        ).fetchone()[0]
        == 0
    )
    assert db.execute("SELECT process_renewals(%s,'2026-05-01')", (admin,)).fetchone()[
        0
    ] == {"renewed_periods": 0, "expired": 0}


def test_suspension_role_and_playback_revocation(db, sample):
    ids = {
        r: db.execute(
            "INSERT INTO admin_user(email,password_hash,full_name,role) VALUES(%s,%s,%s,%s) RETURNING admin_id",
            (r + "@example.test", "test", r, r),
        ).fetchone()[0]
        for r in ["catalogue", "billing"]
    }
    s = sample
    p = db.execute(
        "SELECT start_playback(%s,%s,NULL,'browser-one')", (s["profile"], s["movie"])
    ).fetchone()[0]
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.transaction():
        db.execute("SELECT suspend_account(%s,%s)", (ids["catalogue"], s["account"]))
    db.execute("SELECT suspend_account(%s,%s)", (ids["billing"], s["account"]))
    assert (
        db.execute(
            "SELECT suspended_by_admin FROM account WHERE account_id=%s",
            (s["account"],),
        ).fetchone()[0]
        == ids["billing"]
    )
    reject(db, "SELECT start_session(%s,'new-device')", (s["profile"],))
    reject(db, "SELECT record_progress(%s,%s,30)", (p["session_id"], p["watch_id"]))
    db.execute("SELECT reinstate_account(%s,%s)", (ids["billing"], s["account"]))
    db.execute("SELECT start_session(%s,'new-device')", (s["profile"],))


@pytest.mark.parametrize("operation", ["stream", "profile", "subscription"])
def test_independent_connections_serialize_last_slot(database_dsn, operation):
    with psycopg.connect(database_dsn) as c:
        a = c.execute(
            "INSERT INTO account(email,password_hash) VALUES(%s,'test') RETURNING account_id",
            (uuid.uuid4().hex + "@race.test",),
        ).fetchone()[0]
        plan = c.execute("SELECT plan_id FROM plan WHERE name='Basic'").fetchone()[0]
        if operation != "subscription":
            c.execute("SELECT subscribe(%s,%s)", (a, plan))
        pr = (
            c.execute(
                "INSERT INTO profile(account_id,name) VALUES(%s,'Viewer') RETURNING profile_id",
                (a,),
            ).fetchone()[0]
            if operation == "stream"
            else None
        )
    barrier = Barrier(2)

    def compete(index):
        try:
            with psycopg.connect(database_dsn) as c:
                c.execute("SET lock_timeout='5s'")
                barrier.wait(timeout=10)
                if operation == "stream":
                    c.execute(
                        "SELECT start_session(%s,%s)", (pr, "browser-" + str(index))
                    )
                elif operation == "profile":
                    c.execute(
                        "INSERT INTO profile(account_id,name) VALUES(%s,%s)",
                        (a, "Viewer" + str(index)),
                    )
                else:
                    c.execute("SELECT subscribe(%s,%s)", (a, plan))
            return "accepted"
        except psycopg.errors.CheckViolation:
            return "refused"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(compete, [1, 2])) == ["accepted", "refused"]
    finally:
        with psycopg.connect(database_dsn) as c:
            c.execute("DELETE FROM account WHERE account_id=%s", (a,))
