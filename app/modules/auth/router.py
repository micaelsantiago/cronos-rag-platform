import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.APP_ENV == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    # Path covers both /refresh and /logout endpoints
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post("/register", status_code=201, response_model=UserResponse)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> UserResponse:
    service = AuthService(db, redis)
    user = await service.register(data.name, data.email, data.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> UserResponse:
    service = AuthService(db, redis)
    user, access_token, refresh_token = await service.login(data.email, data.password)
    _set_auth_cookies(response, access_token, refresh_token)
    return UserResponse.model_validate(user)


@router.post("/refresh")
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")
    service = AuthService(db, redis)
    new_access, new_refresh = await service.refresh(refresh_token)
    _set_auth_cookies(response, new_access, new_refresh)
    return {"message": "refreshed"}


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> None:
    service = AuthService(db, redis)
    await service.logout(refresh_token)
    _clear_auth_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
