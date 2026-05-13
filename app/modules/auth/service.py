import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.modules.auth.models import User
from app.modules.auth.repository import RefreshTokenRepository, UserRepository

_LOCKOUT_MAX_ATTEMPTS = 5
_LOCKOUT_TTL_SECONDS = 900  # 15 minutes


class AuthService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.redis = redis

    async def register(self, name: str, email: str, password: str) -> User:
        if await self.user_repo.get_by_email(email):
            raise HTTPException(status_code=400, detail="EMAIL_ALREADY_EXISTS")
        password_hash = security.hash_password(password)
        return await self.user_repo.create(name, email, password_hash)

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        await self._check_lockout(email)

        user = await self.user_repo.get_by_email(email)
        if not user or not security.verify_password(password, user.password_hash):
            await self._record_failed_attempt(email)
            # Same error for unknown email and wrong password — don't reveal existence
            raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="ACCOUNT_DISABLED")

        await self._clear_attempts(email)

        access_token = security.create_access_token(user.id, user.email)
        raw_refresh, token_hash = self._new_refresh_pair()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.token_repo.create(user.id, token_hash, expires_at)

        return user, access_token, raw_refresh

    async def refresh(self, raw_token: str) -> tuple[str, str]:
        token_hash = security.hash_token(raw_token)
        token = await self.token_repo.get_by_hash(token_hash)

        if not token or token.is_revoked:
            raise HTTPException(status_code=401, detail="TOKEN_REVOKED")

        expires_at = token.expires_at
        if expires_at.tzinfo is None:  # pragma: no cover
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="TOKEN_EXPIRED")

        # Rotate: revoke old token, issue new pair
        await self.token_repo.revoke(token)

        user = await self.user_repo.get_by_id(uuid.UUID(str(token.user_id)))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="UNAUTHENTICATED")

        new_access = security.create_access_token(user.id, user.email)
        new_raw, new_hash = self._new_refresh_pair()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.token_repo.create(user.id, new_hash, expires_at)

        return new_access, new_raw

    async def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        token_hash = security.hash_token(raw_token)
        token = await self.token_repo.get_by_hash(token_hash)
        if token and not token.is_revoked:
            await self.token_repo.revoke(token)

    # --- lockout helpers ---

    def _lockout_key(self, email: str) -> str:
        return f"login:attempts:{email}"

    async def _check_lockout(self, email: str) -> None:
        key = self._lockout_key(email)
        attempts = await self.redis.get(key)
        if attempts and int(attempts) >= _LOCKOUT_MAX_ATTEMPTS:
            retry_after = max(await self.redis.ttl(key), 1)
            raise HTTPException(
                status_code=423,
                detail={"code": "ACCOUNT_LOCKED", "retry_after": retry_after},
            )

    async def _record_failed_attempt(self, email: str) -> None:
        key = self._lockout_key(email)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, _LOCKOUT_TTL_SECONDS)

    async def _clear_attempts(self, email: str) -> None:
        await self.redis.delete(self._lockout_key(email))

    # --- token helpers ---

    @staticmethod
    def _new_refresh_pair() -> tuple[str, str]:
        raw = security.generate_refresh_token()
        return raw, security.hash_token(raw)
