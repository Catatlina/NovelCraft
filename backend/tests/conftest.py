"""Test bootstrap: provide safe local defaults before app modules import settings."""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me-32-bytes")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdmin123")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COOKIE_SAMESITE", "lax")
os.environ.setdefault("ACCOUNT_ENCRYPTION_KEY", "")
