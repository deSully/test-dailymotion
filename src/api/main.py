from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr, field_validator

from src.infrastructure.db.activation_token_repository import (
    PostgresActivationTokenRepository,
)
from src.infrastructure.db.database import Database
from src.infrastructure.db.user_repository import PostgresUserRepository
from src.infrastructure.email.mock_email_service import MockEmailService
from src.infrastructure.logging.logger import setup_logger
from src.services.exceptions import (
    InvalidTokenError,
    UserAlreadyActive,
    UserAlreadyExists,
)
from src.services.registration_service import RegistrationService

logger = setup_logger(__name__)


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        return v


class RegisterResponse(BaseModel):
    id: str
    email: EmailStr
    status: str

    class Config:
        from_attributes = True


Database.initialize(minconn=1, maxconn=10)

security = HTTPBasic()

user_repository = PostgresUserRepository()
token_repository = PostgresActivationTokenRepository()
email_service = MockEmailService()

registrasion_service = RegistrationService(
    user_repo=user_repository, token_repo=token_repository, email_service=email_service
)
app = FastAPI(
    title="User Registration API",
    description="Production-ready user registration system with email verification",
    version="1.0.0",
)


@app.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Creates a new user account and sends a 4-digit activation code via email.

    The activation code expires after 60 seconds and must be used with the
    /activate endpoint.

    **Password requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """,
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "status": "PENDING",
                    }
                }
            },
        },
        409: {
            "description": "Email already registered",
            "content": {
                "application/json": {
                    "example": {"detail": "User with this email already exists"}
                }
            },
        },
        422: {
            "description": "Invalid email or password requirements not met",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "password"],
                                "msg": (
                                    "Password must contain at least one "
                                    "uppercase letter"
                                ),
                                "type": "value_error",
                            }
                        ]
                    }
                }
            },
        },
        500: {"description": "Internal server error"},
    },
    tags=["Authentication"],
)
def register_user(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
) -> RegisterResponse:
    logger.info(f"Registration attempt for email: {request.email}")
    try:

        def send_email_task(email: str, code: str) -> None:
            email_service.send_activation_code(email, code)

        user = registrasion_service.register_user(
            request.email,
            request.password,
            lambda email, code: background_tasks.add_task(send_email_task, email, code),
        )
        logger.info(f"User registered successfully: {user.id}")
        return RegisterResponse(
            id=str(user.id), email=user.email, status=user.status.value
        )
    except UserAlreadyExists as e:
        logger.warning(f"Registration failed - email already exists: {request.email}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post(
    "/activate",
    response_model=RegisterResponse,
    summary="Activate user account",
    description="""
    Activates a user account using HTTP Basic Authentication.

    **Authentication:**
    - Username: User's email address
    - Password: 4-digit activation code (received by email)

    **Important:** Activation code expires after 60 seconds.
    """,
    responses={
        200: {
            "description": "User successfully activated",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "email": "user@example.com",
                        "status": "ACTIVE",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {"example": {"detail": "Invalid credentials"}}
            },
        },
        404: {
            "description": "User not found or invalid activation code",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired activation code"}
                }
            },
        },
        409: {
            "description": "User already activated",
            "content": {
                "application/json": {
                    "example": {"detail": "User is already active"}
                }
            },
        },
        500: {"description": "Internal server error"},
    },
    tags=["Authentication"],
)
def activate_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> RegisterResponse:
    logger.info(f"Activation attempt for email: {credentials.username}")
    try:
        user = registrasion_service.activate_user(
            credentials.username, credentials.password
        )
        logger.info(f"User activated successfully: {user.id}")
        return RegisterResponse(
            id=str(user.id), email=user.email, status=user.status.value
        )

    except InvalidTokenError as e:
        logger.warning(
            f"Activation failed - invalid token for email: {credentials.username}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserAlreadyActive as e:
        logger.warning(f"Activation failed - already active: {credentials.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Activation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get(
    "/health",
    summary="Health check",
    description="""
    Performs a health check on the API and database connectivity.

    Returns HTTP 200 if the service is healthy and database is reachable.
    Returns HTTP 503 if the database connection fails.
    """,
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "database": "connected"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Database connection failed"}
                }
            },
        },
    },
    tags=["Monitoring"],
)
def health_check() -> dict[str, str]:
    try:
        conn = Database.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        Database.return_connection(conn)
        logger.debug("Health check passed")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )


@app.on_event("shutdown")
def shutdown_event() -> None:
    logger.info("Shutting down application, closing database connections")
    Database.close_all_connections()
