from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr

from src.infrastructure.db.activation_token_repository import (
    PostgresActivationTokenRepository,
)
from src.infrastructure.db.database import Database
from src.infrastructure.db.user_repository import PostgresUserRepository
from src.infrastructure.email.mock_email_service import MockEmailService
from src.services.exceptions import (
    InvalidTokenError,
    UserAlreadyActive,
    UserAlreadyExists,
)
from src.services.registration_service import RegistrationService


class RegisterRequest(BaseModel):
    email: str
    password: str


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
app = FastAPI(title="User regisrtration API")


@app.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
def register_user(
    request: RegisterRequest, background_tasks: BackgroundTasks
) -> RegisterResponse:
    try:

        def send_email_task(email: str, code: str) -> None:
            email_service.send_activation_code(email, code)

        user = registrasion_service.register_user(
            request.email,
            request.password,
            lambda email, code: background_tasks.add_task(send_email_task, email, code),
        )
        return RegisterResponse(
            id=str(user.id), email=user.email, status=user.status.value
        )
    except UserAlreadyExists as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/activate", response_model=RegisterResponse)
def activate_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> RegisterResponse:
    try:
        user = registrasion_service.activate_user(
            credentials.username, credentials.password
        )
        return RegisterResponse(
            id=str(user.id), email=user.email, status=user.status.value
        )

    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserAlreadyActive as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/health")
def health_check() -> dict[str, str]:
    try:
        conn = Database.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        Database.return_connection(conn)
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )


@app.on_event("shutdown")
def shutdown_event() -> None:
    Database.close_all_connections()
