import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.enums import UserStatus
from src.infrastructure.db.database import Database


@pytest.fixture
def client():
    with TestClient(app=app) as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_test_data():
    if Database._connection_pool is None or Database._connection_pool.closed:
        Database._connection_pool = None
        Database.initialize()

    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM activation_tokens WHERE 1=1;")
            cur.execute("DELETE FROM users WHERE email LIKE '%e2e-test%';")
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            Database.return_connection(conn)
        except Exception:
            pass

    yield


def test_complete_registration_and_activation_flow(client: TestClient):
    email = "user@e2e-test.com"
    password = "SecurePass123"

    register_response = client.post(
        "/v1/register", json={"email": email, "password": password}
    )

    assert register_response.status_code == 201
    user_data = register_response.json()
    assert user_data["email"] == email
    assert user_data["status"] == UserStatus.PENDING.value
    user_id = user_data["id"]

    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT code FROM activation_tokens WHERE user_id = %s;", (user_id,)
            )
            result = cur.fetchone()
            assert result is not None
            activation_code = result[0]
    finally:
        Database.return_connection(conn)

    activate_response = client.post("/v1/activate", auth=(email, activation_code))

    assert activate_response.status_code == 200
    activated_user = activate_response.json()
    assert activated_user["email"] == email
    assert activated_user["status"] == UserStatus.ACTIVE.value
    assert activated_user["id"] == user_id

    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM activation_tokens WHERE user_id = %s;",
                (user_id,),
            )
            token_count = cur.fetchone()[0]
            assert token_count == 0
    finally:
        Database.return_connection(conn)
