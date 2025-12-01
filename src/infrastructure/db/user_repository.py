from typing import Any, Optional
from uuid import UUID

import psycopg2.extras
from psycopg2 import IntegrityError, OperationalError

from src.core.enums import UserStatus
from src.core.models import User
from src.infrastructure.db.database import Database
from src.infrastructure.db.repository_interfaces import AbstractUserRepository
from src.infrastructure.logging.logger import setup_logger

logger = setup_logger(__name__)


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
                    logger.debug(f"User created in database: {row['id']}")
                    return map_row_to_user(row)
                raise Exception("Failed to create user.")
        except IntegrityError as e:
            conn.rollback()
            logger.error(f"Database integrity error creating user: {e}")
            raise ValueError(f"User with email {user.email} already exists")
        except OperationalError as e:
            conn.rollback()
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error creating user: {e}", exc_info=True)
            raise
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
        except OperationalError as e:
            logger.error(f"Database connection error finding user: {e}", exc_info=True)
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            logger.error(f"Unexpected error finding user: {e}", exc_info=True)
            raise
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
                updated = cursor.rowcount > 0
                if updated:
                    logger.debug(f"User status updated: {user_id} -> {status}")
                return updated
        except OperationalError as e:
            conn.rollback()
            logger.error(
                f"Database connection error updating user status: {e}", exc_info=True
            )
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error updating user status: {e}", exc_info=True)
            raise
        finally:
            Database.return_connection(conn)
