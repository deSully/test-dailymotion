import secrets
from passlib.context import CryptContext
from typing import Final
from src.core.models import ActivationToken
from datetime import datetime

password_context: Final = CryptContext(schemes=["bcrypt"], deprecated="auto")
CODE_LENGTH: Final[int] = 4

ACTIVATION_TOKEN_TTL_SECONDS: Final[int] = 15 * 60  # 15 minutes

def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return password_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return password_context.verify(plain_password, hashed_password)

def generate_activation_code(length: int = CODE_LENGTH) -> str:
    """Generate a secure numeric activation code of specified length."""
    return str(secrets.randbelow(10**length)).zfill(length)

def is_token_expired(token : ActivationToken) -> bool:
    time_diff = datetime.now() - token.created_at
    return time_diff.total_seconds() > ACTIVATION_TOKEN_TTL_SECONDS
