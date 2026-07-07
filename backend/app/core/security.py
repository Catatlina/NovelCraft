"""安全工具 — scrypt 密码哈希 + JWT"""
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
        return dk.hex() == stored
    except (ValueError, AttributeError):
        return False


def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiration_hours)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None
