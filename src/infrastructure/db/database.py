import os
from typing import Optional

from psycopg2 import pool
from psycopg2.extensions import connection as connection_type

DB_CONFIG = {
    "host": "db",
    "user": os.getenv("DB_USER"),
    "database": os.getenv("DB_NAME"),
    "password": os.getenv("DB_PASSWORD"),
}


class Database:
    _connection_pool: Optional[pool.SimpleConnectionPool] = None

    @classmethod
    def initialize(cls, minconn: int = 1, maxconn: int = 10):
        if cls._connection_pool is None:
            cls._connection_pool = pool.SimpleConnectionPool(
                minconn, maxconn, **DB_CONFIG
            )

    @classmethod
    def get_connection(cls) -> connection_type:
        if cls._connection_pool is None:
            raise Exception("Connection pool is not initialized.")
        return cls._connection_pool.getconn()

    @classmethod
    def return_connection(cls, conn: connection_type):
        if cls._connection_pool:
            cls._connection_pool.putconn(conn)

    @classmethod
    def close_all_connections(cls):
        if cls._connection_pool:
            cls._connection_pool.closeall()
