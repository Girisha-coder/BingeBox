"""Import a bounded, attributed sample of real Kaggle movie metadata.

Only 1,000 source records are considered and 150 movies are retained by default.
The final database is capped at 1,000 rows across all application tables.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
from itertools import islice
import json
from pathlib import Path
import random
import re
import urllib.request
import zipfile

import psycopg

try:
    from scripts.seed_demo import ROOT, counts, insert, local_dsn
except ModuleNotFoundError:
    from seed_demo import ROOT, counts, insert, local_dsn

DATA_DIRECTORY = ROOT / "data/kaggle"
DATASET = "shivamb/netflix-shows"
SOURCE_URL = "https://www.kaggle.com/datasets/" + DATASET
DOWNLOAD_URL = "https://www.kaggle.com/api/v1/datasets/download/" + DATASET
MAX_SOURCE_ROWS = 1000
MAX_DATABASE_ROWS = 1000
AGE_MAP = {"G": 0, "TV-G": 0, "TV-Y": 0, "TV-Y7": 7, "TV-Y7-FV": 7,
           "PG": 7, "TV-PG": 13, "PG-13": 13, "TV-14": 16,
           "R": 18, "TV-MA": 18, "NC-17": 18, "NR": 18, "UR": 18, "": 18}
GENRE_MAP = {"Dramas": "Drama", "Comedies": "Comedy", "Documentaries": "Documentary",
             "Thrillers": "Thriller", "Children & Family Movies": "Family",
             "International Movies": "International", "Romantic Movies": "Romance",
             "Horror Movies": "Horror", "Classic Movies": "Classics",
             "Cult Movies": "Cult", "Anime Features": "Anime", "Sports Movies": "Sports",
             "Independent Movies": "Independent", "LGBTQ Movies": "LGBTQ"}


def fetch_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": "BingeBox-Course-Project/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read(10_000_001)
    if len(body) > 10_000_000:
        raise ValueError("Source response exceeds the bounded download size.")
    return body


def parse_movie(row):
    if row.get("type") != "Movie":
        return None
    match = re.fullmatch(r"(\d+) min", row.get("duration", "").strip())
    if not match:
        return None
    duration = int(match.group(1))
    try:
        year = int(row["release_year"])
    except (KeyError, ValueError):
        return None
    name, description = row.get("title", "").strip(), row.get("description", "").strip()
    if not name or len(name) > 200 or not 1888 <= year <= 2100 or not 1 <= duration <= 600 or len(description) > 2000:
        return None
    genres = sorted({GENRE_MAP.get(item.strip(), item.strip()) for item in row.get("listed_in", "").split(",") if item.strip()})
    if any(len(genre) > 30 for genre in genres):
        return None
    rating = row.get("rating", "").strip()
    if rating not in AGE_MAP:
        return None
    return dict(name=name, release_year=year, description=description or None, duration_min=duration,
                age_rating=AGE_MAP[rating], genres=genres, source_show_id=row["show_id"], source_rating=rating)


def select_sample(rows, limit):
    if not 1 <= limit <= MAX_SOURCE_ROWS:
        raise ValueError("Sample size must be between 1 and 1,000.")
    candidates, seen = [], set()
    for row in rows:
        parsed = parse_movie(row)
        if parsed is None:
            continue
        key = (parsed["name"], parsed["release_year"])
        if key not in seen:
            seen.add(key)
            candidates.append((row, parsed))
    if len(candidates) < limit:
        raise ValueError(f"Only {len(candidates)} valid movies in the bounded source window.")
    chosen = []

    def take(candidate):
        if candidate not in chosen and len(chosen) < limit:
            chosen.append(candidate)

    # Deliberately retain real runtime/year extremes and maturity-rating diversity.
    for field in ("duration_min", "release_year"):
        ordered = sorted(candidates, key=lambda item: (item[1][field], item[1]["source_show_id"]))
        for candidate in ordered[:3] + ordered[-3:]:
            take(candidate)
    for rating in sorted({item[1]["source_rating"] for item in candidates}):
        take(next(item for item in candidates if item[1]["source_rating"] == rating))
    shuffled = candidates.copy()
    random.Random(20261020).shuffle(shuffled)
    for candidate in shuffled:
        take(candidate)
    return [item[0] for item in chosen]


def download_sample(limit=150):
    sample_path = DATA_DIRECTORY / "netflix_movies_sample.csv"
    metadata_path = DATA_DIRECTORY / "source.json"
    if sample_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if hashlib.sha256(sample_path.read_bytes()).hexdigest() != metadata["sample_sha256"]:
            raise ValueError("Cached sample hash differs from its provenance record.")
        if metadata["retained_rows"] != limit:
            raise ValueError("A different sample already exists; it was not overwritten.")
        return sample_path, metadata
    listing = json.loads(fetch_bytes("https://www.kaggle.com/api/v1/datasets/list?search=netflix-shows&user=shivamb"))
    info = next((item for item in listing if item.get("ref") == DATASET), None)
    if info is None or info.get("licenseName") != "CC0: Public Domain":
        raise ValueError("Expected dataset and CC0 licence could not be verified from Kaggle.")
    archive_bytes = fetch_bytes(DOWNLOAD_URL)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        entry = next((name for name in archive.namelist() if Path(name).name == "netflix_titles.csv"), None)
        if entry is None:
            raise ValueError("Expected CSV is absent from the source archive.")
        with archive.open(entry) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"))
            rows = list(islice(reader, MAX_SOURCE_ROWS))
            columns = reader.fieldnames
    selected = select_sample(rows, limit)
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(selected)
    sample_bytes = buffer.getvalue().encode("utf-8")
    metadata = {
        "dataset": DATASET, "source_url": SOURCE_URL, "download_url": DOWNLOAD_URL,
        "license": info["licenseName"], "dataset_last_updated": info["lastUpdated"],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_rows_considered": len(rows), "retained_rows": len(selected),
        "selection": "First 1000 source rows; valid movies only; runtime/year extremes, rating diversity, then deterministic random sample (seed 20261020). Not population-representative.",
        "sample_sha256": hashlib.sha256(sample_bytes).hexdigest(),
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "archive_retained": False,
    }
    sample_path.write_bytes(sample_bytes)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return sample_path, metadata


def import_sample(connection, sample_path):
    connection.execute("SELECT pg_advisory_xact_lock(200, 2026)")
    connection.execute("SET CONSTRAINTS ALL DEFERRED")
    with Path(sample_path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(islice(csv.DictReader(stream), MAX_SOURCE_ROWS + 1))
    if len(rows) > MAX_SOURCE_ROWS:
        raise ValueError("Source CSV exceeds 1,000 rows.")
    total = sum(counts(connection).values())
    original_total = total
    if total > MAX_DATABASE_ROWS:
        raise ValueError("Database already exceeds the 1,000-row cap; no import performed.")
    mapping, inserted, retained = [], 0, 0
    genre_ids = dict(connection.execute("SELECT name, genre_id FROM genre"))
    for row in rows:
        item = parse_movie(row)
        if item is None:
            raise ValueError(f"Invalid retained source row: {row.get('show_id', 'unknown')}")
        matches = connection.execute(
            """SELECT t.title_id, t.description, t.age_rating, t.original_language, m.duration_min,
                      t.imdb_id, t.imdb_rating, t.imdb_votes
               FROM title t JOIN movie m USING (title_id)
               WHERE t.name = %s AND t.release_year = %s""", (item["name"], item["release_year"])
        ).fetchall()
        if matches:
            if len(matches) != 1 or matches[0][1:] != (item["description"], item["age_rating"], "Unknown", item["duration_min"], None, None, None):
                raise ValueError("A conflicting catalogue title already exists. No existing record was overwritten.")
            title_id = matches[0][0]
            existing_genres = {value[0] for value in connection.execute(
                "SELECT g.name FROM genre g JOIN title_genre tg USING (genre_id) WHERE tg.title_id = %s", (title_id,))}
            if existing_genres != set(item["genres"]):
                raise ValueError("Existing catalogue genres differ from the retained source.")
            retained += 1
        else:
            required = 2 + len(item["genres"]) + sum(genre not in genre_ids for genre in item["genres"])
            if total + required > MAX_DATABASE_ROWS:
                raise ValueError("Import would exceed 1,000 total database rows. Transaction rolled back; use a smaller sample.")
            title_id = insert(connection, "title", name=item["name"], release_year=item["release_year"],
                              description=item["description"], age_rating=item["age_rating"],
                              original_language="Unknown", title_type="M", imdb_id=None,
                              imdb_rating=None, imdb_votes=None)["title_id"]
            insert(connection, "movie", title_id=title_id, duration_min=item["duration_min"])
            for genre in item["genres"]:
                if genre not in genre_ids:
                    genre_ids[genre] = insert(connection, "genre", name=genre)["genre_id"]
                insert(connection, "title_genre", title_id=title_id, genre_id=genre_ids[genre])
            total += required
            inserted += 1
        mapping.append({"title_id": title_id, "source_show_id": item["source_show_id"], "title": item["name"],
                        "source_maturity_rating": item["source_rating"], "mapped_age_rating": item["age_rating"]})
    connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
    final_counts = counts(connection)
    assert sum(final_counts.values()) == total <= MAX_DATABASE_ROWS
    return {"source_rows": len(rows), "movies_inserted": inserted, "movies_retained": retained,
            "database_rows_before": original_total, "database_rows_after": total,
            "table_counts": final_counts, "mapping": mapping}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-size", type=int, default=150)
    parser.add_argument("--download-only", action="store_true")
    arguments = parser.parse_args()
    sample_path, metadata = download_sample(arguments.sample_size)
    if arguments.download_only:
        print(json.dumps(metadata, indent=2))
        return
    with psycopg.connect(local_dsn(), connect_timeout=5) as connection:
        report = import_sample(connection, sample_path)
    report_path = DATA_DIRECTORY / "import-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "mapping"}, indent=2))


if __name__ == "__main__":
    main()
