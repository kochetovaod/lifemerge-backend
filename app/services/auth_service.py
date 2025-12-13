from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_hash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def create_user(
    db: AsyncSession, email: str, password: str, full_name: str | None, timezone_name: str
) -> User:
    user = User(email=email.lower(), password_hash=hash_password(password), full_name=full_name, timezone=timezone_name)
    db.add(user)
    await db.flush()  # assigns id
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    res = await db.execute(select(User).where(User.email == email.lower(), User.deleted == False))  # noqa: E712
    return res.scalar_one_or_none()


async def issue_tokens(db: AsyncSession, user: User, device_id: str) -> tuple[str, str]:
    access = create_access_token(subject=user.email, user_id=str(user.id))
    refresh = create_refresh_token(subject=user.email, user_id=str(user.id), device_id=device_id)

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS)
    rt = RefreshToken(user_id=user.id, device_id=device_id, token_hash=token_hash(refresh), expires_at=expires_at)
    db.add(rt)

    return access, refresh


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def refresh_tokens(db: AsyncSession, refresh_token: str, device_id: str) -> tuple[User, str, str] | None:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        return None

    if payload.get("type") != "refresh":
        return None
    if payload.get("device_id") != device_id:
        return None

    raw_uid = payload.get("uid")
    if not raw_uid:
        return None
    try:
        uid = uuid.UUID(str(raw_uid))
    except Exception:
        return None

    # Validate token exists and is not revoked
    h = token_hash(refresh_token)
    res = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == uid,
            RefreshToken.device_id == device_id,
            RefreshToken.token_hash == h,
            RefreshToken.revoked == False,  # noqa: E712
        )
    )
    stored = res.scalar_one_or_none()
    if not stored:
        return None
    if stored.expires_at < datetime.now(timezone.utc):
        return None

    res2 = await db.execute(select(User).where(User.id == uid, User.deleted == False))  # noqa: E712
    user = res2.scalar_one_or_none()
    if not user:
        return None

    # rotate: revoke old token and issue new
    await db.execute(update(RefreshToken).where(RefreshToken.id == stored.id).values(revoked=True))
    access, new_refresh = await issue_tokens(db, user, device_id)
    return user, access, new_refresh


async def revoke_device_tokens(db: AsyncSession, user: User, device_id: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.device_id == device_id)
        .values(revoked=True)
    )
