"""Real endpoint SQL: filter intersections, search branches and pagination."""

import pytest


@pytest.fixture
def catalogue(query_data):
    q = query_data
    ids = {
        "short": q.title("Short drama", runtime=1, rating=0, genres=("Drama",), audio=("English",), subtitles=("Hindi",)),
        "match": q.title("Boundary drama", runtime=60, rating=8, genres=("Drama", "Mystery"), audio=("English", "Hindi"), subtitles=("English", "Hindi")),
        "long": q.title("Long comedy", runtime=600, rating=10, genres=("Comedy",), audio=("Hindi",)),
        "unknown": q.title("Unrated drama", runtime=60, genres=("Drama",), subtitles=("English",)),
        "adult": q.title("Adult drama", runtime=60, rating=9, age=18, genres=("Drama",), audio=("English",), subtitles=("Hindi",)),
        "series": q.title("A series", series=True, rating=8, genres=("Drama",), audio=("English",), subtitles=("Hindi",)),
        "empty": q.title("Unscheduled series", series=True),
    }
    q.episode(ids["series"], 1, 1, 20)
    q.episode(ids["series"], 2, 1, 40)
    return ids


@pytest.mark.parametrize("params,expected", [
    ({}, ["short", "match", "long", "unknown", "adult", "series", "empty"]),
    ({"genre": "Drama"}, ["short", "match", "unknown", "adult", "series"]),
    ({"genre": "Missing"}, []),
    ({"audio": "Hindi"}, ["match", "long"]),
    ({"subtitle": "English"}, ["match", "unknown"]),
    ({"audio": "Hindi", "subtitle": "English"}, ["match"]),
    ({"genre": "Drama", "audio": "Hindi"}, ["match"]),
    ({"genre": "Comedy", "subtitle": "English"}, []),
    ({"min_runtime": 60, "max_runtime": 60}, ["match", "unknown", "adult", "series"]),
    ({"min_runtime": 600, "max_runtime": 600}, ["long"]),
    ({"min_runtime": 0, "max_runtime": 0}, ["empty"]),
    ({"min_runtime": 61, "max_runtime": 59}, []),
    ({"min_rating": 8}, ["match", "long", "adult", "series"]),
    ({"min_rating": 10}, ["long"]),
    ({"min_rating": 8.1, "max_runtime": 60}, ["adult"]),
    ({"genre": "Mystery", "audio": "Hindi", "subtitle": "English", "min_runtime": 60, "max_runtime": 60, "min_rating": 8}, ["match"]),
    ({"genre": "Drama", "audio": "English", "subtitle": "Hindi", "min_runtime": 60, "max_runtime": 60, "min_rating": 8, "q": "Boundary"}, ["match"]),
])
def test_catalogue_filter_results_and_count_agree(query_client, catalogue, params, expected):
    response = query_client.get("/catalog", params=params)
    assert response.status_code == 200, response.text
    result = response.json()
    assert [row["title_id"] for row in result["items"]] == [catalogue[key] for key in expected]
    assert result["total"] == len(expected)
    assert result["preview"] is True
    for row in result["items"]:
        assert not {"description", "runtime_min", "reviews", "episodes", "subtitle_languages"} & row.keys()


def test_profile_filters_apply_age_to_both_rows_and_total(query_data, query_client, select_query_profile, catalogue):
    pid = query_data.profile(age=7)
    select_query_profile(pid)
    result = query_client.get("/catalog", params={"genre": "Drama", "min_rating": 8, "limit": 1}).json()
    assert result["preview"] is False
    assert result["total"] == 2
    assert [r["title_id"] for r in result["items"]] == [catalogue["match"]]
    assert result["items"][0]["runtime_min"] == 60
    result = query_client.get("/catalog", params={"genre": "Drama", "min_rating": 8, "limit": 1, "page": 2}).json()
    assert [r["title_id"] for r in result["items"]] == [catalogue["series"]]
    assert query_client.get(f"/catalog/{catalogue['adult']}").status_code == 404


def test_search_full_text_description_stemming_substring_and_typo(query_data, query_client):
    q = query_data
    description = q.title("The Orchard", description="Astronauts harvest strange fruit.")
    substring = q.title("Xylophone")
    typo = q.title("Interstellar")
    q.title("Unrelated comedy")
    for term, expected in [("astronaut", description), ("  ASTRONAUT  ", description), ("xy", substring), ("Interstelar", typo)]:
        response = query_client.get("/catalog", params={"q": term})
        assert response.status_code == 200
        assert [r["title_id"] for r in response.json()["items"]] == [expected]
        assert response.json()["total"] == 1


@pytest.mark.parametrize("symbol,name", [("%", "100% Original"), ("_", "Under_score"), ("\\", "Back\\slash")])
def test_search_treats_sql_wildcards_as_literal_input(query_data, query_client, symbol, name):
    target = query_data.title(name)
    query_data.title("Unrelated title")
    response = query_client.get("/catalog", params={"q": symbol})
    assert response.status_code == 200
    assert [r["title_id"] for r in response.json()["items"]] == [target]
    assert response.json()["total"] == 1


def test_search_quote_payload_stays_data(query_data, query_client):
    target = query_data.title("Director's cut")
    assert query_client.get("/catalog", params={"q": "Director's"}).json()["items"][0]["title_id"] == target
    response = query_client.get("/catalog", params={"q": "'; DROP TABLE title; --"})
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert query_data.db.execute("SELECT count(*) FROM title").fetchone()[0] == 1


@pytest.mark.parametrize("term", ["", "Pagination match"])
def test_catalogue_twenty_per_page_stable_order_last_page_and_empty_page(query_data, query_client, term):
    ids = [query_data.title("Pagination match", genres=("Drama", "Mystery"), audio=("English", "Hindi")) for _ in range(42)]
    seen = []
    for page, expected in [(1, ids[:20]), (2, ids[20:40]), (3, ids[40:]), (4, [])]:
        response = query_client.get("/catalog", params={"q": term, "page": page, "limit": 20, "genre": "Drama"})
        assert response.status_code == 200
        result = response.json()
        assert (result["total"], result["limit"], result["page"]) == (42, 20, page)
        assert [r["title_id"] for r in result["items"]] == expected
        seen.extend(r["title_id"] for r in result["items"])
    assert seen == ids  # No overlaps, missing rows or language/genre join multiplication.


@pytest.mark.parametrize("params", [{"page": 0}, {"limit": 0}, {"limit": 61}, {"min_runtime": -1}, {"min_rating": 11}, {"q": "x" * 151}])
def test_invalid_catalogue_ranges_are_rejected(query_client, params):
    assert query_client.get("/catalog", params=params).status_code == 422


def test_filter_options_are_sorted_distinct_and_empty_collections_work(query_data, query_client):
    assert query_client.get("/catalog/filters").json() == {"genres": [], "audio": [], "subtitle": []}
    assert query_client.get("/catalog").json()["items"] == []
    for name in ("First", "Second"):
        query_data.title(name, genres=("Mystery", "Drama"), audio=("Hindi", "English"), subtitles=("French", "English"))
    assert query_client.get("/catalog/filters").json() == {
        "genres": ["Drama", "Mystery"], "audio": ["English", "Hindi"], "subtitle": ["English", "French"],
    }


def test_home_api_binds_the_selected_profile_and_age(query_data, query_client, select_query_profile):
    q = query_data
    kid, other = q.profile(age=7), q.profile()
    movie = q.title("History", genres=("Drama",))
    candidate = q.title("Recommendation", rating=8, genres=("Drama",))
    adult = q.title("Adult", age=18, rating=10, genres=("Drama",))
    series = q.title("Kids series", series=True)
    pilot, next_episode = q.episode(series, 1, 1), q.episode(series, 2, 1)
    watch = q.watch(kid, movie=movie, progress=12)
    q.watch(kid, episode=pilot)
    q.watch(other, movie=candidate)
    select_query_profile(kid)
    response = query_client.get("/home")
    assert response.status_code == 200
    result = response.json()
    assert [(r["watch_id"], r["progress_sec"]) for r in result["continue_watching"]] == [(watch, 12)]
    assert [r["episode_id"] for r in result["up_next"]] == [next_episode]
    assert [r["title_id"] for r in result["recommendations"]] == [candidate]
    assert [r["title_id"] for r in result["top_genres"]] == [candidate, movie]
    assert adult not in {r["title_id"] for rows in result.values() for r in rows}
