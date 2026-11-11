import os
import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise HTTPException(503, "Database is not configured.")
    connection = psycopg.connect(url, connect_timeout=3, row_factory=dict_row)
    try:
        connection.execute("SET ROLE bingebox_app")
    except Exception:
        connection.close()
        raise
    return connection
