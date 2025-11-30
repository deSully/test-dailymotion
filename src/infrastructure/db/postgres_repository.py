import psycopg2.extras
from typing import List, Dict, Any, Optional
from uuid import UUID

from src.core.models import User, ActivationToken
from src.core.enums import UserStatus
from src.infrastructure.db.repository_interfaces import AbstractUserRepository
from src.infrastructure.db.database import Database

def map_row_to_user(row: Dict[str, Any]) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        status=UserStatus(row["status"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

class PostgresUserRepository(AbstractUserRepository):
    def __init__(self):
        Database.initialize()

    def create_user(self, user: User) -> User:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (id, email, password_hash, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (str(user.id), user.email, user.password_hash, user.status.value, user.created_at, user.updated_at),
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
                    "SELECT id, email, password_hash, status, created_at, updated_at FROM users WHERE email = %s;",
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


def map_row_to_activation_token(row: Dict[str, Any]) -> ActivationToken:
    return ActivationToken(
        user_id=row["user_id"],
        code=row["code"],
        created_at=row["created_at"],
    )

class PostgresActivationTokenRepository:
    def __init__(self):
        Database.initialize()

    def create_activation_token(self, token: ActivationToken) -> ActivationToken:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO activation_tokens (user_id, code, created_at)
                    VALUES (%s, %s, %s)
                    RETURNING *;
                    """,
                    (str(token.user_id), token.code, token.created_at),
                )
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return map_row_to_activation_token(row)
                raise Exception("Failed to create activation token.")
        finally:
            Database.return_connection(conn)

    def find_by_user_id_and_code(self, user_id: UUID, code: str) -> Optional[ActivationToken]:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT user_id, code, created_at FROM activation_tokens WHERE user_id = %s AND code = %s;",
                    (str(user_id), code),
                )
                row = cursor.fetchone()
                if row:
                    return ActivationToken(
                        user_id=row["user_id"],
                        code=row["code"],
                        created_at=row["created_at"],
                    )
                return None
        finally:
            Database.return_connection(conn)

    def delete_activation_token(self, user_id: UUID) -> bool:
        conn = Database.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM activation_tokens WHERE user_id = %s;",
                    (str(user_id),),
                )
                conn.commit()
                return cursor.rowcount > 0
        finally:
            Database.return_connection(conn)