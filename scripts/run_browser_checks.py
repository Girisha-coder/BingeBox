"""Run browser tests on an isolated 840-row database, never the application DB."""

from datetime import date
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import uuid
import httpx
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from seed_demo import local_dsn, seed_demo
from import_kaggle import import_sample

ROOT = Path(__file__).resolve().parents[1]


def wait_http(url, process):
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError("Test server stopped before readiness.")
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Test server did not become ready.")


def main():
    name = "bingebox_test_" + uuid.uuid4().hex
    admin_dsn = local_dsn()
    dsn = make_conninfo(admin_dsn, dbname=name)
    processes = []
    with (
        psycopg.connect(admin_dsn, autocommit=True) as admin,
        tempfile.TemporaryDirectory(prefix="bingebox_browser_") as folder,
    ):
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            with psycopg.connect(dsn) as c:
                for path in sorted((ROOT / "db").glob("*.sql")):
                    c.execute(path.read_text(encoding="utf-8"))
                seed_demo(c, date.today())
                sample = next((ROOT / "data/kaggle").glob("*.csv"))
                assert import_sample(c, sample)["database_rows_after"] == 840
            print("Browser database ready: isolated 840-row fixture.", flush=True)
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            api_env = {
                **os.environ,
                "DATABASE_URL": dsn,
                "AUTH_SECRET": secrets.token_hex(32),
                "MEDIA_ROOT": folder + "/media",
                "APP_ORIGIN": "http://127.0.0.1:18081",
                "PYTHONPATH": str(ROOT / "backend"),
            }
            web_env = {**os.environ, "API_TARGET": "http://127.0.0.1:18001"}
            with (
                open(Path(folder) / "api.log", "w", encoding="utf-8") as apilog,
                open(Path(folder) / "web.log", "w", encoding="utf-8") as weblog,
            ):
                backend = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "18001",
                        "--no-access-log",
                    ],
                    cwd=ROOT,
                    env=api_env,
                    stdout=apilog,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                processes.append(backend)
                wait_http("http://127.0.0.1:18001/health/ready", backend)
                npm = ["cmd", "/c", "npm"] if os.name == "nt" else ["npm"]
                frontend = subprocess.Popen(
                    npm + ["run", "dev", "--", "--port", "18081", "--strictPort"],
                    cwd=ROOT / "frontend",
                    env=web_env,
                    stdout=weblog,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                processes.append(frontend)
                wait_http("http://127.0.0.1:18081", frontend)
                runner = subprocess.Popen(
                    npm + ["run", "test:e2e", "--", *sys.argv[1:]],
                    cwd=ROOT / "frontend",
                    env={**os.environ, "BASE_URL": "http://127.0.0.1:18081"},
                    creationflags=flags,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                for line in runner.stdout:
                    print(line, end="", flush=True)
                result = runner.wait()
            return result
        finally:
            for process in reversed(processes):
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    process.terminate()
                process.wait(timeout=15)
            assert name.startswith("bingebox_test_") and len(name) == 46
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
            print("Isolated browser database and test servers removed.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
