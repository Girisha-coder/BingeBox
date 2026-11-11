"""HTTP workflows against PostgreSQL; each fixture removes only its own records."""

import uuid
import psycopg
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import main, security


@pytest.fixture
def journey(database_dsn, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", database_dsn)
    monkeypatch.setenv("AUTH_SECRET", "isolated-test-secret-not-for-deployment")
    monkeypatch.setattr(main, "MEDIA", tmp_path)
    tag = uuid.uuid4().hex[:10]
    password = "Test-password-2026!"
    with psycopg.connect(database_dsn) as c:
        admins = {
            role: c.execute(
                "INSERT INTO admin_user(email,password_hash,full_name,role) VALUES(%s,%s,%s,%s) RETURNING admin_id",
                (
                    role + tag + "@test.example",
                    security.hash_password(password),
                    role,
                    role,
                ),
            ).fetchone()[0]
            for role in ["catalogue", "billing", "super"]
        }
        title = c.execute(
            "INSERT INTO title(name,release_year,description,age_rating,title_type) VALUES(%s,2026,'An original one-minute demo story.',7,'M') RETURNING title_id",
            ("Journey " + tag,),
        ).fetchone()[0]
        c.execute("INSERT INTO movie(title_id,duration_min) VALUES(%s,1)", (title,))
        genre = c.execute("INSERT INTO genre(name) VALUES(%s) RETURNING genre_id", ("Journey " + tag,)).fetchone()[0]
        genre_name = "Journey " + tag
        c.execute("INSERT INTO title_genre VALUES(%s,%s)", (title, genre))
    client = TestClient(app)

    def login(role=None):
        email = (role + tag + "@test.example") if role else (tag + "@test.example")
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password, "staff": bool(role)},
        )
        assert response.status_code == 200, response.text

    response = client.post(
        "/auth/signup", json={"email": tag + "@test.example", "password": password}
    )
    assert response.status_code == 201
    account = client.get("/me").json()["account_id"]
    plans = {p["name"]: p["plan_id"] for p in client.get("/plans").json()}
    try:
        yield dict(
            client=client,
            login=login,
            password=password,
            account=account,
            admins=admins,
            title=title,
            plans=plans,
            genre=genre_name,
            dsn=database_dsn,
        )
    finally:
        client.close()
        with psycopg.connect(database_dsn) as c:
            c.execute("DELETE FROM account WHERE account_id=%s", (account,))
            c.execute("DELETE FROM movie WHERE title_id=%s", (title,))
            c.execute("DELETE FROM title WHERE title_id=%s", (title,))
            c.execute("DELETE FROM genre WHERE genre_id=%s", (genre,))
            c.execute(
                "DELETE FROM admin_user WHERE admin_id=ANY(%s)",
                (list(admins.values()),),
            )


def subscribe_profile(j, plan="Basic", kids=False):
    c = j["client"]
    assert (
        c.post("/account/subscribe", json={"plan_id": j["plans"][plan]}).status_code
        == 200
    )
    response = c.post(
        "/profiles",
        json={"name": "Viewer", "is_kids": kids, "max_age_rating": 7 if kids else 18},
    )
    assert response.status_code == 201, response.text
    pid = response.json()["profile_id"]
    assert c.post(f"/profiles/{pid}/select").status_code == 200
    return pid


def test_guest_preview_and_search_are_restricted(journey):
    j = journey
    c = j["client"]
    c.post("/auth/logout")
    detail = c.get("/catalog/" + str(j["title"])).json()
    assert detail["preview"] and len(detail["teaser"]) <= 90
    assert (
        not {"description", "runtime_min", "reviews", "episodes", "subtitle_languages"}
        & detail.keys()
    )
    result = c.get("/catalog", params={"q": "Journey"})
    assert result.status_code == 200
    assert any(t["title_id"] == j["title"] for t in result.json()["items"])
    assert (
        c.post(
            "/playback/start", json={"movie_id": j["title"], "device": "guest-device"}
        ).status_code
        == 401
    )
    assert c.get("/admin/accounts").status_code == 401


def test_assumption_a1_password_hashes_staff_namespace_and_no_guest_storage(journey):
    j, c = journey, journey["client"]
    with psycopg.connect(j["dsn"]) as db:
        account_email, account_hash = db.execute("SELECT email,password_hash FROM account WHERE account_id=%s", (j["account"],)).fetchone()
        staff_email, staff_hash = db.execute("SELECT email,password_hash FROM admin_user WHERE admin_id=%s", (j["admins"]["billing"],)).fetchone()
        before = db.execute("SELECT count(*) FROM account").fetchone()[0]
    for stored in (account_hash, staff_hash):
        assert stored.startswith("scrypt$") and stored != j["password"]
        assert security.verify_password(j["password"], stored)
        assert not security.verify_password("incorrect", stored)
    assert account_hash != staff_hash  # Same fixture password, separate random salts.
    c.post("/auth/logout")
    assert c.get("/me").json() == {"kind": "guest"}
    assert c.get("/catalog").status_code == c.get("/plans").status_code == 200
    assert c.post("/auth/login", json={"email": staff_email, "password": j["password"], "staff": False}).status_code == 401
    assert c.post("/auth/login", json={"email": account_email, "password": j["password"], "staff": True}).status_code == 401
    assert c.post("/auth/signup", json={"email": "not-provisioned@test.example", "password": j["password"], "staff": True}).status_code == 403
    with psycopg.connect(j["dsn"]) as db:
        assert db.execute("SELECT count(*) FROM account").fetchone()[0] == before


def test_staff_cannot_read_hashes_edit_history_reviews_or_extend_periods(journey):
    j, c = journey, journey["client"]
    subscribe_profile(j, "Family")
    with psycopg.connect(j["dsn"]) as db:
        before = db.execute("SELECT start_date,end_date,status FROM subscription WHERE account_id=%s", (j["account"],)).fetchall()
    for role in ("catalogue", "billing", "super"):
        j["login"](role)
        assert "password_hash" not in c.get("/me").text
        if role != "catalogue":
            assert "password_hash" not in c.get("/admin/accounts").text
        for resource in ("watch_history", "title_review", "episode_rating", "subscriptions", "admin_user"):
            url = "/admin/manage/" + resource
            assert c.get(url).status_code == 404
            assert c.post(url, json={"end_date": "2099-01-01"}).status_code == 404
        assert c.patch(f"/admin/accounts/{j['account']}", json={"end_date": "2099-01-01"}).status_code == 404
    with psycopg.connect(j["dsn"]) as db:
        assert db.execute("SELECT start_date,end_date,status FROM subscription WHERE account_id=%s", (j["account"],)).fetchall() == before


def test_stop_still_releases_slot_after_unprocessed_period_expiry(journey):
    j = journey
    c = j["client"]
    subscribe_profile(j)
    p = c.post(
        "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
    ).json()
    with psycopg.connect(j["dsn"]) as db:
        db.execute(
            "UPDATE subscription SET end_date=CURRENT_DATE WHERE account_id=%s",
            (j["account"],),
        )
    assert (
        c.post(
            "/playback/progress", json={"token": p["token"], "position": 30}
        ).status_code
        == 403
    )
    assert (
        c.post("/playback/stop", json={"token": p["token"], "position": 30}).status_code
        == 200
    )
    assert c.get("/account").json()["live_streams"] == 0


def test_watch_save_resume_range_and_review(journey):
    j = journey
    c = j["client"]
    subscribe_profile(j)
    assert c.put(f"/catalog/{j['title']}/review", json={"rating": 8}).status_code == 400
    first = c.post(
        "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
    )
    assert first.status_code == 200, first.text
    p = first.json()
    assert p["quality"] == "SD" and p["runtime_sec"] == 60 and p["is_placeholder"]
    media = c.get(p["media_url"].removeprefix("/api"), headers={"Range": "bytes=0-99"})
    assert (
        media.status_code == 206
        and len(media.content) == 100
        and media.headers["content-range"].startswith("bytes 0-99/")
    )
    assert (
        c.post(
            "/playback/progress", json={"token": p["token"], "position": 61}
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/playback/progress", json={"token": p["token"], "position": 27}
        ).status_code
        == 200
    )
    blocked = c.post(
        "/playback/start", json={"movie_id": j["title"], "device": "browser-two"}
    )
    assert blocked.status_code == 400
    c.post("/playback/stop", json={"token": p["token"], "position": 28})
    assert c.get(p["media_url"].removeprefix("/api")).status_code == 403
    resumed = c.post(
        "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
    ).json()
    assert resumed["watch_id"] == p["watch_id"] and resumed["progress_sec"] == 28
    assert c.post(
        "/playback/progress", json={"token": resumed["token"], "position": 54}
    ).json()["completed"]
    assert (
        c.put(
            f"/catalog/{j['title']}/review",
            json={"rating": 9, "review_text": "A good demonstration."},
        ).status_code
        == 200
    )
    assert (
        c.put(
            f"/catalog/{j['title']}/review",
            json={"rating": 8, "review_text": "Updated review."},
        ).status_code
        == 200
    )
    assert c.get("/home").status_code == 200
    assert c.delete(f"/catalog/{j['title']}/review").status_code == 200
    assert c.post("/playback/stop", json={"token": resumed["token"]}).status_code == 200
    assert c.post("/playback/stop", json={"token": resumed["token"]}).status_code == 200


def test_ownership_cookie_tampering_and_origin(journey):
    j = journey
    c = j["client"]
    subscribe_profile(j, "Family")
    assert c.post("/profiles/999999/select").status_code == 404
    assert (
        c.patch(
            "/profiles/999999", json={"name": "Other", "max_age_rating": 18}
        ).status_code
        == 404
    )
    assert c.delete("/profiles/999999").status_code == 404
    assert c.delete("/account/sessions/999999").status_code == 404
    assert (
        c.post(
            "/auth/logout", headers={"Origin": "https://untrusted.example"}
        ).status_code
        == 403
    )
    assert c.get("/me").json()["kind"] == "account"
    token = c.cookies.get(security.COOKIE)
    c.cookies.clear()
    c.cookies.set(security.COOKIE, token[:-1] + ("0" if token[-1] != "0" else "1"))
    assert c.get("/me").status_code == 401


def test_kids_unlock_and_direct_url_age(journey):
    j = journey
    c = j["client"]
    pid = subscribe_profile(j, "Family", True)
    for endpoint in ["/profiles", "/account"]:
        assert c.get(endpoint).status_code == 403
    assert c.post(f"/profiles/{pid}/select").status_code == 403
    with psycopg.connect(j["dsn"]) as db:
        db.execute("UPDATE title SET age_rating=18 WHERE title_id=%s", (j["title"],))
    assert c.get("/catalog/" + str(j["title"])).status_code == 404
    assert (
        c.post(
            "/playback/start", json={"movie_id": j["title"], "device": "kids-device"}
        ).status_code
        == 400
    )
    assert c.post("/account/unlock", json={"password": "wrong"}).status_code == 401
    assert (
        c.post("/account/unlock", json={"password": j["password"]}).status_code == 200
    )
    assert c.get("/profiles").status_code == 200


def test_role_gates_and_staff_catalogue_crud(journey):
    j = journey
    c = j["client"]
    j["login"]("billing")
    assert c.get("/admin/manage/titles").status_code == 403
    assert c.get("/admin/accounts").status_code == 200
    for name in ["active-subscriptions", "lapsing", "binge", "rating-comparison"]:
        assert c.get("/admin/reports/" + name).status_code == 200
    j["login"]("catalogue")
    assert c.get("/admin/accounts").status_code == 403
    assert c.get("/admin/manage/plans").status_code == 403
    assert (
        c.post("/admin/accounts/" + str(j["account"]) + "/suspend").status_code == 403
    )
    assert (
        c.post(
            "/admin/manage/titles",
            json={
                "name": "Missing subtype",
                "genres": [j["genre"]],
                "release_year": 2026,
                "age_rating": 0,
                "title_type": "M",
            },
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/admin/manage/titles",
            json={
                "name": "Invalid runtime",
                "genres": [j["genre"]],
                "release_year": 2026,
                "age_rating": 0,
                "title_type": "M",
                "duration_min": "bad",
            },
        ).status_code
        == 400
    )
    missing_genre = c.post("/admin/manage/titles", json={"name": "Unclassified", "release_year": 2026, "age_rating": 0, "title_type": "M", "duration_min": 2})
    assert missing_genre.status_code == 400
    assert "genre" in missing_genre.json()["detail"]
    r = c.post(
        "/admin/manage/titles",
        json={
            "name": "CRUD story",
            "genres": [j["genre"]],
            "release_year": 2026,
            "age_rating": 0,
            "title_type": "M",
            "duration_min": 2,
            "audio_languages": ["Hindi"],
            "subtitle_languages": ["English"],
        },
    )
    assert r.status_code == 201, r.text
    mid = r.json()["title_id"]
    try:
        refused = c.patch(f"/admin/manage/titles/{mid}", json={"name": "Should roll back", "genres": []})
        assert refused.status_code == 400
        with psycopg.connect(j["dsn"]) as db:
            assert db.execute("SELECT name FROM title WHERE title_id=%s", (mid,)).fetchone()[0] == "CRUD story"
        assert (
            c.patch(
                f"/admin/manage/titles/{mid}",
                json={"name": "CRUD updated", "duration_min": 3},
            ).status_code
            == 200
        )
        r = c.post(
            "/admin/manage/videos",
            json={
                "asset_kind": "trailer",
                "title_id": mid,
                "provider": "youtube",
                "source_ref": "abcdefghijk",
                "quality": "HD",
                "duration_sec": 60,
            },
        )
        assert r.status_code == 201, r.text
        assert c.get("/catalog/" + str(mid)).json()["trailer_ref"] == "abcdefghijk"
        assert (
            c.delete("/admin/manage/videos/" + str(r.json()["asset_id"])).status_code
            == 200
        )
    finally:
        assert c.delete("/admin/manage/titles/" + str(mid)).status_code == 200
    j["login"]("super")
    assert c.get("/admin/manage/plans").status_code == 200


def test_subscriptions_profiles_and_admin_suspension(journey):
    j = journey
    c = j["client"]
    pid = subscribe_profile(j, "Duo")
    second = c.post("/profiles", json={"name": "Second", "max_age_rating": 18}).json()[
        "profile_id"
    ]
    assert (
        c.post("/profiles", json={"name": "Third", "max_age_rating": 18}).status_code
        == 400
    )
    assert (
        c.post(
            "/account/change-plan", json={"plan_id": j["plans"]["Basic"]}
        ).status_code
        == 400
    )
    assert c.patch("/account/auto-renew", json={"enabled": False}).status_code == 200
    assert c.get("/account").json()["auto_renew"] is False
    assert c.delete("/profiles/" + str(second)).status_code == 200
    assert (
        c.post(
            "/account/change-plan", json={"plan_id": j["plans"]["Basic"]}
        ).status_code
        == 200
    )
    p = c.post(
        "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
    ).json()
    j["login"]("billing")
    assert (
        c.post("/admin/accounts/" + str(j["account"]) + "/suspend").status_code == 200
    )
    j["login"]()
    c.post(f"/profiles/{pid}/select")
    assert c.get(p["media_url"].removeprefix("/api")).status_code == 403
    assert (
        c.post(
            "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
        ).status_code
        == 400
    )
    j["login"]("billing")
    assert (
        c.post("/admin/accounts/" + str(j["account"]) + "/reinstate").status_code == 200
    )
    j["login"]()
    c.post(f"/profiles/{pid}/select")
    assert (
        c.post(
            "/playback/start", json={"movie_id": j["title"], "device": "browser-one"}
        ).status_code
        == 200
    )
