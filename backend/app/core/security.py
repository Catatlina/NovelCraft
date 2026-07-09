"""安全工具 — scrypt 密码哈希 + JWT (access + refresh tokens)"""
import hashlib
import hmac
import secrets
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """scrypt KDF — 抗暴力破解，N=16384, r=8, p=1"""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + dk.hex()


def verify_password(plain: str, hashed: str) -> bool:
    """恒定时间密码比较 (P0-2): hmac.compare_digest 防时序攻击。
    异常分支也执行伪计算保持恒定时间，避免分支信息泄露。"""
    try:
        salt_hex, stored = hashed.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(plain.encode(), salt=salt, n=16384, r=8, p=1)
        return hmac.compare_digest(dk.hex(), stored)
    except (ValueError, AttributeError):
        # 恒定时间：异常路径也做伪计算参与比较，避免异常分支泄露时序信息
        dummy = hashlib.scrypt(b"", salt=secrets.token_bytes(16), n=16384, r=8, p=1)
        return hmac.compare_digest(dummy.hex(), stored if ":" in (hashed or "") else "")


def create_access_token(user_id: str, token_version: int = 0) -> str:
    """短期 access token (默认 15 分钟), 携带 jti 用于单 token 撤销"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access",
         "tv": token_version, "jti": _uuid.uuid4().hex},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    """长期 refresh token (默认 7 天), 携带 jti 用于单 token 撤销"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh",
         "tv": token_version, "jti": _uuid.uuid4().hex},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token(user_id: str) -> str:
    """向后兼容: 返回 access token"""
    return create_access_token(user_id)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if _is_jti_revoked(payload.get("jti")):
            return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_token_with_type(token: str, expected_type: str = "access") -> str | None:
    """解码 token 并校验类型 + jti 黑名单"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            return None
        if _is_jti_revoked(payload.get("jti")):
            return None
        return payload.get("sub")
    except JWTError:
        return None


def _is_jti_revoked(jti: str | None) -> bool:
    """检查 jti 是否在黑名单中; jti 缺失时返回 False"""
    if not jti:
        return False
    try:
        from app.core.token_blacklist import is_revoked
        return is_revoked(jti)
    except Exception:
        return False  # Redis 不可用时放行
