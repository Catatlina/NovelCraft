"""用户级 AI 配置 API。

API Key 只接收、不回显，使用与平台账号相同的 Fernet 固定密钥加密保存。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.platform_accounts import decrypt_credentials, encrypt_credentials
from app.db.database import get_db
from app.db.models import User, UserAISettings

router = APIRouter(prefix="/api/v1/ai-settings", tags=["ai-settings"])


class AISettingsIn(BaseModel):
    deepseek_api_key: str | None = Field(default=None, description="DeepSeek API Key；为空时不覆盖旧值")
    deepseek_model: str | None = Field(default="deepseek-chat", description="DeepSeek 模型名")


class AISettingsOut(BaseModel):
    has_deepseek_api_key: bool
    deepseek_model: str


@router.get("", response_model=AISettingsOut)
async def get_ai_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = await db.get(UserAISettings, user.id)
    return AISettingsOut(
        has_deepseek_api_key=bool(settings and settings.encrypted_deepseek_api_key),
        deepseek_model=(settings.deepseek_model if settings and settings.deepseek_model else "deepseek-chat"),
    )


@router.put("", response_model=AISettingsOut)
async def save_ai_settings(
    req: AISettingsIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = await db.get(UserAISettings, user.id)
    if not settings:
        settings = UserAISettings(user_id=user.id)
        db.add(settings)

    if req.deepseek_model:
        settings.deepseek_model = req.deepseek_model.strip()

    if req.deepseek_api_key is not None:
        key = req.deepseek_api_key.strip()
        if key:
            if not key.startswith("sk-"):
                raise HTTPException(422, "DeepSeek API Key 格式不正确")
            settings.encrypted_deepseek_api_key = encrypt_credentials(key)

    await db.commit()
    await db.refresh(settings)
    return AISettingsOut(
        has_deepseek_api_key=bool(settings.encrypted_deepseek_api_key),
        deepseek_model=settings.deepseek_model or "deepseek-chat",
    )


async def load_user_deepseek_settings(db: AsyncSession, user_id) -> tuple[str | None, str | None]:
    """供 middleware 调用：返回明文 API Key + 模型名；解密失败时不泄露细节。"""
    settings = await db.get(UserAISettings, user_id)
    if not settings:
        return None, None
    key = None
    if settings.encrypted_deepseek_api_key:
        try:
            key = decrypt_credentials(settings.encrypted_deepseek_api_key)
        except Exception:
            key = None
    return key, settings.deepseek_model
