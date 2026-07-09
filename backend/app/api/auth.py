"""认证 API — 注册/登录/刷新 token（含速率限制 + httpOnly cookie）"""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.ratelimit import limiter
from secrets import token_urlsafe

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token_payload,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


def _validate_password(password: str) -> str:
    """校验密码强度，返回错误消息或空字符串"""
    if not password or len(password) < 8:
        return "密码长度至少8个字符"
    if not any(c.isupper() for c in password) and not any(c.islower() for c in password):
        return "密码需包含至少一个字母"
    if not any(c.isdigit() for c in password):
        return "密码需包含至少一个数字"
    return ""


def _set_auth_cookies(response: Response, user_id: str, token_version: int = 0) -> dict:
    """设置 httpOnly secure cookies 并返回 user 对象"""
    access = create_access_token(user_id, token_version)
    refresh = create_refresh_token(user_id, token_version)
    secure = settings.cookie_secure
    samesite = settings.cookie_samesite.lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    if samesite == "none" and not secure:
        # 浏览器要求 SameSite=None 必须 Secure；配置错误时拒绝不安全降级。
        raise HTTPException(500, "COOKIE_SAMESITE=none 时必须设置 COOKIE_SECURE=true")
    response.set_cookie(
        key="access_token", value=access,
        httponly=True, secure=secure,
        max_age=settings.jwt_access_expire_minutes * 60,
        samesite=samesite,
    )
    response.set_cookie(
        key="refresh_token", value=refresh,
        httponly=True, secure=secure,
        max_age=settings.jwt_refresh_expire_days * 86400,
        samesite=samesite,
    )
    # 非 httpOnly CSRF cookie：前端读取后放入 X-CSRF-Token，服务端做双提交校验。
    response.set_cookie(
        key="csrf_token", value=token_urlsafe(32),
        httponly=False, secure=secure,
        max_age=settings.jwt_refresh_expire_days * 86400,
        samesite=samesite,
    )
    return {}


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, req: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    pwd_err = _validate_password(req.password)
    if pwd_err:
        raise HTTPException(422, pwd_err)
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "用户名已存在")
    user = User(username=req.username, password_hash=hash_password(req.password), email=req.email)
    db.add(user)
    await db.commit()
    _set_auth_cookies(response, str(user.id), user.token_version)
    return {"user": {"id": str(user.id), "username": user.username, "email": user.email}}


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    _set_auth_cookies(response, str(user.id), user.token_version)
    return {"user": {"id": str(user.id), "username": user.username, "email": user.email}}


@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh_token(
    response: Response,
    db: AsyncSession = Depends(get_db),
    req: RefreshRequest | None = None,
    refresh_token: str | None = Cookie(None),
):
    """用 refresh token 换取新的 access token。

    优先从 httpOnly cookie 读取（浏览器场景：前端 JS 读不到 cookie 值，
    只需 fetch 时带上 credentials:'include'，不需要在请求体里传任何东西）。
    请求体里的 refresh_token 作为向后兼容保留，供非浏览器 API 客户端使用。
    """
    token = refresh_token or (req.refresh_token if req else None)
    if not token:
        raise HTTPException(401, "未提供 refresh token")

    payload = decode_token_payload(token, "refresh")
    if not payload:
        raise HTTPException(401, "refresh token 无效或已过期")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "refresh token 无效或已过期")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("csrf_token")
        raise HTTPException(401, "用户不存在或已禁用")

    if payload.get("tv", 0) != user.token_version:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("csrf_token")
        raise HTTPException(401, "refresh token 已失效，请重新登录")

    _set_auth_cookies(response, str(user.id), user.token_version)
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response, db: AsyncSession = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """清除认证 cookies 并使所有已签发 token 失效"""
    user.token_version += 1
    await db.commit()
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")
    return {"status": "ok"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """返回当前登录用户信息（前端刷新页面后用来恢复登录态）。

    此前前端 authStore.checkAuth() 一直在调用这个路径，但后端从未实现，
    导致每次刷新页面 httpOnly cookie 明明还有效，前端却因为 404 把用户当作
    未登录处理——这里补上这个此前一直缺失的端点。
    """
    return {"id": str(user.id), "username": user.username, "email": user.email}
