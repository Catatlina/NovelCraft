"""
可视化配置中心 — 所有运行时配置可在 Web 页面编辑。
替代手动修改 .env 文件，保存时校验格式。
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.database import get_db
from app.db.models import User

router = APIRouter(prefix="/api/v1/config", tags=["config"])

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


class ConfigResponse(BaseModel):
    """所有可编辑的配置项"""
    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_embedding_model: str = "deepseek-embedding"
    # 定价 (¥/百万 tokens)
    deepseek_price_input: float = 1.0
    deepseek_price_output: float = 2.0
    deepseek_price_cache_hit: float = 0.25
    # 生成参数
    max_chapter_tokens: int = 4000
    context_prev_chapters: int = 5
    # 安全
    environment: str = "development"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cors_origins: str = "http://localhost:8080"
    # 管理
    admin_username: str = "admin"


class ConfigUpdateRequest(BaseModel):
    key: str  # 配置键名
    value: str  # 新值


def _read_env() -> dict[str, str]:
    """读取 .env 文件"""
    env = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    return env


def _write_env(env: dict[str, str]) -> None:
    """写入 .env 文件（保留注释和空行结构）"""
    lines = []
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            lines = f.readlines()

    updated = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in env:
                new_lines.append(f"{k}={env[k]}\n")
                updated.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 追加未写入的键
    for k, v in env.items():
        if k not in updated:
            new_lines.append(f"{k}={v}\n")

    with open(CONFIG_FILE, "w") as f:
        f.writelines(new_lines)


def _safe_key(key: str) -> str:
    """允许编辑的白名单键"""
    allowed = {
        "deepseek_api_key", "deepseek_base_url", "deepseek_model",
        "deepseek_embedding_model", "DEEPSEEK_PRICE_INPUT_PER_1M",
        "DEEPSEEK_PRICE_OUTPUT_PER_1M", "DEEPSEEK_PRICE_CACHE_HIT_PER_1M",
        "max_chapter_tokens", "context_prev_chapters",
        "environment", "COOKIE_SECURE", "COOKIE_SAMESITE",
        "CORS_ORIGINS", "admin_username", "TOKEN_BLACKLIST_FAIL_CLOSED",
        "REDIS_PASSWORD", "admin_password",
    }
    if key not in allowed:
        raise HTTPException(403, f"不允许编辑配置项: {key}")
    return key


@router.get("/", response_model=ConfigResponse)
async def get_config():
    """获取当前配置（敏感值脱敏）"""
    env = _read_env()
    return ConfigResponse(
        deepseek_api_key=_mask(env.get("deepseek_api_key", "")),
        deepseek_base_url=env.get("deepseek_base_url", "https://api.deepseek.com"),
        deepseek_model=env.get("deepseek_model", "deepseek-chat"),
        deepseek_embedding_model=env.get("deepseek_embedding_model", "deepseek-embedding"),
        deepseek_price_input=float(env.get("DEEPSEEK_PRICE_INPUT_PER_1M", "1.0")),
        deepseek_price_output=float(env.get("DEEPSEEK_PRICE_OUTPUT_PER_1M", "2.0")),
        deepseek_price_cache_hit=float(env.get("DEEPSEEK_PRICE_CACHE_HIT_PER_1M", "0.25")),
        max_chapter_tokens=int(env.get("max_chapter_tokens", "4000")),
        context_prev_chapters=int(env.get("context_prev_chapters", "5")),
        environment=env.get("environment", "development"),
        cookie_secure=env.get("COOKIE_SECURE", "false").lower() == "true",
        cookie_samesite=env.get("COOKIE_SAMESITE", "lax"),
        cors_origins=env.get("CORS_ORIGINS", "http://localhost:8080"),
        admin_username=env.get("admin_username", "admin"),
    )


@router.put("/")
async def update_config(
    req: ConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """更新配置项（仅管理员）"""
    key = _safe_key(req.key)
    env = _read_env()
    env[key] = req.value
    _write_env(env)
    return {"status": "ok", "key": key, "saved": True}


@router.get("/status")
async def config_status():
    """系统状态：API 健康 + DB 连接 + Redis + DeepSeek 配置状态"""
    import sys
    env = _read_env()
    has_deepseek = bool(env.get("deepseek_api_key", "").strip() and "sk-" in env.get("deepseek_api_key", ""))
    return {
        "api": "ok",
        "version": "8.0.0",
        "python": sys.version.split()[0],
        "deepseek_configured": has_deepseek,
        "deepseek_model": env.get("deepseek_model", "deepseek-chat"),
        "environment": env.get("environment", "development"),
        "cookie_secure": env.get("COOKIE_SECURE", "false").lower() == "true",
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


def _mask(val: str) -> str:
    if not val or len(val) < 12:
        return val
    return val[:6] + "..." + val[-4:]
