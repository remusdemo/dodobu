import time

import psycopg2
from backend.config import Config


def get_conn(max_retries=5, retry_delay=2):
    """Return a database connection, retrying on failure.

    Production (Railway) sets DATABASE_URL — the DB is external and may
    not be ready on first connect. Retry gracefully instead of crashing.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            if Config.DATABASE_URL:
                return psycopg2.connect(Config.DATABASE_URL)

            return psycopg2.connect(
                host=Config.DB_HOST,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
            )
        except psycopg2.OperationalError as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    raise last_exc
