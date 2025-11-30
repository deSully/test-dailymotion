import secrets
from passlib.context import CryptContext
from typing import Final

password_context: Final = CryptContext(schemes=["bcrypt"], deprecated="auto")
CODE_LENGTH: Final[int] = 4

def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return password_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return password_context.verify(plain_password, hashed_password)

def generate_activation_code(length: int = CODE_LENGTH) -> str:
    """Generate a secure numeric activation code of specified length."""
    return str(secrets.randbelow(10**length)).zfill(length)