from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from uuid import UUID
from src.services.registration_service import RegistrationService
from src.infrastructure.db.postgres_repository import PostgresUserRepository, PostgresActivationTokenRepository
from src.infrastructure.email.mock_email_service import MockEmailService
from src.infrastructure.db.database import Database
from src.services.exceptions import UserAlreadyExists, InvalidTokenError, UserAlreadyActive

class RegisterRequest(BaseModel):
    email: str
    password: str

class ActivateRequest(BaseModel):
    email: str
    code: str

class RegisterResponse(BaseModel):
    id: str
    email: EmailStr
    status: str

    class Config:
        from_attributes = True

Database.initialize(minconn=1, maxconn=10)

user_repository = PostgresUserRepository()
token_repository = PostgresActivationTokenRepository()
email_service = MockEmailService()

registrasion_service = RegistrationService(
    user_repo=user_repository,
    token_repo=token_repository,
    email_service=email_service
)
app = FastAPI(title="User regisrtration API")

@app.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: RegisterRequest):
    try:
        user = registrasion_service.register_user(request.email, request.password)
        return RegisterResponse(
            id=str(user.id),
            email=user.email,
            status=user.status.value
        )
    except UserAlreadyExists as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/activate", response_model=RegisterResponse)
def activate_user(request: ActivateRequest):
    try:
        user = registrasion_service.activate_user(request.email, request.code)
        return RegisterResponse(
            id=str(user.id),
            email=user.email,
            status=user.status.value
        )
    
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UserAlreadyActive as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    
@app.on_event("shutdown")
def shutdown_event():
    Database.close_all_connections()