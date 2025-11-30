from uuid import UUID
from datetime import datetime, timedelta
from src.infrastructure.db.repository_interfaces import AbstractUserRepository, AbstractActivationTokenRepository
from src.services.email_interfaces import AbstractEmailService
from src.core.models import User, ActivationToken
from src.core.enums import UserStatus
from src.core.utils import generate_activation_code, hash_password, ACTIVATION_TOKEN_TTL_SECONDS
from src.infrastructure.db.database import Database

class UserAlreadyExists(Exception):
    pass
class IvalidTokenError(Exception):
    pass
class UserAlreadyActive(Exception):
    pass

class RegistrationService:
    def __init__(self, user_repo: AbstractUserRepository,
                 token_repo: AbstractActivationTokenRepository,
                 email_service: AbstractEmailService):
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.email_service = email_service

    def register_user(self, email: str, password: str) -> User:
        if self.user_repo.find_by_email(email):
            raise UserAlreadyExists("An account with this email already exists.")
        
        hashed_password = hash_password(password)

        new_user = User(email=email, password_hash=hashed_password, status=UserStatus.PENDING)
        created_user = self.user_repo.create_user(new_user)

        activation_code = generate_activation_code()
        activation_token = ActivationToken(user_id=created_user.id, code=activation_code)
        self.token_repo.create_activation_token(activation_token)
        self.email_service.send_activation_email(created_user.email, activation_code)
        return created_user
    
    def activate_user(self, email: str, code: str) -> User:
        user = self.user_repo.find_by_email(email)
        if not user:
            raise IvalidTokenError("Invalid email or activation code.")
        
        if user.is_active():
            raise UserAlreadyActive("User account is already active.")
        
        token = self.token_repo.find_by_user_id_and_code(user.id, code)
        if not token:
            raise IvalidTokenError("Invalid email or activation code.")
        
        time_diff = datetime.now() - token.created_at
        if time_diff.total_seconds() > ACTIVATION_TOKEN_TTL_SECONDS:
            self.token_repo.delete_activation_token(user.id)
            raise IvalidTokenError("Activation token has expired.")
        
        user.activate()
        self.user_repo.update_user_status(user.id, UserStatus.ACTIVE.value)
        self.token_repo.delete_activation_token(user.id)
        return user