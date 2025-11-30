from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.core.models import User, ActivationToken

class AbstractUserRepository(ABC):
    @abstractmethod
    def create_user(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        raise NotImplementedError

    @abstractmethod
    def update_user_status(self, user_id: UUID, status: str) -> bool:
        raise NotImplementedError

class AbstractActivationTokenRepository(ABC):

    @abstractmethod
    def create_activation_token(self, token: ActivationToken) -> ActivationToken:
        raise NotImplementedError

    @abstractmethod
    def find_by_user_id_and_code(self, user_id: UUID, code: str) -> Optional[ActivationToken]:
        raise NotImplementedError
    
    @abstractmethod
    def delete_activation_token(self, user_id: UUID) -> bool:
        raise NotImplementedError