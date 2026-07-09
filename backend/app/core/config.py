"""全局配置 — 所有敏感值从环境变量读取，不提供不安全默认值"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_file tries multiple paths: repo root (local dev) or /app (Docker container)
    _env_paths = [
        str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        str(Path(__file__).resolve().parent.parent.parent / ".env"),
        "/app/.env",
    ]
    _env_file = next((p for p in _env_paths if Path(p).exists()), ".env")
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库 (生产环境必须通过环境变量覆盖)
    database_url: str = ""

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_embedding_model: str = "deepseek-embedding"

    # 生成参数
    max_chapter_tokens: int = 4000
    context_prev_chapters: int = 5

    # Auth — 生产环境必须通过环境变量覆盖
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    admin_username: str = "admin"
    admin_password: str = ""

    # 加密
    account_encryption_key: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY 未设置，请在 .env 中配置。"
                "生成方法: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if not self.admin_password:
            raise ValueError("ADMIN_PASSWORD 未设置，请在 .env 中配置")
        if not self.database_url:
            raise ValueError("DATABASE_URL 未设置，请在 .env 中配置数据库连接字符串")
        # 启动时校验加密密钥格式（非空且为合法 Fernet key）
        if self.account_encryption_key:
            try:
                from cryptography.fernet import Fernet
                Fernet(self.account_encryption_key.encode() if isinstance(self.account_encryption_key, str) else self.account_encryption_key)
            except Exception as e:
                raise ValueError(f"ACCOUNT_ENCRYPTION_KEY 格式无效: {e}") from e

    # 服务
    api_host: str = "0.0.0.0"
    api_port: int = 8100
    cors_origins: str = "http://localhost:8080,http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"

    # Cookie 安全策略：生产建议 COOKIE_SECURE=true、COOKIE_SAMESITE=lax/strict。
    # 如果前后端跨站部署且必须走 cookie，需要 https + samesite=none + secure=true。
    cookie_secure: bool = False
    cookie_samesite: str = "lax"


settings = Settings()
