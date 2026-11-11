"""Run integration tests using isolated, temporary PostgreSQL databases."""

import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def main():
    configuration = ROOT / ".env"
    if not configuration.exists():
        raise SystemExit("Run python scripts/configure.py and start the database first.")
    values = {}
    for line in configuration.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    environment = os.environ.copy()
    environment["TEST_ADMIN_DSN"] = (
        "postgresql://bingebox:"
        + quote(values["POSTGRES_PASSWORD"], safe="")
        + f"@127.0.0.1:{int(values.get('DB_PORT', '15432'))}/bingebox"
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", *sys.argv[1:]], cwd=ROOT, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
    )
    for line in process.stdout:
        for key in ('POSTGRES_PASSWORD','AUTH_SECRET'):
            if values.get(key): line=line.replace(values[key], '[REDACTED]')
        print(line,end='',flush=True)
    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
