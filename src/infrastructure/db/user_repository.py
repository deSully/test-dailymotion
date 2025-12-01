from typing import Any, Optional
from uuid import UUID

import psycopg2.extras

from src.core.enums import UserStatus
from src.core.models import User
from src.infrastructure.db.database import Database
from src.infrastructure.db.repository_interfaces import AbstractUserRepository


def map_row_to_user(row: Any) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        status=UserStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostgresUserRepository(AbstractUserRepository):
    def __init__(self) -> None:
        Database.initialize()

    def create_user(self, user: User) -> User:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (
                        id, email, password_hash, status, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        str(user.id),
                        user.email,
                        user.password_hash,
                        user.status.value,
                        user.created_at,
                        user.updated_at,
                    ),
                )
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return map_row_to_user(row)
                raise Exception("Failed to create user.")
        finally:
            Database.return_connection(conn)

    def find_by_email(self, email: str) -> Optional[User]:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT id, email, password_hash, status, created_at, "
                    "updated_at FROM users WHERE email = %s;",
                    (email,),
                )
                row = cursor.fetchone()
                if row:
                    return map_row_to_user(row)
                return None
        finally:
            Database.return_connection(conn)

    def update_user_status(self, user_id: UUID, status: str) -> bool:
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET status = %s, updated_at = NOW() WHERE id = %s;",
                    (status, str(user_id)),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            Database.return_connection(conn)
