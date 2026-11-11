import csv
from datetime import date
import hashlib
import json

import pytest

from scripts.import_kaggle import DATA_DIRECTORY, import_sample, parse_movie, select_sample
from scripts.seed_demo import counts, seed_demo, validate

SAMPLE = DATA_DIRECTORY / "netflix_movies_sample.csv"


def test_cached_kaggle_sample_is_attributed_bounded_and_valid():
    metadata = json.loads((DATA_DIRECTORY / "source.json").read_text(encoding="utf-8"))
    assert metadata["license"] == "CC0: Public Domain"
    assert metadata["source_rows_considered"] <= 1000
    assert metadata["sample_sha256"] == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    with SAMPLE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == metadata["retained_rows"] == 150
    assert len({row["show_id"] for row in rows}) == 150
    assert all(parse_movie(row) is not None for row in rows)
    assert select_sample(rows, 25) == select_sample(rows, 25)


def test_real_catalogue_import_preserves_provenance_and_is_repeatable(db):
    snapshot = date(2026, 10, 20)
    seed_demo(db, snapshot)
    report = import_sample(db, SAMPLE)
    assert report["movies_inserted"] == 150
    assert report["database_rows_before"] == 200
    assert 200 < report["database_rows_after"] <= 1000
    assert len(report["mapping"]) == 150
    ids = [row["title_id"] for row in report["mapping"]]
    assert db.execute("""SELECT count(*) FROM title WHERE title_id = ANY(%s)
                         AND original_language = 'Unknown' AND imdb_id IS NULL
                         AND imdb_rating IS NULL AND imdb_votes IS NULL""", (ids,)).fetchone()[0] == 150
    assert db.execute("SELECT count(*) FROM media_asset WHERE movie_id = ANY(%s)", (ids,)).fetchone()[0] == 0
    before = counts(db)
    again = import_sample(db, SAMPLE)
    assert again["movies_inserted"] == 0 and again["movies_retained"] == 150
    assert again["mapping"] == report["mapping"]
    assert counts(db) == before
    assert validate(db, snapshot, allow_catalog_additions=True)["consistency_checks_passed"] == 11
    assert seed_demo(db, date(2026, 11, 20))["action"] == "existing demo retained"
    assert counts(db) == before


def test_import_refuses_conflicting_existing_title_without_overwrite(db):
    with SAMPLE.open(encoding="utf-8", newline="") as stream:
        source = parse_movie(next(csv.DictReader(stream)))
    existing_id = db.execute("""INSERT INTO title (name, release_year, age_rating, title_type)
                                VALUES (%s, %s, 0, 'M') RETURNING title_id""",
                             (source["name"], source["release_year"])).fetchone()[0]
    db.execute("INSERT INTO movie (title_id, duration_min) VALUES (%s, 100)", (existing_id,))
    before = counts(db)
    with pytest.raises(ValueError, match="conflicting catalogue"), db.transaction():
        import_sample(db, SAMPLE)
    assert counts(db) == before


def test_import_rolls_back_when_normalised_rows_would_exceed_cap(db):
    # Unrelated, valid catalogue rows simulate a populated database without mocking SQL.
    db.execute("""INSERT INTO genre (name)
                  SELECT 'Existing genre ' || n FROM generate_series(1, 990) n""")
    before = counts(db)
    assert sum(before.values()) == 995
    with pytest.raises(ValueError, match="exceed 1,000"), db.transaction():
        import_sample(db, SAMPLE)
    assert counts(db) == before
