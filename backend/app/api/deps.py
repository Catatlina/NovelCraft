"""API 认证依赖 + 数据隔离校验"""
import uuid
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token_with_type
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, User


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    access_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从 Authorization header 或 httpOnly Cookie 中提取 JWT 并验证用户。

    优先级：Authorization header > access_token cookie
    """
    token: str | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(401, "未提供认证 token")

    # 只接受 access token。refresh token 只能用于 /auth/refresh，不能直接访问业务 API。
    user_id_str = decode_token_with_type(token, "access")
    if not user_id_str:
        raise HTTPException(401, "access token 无效、类型错误或已过期")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(401, "token 格式无效")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")
    # 校验 token_version：改密/登出后旧 token 自动失效
    import jwt as _jwt
    try:
        payload = _jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm],
                              options={"verify_exp": False})
        token_tv = payload.get("tv", 0)
        if token_tv != user.token_version:
            raise HTTPException(401, "token 已失效，请重新登录")
    except _jwt.JWTError:
        pass  # 解析失败由外层 JWTError 处理
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
    try:
        cid = uuid.UUID(chapter_id)
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


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """要求管理员角色"""
    if not user.is_admin:
        raise HTTPException(403, "需要管理员权限")
    return user
