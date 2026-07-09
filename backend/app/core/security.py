"""安全工具 — scrypt 密码哈希 + JWT (access + refresh tokens)"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """scrypt KDF — 抗暴力破解，N=16384, r=8, p=1"""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return salt.hex() + ":" + dk.hex()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt_hex, stored = hashed.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(plain.encode(), salt=salt, n=16384, r=8, p=1)
        return secrets.compare_digest(dk.hex(), stored)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: str, token_version: int = 0) -> str:
    """短期 access token (默认 15 分钟)"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access", "tv": token_version},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    """长期 refresh token (默认 7 天)"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh", "tv": token_version},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_token(user_id: str) -> str:
    """向后兼容: 返回 access token"""
    return create_access_token(user_id)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def decode_token_with_type(token: str, expected_type: str = "access") -> str | None:
    """解码 token 并校验类型"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != expected_type:
            return None
        return payload.get("sub")
    except JWTError:
        return None
