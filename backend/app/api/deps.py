"""API 认证依赖 + 数据隔离校验"""
import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, User


async def get_deepseek_api_key(
    x_deepseek_api_key: Optional[str] = Header(None, alias="X-DeepSeek-API-Key"),
) -> str | None:
    """从前端请求头提取 DeepSeek API Key"""
    return x_deepseek_api_key


async def get_current_user(
    authorization: str = Header(...), db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    token = authorization[7:]
    user_id_str = decode_token(token)
    if not user_id_str:
        raise HTTPException(401, "Invalid or expired token")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(401, "Invalid token payload")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found")
    return user


async def get_user_project(project_id: str, user: User, db: AsyncSession) -> NovelProject:
    """校验用户拥有该项目，否则抛 404"""
    result = await db.execute(
        select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


async def get_user_chapter(chapter_id: str, user: User, db: AsyncSession) -> NovelChapter:
    """校验用户拥有该章节所属项目，否则抛 404"""
    from uuid import UUID
    try:
        cid = UUID(chapter_id)
    except (ValueError, AttributeError):
        raise HTTPException(404, "章节不存在")
    result = await db.execute(
        select(NovelChapter).join(NovelProject).where(
            NovelChapter.id == cid, NovelProject.user_id == user.id
        )
    )
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    return chapter
