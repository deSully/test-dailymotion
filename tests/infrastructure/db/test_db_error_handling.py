from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg2
import pytest

from src.core.enums import UserStatus
from src.core.models import ActivationToken, User
from src.infrastructure.db.activation_token_repository import (
    PostgresActivationTokenRepository,
)
from src.infrastructure.db.user_repository import PostgresUserRepository


@pytest.fixture
def user_repo():
    return PostgresUserRepository()


@pytest.fixture
def token_repo():
    return PostgresActivationTokenRepository()


@pytest.fixture
def sample_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hashed_password",
        status=UserStatus.PENDING,
    )


@pytest.fixture
def sample_token():
    return ActivationToken(user_id=uuid4(), code="1234")


class TestUserRepositoryErrorHandling:
    @patch("src.infrastructure.db.user_repository.Database.return_connection")
    @patch("src.infrastructure.db.user_repository.Database.get_connection")
    def test_create_user_integrity_error(
        self, mock_get_conn, mock_return_conn, user_repo, sample_user
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("duplicate key")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ValueError, match="already exists"):
            user_repo.create_user(sample_user)

        mock_conn.rollback.assert_called_once()

    @patch("src.infrastructure.db.user_repository.Database.return_connection")
    @patch("src.infrastructure.db.user_repository.Database.get_connection")
    def test_create_user_operational_error(
        self, mock_get_conn, mock_return_conn, user_repo, sample_user
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError("connection lost")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            user_repo.create_user(sample_user)

        mock_conn.rollback.assert_called_once()

    @patch("src.infrastructure.db.user_repository.Database.return_connection")
    @patch("src.infrastructure.db.user_repository.Database.get_connection")
    def test_find_by_email_operational_error(
        self, mock_get_conn, mock_return_conn, user_repo
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError(
            "connection timeout"
        )
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            user_repo.find_by_email("test@example.com")

    @patch("src.infrastructure.db.user_repository.Database.return_connection")
    @patch("src.infrastructure.db.user_repository.Database.get_connection")
    def test_update_user_status_operational_error(
        self, mock_get_conn, mock_return_conn, user_repo
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError("db down")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            user_repo.update_user_status(uuid4(), UserStatus.ACTIVE.value)

        mock_conn.rollback.assert_called_once()


class TestActivationTokenRepositoryErrorHandling:
    @patch(
        "src.infrastructure.db.activation_token_repository.Database.return_connection"
    )
    @patch(
        "src.infrastructure.db.activation_token_repository.Database.get_connection"
    )
    def test_create_token_integrity_error(
        self, mock_get_conn, mock_return_conn, token_repo, sample_token
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.IntegrityError("duplicate token")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ValueError, match="already exists"):
            token_repo.create_activation_token(sample_token)

        mock_conn.rollback.assert_called_once()

    @patch(
        "src.infrastructure.db.activation_token_repository.Database.return_connection"
    )
    @patch(
        "src.infrastructure.db.activation_token_repository.Database.get_connection"
    )
    def test_create_token_operational_error(
        self, mock_get_conn, mock_return_conn, token_repo, sample_token
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError("network error")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            token_repo.create_activation_token(sample_token)

        mock_conn.rollback.assert_called_once()

    @patch(
        "src.infrastructure.db.activation_token_repository.Database.return_connection"
    )
    @patch(
        "src.infrastructure.db.activation_token_repository.Database.get_connection"
    )
    def test_find_token_operational_error(
        self, mock_get_conn, mock_return_conn, token_repo
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError("timeout")
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            token_repo.find_by_user_id_and_code(uuid4(), "1234")

    @patch(
        "src.infrastructure.db.activation_token_repository.Database.return_connection"
    )
    @patch(
        "src.infrastructure.db.activation_token_repository.Database.get_connection"
    )
    def test_delete_token_operational_error(
        self, mock_get_conn, mock_return_conn, token_repo
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = psycopg2.OperationalError(
            "connection failed"
        )
        mock_get_conn.return_value = mock_conn

        with pytest.raises(ConnectionError, match="Database is unavailable"):
            token_repo.delete_activation_token(uuid4())

        mock_conn.rollback.assert_called_once()
