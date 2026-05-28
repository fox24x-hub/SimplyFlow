from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.core.deps import CurrentUser, DBSession
from app.schemas.auth import UserRegister, UserResponse, TokenResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db:   DBSession,
) -> TokenResponse:
    svc = AuthService(db)
    try:
        user = await svc.authenticate(email=form.username, password=form.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=svc.mint_token(user))


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserRegister,
    db:   DBSession,
) -> UserResponse:
    svc = AuthService(db)
    try:
        user = await svc.register(
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)