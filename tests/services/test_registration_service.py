import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.registration_service import RegistrationService, UserAlreadyExists, InvalidTokenError, UserAlreadyActive
from src.core.models import User, ActivationToken
from src.core.enums import UserStatus
from src.core.utils import hash_password, generate_activation_code, ACTIVATION_TOKEN_TTL_SECONDS

@pytest.fixture
def user_repo_mock():
    return MagicMock()

@pytest.fixture
def token_repo_mock():
    return MagicMock()

@pytest.fixture
def email_service_mock():
    return MagicMock()

@pytest.fixture
def registration_service(user_repo_mock, token_repo_mock, email_service_mock):
    return RegistrationService(user_repo_mock, token_repo_mock, email_service_mock)

# TEST DATA
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "securepassword"
TEST_HASHED_PASSWORD = hash_password(TEST_PASSWORD)
TEST_USER_ID = uuid4()
TEST_ACTIVATION_CODE = "1234"
TOKEN_CREATION_TIME = datetime.now()

@patch('src.services.registration_service.generate_activation_code', return_value=TEST_ACTIVATION_CODE)
@patch('src.services.registration_service.hash_password', return_value=TEST_HASHED_PASSWORD)
@patch('src.services.registration_service.datetime')
def test_register_user_success(mock_datetime, mock_hash_password, mock_generate_code, registration_service, user_repo_mock, token_repo_mock, email_service_mock):
    user_repo_mock.find_by_email.return_value = None
    user_repo_mock.create_user.return_value = User(id=TEST_USER_ID, email=TEST_EMAIL, password_hash=TEST_HASHED_PASSWORD, status=UserStatus.PENDING)

    user = registration_service.register_user(TEST_EMAIL, TEST_PASSWORD)

    assert user.email == TEST_EMAIL
    assert user.status == UserStatus.PENDING
    user_repo_mock.find_by_email.assert_called_once_with(TEST_EMAIL)
    user_repo_mock.create_user.assert_called_once()
    token_repo_mock.create_activation_token.assert_called_once()
    email_service_mock.send_activation_email.assert_called_once_with(TEST_EMAIL, TEST_ACTIVATION_CODE)

@patch('src.services.registration_service.datetime')
def test_activate_user_success(mock_datetime, registration_service, user_repo_mock, token_repo_mock):
    user = User(id=TEST_USER_ID, email=TEST_EMAIL, password_hash=TEST_HASHED_PASSWORD, status=UserStatus.PENDING)
    token = ActivationToken(user_id=TEST_USER_ID, code=TEST_ACTIVATION_CODE, created_at=TOKEN_CREATION_TIME)

    user_repo_mock.find_by_email.return_value = user
    token_repo_mock.find_by_user_id_and_code.return_value = token

    mock_datetime.now.return_value = TOKEN_CREATION_TIME + timedelta(seconds=ACTIVATION_TOKEN_TTL_SECONDS - 10)

    activated_user = registration_service.activate_user(TEST_EMAIL, TEST_ACTIVATION_CODE)

    assert activated_user.is_active()
    user_repo_mock.update_user_status.assert_called_once_with(TEST_USER_ID, UserStatus.ACTIVE.value)
    token_repo_mock.delete_activation_token.assert_called_once_with(TEST_USER_ID)


@patch('src.services.registration_service.hash_password', return_value=TEST_HASHED_PASSWORD)
def test_register_user_existing_email(mock_hash_password, registration_service, user_repo_mock):
    user_repo_mock.find_by_email.return_value = User(id=TEST_USER_ID, email=TEST_EMAIL, password_hash=TEST_HASHED_PASSWORD, status=UserStatus.PENDING)

    with pytest.raises(UserAlreadyExists):
        registration_service.register_user(TEST_EMAIL, TEST_PASSWORD)

    user_repo_mock.find_by_email.assert_called_once_with(TEST_EMAIL)


def test_activate_user_invalid_token(registration_service, user_repo_mock, token_repo_mock):
    user = User(id=TEST_USER_ID, email=TEST_EMAIL, password_hash=TEST_HASHED_PASSWORD, status=UserStatus.PENDING)

    user_repo_mock.find_by_email.return_value = user
    token_repo_mock.find_by_user_id_and_code.return_value = None

    with pytest.raises(InvalidTokenError):
        registration_service.activate_user(TEST_EMAIL, "WRONGCODE")

    user_repo_mock.find_by_email.assert_called_once_with(TEST_EMAIL)
    token_repo_mock.find_by_user_id_and_code.assert_called_once_with(TEST_USER_ID, "WRONGCODE")

@patch('src.services.registration_service.datetime')
def test_activate_user_token_expired(mock_datetime, registration_service, user_repo_mock, token_repo_mock):
    user = User(id=TEST_USER_ID, email=TEST_EMAIL, password_hash=TEST_HASHED_PASSWORD, status=UserStatus.PENDING)
    token = ActivationToken(user_id=TEST_USER_ID, code=TEST_ACTIVATION_CODE, created_at=TOKEN_CREATION_TIME)

    user_repo_mock.find_by_email.return_value = user
    token_repo_mock.find_by_user_id_and_code.return_value = token

    with patch('src.services.registration_service.datetime') as mock_datetime:
        mock_datetime.now.return_value = TOKEN_CREATION_TIME + timedelta(seconds=ACTIVATION_TOKEN_TTL_SECONDS + 10)

        with pytest.raises(InvalidTokenError):
            registration_service.activate_user(TEST_EMAIL, TEST_ACTIVATION_CODE)

    token_repo_mock.delete_activation_token.assert_called_once_with(TEST_USER_ID)