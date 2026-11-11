"""Read-only checks of the delivered application and document links."""

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote
import httpx
import psycopg
from seed_demo import local_dsn, validate

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert not (ROOT / ".git").exists() and not (ROOT / ".venv").exists()
    links = 0
    documents = [
        ROOT / "README.md",
        ROOT / "DESIGN.md",
        ROOT / "progress.md",
        *(ROOT / "docs").rglob("*.md"),
    ]
    missing = []
    for path in documents:
        for raw in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = raw.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[a-z]+://|^mailto:", target, re.I):
                continue
            if not (path.parent / unquote(target)).exists():
                missing.append(f"{path.relative_to(ROOT)}: {target}")
            links += 1
    if missing:
        raise ValueError("Broken document links: " + str(missing))
    with psycopg.connect(local_dsn()) as c:
        snapshot = c.execute(
            "SELECT max(last_watched_at) FROM watch_history"
        ).fetchone()[0]
        dataset = validate(c, snapshot, allow_catalog_additions=True)
        columns = c.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name IN(SELECT tablename FROM pg_tables WHERE schemaname='public')"
        ).fetchone()[0]
        views = c.execute(
            "SELECT count(*) FROM information_schema.views WHERE table_schema='public'"
        ).fetchone()[0]
        version = c.execute("SHOW server_version").fetchone()[0]
        unclassified = c.execute("SELECT count(*) FROM title t WHERE NOT EXISTS (SELECT 1 FROM title_genre g WHERE g.title_id=t.title_id)").fetchone()[0]
        genre_guards = c.execute("SELECT count(*) FROM pg_trigger WHERE tgname IN ('title_requires_genre','title_genre_preserves_participation') AND tgdeferrable AND tginitdeferred").fetchone()[0]
        assert unclassified == 0 and genre_guards == 2
        assert columns == 99 and views == 4 and dataset["total_rows"] == 840
        temporary = c.execute(
            "SELECT count(*) FROM pg_database WHERE datname LIKE 'bingebox_test_%'"
        ).fetchone()[0]
    endpoints = {}
    for endpoint in [
        "http://localhost:18080/",
        "http://localhost:18080/api/health/ready",
        "http://localhost:18000/health/ready",
        "http://localhost:18080/api/catalog",
    ]:
        response = httpx.get(endpoint, timeout=10)
        response.raise_for_status()
        endpoints[endpoint] = response.status_code
    manifest = json.loads((ROOT / "media/manifest.json").read_text(encoding="utf-8"))
    assert manifest["count"] == len(manifest["items"])
    for item in manifest["items"]:
        file = ROOT / "media/placeholder" / f"{item['runtime_sec']}.mp4"
        assert file.is_file() and file.stat().st_size == item["bytes"]
    reference = ROOT / "docs/reference/BingeBox_MidSem_Submission.md"
    root_reference = ROOT.parent / "BingeBox_MidSem_Submission.md"
    if root_reference.exists():
        assert reference.read_bytes() == root_reference.read_bytes()
    report = {
        "database_version": version,
        "dataset": dataset,
        "source_columns": columns,
        "views": views,
        "titles_without_genres": unclassified,
        "deferred_genre_guards": genre_guards,
        "temporary_test_databases_remaining": temporary,
        "markdown_files_checked": len(documents),
        "local_links_checked": links,
        "non_git": True,
        "no_venv": True,
        "media_files_verified": manifest["count"],
        "media_total_bytes": manifest["total_bytes"],
        "reference_markdown_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "http_statuses": endpoints,
    }
    evidence = ROOT / "docs/evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "delivery-check.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
