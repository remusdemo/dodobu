import psycopg2
from backend.config import Config


def get_conn():
    if Config.DATABASE_URL:
        return psycopg2.connect(Config.DATABASE_URL)

    return psycopg2.connect(
        host=Config.DB_HOST,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )
