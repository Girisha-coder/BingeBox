"""Exact results, exclusions and ordering for discovery, views and reports."""

from datetime import timedelta
from decimal import Decimal

from app.queries import REPORTS, RECOMMEND, TOP_GENRE, UP_NEXT


def test_empty_discovery_and_reports(query_data):
    q = query_data
    pid = q.profile()
    assert q.rows(UP_NEXT, (pid, 18)) == []
    assert q.rows(RECOMMEND, (pid, 18)) == []
    assert q.rows(TOP_GENRE, (18,)) == []
    for report in ("lapsing", "binge", "rating-comparison"):
        assert q.rows(REPORTS[report]) == []


def test_up_next_season_gaps_latest_completion_profile_and_age(query_data):
    q = query_data
    viewer, other = q.profile(), q.profile()
    series = q.title("Season transitions", series=True, age=13)
    pilot, finale, next_season, end = [q.episode(series, s, e) for s, e in [(1, 1), (1, 3), (2, 1), (2, 2)]]
    q.watch(viewer, episode=pilot)
    q.watch(viewer, episode=finale)  # Same DATE: greater watch_id breaks the tie.
    q.watch(viewer, episode=end, progress=100)  # Incomplete attempts do not advance it.
    q.watch(other, episode=end)
    assert q.rows(UP_NEXT, (viewer, 18)) == [{
        "title_id": series, "name": "Season transitions", "episode_id": next_season,
        "episode_name": "Episode 2.1", "season_no": 2, "episode_no": 1,
    }]
    assert q.rows(UP_NEXT, (viewer, 7)) == []
    assert q.rows(UP_NEXT, (other, 18)) == []  # Completed final episode.
    q.watch(viewer, episode=end)
    assert q.rows(UP_NEXT, (viewer, 18)) == []


def test_up_next_orders_recent_activity_before_larger_ids(query_data):
    q = query_data
    pid = q.profile()
    recent = q.title("Recent series", series=True)
    older = q.title("Older series", series=True)
    first = q.episode(recent, 1, 1)
    recent_next = q.episode(recent, 1, 2)
    old_first = q.episode(older, 1, 1)
    old_next = q.episode(older, 1, 2)
    q.watch(pid, episode=first, day=0)
    q.watch(pid, episode=old_first, day=-1)  # A later insert is not later viewing.
    q.watch(pid, episode=recent_next, day=-2)
    assert [r["episode_id"] for r in q.rows(UP_NEXT, (pid, 18))] == [recent_next, old_next]


def test_top_genre_ties_nulls_age_limit_and_independent_partitions(query_data):
    q = query_data
    tie1 = q.title("First tie", rating=9, genres=("Drama", "Comedy"))
    tie2 = q.title("Second tie", rating=9, genres=("Drama",))
    rest = [q.title(f"Drama {i}", rating=8 - i / 10, genres=("Drama",)) for i in range(10)]
    unrated = q.title("Unrated", genres=("Comedy",))
    q.title("Adult maximum", age=18, rating=10, genres=("Drama", "Comedy"))
    rows = q.rows(TOP_GENRE, (7,))
    assert [(r["genre"], r["title_id"], r["rank"]) for r in rows] == [
        ("Comedy", tie1, 1), ("Comedy", unrated, 2),
        *[("Drama", tid, rank) for rank, tid in enumerate([tie1, tie2, *rest[:8]], 1)],
    ]
    assert rows[1]["imdb_rating"] is None
    assert rows[0]["genres"] == ["Comedy", "Drama"]


def test_recommendations_deduplicate_genres_exclude_watched_and_respect_age(query_data):
    q = query_data
    viewer, other = q.profile(), q.profile()
    watched = q.title("Watched film", genres=("Drama", "Comedy"))
    series = q.title("Watched series", series=True, genres=("Mystery", "Drama"))
    episode = q.episode(series, 1, 1)
    q.watch(viewer, movie=watched, progress=1)
    q.watch(viewer, movie=watched)  # Repeated history must not inflate shared_genres.
    q.watch(viewer, episode=episode, progress=1)
    both = q.title("Two shared", rating=5, genres=("Drama", "Mystery"))
    first = q.title("Tie first", rating=9, genres=("Comedy",))
    second = q.title("Tie second", rating=9, genres=("Drama",))
    unrated = q.title("Unrated match", genres=("Mystery",))
    q.watch(other, movie=first)  # Another profile's history cannot exclude it.
    q.title("No shared genre", rating=10, genres=("History",))
    q.title("Adult match", age=18, rating=10, genres=("Drama", "Mystery", "Comedy"))
    assert [(r["title_id"], r["shared_genres"]) for r in q.rows(RECOMMEND, (viewer, 7))] == [
        (both, 2), (first, 1), (second, 1), (unrated, 1),
    ]


def test_recommendations_limit_twelve_and_history_without_genres(query_data):
    q = query_data
    pid = q.profile()
    no_genre = q.title("No genres")
    q.watch(pid, movie=no_genre)
    assert q.rows(RECOMMEND, (pid, 18)) == []
    source = q.title("Source", genres=("Drama",))
    q.watch(pid, movie=source)
    ids = [q.title(f"Candidate {i}", rating=8, genres=("Drama",)) for i in range(14)]
    assert [r["title_id"] for r in q.rows(RECOMMEND, (pid, 18))] == ids[:12]


def test_continue_watching_latest_attempt_replay_completion_and_age(query_data):
    q = query_data
    pid, other = q.profile(), q.profile()
    movie = q.title("Resume movie")
    older = q.watch(pid, movie=movie, progress=100)
    latest = q.watch(pid, movie=movie, progress=200)
    q.watch(pid, movie=movie, progress=300, day=-1)
    q.watch(other, movie=movie, progress=400)
    read = lambda: q.rows("SELECT * FROM v_continue_watching WHERE profile_id=%s ORDER BY watch_id", (pid,))
    rows = read()
    assert [(r["watch_id"], r["progress_sec"], r["runtime_sec"]) for r in rows] == [(latest, 200, 600)]
    assert older != latest
    q.watch(pid, movie=movie)  # A completed latest attempt hides old unfinished attempts.
    assert read() == []
    q.watch(pid, movie=movie, progress=0)
    assert read() == []
    replay = q.watch(pid, movie=movie, progress=5)
    series = q.title("Episode resume", series=True, age=13)
    episode = q.episode(series, 2, 4)
    episode_watch = q.watch(pid, episode=episode, progress=120)
    assert [(r["watch_id"], r["title_id"], r["episode_name"]) for r in read()] == [
        (replay, movie, None), (episode_watch, series, "Episode 2.4"),
    ]
    q.db.execute("UPDATE profile SET max_age_rating=7,is_kids=TRUE WHERE profile_id=%s", (pid,))
    assert [r["watch_id"] for r in read()] == [replay]


def test_catalogue_view_aggregates_without_join_multiplication(query_data):
    q = query_data
    first, second = q.profile(), q.profile()
    tid = q.title("Rich series", series=True, genres=("Mystery", "Drama"), audio=("Hindi", "English"),
                  subtitles=("French", "English"), description="x" * 120, rating=8.1, votes=300)
    pilot = q.episode(tid, 1, 1, 10)
    q.episode(tid, 1, 2, 20)
    q.episode(tid, 2, 1, 30)
    for pid, rating in [(first, 7), (second, 8)]:
        q.watch(pid, episode=pilot)
        q.review(pid, tid, rating)
    for quality, reference in [("SD", "first-ref"), ("HD", "later-ref")]:
        q.db.execute("INSERT INTO media_asset(asset_kind,title_id,provider,source_ref,quality,duration_sec) VALUES('trailer',%s,'youtube',%s,%s,60)", (tid, reference, quality))
    row = q.rows("SELECT * FROM v_title_catalog WHERE title_id=%s", (tid,))[0]
    assert (row["runtime_min"], row["season_count"], row["episode_count"]) == (60, 2, 3)
    assert (row["review_count"], row["user_rating"]) == (2, Decimal("7.5"))
    assert row["genres"] == ["Drama", "Mystery"]
    assert row["audio_languages"] == ["English", "Hindi"]
    assert row["subtitle_languages"] == ["English", "French"]
    assert (row["trailer_ref"], row["trailer_provider"]) == ("first-ref", "youtube")
    guest = q.rows("SELECT * FROM v_guest_catalog WHERE title_id=%s", (tid,))[0]
    assert guest["teaser"] == "x" * 90
    assert set(guest) == {"title_id", "name", "release_year", "title_type", "genres", "audio_languages", "imdb_rating", "season_count", "teaser", "trailer_ref", "trailer_provider"}
    empty = q.title("Empty series", series=True)
    row = q.rows("SELECT * FROM v_title_catalog WHERE title_id=%s", (empty,))[0]
    assert (row["runtime_min"], row["season_count"], row["episode_count"], row["review_count"]) == (0, 0, 0, 0)
    assert row["genres"] == row["audio_languages"] == row["subtitle_languages"] == []
    assert row["user_rating"] is row["imdb_rating"] is row["trailer_ref"] is None


def test_active_subscriptions_date_status_boundaries_and_zero_plans(query_data):
    q = query_data
    q.subscription(start=0, end=1)
    q.subscription(start=-1, end=7)
    q.subscription(plan="Family", start=-1, end=1)
    for start, end, status in [(-1, 0, "active"), (-2, -1, "active"), (1, 7, "active"),
                               (-1, 1, "past_due"), (-1, 1, "expired"), (-1, 1, "cancelled")]:
        q.subscription(start=start, end=end, status=status)
    assert q.rows(REPORTS["active-subscriptions"]) == [
        {"name": "Student", "accounts": 0}, {"name": "Basic", "accounts": 2},
        {"name": "Duo", "accounts": 0}, {"name": "Premium", "accounts": 0},
        {"name": "Family", "accounts": 1},
    ]


def test_lapsing_window_boundaries_status_start_and_renewal_flag(query_data):
    q = query_data
    due = q.subscription(end=0, renew=False)
    edge = q.subscription(end=7, renew=True)
    tie = q.subscription(end=7, renew=False)
    for start, end, status in [(-10, -1, "active"), (-10, 8, "active"), (1, 7, "active"),
                               (-10, 2, "cancelled"), (-10, 2, "expired"), (-10, 2, "past_due")]:
        q.subscription(start=start, end=end, status=status)
    emails = {r["account_id"]: r["email"] for r in q.rows("SELECT account_id,email FROM account")}
    assert q.rows(REPORTS["lapsing"]) == [
        {"email": emails[due], "plan": "Basic", "end_date": q.today, "auto_renew": False},
        {"email": emails[edge], "plan": "Basic", "end_date": q.today + timedelta(days=7), "auto_renew": True},
        {"email": emails[tie], "plan": "Basic", "end_date": q.today + timedelta(days=7), "auto_renew": False},
    ]


def test_binge_report_counts_episode_attempts_per_profile_and_day(query_data):
    q = query_data
    pid, other = q.profile(), q.profile()
    series = q.title("Binge series", series=True)
    first, second = q.episode(series, 1, 1), q.episode(series, 1, 2)
    movie = q.title("Not an episode")
    q.watch(pid, episode=first)
    q.watch(pid, episode=first)  # Replays count as completed attempts by the documented metric.
    q.watch(pid, episode=second, progress=539)  # Below the 90% boundary.
    q.watch(pid, movie=movie)
    q.watch(pid, episode=first, day=-1)
    q.watch(pid, episode=second, day=-1, progress=540)
    q.watch(other, episode=first)
    assert [(r["profile_id"], r["last_watched_at"], r["completed_episodes"]) for r in q.rows(REPORTS["binge"])] == [
        (pid, q.today, 2), (pid, q.today - timedelta(days=1), 2), (other, q.today, 1),
    ]


def test_rating_comparison_exact_average_counts_order_and_null_imdb(query_data):
    q = query_data
    first, second = q.profile(), q.profile()
    one = q.title("Single review", rating=8.2, votes=900)
    two = q.title("Two reviews", rating=7.1, votes=20)
    no_imdb = q.title("Unknown IMDb")
    q.title("No reviews", rating=10)
    for pid, tid, rating in [(first, one, 4), (first, two, 7), (second, two, 8), (first, no_imdb, 9)]:
        q.watch(pid, movie=tid)
        q.review(pid, tid, rating)
    assert q.rows(REPORTS["rating-comparison"]) == [
        {"name": "Two reviews", "imdb_rating": Decimal("7.1"), "imdb_votes": 20, "user_rating": Decimal("7.5"), "review_count": 2},
        {"name": "Single review", "imdb_rating": Decimal("8.2"), "imdb_votes": 900, "user_rating": Decimal("4.0"), "review_count": 1},
        {"name": "Unknown IMDb", "imdb_rating": None, "imdb_votes": None, "user_rating": Decimal("9.0"), "review_count": 1},
    ]


def test_account_status_no_subscription_and_latest_period_counts(query_data):
    q = query_data
    empty = q.account()
    row = q.rows("SELECT * FROM v_account_status WHERE account_id=%s", (empty,))[0]
    assert (row["sub_id"], row["plan_name"], row["profile_count"], row["live_streams"]) == (None, None, 0, 0)
    pid = q.profile()
    account = q.rows("SELECT account_id FROM profile WHERE profile_id=%s", (pid,))[0]["account_id"]
    q.profile(account=account)
    q.db.execute("INSERT INTO stream_session(profile_id,device_type,device_name) VALUES(%s,'web','live')", (pid,))
    q.db.execute("INSERT INTO stream_session(profile_id,device_type,device_name,ended_at) VALUES(%s,'web','closed',CURRENT_DATE)", (pid,))
    q.db.execute("UPDATE subscription SET status='cancelled' WHERE account_id=%s", (account,))
    q.db.execute("INSERT INTO subscription(account_id,plan_id,start_date,end_date,status) SELECT %s,plan_id,CURRENT_DATE,CURRENT_DATE+5,'past_due' FROM plan WHERE name='Duo'", (account,))
    row = q.rows("SELECT * FROM v_account_status WHERE account_id=%s", (account,))[0]
    assert (row["plan_name"], row["status"], row["profile_count"], row["live_streams"]) == ("Duo", "past_due", 2, 1)
