"""Small real-PostgreSQL fixtures for result-level query assertions."""

from contextlib import contextmanager
from datetime import timedelta

from fastapi.testclient import TestClient
from psycopg.rows import dict_row
import pytest

from app import main, security


class QueryData:
    def __init__(self, db):
        self.db = db
        self.today = db.execute("SELECT CURRENT_DATE").fetchone()[0]
        self.serial = 0

    def rows(self, sql, params=()):
        with self.db.cursor(row_factory=dict_row) as cursor:
            return cursor.execute(sql, params).fetchall()

    def account(self):
        self.serial += 1
        return self.db.execute(
            "INSERT INTO account(email,password_hash) VALUES(%s,'fixture') RETURNING account_id",
            (f"query-{self.serial}@example.test",),
        ).fetchone()[0]

    def profile(self, age=18, account=None):
        if account is None:
            account = self.account()
            self.db.execute(
                "SELECT subscribe(%s,(SELECT plan_id FROM plan WHERE name='Family'))",
                (account,),
            )
        self.serial += 1
        return self.db.execute(
            "INSERT INTO profile(account_id,name,max_age_rating,is_kids) VALUES(%s,%s,%s,%s) RETURNING profile_id",
            (account, f"Viewer {self.serial}", age, age <= 7),
        ).fetchone()[0]

    def title(self, name, *, age=7, rating=None, runtime=10, series=False,
              genres=(), audio=(), subtitles=(), description=None, votes=None):
        tid = self.db.execute(
            """INSERT INTO title(name,release_year,description,age_rating,title_type,imdb_rating,imdb_votes)
               VALUES(%s,2026,%s,%s,%s,%s,%s) RETURNING title_id""",
            (name, description, age, "S" if series else "M", rating, votes),
        ).fetchone()[0]
        if series:
            self.db.execute("INSERT INTO series(title_id,series_status) VALUES(%s,'ongoing')", (tid,))
        else:
            self.db.execute("INSERT INTO movie(title_id,duration_min) VALUES(%s,%s)", (tid, runtime))
        for name in genres:
            gid = self.db.execute(
                "INSERT INTO genre(name) VALUES(%s) ON CONFLICT(name) DO UPDATE SET name=excluded.name RETURNING genre_id",
                (name,),
            ).fetchone()[0]
            self.db.execute("INSERT INTO title_genre VALUES(%s,%s)", (tid, gid))
        for language in audio:
            self.db.execute("INSERT INTO title_audio VALUES(%s,%s)", (tid, language))
        for language in subtitles:
            self.db.execute("INSERT INTO title_subtitle VALUES(%s,%s)", (tid, language))
        return tid

    def episode(self, series, season, number, runtime=10):
        return self.db.execute(
            "INSERT INTO episode(series_id,season_no,episode_no,name,duration_min) VALUES(%s,%s,%s,%s,%s) RETURNING episode_id",
            (series, season, number, f"Episode {season}.{number}", runtime),
        ).fetchone()[0]

    def watch(self, profile, *, movie=None, episode=None, progress=600, day=0):
        date = self.today + timedelta(days=day)
        return self.db.execute(
            "INSERT INTO watch_history(profile_id,movie_id,episode_id,progress_sec,started_at,last_watched_at) VALUES(%s,%s,%s,%s,%s,%s) RETURNING watch_id",
            (profile, movie, episode, progress, date, date),
        ).fetchone()[0]

    def review(self, profile, title, rating):
        self.db.execute("INSERT INTO title_review(profile_id,title_id,rating) VALUES(%s,%s,%s)", (profile, title, rating))

    def subscription(self, plan="Basic", start=-10, end=1, status="active", renew=True):
        account = self.account()
        self.db.execute(
            """INSERT INTO subscription(account_id,plan_id,start_date,end_date,status,auto_renew)
               SELECT %s,plan_id,%s,%s,%s,%s FROM plan WHERE name=%s""",
            (account, self.today + timedelta(days=start), self.today + timedelta(days=end), status, renew, plan),
        )
        return account


@pytest.fixture
def query_data(db):
    return QueryData(db)


@pytest.fixture
def query_client(query_data, monkeypatch):
    """Run real endpoint SQL in the fixture's rollback-only transaction.

    Only connection acquisition changes. No SQL, query results, authentication
    checks or request validation are mocked. Requests run sequentially.
    """
    db = query_data.db

    @contextmanager
    def connection():
        previous = db.row_factory
        db.row_factory = dict_row
        db.execute("SET LOCAL ROLE bingebox_app")
        try:
            yield db
        finally:
            db.execute("RESET ROLE")
            db.row_factory = previous

    monkeypatch.setattr(main, "connect", connection)
    monkeypatch.setenv("AUTH_SECRET", "query-tests-only-not-a-deployment-secret")
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def select_query_profile(query_data, query_client):
    def select(profile):
        account, kids = query_data.db.execute("SELECT account_id,is_kids FROM profile WHERE profile_id=%s", (profile,)).fetchone()
        query_client.cookies.set(security.COOKIE, security.sign({"kind": "account", "id": account, "profile_id": profile, "kids": kids}))
    return select
