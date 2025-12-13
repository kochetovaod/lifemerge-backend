from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.response import err, ok
from app.db.session import get_db
from app.schemas.auth import (
    AuthOut,
    ForgotIn,
    LoginIn,
    LogoutIn,
    RefreshIn,
    ResetIn,
    SignupIn,
)
from app.schemas.user import UserOut
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    issue_tokens,
    refresh_tokens,
    revoke_device_tokens,
)

router = APIRouter(prefix="/auth")


@router.post("/signup", response_model=AuthOut)
async def signup(
    request: Request,
    body: SignupIn,
    db: AsyncSession = Depends(get_db),
    x_device_id: str | None = Header(default=None, alias="X-Device-Id"),
):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=409, detail=err(request, "user_exists", "User already exists"))

    user = await create_user(db, body.email, body.password, body.full_name, body.timezone)
    device_id = x_device_id or "default"
    access, refresh = await issue_tokens(db, user, device_id)
    await db.commit()

    return ok(
        request,
        {
            "user": UserOut.model_validate(user),
            "access_token": access,
            "refresh_token": refresh,
        },
    )


@router.post("/login", response_model=AuthOut)
async def login(request: Request, body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail=err(request, "invalid_credentials", "Invalid email or password"))

    access, refresh = await issue_tokens(db, user, body.device_id)
    await db.commit()

    return ok(
        request,
        {
            "user": UserOut.model_validate(user),
            "access_token": access,
            "refresh_token": refresh,
        },
    )


@router.post("/refresh", response_model=AuthOut)
async def refresh(request: Request, body: RefreshIn, db: AsyncSession = Depends(get_db)):
    res = await refresh_tokens(db, body.refresh_token, body.device_id)
    if not res:
        raise HTTPException(status_code=401, detail=err(request, "invalid_refresh", "Invalid refresh token"))

    user, access, refresh = res
    await db.commit()

    return ok(
        request,
        {
            "user": UserOut.model_validate(user),
            "access_token": access,
            "refresh_token": refresh,
        },
    )


@router.post("/forgot")
async def forgot(request: Request, body: ForgotIn):
    # Stub: production will enqueue email sending and return 200 regardless
    return ok(request, {"status": "ok"})


@router.post("/reset")
async def reset(request: Request, body: ResetIn):
    # Stub: production will validate reset token and update password
    return ok(request, {"status": "ok"})


@router.post("/logout")
async def logout(
    request: Request,
    body: LogoutIn,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_device_tokens(db, current_user, body.device_id)
    await db.commit()
    return ok(request, {"status": "ok"})
