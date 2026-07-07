"""全局配置 — 所有敏感值从环境变量读取，不提供不安全默认值"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_file tries multiple paths: repo root (local dev) or /app (Docker container)
    _env_paths = [
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent / ".env"),
        "/app/.env",
    ]
    _env_file = next((p for p in _env_paths if __import__("pathlib").Path(p).exists()), ".env")
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 数据库
    database_url: str = "postgresql+asyncpg://novelcraft:novelcraft123@localhost:5432/novelcraft_v7"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 生成参数
    max_chapter_tokens: int = 4000
    context_prev_chapters: int = 5

    # Auth — 生产环境必须通过环境变量覆盖
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 720
    admin_username: str = "admin"
    admin_password: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY 未设置，请在 .env 中配置。"
                "生成方法: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if not self.admin_password:
            raise ValueError("ADMIN_PASSWORD 未设置，请在 .env 中配置")

    # 加密
    account_encryption_key: str = ""

    # 服务
    api_host: str = "0.0.0.0"
    api_port: int = 8100
    cors_origins: str = "http://localhost:8080,http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
