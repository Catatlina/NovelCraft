"""星禾写作助手 API v8.0"""
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-DeepSeek-API-Key", "X-DeepSeek-Model"],
)

# Middleware: 从前端 header 读取 DeepSeek API Key，注入请求上下文
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.deepseek_client import set_request_api_key, set_request_model

class DeepSeekKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        key = request.headers.get("X-DeepSeek-API-Key")
        model = request.headers.get("X-DeepSeek-Model")
        set_request_api_key(key)
        set_request_model(model)
        response = await call_next(request)
        return response

app.add_middleware(DeepSeekKeyMiddleware)

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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "8.0.0"}
