"""JWT 撤销黑名单 (P0-3) — 基于 Redis 存储 jti，TTL = token 剩余有效期。

登出 / 强制撤销时把 token 的 jti 写入黑名单；校验 token 时查黑名单，
命中即视为无效。使用独立 db(2) 避免与 Celery broker(0)/backend(1) 键冲突。

Redis 不可用时静默降级：登出不报错、校验放行（不阻断正常请求），
但撤销在 Redis 恢复前不生效——这与「token 自然过期」的安全模型一致。
"""
from datetime import datetime, timezone

import redis

from app.core.config import settings

_BLACKLIST_DB = 2
_client: "redis.Redis | None" = None


def _get_client() -> "redis.Redis | None":
    url = settings.redis_url
    if not url:
        return None
    global _client
    if _client is None:
        _client = redis.Redis.from_url(url, db=_BLACKLIST_DB, decode_responses=True)
    return _client


def revoke(jti: str, exp: datetime) -> None:
    """将 token 加入黑名单，TTL = 剩余有效期（秒）。失败静默跳过。"""
    if not jti:
        return
    client = _get_client()
    if client is None:
        return
    try:
        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            client.set(f"jwt:bl:{jti}", "1", ex=ttl)
    except Exception:
        # 黑名单写入失败不应阻断登出流程
        pass


def is_revoked(jti: str) -> bool:
    """检查 token 是否已撤销。jti 缺失或 Redis 不可用时返回 False（放行）。"""
    if not jti:
        return False
    client = _get_client()
    if client is None:
        return False
    try:
        return client.exists(f"jwt:bl:{jti}") == 1
    except Exception:
        return False
