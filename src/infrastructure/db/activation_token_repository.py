from typing import Any, Optional
from uuid import UUID

import psycopg2.extras
from psycopg2 import IntegrityError, OperationalError

from src.core.models import ActivationToken
from src.infrastructure.db.database import Database
from src.infrastructure.logging.logger import setup_logger

logger = setup_logger(__name__)


def map_row_to_activation_token(row: Any) -> ActivationToken:
    return ActivationToken(
        user_id=row["user_id"],
        code=row["code"],
        created_at=row["created_at"],
    )


class PostgresActivationTokenRepository:
    def __init__(self) -> None:
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
                    logger.debug(f"Activation token created for user: {token.user_id}")
                    return map_row_to_activation_token(row)
                raise Exception("Failed to create activation token.")
        except IntegrityError as e:
            conn.rollback()
            logger.error(f"Database integrity error creating token: {e}")
            raise ValueError("Activation token already exists")
        except OperationalError as e:
            conn.rollback()
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error creating token: {e}", exc_info=True)
            raise
        finally:
            Database.return_connection(conn)

    def find_by_user_id_and_code(
        self, user_id: UUID, code: str
    ) -> Optional[ActivationToken]:
        conn = Database.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT user_id, code, created_at FROM activation_tokens "
                    "WHERE user_id = %s AND code = %s;",
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
        except OperationalError as e:
            logger.error(f"Database connection error finding token: {e}", exc_info=True)
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            logger.error(f"Unexpected error finding token: {e}", exc_info=True)
            raise
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
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.debug(f"Activation token deleted for user: {user_id}")
                return deleted
        except OperationalError as e:
            conn.rollback()
            logger.error(
                f"Database connection error deleting token: {e}", exc_info=True
            )
            raise ConnectionError("Database is unavailable")
        except Exception as e:
            conn.rollback()
            logger.error(f"Unexpected error deleting token: {e}", exc_info=True)
            raise
        finally:
            Database.return_connection(conn)
