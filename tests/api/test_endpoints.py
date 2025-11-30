from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.enums import UserStatus
from src.core.utils import ACTIVATION_TOKEN_TTL_SECONDS
from src.infrastructure.db.database import Database
from src.infrastructure.db.postgres_repository import PostgresUserRepository


@pytest.fixture(scope="module")
def client():
    with TestClient(app=app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data before each test"""
    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM activation_tokens WHERE 1=1;")
            cur.execute("DELETE FROM users WHERE email LIKE '%@example.com';")
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            Database.return_connection(conn)
        except Exception:
            pass

    yield


def test_register_and_activate_user_success(client: TestClient):
    registration_data = {"email": "api_test@example.com", "password": "TestPassword123"}
    response_register = client.post("/register", json=registration_data)

    assert response_register.status_code == 201
    user_data = response_register.json()
    assert user_data["email"] == registration_data["email"]
    assert user_data["status"] == UserStatus.PENDING.value

    user_id = user_data["id"]

    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code FROM activation_tokens WHERE user_id = %s;", (user_id,)
            )
            activation_code = cur.fetchone()[0]
    finally:
        Database.return_connection(conn)

    activation_data = {"email": registration_data["email"], "code": activation_code}
    response_activate = client.post("/activate", json=activation_data)

    assert response_activate.status_code == 200
    activated_data = response_activate.json()
    assert activated_data["status"] == UserStatus.ACTIVE.value


def test_register_user_already_exists(client: TestClient):
    data = {"email": "conflict@example.com", "password": "p"}
    client.post("/register", json=data)
    response = client.post("/register", json=data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


def test_activate_user_invalid_code(client: TestClient):
    email = "invalidcode@example.com"
    client.post("/register", json={"email": email, "password": "p"})

    response = client.post("/activate", json={"email": email, "code": "0000"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid email or activation code" in response.json()["detail"]


def test_activate_user_token_expired(client: TestClient):
    email = "expired@example.com"
    client.post("/register", json={"email": email, "password": "p"})

    user_repo = PostgresUserRepository()
    user = user_repo.find_by_email(email)

    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code FROM activation_tokens WHERE user_id = %s;",
                (str(user.id),),
            )
            activation_code = cur.fetchone()[0]

            expired_time = datetime.now(timezone.utc) - timedelta(
                seconds=ACTIVATION_TOKEN_TTL_SECONDS + 1
            )
            cur.execute(
                "UPDATE activation_tokens SET created_at = %s WHERE user_id = %s;",
                (expired_time, str(user.id)),
            )
        conn.commit()
    finally:
        Database.return_connection(conn)

    response = client.post("/activate", json={"email": email, "code": activation_code})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Activation token has expired" in response.json()["detail"]
