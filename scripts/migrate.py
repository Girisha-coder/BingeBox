"""Apply only additive application migrations to the existing database."""

from pathlib import Path
import psycopg
from seed_demo import local_dsn

root = Path(__file__).resolve().parents[1]
with psycopg.connect(local_dsn()) as connection:
    for path in sorted((root / "db").glob("*.sql")):
        if int(path.name[:2]) >= 5:
            connection.execute(path.read_text(encoding="utf-8"))
            print("Applied", path.name)
