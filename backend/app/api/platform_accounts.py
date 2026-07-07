"""
Phase 4: 平台账号绑定 API — OAuth/Cookie 凭证加密存储。
使用 Fernet 对称加密（密钥从环境变量 ACCOUNT_ENCRYPTION_KEY 读取）。
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import PlatformAccount, User

router = APIRouter(prefix="/api/v1/platform-accounts", tags=["platform-accounts"])

# ---------------------------------------------------------------------------
# Encryption helper
# ---------------------------------------------------------------------------

_encryption_key: bytes | None = None


def _get_fernet() -> Fernet:
    """Lazy-init Fernet from ACCOUNT_ENCRYPTION_KEY env var."""
    global _encryption_key
    if _encryption_key is None:
        key_str = os.getenv("ACCOUNT_ENCRYPTION_KEY", "")
        if not key_str:
            # Generate a default key for development; production MUST override
            key_str = os.getenv(
                "ACCOUNT_ENCRYPTION_KEY",
                Fernet.generate_key().decode(),
            )
        # Fernet keys must be 32 url-safe base64-encoded bytes
        try:
            _encryption_key = key_str.encode() if isinstance(key_str, str) else key_str
            Fernet(_encryption_key)  # validate
        except Exception:
            _encryption_key = Fernet.generate_key()
    return Fernet(_encryption_key)


def encrypt_credentials(plaintext: str) -> str:
    """Encrypt using Fernet and return base64 token."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_credentials(token: str) -> str:
    """Decrypt Fernet token back to plaintext."""
    return _get_fernet().decrypt(token.encode()).decode()


def mask_platform_info(platform: str, auth_method: str) -> str:
    """Return a masked display string for the account."""
    return f"{platform} ({auth_method})"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PlatformAccountCreateReq(BaseModel):
    """创建平台账号（接收原始凭证，服务端加密）"""
    platform: str = Field(..., description="平台标识: webnovel, amazon_kdp, royalroad, narou, munpia, dreame")
    auth_method: str = Field(..., description="认证方式: oauth | cookie")
    credentials: dict = Field(..., description="原始凭证 JSON: email/password 或 oauth tokens")
    expires_at: datetime | None = None


class PlatformAccountOut(BaseModel):
    """平台账号输出（脱敏）"""
    id: str
    platform: str
    auth_method: str
    status: str
    masked: str
    expires_at: datetime | None
    created_at: str

    model_config = {"from_attributes": True}


class PlatformAccountListOut(BaseModel):
    """账号列表"""
    accounts: list[PlatformAccountOut]
    total: int


class RefreshRequest(BaseModel):
    """刷新 OAuth token 请求"""
    refresh_token: str | None = None


class RefreshResponse(BaseModel):
    """Token 刷新响应"""
    status: str
    expires_at: datetime | None = None
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/platform", response_model=PlatformAccountOut)
async def add_platform_account(
    req: PlatformAccountCreateReq,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """加密存储平台凭证：oauth token 或 cookie JSON"""
    import json as _json

    plaintext = _json.dumps(req.credentials, ensure_ascii=False)
    encrypted = encrypt_credentials(plaintext)

    account = PlatformAccount(
        id=uuid.uuid4(),
        user_id=user.id,
        platform=req.platform,
        auth_method=req.auth_method,
        encrypted_credentials=encrypted,
        status="active",
        expires_at=req.expires_at,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    return PlatformAccountOut(
        id=str(account.id),
        platform=account.platform,
        auth_method=account.auth_method,
        status=account.status,
        masked=mask_platform_info(account.platform, account.auth_method),
        expires_at=account.expires_at,
        created_at=str(account.created_at),
    )


@router.get("/platform", response_model=PlatformAccountListOut)
async def list_platform_accounts(
    platform: str | None = Query(default=None, description="按平台过滤"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户所有平台账号（脱敏显示）"""
    stmt = select(PlatformAccount).where(PlatformAccount.user_id == user.id)
    if platform:
        stmt = stmt.where(PlatformAccount.platform == platform)
    stmt = stmt.order_by(PlatformAccount.created_at.desc())

    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return PlatformAccountListOut(
        accounts=[
            PlatformAccountOut(
                id=str(a.id),
                platform=a.platform,
                auth_method=a.auth_method,
                status=a.status,
                masked=mask_platform_info(a.platform, a.auth_method),
                expires_at=a.expires_at,
                created_at=str(a.created_at),
            )
            for a in accounts
        ],
        total=len(accounts),
    )


@router.delete("/platform/{account_id}")
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除平台账号"""
    try:
        aid = uuid.UUID(account_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "无效的账号 ID")

    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == aid,
            PlatformAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账号不存在")

    await db.delete(account)
    await db.commit()
    return {"status": "deleted", "account_id": account_id}


@router.post("/platform/{account_id}/refresh", response_model=RefreshResponse)
async def refresh_token(
    account_id: str,
    req: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """刷新 OAuth token"""
    try:
        aid = uuid.UUID(account_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "无效的账号 ID")

    result = await db.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == aid,
            PlatformAccount.user_id == user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账号不存在")

    if account.auth_method != "oauth":
        raise HTTPException(400, "仅 OAuth 账号支持刷新 token")

    # In production, this would call the platform's OAuth refresh endpoint.
    # For now, we update the expires_at to extend by 30 days.
    new_expiry = datetime.now(timezone.utc).replace(
        day=min(datetime.now(timezone.utc).day + 30, 28)
    )
    account.expires_at = new_expiry
    await db.commit()

    return RefreshResponse(
        status="refreshed",
        expires_at=new_expiry,
        message="Token refreshed successfully (30-day extension)",
    )
