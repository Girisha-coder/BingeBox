"""Result-level checks for submission assumptions and cross-cutting requirements."""

from datetime import date, timedelta

import psycopg
import pytest

from app import security


@pytest.mark.parametrize("plan,profiles,streams,quality", [
    ("Student", 1, 1, "HD"), ("Basic", 1, 1, "HD"), ("Duo", 2, 2, "HD"),
    ("Premium", 1, 3, "4K"), ("Family", 4, 4, "4K"),
])
def test_all_five_plans_enforce_profile_stream_and_quality_limits(query_data, plan, profiles, streams, quality):
    q = query_data
    account = q.subscription(plan=plan)
    ids = [q.profile(account=account) for _ in range(profiles)]
    with pytest.raises(psycopg.errors.CheckViolation), q.db.transaction():
        q.profile(account=account)
    sessions = [q.db.execute("SELECT start_session(%s,%s)", (ids[0], f"device-{i}")).fetchone()[0] for i in range(streams)]
    with pytest.raises(psycopg.errors.CheckViolation), q.db.transaction():
        q.db.execute("SELECT start_session(%s,'one-too-many')", (ids[0],))
    movie = q.title("Quality selection")
    playback = q.db.execute("SELECT start_playback(%s,%s,NULL,'device-0')", (ids[0], movie)).fetchone()[0]
    assert (playback["is_placeholder"], playback["quality"], playback["runtime_sec"]) == (True, "SD", 600)
    assert q.db.execute("SELECT ended_at FROM stream_session WHERE session_id=%s", (sessions[0],)).fetchone()[0] == q.today
    for file_quality in ("SD", "HD", "4K"):
        q.db.execute("INSERT INTO media_asset(asset_kind,movie_id,provider,source_ref,quality,duration_sec) VALUES('full',%s,'file','fixture.mp4',%s,600)", (movie, file_quality))
    playback = q.db.execute("SELECT start_playback(%s,%s,NULL,'device-0')", (ids[0], movie)).fetchone()[0]
    assert playback["quality"] == quality and playback["is_placeholder"] is False
    assert q.db.execute("SELECT count(*) FROM stream_session WHERE ended_at IS NULL").fetchone()[0] == streams
    q.db.execute("SELECT end_playback(%s)", (playback["session_id"],))
    assert q.db.execute("SELECT count(*) FROM stream_session WHERE ended_at IS NULL").fetchone()[0] == streams - 1


@pytest.mark.parametrize("start,end", [(date(2024, 1, 31), date(2024, 2, 29)),
                                      (date(2025, 1, 31), date(2025, 2, 28)),
                                      (date(2026, 12, 31), date(2027, 1, 31))])
def test_subscription_starts_and_changes_call_hook_and_preserve_history(query_data, start, end):
    q = query_data
    q.db.execute("CREATE TEMP TABLE hook_calls(account_id INT,plan_id INT)")
    q.db.execute("CREATE OR REPLACE FUNCTION confirm_payment(a INT,p INT) RETURNS BOOLEAN LANGUAGE plpgsql AS $$ BEGIN INSERT INTO hook_calls VALUES(a,p); RETURN TRUE; END $$")
    account = q.account()
    plans = {r["name"]: r["plan_id"] for r in q.rows("SELECT name,plan_id FROM plan")}
    first = q.db.execute("SELECT subscribe(%s,%s,%s)", (account, plans["Basic"], start)).fetchone()[0]
    assert q.db.execute("SELECT end_date FROM subscription WHERE sub_id=%s", (first,)).fetchone()[0] == end
    changed = start + timedelta(days=1)
    second = q.db.execute("SELECT change_plan(%s,%s,%s)", (account, plans["Family"], changed)).fetchone()[0]
    assert q.db.execute("SELECT plan_id,start_date,status FROM subscription WHERE sub_id=%s", (first,)).fetchone() == (plans["Basic"], start, "cancelled")
    assert q.db.execute("SELECT plan_id,start_date,status FROM subscription WHERE sub_id=%s", (second,)).fetchone() == (plans["Family"], changed, "active")
    assert q.db.execute("SELECT account_id,plan_id FROM hook_calls ORDER BY plan_id").fetchall() == [(account, plans["Basic"]), (account, plans["Family"])]


def test_successful_renewal_retains_streams_and_repeat_run_is_noop(query_data):
    q = query_data
    pid = q.profile()
    session = q.db.execute("SELECT start_session(%s,'renewing-device')", (pid,)).fetchone()[0]
    q.db.execute("UPDATE subscription SET end_date=CURRENT_DATE")
    admin = q.db.execute("INSERT INTO admin_user(email,password_hash,full_name,role) VALUES('renew@test.example','fixture','Renew','billing') RETURNING admin_id").fetchone()[0]
    assert q.db.execute("SELECT process_renewals(%s,CURRENT_DATE)", (admin,)).fetchone()[0] == {"renewed_periods": 1, "expired": 0}
    assert q.db.execute("SELECT ended_at FROM stream_session WHERE session_id=%s", (session,)).fetchone()[0] is None
    assert q.db.execute("SELECT end_date>CURRENT_DATE FROM subscription").fetchone()[0] is True
    assert q.db.execute("SELECT process_renewals(%s,CURRENT_DATE)", (admin,)).fetchone()[0] == {"renewed_periods": 0, "expired": 0}


def test_failed_payment_hook_rolls_back_plan_change_and_stream_closure(query_data):
    q = query_data
    pid = q.profile()
    account = q.db.execute("SELECT account_id FROM profile WHERE profile_id=%s", (pid,)).fetchone()[0]
    session = q.db.execute("SELECT start_session(%s,'device')", (pid,)).fetchone()[0]
    before = q.rows("SELECT * FROM subscription WHERE account_id=%s", (account,))
    q.db.execute("CREATE OR REPLACE FUNCTION confirm_payment(a INT,p INT) RETURNS BOOLEAN LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Test hook failure' USING ERRCODE='23514'; END $$")
    with pytest.raises(psycopg.errors.CheckViolation, match="Test hook failure"), q.db.transaction():
        q.db.execute("SELECT change_plan(%s,(SELECT plan_id FROM plan WHERE name='Basic'))", (account,))
    assert q.rows("SELECT * FROM subscription WHERE account_id=%s", (account,)) == before
    assert q.db.execute("SELECT ended_at FROM stream_session WHERE session_id=%s", (session,)).fetchone()[0] is None


def test_trailer_discovery_creates_no_guest_account_history_or_device_slot(query_data, query_client, select_query_profile):
    q = query_data
    tid = q.title("Free trailer", description="Private long description " * 10)
    q.db.execute("INSERT INTO media_asset(asset_kind,title_id,provider,source_ref,duration_sec) VALUES('trailer',%s,'youtube','abcdefghijk',60)", (tid,))
    pid = q.profile(age=7)
    account = q.db.execute("SELECT account_id FROM profile WHERE profile_id=%s", (pid,)).fetchone()[0]
    before = q.db.execute("SELECT (SELECT count(*) FROM account),(SELECT count(*) FROM profile),(SELECT count(*) FROM watch_history),(SELECT count(*) FROM stream_session)").fetchone()
    for mode in ("guest", "account", "profile"):
        query_client.cookies.clear()
        if mode == "account":
            query_client.cookies.set(security.COOKIE, security.sign({"kind": "account", "id": account}))
        elif mode == "profile":
            select_query_profile(pid)
        response = query_client.get(f"/catalog/{tid}")
        assert response.status_code == 200
        assert (response.json()["trailer_provider"], response.json()["trailer_ref"]) == ("youtube", "abcdefghijk")
        if mode != "profile":
            assert response.json()["preview"] and "episodes" not in response.json()
            assert query_client.post("/playback/start", json={"movie_id": tid, "device": mode + "-device"}).status_code in (401, 403)
        assert q.db.execute("SELECT (SELECT count(*) FROM account),(SELECT count(*) FROM profile),(SELECT count(*) FROM watch_history),(SELECT count(*) FROM stream_session)").fetchone() == before


def test_resume_date_order_and_same_day_id_tie(query_data):
    q = query_data
    pid = q.profile()
    movie = q.title("Resume dates")
    q.watch(pid, movie=movie, progress=10)
    latest = q.watch(pid, movie=movie, progress=20)
    q.watch(pid, movie=movie, progress=30, day=-1)
    playback = q.db.execute("SELECT start_playback(%s,%s,NULL,'resume-device')", (pid, movie)).fetchone()[0]
    assert (playback["watch_id"], playback["progress_sec"]) == (latest, 20)


@pytest.mark.parametrize("rating", [0, 7, 13, 16, 18])
def test_each_age_boundary_allows_equal_and_rejects_higher(query_data, rating):
    q = query_data
    pid = q.profile(age=rating)
    movie = q.title("Exact age", age=rating)
    assert q.db.execute("SELECT start_playback(%s,%s,NULL,'age-device')", (pid, movie)).fetchone()[0]["movie_id"] == movie
    higher = next((n for n in [0, 7, 13, 16, 18] if n > rating), None)
    if higher is not None:
        blocked = q.title("Too old", age=higher)
        with pytest.raises(psycopg.errors.CheckViolation), q.db.transaction():
            q.db.execute("SELECT start_playback(%s,%s,NULL,'age-device')", (pid, blocked))
        assert q.db.execute("SELECT count(*) FROM stream_session WHERE ended_at IS NULL").fetchone()[0] == 1
