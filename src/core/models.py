import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from src.core.enums import UserStatus


class User(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    email: EmailStr
    password_hash: str
    status: UserStatus = UserStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    def activate(self) -> None:
        """Activate the user account."""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now()


class ActivationToken(BaseModel):
    user_id: uuid.UUID
    code: str = Field(..., min_length=4, max_length=4)
    created_at: datetime = Field(default_factory=datetime.now)
