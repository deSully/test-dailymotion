from datetime import datetime, timezone
from typing import Callable

from src.core.enums import UserStatus
from src.core.models import ActivationToken, User
from src.core.utils import (
    ACTIVATION_TOKEN_TTL_SECONDS,
    generate_activation_code,
    hash_password,
)
from src.infrastructure.db.activation_token_repository import (
    PostgresActivationTokenRepository,
)
from src.infrastructure.db.user_repository import PostgresUserRepository
from src.infrastructure.logging.logger import setup_logger
from src.services.email_interfaces import AbstractEmailService
from src.services.exceptions import (
    InvalidTokenError,
    UserAlreadyActive,
    UserAlreadyExists,
)

logger = setup_logger(__name__)


class RegistrationService:
    def __init__(
        self,
        user_repo: PostgresUserRepository,
        token_repo: PostgresActivationTokenRepository,
        email_service: AbstractEmailService,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.email_service = email_service

    def register_user(
        self,
        email: str,
        password: str,
        background_tasks: Callable[[str, str], None],
    ) -> User:
        logger.debug(f"Checking if email already exists: {email}")
        if self.user_repo.find_by_email(email):
            logger.warning(f"User registration failed - email exists: {email}")
            raise UserAlreadyExists("An account with this email already exists.")

        hashed_password = hash_password(password)

        new_user = User(
            email=email, password_hash=hashed_password, status=UserStatus.PENDING
        )
        created_user = self.user_repo.create_user(new_user)
        logger.info(f"User created in database: {created_user.id}")

        activation_code = generate_activation_code()
        activation_token = ActivationToken(
            user_id=created_user.id, code=activation_code
        )
        self.token_repo.create_activation_token(activation_token)
        logger.debug(f"Activation token created for user: {created_user.id}")

        background_tasks(created_user.email, activation_code)
        logger.info(f"Activation email scheduled for: {created_user.email}")

        return created_user

    def activate_user(self, email: str, code: str) -> User:
        logger.debug(f"Looking up user by email: {email}")
        user = self.user_repo.find_by_email(email)
        if not user:
            logger.warning(f"Activation failed - user not found: {email}")
            raise InvalidTokenError("Invalid email or activation code.")

        if user.is_active():
            logger.warning(f"Activation failed - user already active: {email}")
            raise UserAlreadyActive("User account is already active.")

        token = self.token_repo.find_by_user_id_and_code(user.id, code)
        if not token:
            logger.warning(f"Activation failed - invalid code for user: {user.id}")
            raise InvalidTokenError("Invalid email or activation code.")

        now = datetime.now(timezone.utc) if token.created_at.tzinfo else datetime.now()
        time_diff = now - token.created_at
        if time_diff.total_seconds() > ACTIVATION_TOKEN_TTL_SECONDS:
            logger.warning(
                f"Activation failed - token expired for user: {user.id} "
                f"(age: {time_diff.total_seconds()}s)"
            )
            self.token_repo.delete_activation_token(user.id)
            raise InvalidTokenError("Activation token has expired.")

        user.activate()
        self.user_repo.update_user_status(user.id, UserStatus.ACTIVE.value)
        self.token_repo.delete_activation_token(user.id)
        logger.info(f"User activated successfully: {user.id}")
        return user
