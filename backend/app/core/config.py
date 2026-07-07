"""全局配置 — 所有敏感值从环境变量读取，不提供不安全默认值"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    # 加密
    account_encryption_key: str = ""

    # 服务
    api_host: str = "0.0.0.0"
    api_port: int = 8100
    cors_origins: str = "http://localhost:8080,http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
