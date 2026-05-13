import uuid

from fastapi import Cookie, Depends, HTTPException
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository


async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="UNAUTHENTICATED")
    try:
        payload = decode_access_token(access_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    user = await UserRepository(db).get_by_id(uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="UNAUTHENTICATED")

    return user
