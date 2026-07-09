"""星禾写作助手 API v8.0"""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.core.ratelimit import ai_limiter
from app.api import (
    ab_tests,
    analytics,
    auth,
    chapter_versions,
    feedback,
    foreshadows,
    generation,
    hit_analysis,
    knowledge,
    learning,
    ops,
    pipeline,
    platform_accounts,
    projects,
    prompt_optimization,
    publish,
    publish_executions,
    quality,
    quality_benchmarks,
    scan,
    search,
    short_story,
    tools,
    translate,
    world_rules,
    world_setting_embeddings,
    user_ai_settings,
)
from app.core.config import settings
from app.core.security import hash_password
from app.db.database import AsyncSessionLocal, engine
from app.db.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed admin user (tables created via schema_v8.sql run separately)
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(User).where(User.username == settings.admin_username))
        if not r.scalar_one_or_none():
            db.add(
                User(
                    id=uuid.uuid4(),
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    email="admin@novelcraft.local",
                )
            )
            await db.commit()
    yield


app = FastAPI(title="星禾写作助手 API", version="8.0.0", lifespan=lifespan)

# slowapi 限流：注册官方异常处理器，让限流触发时返回带 Retry-After 头的
# 规范 429 响应。app.state.limiter 是 slowapi 处理器读取配置的约定位置。
app.state.limiter = ai_limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "*" in _cors_origins:
    raise RuntimeError("CORS_ORIGINS 不能在 allow_credentials=True 时使用 *，请显式配置前端域名")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

from secrets import token_urlsafe
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.security import decode_token_with_type
from app.services.deepseek_client import set_request_api_key, set_request_model


class CSRFMiddleware(BaseHTTPMiddleware):
    """Cookie 认证下的 CSRF 防护。

    认证态的 POST/PUT/PATCH/DELETE 必须携带与 csrf_token cookie 一致的
    X-CSRF-Token。登录/注册/刷新接口不强制，因为用户尚未有会话或正在恢复会话。
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    EXEMPT_PATHS = {"/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"}

    async def dispatch(self, request, call_next):
        if request.method not in self.SAFE_METHODS and request.url.path not in self.EXEMPT_PATHS:
            if request.cookies.get("access_token"):
                cookie_token = request.cookies.get("csrf_token")
                header_token = request.headers.get("X-CSRF-Token")
                if not cookie_token or not header_token or cookie_token != header_token:
                    return JSONResponse({"detail": "CSRF 校验失败"}, status_code=403)
        return await call_next(request)


class DeepSeekKeyMiddleware(BaseHTTPMiddleware):
    """从服务端用户配置加载 AI Key，不再信任前端 header/localStorage。"""

    async def dispatch(self, request, call_next):
        set_request_api_key(None)
        set_request_model(None)
        token = request.cookies.get("access_token")
        user_id = decode_token_with_type(token, "access") if token else None
        if user_id:
            try:
                from app.api.user_ai_settings import load_user_deepseek_settings
                async with AsyncSessionLocal() as db:
                    key, model = await load_user_deepseek_settings(db, uuid.UUID(user_id))
                    set_request_api_key(key)
                    set_request_model(model)
            except Exception:
                # 配置损坏不应影响普通页面/API；真正调用模型时会给出明确错误。
                set_request_api_key(None)
                set_request_model(None)
        return await call_next(request)


app.add_middleware(DeepSeekKeyMiddleware)
app.add_middleware(CSRFMiddleware)

# ---- v7 原有路由 ----
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router)
app.include_router(generation.router)
app.include_router(tools.router)
app.include_router(quality.router)
app.include_router(foreshadows.router)
app.include_router(pipeline.router)
app.include_router(publish.router)
app.include_router(feedback.router)
app.include_router(hit_analysis.router)
app.include_router(knowledge.router)
app.include_router(ops.router)
app.include_router(learning.router)
app.include_router(scan.router)

# ---- v8 新增路由 (Phase 3-9) ----
app.include_router(world_rules.router)                 # Phase 3: 世界观推理规则
app.include_router(world_setting_embeddings.router)    # Phase 3: 世界观 Embedding
app.include_router(platform_accounts.router)           # Phase 4: 平台账号
app.include_router(publish_executions.router)          # Phase 4: 发布执行
app.include_router(quality_benchmarks.router)          # Phase 5: 质量基准
app.include_router(ab_tests.router)                    # Phase 6: A/B 测试
app.include_router(prompt_optimization.router)         # Phase 6: Prompt 优化
app.include_router(chapter_versions.router)            # Phase 7: 章节版本
app.include_router(analytics.router)                   # Phase 8: 埋点分析
app.include_router(search.router)                      # Phase 9: 全局搜索
app.include_router(short_story.router)                 # Phase 3: 短篇生成
app.include_router(translate.router)                   # Phase 3: 翻译出海
app.include_router(user_ai_settings.router)                # 用户级 AI 配置


@app.get("/health")
async def health():
    return {"status": "ok", "version": "8.0.0"}


# Global exception handler (P1-5)
import traceback as _tb
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("novelcraft").error(
        f"Unhandled exception: {exc}", extra={
            "path": str(request.url),
            "method": request.method,
            "traceback": _tb.format_exc(),
        }
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "服务器内部错误，请稍后重试"},
    )
