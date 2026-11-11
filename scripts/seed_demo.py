"""Insert a coherent 200-row fictional demo snapshot, without replacing data.

Run in gpu_env after Docker startup. Existing demo snapshots are validated and
retained; any other nonempty database is refused. No media files are fabricated.
"""

import argparse
import calendar
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import secrets
from urllib.parse import quote

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
DEMO_PASSWORD = "BingeBox-Demo-2026!"
EXPECTED_COUNTS = {
    "plan": 5, "admin_user": 3, "account": 12, "subscription": 16,
    "profile": 18, "stream_session": 8, "title": 12, "movie": 9,
    "series": 3, "episode": 12, "genre": 6, "title_genre": 18,
    "title_audio": 15, "title_subtitle": 10, "media_asset": 21,
    "watch_history": 23, "title_review": 6, "episode_rating": 3,
}
PEOPLE = [
    ("aarav.sharma", "Student", ["Aarav"]),
    ("meera.iyer", "Basic", ["Meera"]),
    ("kabir.malhotra", "Duo", ["Kabir", "Ananya"]),
    ("isha.nair", "Premium", ["Isha"]),
    ("rohan.desai", "Family", ["Rohan", "Kavya", "Tara", "Vihaan"]),
    ("ananya.sen", "Basic", ["Ananya"]),
    ("vikram.rao", "Duo", ["Vikram", "Nisha"]),
    ("neha.kapoor", "Family", ["Neha", "Arya"]),
    ("aditya.bose", "Student", ["Aditya"]),
    ("sana.khan", "Premium", ["Sana"]),
    ("dev.menon", "Basic", ["Dev"]),
    ("farah.ali", "Duo", ["Farah"]),
]
ADMIN_EMAILS = {"catalogue@staff.bingebox.example", "billing@staff.bingebox.example", "super@staff.bingebox.example"}
TITLES = [
    # Name, year, age, runtime (None for series), language, mock IMDb rating/votes, genre, description.
    ("The Last Local", 2024, 13, 118, "Hindi", "7.4", 18420, "Drama",
     "A night-shift nurse and a railway clerk search for a missing passenger before the last suburban train leaves."),
    ("Monsoon Letters", 2022, 7, 104, "Hindi", "8.1", 42600, "Drama",
     "A schoolteacher returns to her coastal hometown and follows a trail of letters that her mother never posted."),
    ("Borrowed Sundays", 2023, 0, 96, "English", "6.8", 3100, "Comedy",
     "Three neighbours share a broken-down food truck for a month and discover that their weekend plans rarely agree."),
    ("North of the Orchard", 2021, 13, 143, "Tamil", "8.6", 9200, "Mystery",
     "An orchard keeper investigates the sale of her family's land while an unseasonal frost approaches."),
    ("Paper Lanterns", 2025, 7, 82, "English", "8.9", 1280, "Animation",
     "Two siblings build a lantern that carries forgotten wishes across their town during a summer festival."),
    ("Saltwater Mile", 2020, 13, 111, "Malayalam", "7.2", 21800, "Drama",
     "A retired swimmer trains a fishing crew for a community relay while negotiating a difficult return home."),
    ("A Minute of Rain", 2026, 0, 1, "Bengali", "6.1", 42, "Documentary",
     "A one-minute observational film records the first rainfall over a busy market. Short-form runtime boundary case."),
    ("The Long Winter Archive", 2019, 16, 600, "English", "8.0", 180, "Documentary",
     "A ten-hour experimental archive follows a remote weather station through one winter. Deliberately rare long-form outlier."),
    ("Midnight Signal", 2024, 18, 127, "Marathi", "2.3", 6400, "Thriller",
     "A radio host traces an anonymous caller through an industrial district. This fictional title supplies a low-rating outlier."),
    ("Platform Nine", 2025, 13, None, "Hindi", "8.4", 12000, "Mystery",
     "A railway investigator follows small disappearances that connect commuters across two seasons."),
    ("The Mango House", 2023, 7, None, "Tamil", "7.8", 4200, "Comedy",
     "Three generations try to save their shared house by turning its courtyard into a neighbourhood cafe."),
    ("After the Flood", 2026, 16, None, "English", "9.7", 18, "Documentary",
     "A documentary series follows community rebuilding, including a brief field note and an extended testimony episode. High score, very small sample."),
]


def local_dsn():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return ("postgresql://bingebox:" + quote(values["POSTGRES_PASSWORD"], safe="")
            + f"@127.0.0.1:{int(values.get('DB_PORT', '15432'))}/bingebox")


def password_hash():
    # Separate random salt per fictional login. Public demo password, never production credentials.
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(DEMO_PASSWORD.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def shift_month(value, offset):
    year, month_zero = divmod(value.year * 12 + value.month - 1 + offset, 12)
    month = month_zero + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def insert(connection, table, **values):
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, values)),
        sql.SQL(", ").join(sql.Placeholder() for _ in values),
    )
    cursor = connection.execute(statement, list(values.values()))
    return dict(zip((column.name for column in cursor.description), cursor.fetchone()))


def counts(connection):
    return {table: connection.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
            for table in EXPECTED_COUNTS}


def validate(connection, as_of, allow_catalog_additions=False):
    actual = counts(connection)
    extensible = {"title", "movie", "genre", "title_genre"} if allow_catalog_additions else set()
    if any(actual[table] < value if table in extensible else actual[table] != value
           for table, value in EXPECTED_COUNTS.items()) or sum(actual.values()) > 1000:
        raise ValueError(f"Unexpected row distribution: {actual}")
    # Force transaction-end subtype checks before reporting success.
    connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
    violations = {}
    checks = {
        "profiles_over_plan_limit": """
            SELECT count(*) FROM (
                SELECT a.account_id FROM account a
                JOIN LATERAL (SELECT plan_id FROM subscription WHERE account_id = a.account_id
                              ORDER BY start_date DESC, sub_id DESC LIMIT 1) s ON TRUE
                JOIN plan p USING (plan_id) JOIN profile pr USING (account_id)
                GROUP BY a.account_id, p.max_profiles HAVING count(*) > p.max_profiles
            ) invalid""",
        "ineligible_live_sessions": """
            SELECT count(*) FROM stream_session ss JOIN profile pr USING (profile_id)
            JOIN account a USING (account_id)
            WHERE ss.ended_at IS NULL AND (a.suspended_at IS NOT NULL OR NOT EXISTS (
                SELECT 1 FROM subscription s WHERE s.account_id = a.account_id AND s.status = 'active'
                AND s.start_date <= %(as_of)s AND s.end_date > %(as_of)s))""",
        "too_many_live_sessions": """
            SELECT count(*) FROM (
                SELECT a.account_id FROM stream_session ss JOIN profile pr USING (profile_id)
                JOIN account a USING (account_id) JOIN subscription s USING (account_id)
                JOIN plan p USING (plan_id) WHERE ss.ended_at IS NULL AND s.status = 'active'
                GROUP BY a.account_id, p.max_streams HAVING count(*) > p.max_streams
            ) invalid""",
        "invalid_watch_progress": """
            SELECT count(*) FROM watch_history w LEFT JOIN movie m ON m.title_id = w.movie_id
            LEFT JOIN episode e USING (episode_id)
            WHERE w.progress_sec > coalesce(m.duration_min, e.duration_min) * 60
               OR w.completed <> (w.progress_sec * 10 >= coalesce(m.duration_min, e.duration_min) * 60 * 9)
               OR w.last_watched_at < w.started_at OR w.last_watched_at > %(as_of)s""",
        "age_restricted_watches": """
            SELECT count(*) FROM watch_history w JOIN profile p USING (profile_id)
            LEFT JOIN episode e USING (episode_id)
            JOIN title t ON t.title_id = coalesce(w.movie_id, e.series_id)
            WHERE t.age_rating > p.max_age_rating""",
        "watch_outside_subscription_period": """
            SELECT count(*) FROM watch_history w JOIN profile p USING (profile_id)
            WHERE NOT EXISTS (SELECT 1 FROM subscription s WHERE s.account_id = p.account_id
                AND s.start_date <= w.last_watched_at AND s.end_date > w.last_watched_at)""",
        "watch_after_suspension": """
            SELECT count(*) FROM watch_history w JOIN profile p USING (profile_id)
            JOIN account a USING (account_id) WHERE a.suspended_at IS NOT NULL
            AND w.last_watched_at >= a.suspended_at""",
        "invalid_asset_runtime": """
            SELECT count(*) FROM media_asset a LEFT JOIN movie m ON m.title_id = a.movie_id
            LEFT JOIN episode e USING (episode_id) WHERE a.asset_kind = 'full'
            AND (a.duration_sec <> coalesce(m.duration_min, e.duration_min) * 60
                 OR NOT a.is_placeholder OR a.quality <> 'SD' OR a.provider <> 'file')""",
        "unwatched_title_reviews": """
            SELECT count(*) FROM title_review r WHERE NOT EXISTS (
                SELECT 1 FROM watch_history w LEFT JOIN episode e USING (episode_id)
                WHERE w.profile_id = r.profile_id AND w.completed
                AND coalesce(w.movie_id, e.series_id) = r.title_id
                AND w.last_watched_at <= r.created_at)""",
        "unwatched_episode_ratings": """
            SELECT count(*) FROM episode_rating r WHERE NOT EXISTS (
                SELECT 1 FROM watch_history w WHERE w.profile_id = r.profile_id
                AND w.episode_id = r.episode_id AND w.completed AND w.last_watched_at <= r.rated_at)""",
        "invalid_signup_dates": """
            SELECT count(*) FROM account a JOIN subscription s USING (account_id)
            WHERE s.start_date < a.created_at OR a.created_at > %(as_of)s""",
    }
    for name, query in checks.items():
        result = connection.execute(query, {"as_of": as_of}).fetchone()[0]
        if result:
            violations[name] = result
    if violations:
        raise ValueError(f"Mock-data consistency checks failed: {violations}")
    return {"total_rows": sum(actual.values()), "tables": actual, "as_of": as_of.isoformat(),
            "consistency_checks_passed": len(checks)}


def seed_demo(connection, as_of):
    # Serialise competing seed runs. All writes and checks share the caller's transaction.
    connection.execute("SELECT pg_advisory_xact_lock(200, 2026)")
    existing = counts(connection)
    if any(value for table, value in existing.items() if table != "plan"):
        expected_accounts = {person[0] + "@bingebox.example" for person in PEOPLE}
        actual_accounts = {row[0] for row in connection.execute("SELECT email FROM account")}
        actual_admins = {row[0] for row in connection.execute("SELECT email FROM admin_user")}
        actual_titles = {row[0] for row in connection.execute("SELECT name FROM title")}
        if (actual_accounts != expected_accounts or actual_admins != ADMIN_EMAILS
                or not {title[0] for title in TITLES}.issubset(actual_titles)):
            raise ValueError("Database already contains other data. Nothing was replaced or deleted.")
        # Recover the original snapshot date; later reruns must not age/overwrite it.
        original_date = connection.execute("SELECT max(last_watched_at) FROM watch_history").fetchone()[0]
        report = validate(connection, original_date, allow_catalog_additions=True)
        return {**report, "action": "existing demo retained"}
    expected_plans = [("Student", 99, 1, 1, "HD"), ("Basic", 199, 1, 1, "HD"),
                      ("Duo", 349, 2, 2, "HD"), ("Premium", 499, 1, 3, "4K"),
                      ("Family", 649, 4, 4, "4K")]
    plans = connection.execute("SELECT name, monthly_price, max_profiles, max_streams, max_quality FROM plan ORDER BY monthly_price").fetchall()
    if plans != expected_plans:
        raise ValueError("Seed the five unchanged source plans first. Existing plans were not modified.")
    plan_ids = dict(connection.execute("SELECT name, plan_id FROM plan"))
    admins = {}
    for role, name in [("catalogue", "Priya Sethi"), ("billing", "Arjun Kulkarni"), ("super", "Leena Thomas")]:
        admins[role] = insert(connection, "admin_user", email=f"{role}@staff.bingebox.example",
                              password_hash=password_hash(), full_name=name, role=role,
                              created_at=as_of - timedelta(days=400))["admin_id"]
    accounts, profiles, starts, ends = [], [], [], []
    for index, (handle, plan_name, names) in enumerate(PEOPLE):
        suspended = index == 6
        account = insert(connection, "account", email=handle + "@bingebox.example",
                         password_hash=password_hash(), phone=None,
                         created_at=as_of - timedelta(days=1 if index == 10 else 120 + index * 17),
                         suspended_at=as_of - timedelta(days=3) if suspended else None,
                         suspended_by_admin=admins["billing"] if suspended else None)["account_id"]
        accounts.append(account)
        start = as_of - timedelta(days=1 if index == 10 else (45 if index == 11 else (32 if index in (5, 8) else 20)))
        end = shift_month(start, 1)
        if index == 1:
            end = as_of + timedelta(days=1)
            start = shift_month(end, -1)
        starts.append(start)
        ends.append(end)
        status = "cancelled" if index == 11 else ("expired" if index in (5, 8) else "active")
        insert(connection, "subscription", account_id=account, plan_id=plan_ids[plan_name],
               start_date=start, end_date=end, status=status, auto_renew=index not in (1, 5, 8, 9, 11))
        for name in names:
            is_kids = name in ("Tara", "Vihaan", "Arya")
            profiles.append(insert(connection, "profile", account_id=account, name=name, is_kids=is_kids,
                                   max_age_rating=7 if is_kids else (13 if name == "Nisha" else 18),
                                   created_at=start)["profile_id"])
    for account_index, old_plan, status in [(1, "Student", "cancelled"), (2, "Basic", "expired"),
                                            (4, "Premium", "cancelled"), (9, "Family", "expired")]:
        insert(connection, "subscription", account_id=accounts[account_index], plan_id=plan_ids[old_plan],
               start_date=shift_month(starts[account_index], -1), end_date=starts[account_index],
               status=status, auto_renew=False)

    for profile_index, device, label, start_days, end_days in [
        (1, "web", "Meera - Chrome laptop", 0, None),
        (2, "mobile", "Kabir - Android phone", 0, None),
        (3, "tv", "Ananya - Living room TV", 0, None),
        (4, "tv", "Isha - Bedroom TV", 0, None),
        (4, "web", "Isha - Laptop browser", 0, None),
        (5, "tv", "Desai family - Living room", 0, None),
        (9, "tablet", "Ananya - Tablet", 5, 2),
        (10, "web", "Vikram - Desktop browser", 4, 3),
    ]:
        # Source schema lacks separate token/display columns. Store stable demo tokens.
        token = hashlib.sha256(label.encode()).hexdigest()[:32]
        insert(connection, "stream_session", profile_id=profiles[profile_index], device_type=device,
               device_name=token, started_at=as_of - timedelta(days=start_days),
               ended_at=None if end_days is None else as_of - timedelta(days=end_days))

    genre_ids = {name: insert(connection, "genre", name=name)["genre_id"]
                 for name in ("Drama", "Thriller", "Comedy", "Documentary", "Animation", "Mystery")}
    title_ids = []
    runtimes = {}
    for index, (name, year, age, duration, language, rating, votes, genre, description) in enumerate(TITLES):
        title_id = insert(connection, "title", name=name, release_year=year, age_rating=age,
                          description=description, original_language=language, imdb_id=None,
                          imdb_rating=rating, imdb_votes=votes, title_type="M" if duration else "S")["title_id"]
        title_ids.append(title_id)
        if duration:
            insert(connection, "movie", title_id=title_id, duration_min=duration)
            runtimes[("movie", index)] = duration * 60
        else:
            insert(connection, "series", title_id=title_id, series_status="ended" if index == 10 else "ongoing")
        insert(connection, "title_genre", title_id=title_id, genre_id=genre_ids[genre])
        insert(connection, "title_audio", title_id=title_id, language=language)
    for index, genre in [(0, "Thriller"), (1, "Mystery"), (2, "Drama"), (4, "Comedy"), (9, "Drama"), (10, "Drama")]:
        insert(connection, "title_genre", title_id=title_ids[index], genre_id=genre_ids[genre])
    for index, language in [(1, "English"), (4, "Hindi"), (10, "Hindi")]:
        insert(connection, "title_audio", title_id=title_ids[index], language=language)
    for index in (0, 1, 2, 3, 4, 5, 7, 8, 9, 11):
        insert(connection, "title_subtitle", title_id=title_ids[index], language="English" if TITLES[index][4] != "English" else "Hindi")

    episodes = {}
    episode_specs = {
        9: [(1, 1, "The Missing Ticket", 42), (1, 2, "Lost Property", 45),
            (2, 1, "A Different Timetable", 43), (2, 2, "Last Connection", 49)],
        10: [(1, 1, "Grandmother's Recipe", 22), (1, 2, "The Broken Sign", 24),
             (1, 3, "Sunday Rush", 23), (1, 4, "A Table for Everyone", 26)],
        11: [(1, 1, "The Waterline", 55), (1, 2, "Starting Again", 61),
             (1, 3, "Field Note: One Minute", 1), (1, 4, "Community Testimony: Extended Cut", 300)],
    }
    for title_index, rows in episode_specs.items():
        for index, (season, number, name, duration) in enumerate(rows):
            episode_id = insert(connection, "episode", series_id=title_ids[title_index], season_no=season,
                                episode_no=number, name=name, duration_min=duration,
                                imdb_rating=str(7.0 + ((title_index + index) % 6) * 0.4),
                                air_date=as_of - timedelta(days=60 - index * 7))["episode_id"]
            episodes[(title_index, index)] = episode_id
            runtimes[("episode", (title_index, index))] = duration * 60

    for index in range(9):
        slug = TITLES[index][0].lower().replace(" ", "-")
        insert(connection, "media_asset", asset_kind="full", movie_id=title_ids[index], provider="file",
               source_ref=f"mock/{slug}.mp4", quality="SD", duration_sec=runtimes[("movie", index)],
               is_placeholder=True, created_at=as_of - timedelta(days=90))
    for key, episode_id in episodes.items():
        series_index, episode_index = key
        season, number, *_ = episode_specs[series_index][episode_index]
        slug = TITLES[series_index][0].lower().replace(" ", "-")
        insert(connection, "media_asset", asset_kind="full", episode_id=episode_id, provider="file",
               source_ref=f"mock/{slug}/s{season:02}e{number:02}.mp4", quality="SD",
               duration_sec=runtimes[("episode", key)], is_placeholder=True,
               created_at=as_of - timedelta(days=60 - episode_index * 7))

    # Profile indices follow PEOPLE order. Ratios deliberately include 0%, 90%, 100%,
    # exactly one second below 90%, rewatches and a nearly completed attempt.
    watches = [
        (0, "movie", 0, 1, 2), (1, "movie", 1, .9, 1),
        (2, "movie", 3, 1, 3), (3, "movie", 2, 1, 4),
        (4, "movie", 7, .1, 0), (5, "movie", 8, 1, 2),
        (6, "movie", 4, 1, 3), (7, "movie", 4, .5, 0),
        (8, "movie", 6, 1, 0), (9, "movie", 1, .95, 5),
        (10, "movie", 5, .4, 4), (11, "episode", (9, 0), 1, 5),
        (12, "episode", (11, 0), 1, 3), (13, "episode", (10, 0), .9, 1),
        (14, "episode", (9, 1), .3, 5), (15, "episode", (11, 3), .02, 1),
        (16, "movie", 2, 0, 0), (17, "movie", 5, 1, 16),
        (0, "movie", 0, .25, 0), (1, "movie", 1, "below90", 0),
        (2, "episode", (9, 0), 1, 2), (5, "episode", (11, 2), 1, 1),
        (4, "movie", 8, .995, 0),
    ]
    for profile_index, kind, target, ratio, days_ago in watches:
        runtime = runtimes[(kind, target)]
        progress = runtime * 9 // 10 - 1 if ratio == "below90" else round(runtime * ratio)
        watched_at = as_of - timedelta(days=days_ago)
        insert(connection, "watch_history", profile_id=profiles[profile_index],
               movie_id=title_ids[target] if kind == "movie" else None,
               episode_id=episodes[target] if kind == "episode" else None,
               started_at=watched_at, last_watched_at=watched_at, progress_sec=progress,
               completed=progress * 10 >= runtime * 9)
    reviews = [
        (0, 0, 8, "The station scenes felt lived-in, and the final conversation stayed with me."),
        (1, 1, 9, "Patient storytelling and a lovely sense of place. The letters tie together well."),
        (3, 2, 6, "Warm performances, though the middle section repeats the same joke a little too often."),
        (5, 8, 1, "The sound design promised a lot, but the plot lost its own rules by the last act."),
        (6, 4, 10, "Inventive animation and a story the whole family wanted to talk about afterwards."),
        (12, 11, 9, "The first episode gives residents time to speak. Looking forward to the rest of the series."),
    ]
    for profile_index, title_index, rating, review in reviews:
        insert(connection, "title_review", profile_id=profiles[profile_index], title_id=title_ids[title_index],
               rating=rating, review_text=review, created_at=as_of, updated_at=as_of)
    for profile_index, key, rating in [(11, (9, 0), 8), (12, (11, 0), 9), (13, (10, 0), 7)]:
        insert(connection, "episode_rating", profile_id=profiles[profile_index], episode_id=episodes[key],
               rating=rating, rated_at=as_of)
    return {**validate(connection, as_of), "action": "inserted 195 fictional rows alongside 5 existing plans"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--check-only", action="store_true")
    arguments = parser.parse_args()
    try:
        with psycopg.connect(local_dsn(), connect_timeout=5) as connection:
            if arguments.check_only:
                snapshot = connection.execute("SELECT max(last_watched_at) FROM watch_history").fetchone()[0]
                if snapshot is None:
                    raise ValueError("No mock snapshot found.")
                report = {**validate(connection, snapshot, allow_catalog_additions=True), "action": "validated existing snapshot"}
            else:
                report = seed_demo(connection, arguments.as_of)
        print(json.dumps(report, indent=2))
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error)) from None
    except psycopg.Error as error:
        # SQLSTATE is sufficient for diagnostics; avoid rendering DSNs/passwords.
        raise SystemExit(f"Database operation failed ({error.sqlstate or 'connection error'}). Transaction rolled back.") from None


if __name__ == "__main__":
    main()
