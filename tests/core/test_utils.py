import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from src.core.models import ActivationToken
from src.core.utils import (
    ACTIVATION_TOKEN_TTL_SECONDS,
    generate_activation_code,
    hash_password,
    is_token_expired,
    verify_password,
)


def test_password_hashing_and_verification():
    password = "securepassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_Activation_code_generation():
    code = generate_activation_code()
    assert len(code) == 4
    assert code.isdigit()


@patch("src.core.utils.datetime")
def test_activation_token_expiry(mock_datetime):
    creation_time = datetime(2025, 1, 1, 12, 0, 0)
    token = ActivationToken(user_id=uuid.uuid4(), created_at=creation_time, code="1234")

    mock_datetime.now.return_value = creation_time + timedelta(
        seconds=ACTIVATION_TOKEN_TTL_SECONDS - 1
    )
    assert not is_token_expired(token)

    mock_datetime.now.return_value = creation_time + timedelta(
        seconds=ACTIVATION_TOKEN_TTL_SECONDS + 1
    )
    assert is_token_expired(token)
