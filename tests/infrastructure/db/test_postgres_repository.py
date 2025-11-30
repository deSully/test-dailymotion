import pytest

from src.core.enums import UserStatus
from src.core.models import ActivationToken, User
from src.core.utils import hash_password
from src.infrastructure.db.database import Database
from src.infrastructure.db.postgres_repository import (
    PostgresActivationTokenRepository,
    PostgresUserRepository,
)


@pytest.fixture(scope="session", autouse=True)
def setup_db_pool():
    Database.initialize()
    yield
    if Database._connection_pool and not Database._connection_pool.closed:
        Database.close_all_connections()


@pytest.fixture
def cleanup_db():
    if Database._connection_pool is None or Database._connection_pool.closed:
        Database._connection_pool = None
        Database.initialize()

    conn = Database.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE users, activation_tokens CASCADE;")
            conn.commit()
    finally:
        Database.return_connection(conn)


@pytest.fixture
def user_repo() -> PostgresUserRepository:
    return PostgresUserRepository()


@pytest.fixture
def token_repo() -> PostgresActivationTokenRepository:
    return PostgresActivationTokenRepository()


def test_user_creation_and_retrieval(user_repo: PostgresUserRepository, cleanup_db):
    password = "testpassword"
    hashed_password = hash_password(password)
    user = User(email="test@example.com", password_hash=hashed_password)

    created_user = user_repo.create_user(user)
    assert created_user.email == user.email
    assert created_user.password_hash == user.password_hash
    assert created_user.status == UserStatus.PENDING

    retrieved_user = user_repo.find_by_email("test@example.com")
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.email == created_user.email
    assert retrieved_user.status == UserStatus.PENDING


def test_token_creation_and_retrieval(
    token_repo: PostgresActivationTokenRepository,
    user_repo: PostgresUserRepository,
    cleanup_db,
):
    password = "testpassword"
    hashed_password = hash_password(password)
    user = User(email="test@example.com", password_hash=hashed_password)
    created_user = user_repo.create_user(user)
    token = ActivationToken(user_id=created_user.id, code="1234")
    created_token = token_repo.create_activation_token(token)
    retrieved_token = token_repo.find_by_user_id_and_code(created_user.id, "1234")
    assert retrieved_token is not None
    assert retrieved_token.user_id == created_token.user_id
    assert retrieved_token.code == created_token.code
