"""批量生成 + 调度监控 + 三级流水线 API (Phase 4)"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import GenerationTask, NovelProject, User
from app.tasks.pipeline import (
    enqueue_batch_generation,
    idea_pipeline_task,
    outline_pipeline_task,
    publish_pipeline_task,
)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


# -----------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------


class BatchGenerateRequest(BaseModel):
    project_id: str
    chapter_count: int = 10


class IdeaPipelineRequest(BaseModel):
    project_id: str
    platforms: list[str] | None = None


class OutlinePipelineRequest(BaseModel):
    project_id: str
    topic: str
    world_setting: str = ""
    target_words: int = Field(default=1000000, ge=100000, le=10000000)
    outline_count: int = Field(default=3, ge=1, le=10)


class PublishPipelineRequest(BaseModel):
    project_id: str
    target_platforms: list[str]
    chapters: list[int] | None = None
    glossary: dict | None = None


# -----------------------------------------------------------
# Batch Generate
# -----------------------------------------------------------


@router.post("/batch-generate")
async def batch_generate(req: BatchGenerateRequest, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    await get_user_project(req.project_id, user, db)
    try:
        batch_id = await enqueue_batch_generation(db, req.project_id, req.chapter_count)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"batch_id": batch_id, "chapter_count": req.chapter_count, "status": "queued"}


# -----------------------------------------------------------
# Idea Pipeline
# -----------------------------------------------------------


@router.post("/idea")
async def trigger_idea_pipeline(
    req: IdeaPipelineRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发选题流水线：扫描平台榜单 → 去重 → 分析评分 → 推荐排序"""
    await get_user_project(req.project_id, user, db)
    task_result = idea_pipeline_task.delay(req.project_id, req.platforms)
    return {
        "task_id": task_result.id,
        "project_id": req.project_id,
        "status": "queued",
        "platforms": req.platforms or ["全部平台"],
    }


@router.get("/idea/{project_id}/result")
async def get_idea_result(
    project_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询选题流水线的最新结果"""
    await get_user_project(project_id, user, db)
    result = await db.execute(
        select(GenerationTask)
        .where(
            GenerationTask.project_id == project_id,
            GenerationTask.type == "idea_pipeline",
        )
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    return {
        "project_id": project_id,
        "tasks": [
            {
                "id": str(t.id),
                "status": t.status,
                "progress": t.progress,
                "error_log": t.error_log,
                "created_at": str(t.created_at),
            }
            for t in tasks
        ],
    }


# -----------------------------------------------------------
# Outline Pipeline
# -----------------------------------------------------------


@router.post("/outline")
async def trigger_outline_pipeline(
    req: OutlinePipelineRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发大纲流水线：基于选题+世界观 → 批量生成大纲变体 → 校验 → 评分"""
    await get_user_project(req.project_id, user, db)
    task_result = outline_pipeline_task.delay(
        req.project_id, req.topic, req.world_setting,
        req.target_words, req.outline_count,
    )
    return {
        "task_id": task_result.id,
        "project_id": req.project_id,
        "topic": req.topic,
        "outline_count": req.outline_count,
        "status": "queued",
    }


@router.get("/outline/{project_id}/result")
async def get_outline_result(
    project_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询大纲流水线的最新结果"""
    await get_user_project(project_id, user, db)
    result = await db.execute(
        select(GenerationTask)
        .where(
            GenerationTask.project_id == project_id,
            GenerationTask.type == "outline_pipeline",
        )
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    return {
        "project_id": project_id,
        "tasks": [
            {
                "id": str(t.id),
                "status": t.status,
                "progress": t.progress,
                "error_log": t.error_log,
                "created_at": str(t.created_at),
            }
            for t in tasks
        ],
    }


# -----------------------------------------------------------
# Publish Pipeline
# -----------------------------------------------------------


@router.post("/publish")
async def trigger_publish_pipeline(
    req: PublishPipelineRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发发布流水线：选择章节 → 翻译 → 格式适配 → 发布 → 验证"""
    await get_user_project(req.project_id, user, db)
    task_result = publish_pipeline_task.delay(
        req.project_id, req.target_platforms, req.chapters, req.glossary,
    )
    return {
        "task_id": task_result.id,
        "project_id": req.project_id,
        "platforms": req.target_platforms,
        "chapters": req.chapters or "全部草稿章节",
        "status": "queued",
    }


@router.get("/publish/{project_id}/result")
async def get_publish_result(
    project_id: str,
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询发布流水线的最新结果"""
    await get_user_project(project_id, user, db)
    result = await db.execute(
        select(GenerationTask)
        .where(
            GenerationTask.project_id == project_id,
            GenerationTask.type == "publish_pipeline",
        )
        .order_by(GenerationTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()
    return {
        "project_id": project_id,
        "tasks": [
            {
                "id": str(t.id),
                "status": t.status,
                "progress": t.progress,
                "error_log": t.error_log,
                "created_at": str(t.created_at),
            }
            for t in tasks
        ],
    }


# -----------------------------------------------------------
# Pipeline Status & Cancel (existing)
# -----------------------------------------------------------


@router.get("/status")
async def pipeline_status(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Filter tasks by user's projects
    user_projects = await db.execute(select(NovelProject.id).where(NovelProject.user_id == user.id))
    user_pids = [p[0] for p in user_projects]
    tasks = await db.execute(
        select(GenerationTask).where(GenerationTask.project_id.in_(user_pids))
        .order_by(GenerationTask.created_at.desc()).limit(20)
    )
    tasks_list = [{"id": str(t.id), "project_id": str(t.project_id), "type": t.type,
                   "status": t.status, "progress": t.progress,
                   "error_log": t.error_log, "created_at": str(t.created_at)}
                  for t in tasks.scalars().all()]
    statuses = {}
    for t in tasks_list:
        statuses[t["status"]] = statuses.get(t["status"], 0) + 1
    return {"queues": {"idea": statuses.get("queued", 0), "running": statuses.get("running", 0),
            "done": statuses.get("done", 0), "failed": statuses.get("failed", 0)},
            "recent_tasks": tasks_list[:10]}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    task = await db.get(GenerationTask, task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    # Verify user owns the project
    user_projects = await db.execute(select(NovelProject.id).where(NovelProject.user_id == user.id))
    if task.project_id not in {p[0] for p in user_projects}:
        raise HTTPException(404, "任务不存在")
    task.status = "cancelled"
    await db.commit()
    return {"status": "cancelled"}
