"""
Phase 4: 发布执行记录 API — 批量发布 + 步骤日志 + 截图管理。
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, PlatformAccount, PublishExecution, User
from app.schemas import PublishExecuteRequest, PublishExecuteResponse, PublishExecutionOut

router = APIRouter(prefix="/api/v1/publish-executions", tags=["publish_executions"])


async def _validate_publish_scope(
    db: AsyncSession,
    *,
    project: NovelProject,
    user: User,
    chapter_ids: list[str],
    account_id: str | None,
) -> list[uuid.UUID]:
    """发布前强校验：章节必须属于当前项目，平台账号必须属于当前用户。"""
    if not chapter_ids:
        raise HTTPException(400, "至少选择一个要发布的章节")

    parsed_ids: list[uuid.UUID] = []
    for cid in chapter_ids:
        try:
            parsed_ids.append(uuid.UUID(str(cid)))
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(400, f"无效章节 ID: {cid}")

    rows = await db.execute(
        select(NovelChapter.id).where(
            NovelChapter.id.in_(parsed_ids),
            NovelChapter.project_id == project.id,
        )
    )
    existing = {row[0] for row in rows.all()}
    missing = [str(cid) for cid in parsed_ids if cid not in existing]
    if missing:
        # 不暴露跨租户章节是否真实存在，统一按不存在处理。
        raise HTTPException(404, f"章节不存在或不属于当前项目: {', '.join(missing)}")

    if account_id:
        try:
            aid = uuid.UUID(str(account_id))
        except (ValueError, AttributeError, TypeError):
            raise HTTPException(400, "无效的平台账号 ID")
        acct = await db.scalar(
            select(PlatformAccount).where(
                PlatformAccount.id == aid,
                PlatformAccount.user_id == user.id,
            )
        )
        if not acct:
            raise HTTPException(404, "平台账号不存在或不属于当前用户")
    return parsed_ids


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------


async def _run_publish_execution(
    execution_id: str,
    platform: str,
    chapter_ids: list[str],
    headless: bool,
    account_id: str | None = None,
) -> None:
    """Background task: execute Playwright publish and update DB."""
    from app.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PublishExecution, NovelProject)
            .join(NovelProject, PublishExecution.project_id == NovelProject.id)
            .where(PublishExecution.id == uuid.UUID(str(execution_id)))
        )
        row = result.one_or_none()
        if not row:
            return
        execution, project = row

        execution.status = "running"
        execution.steps = [{"step": "started", "ts": datetime.utcnow().isoformat()}]
        await db.commit()

        try:
            # Load chapters
            chapters_data = []
            for cid_str in (chapter_ids or []):
                try:
                    cid = uuid.UUID(cid_str)
                except (ValueError, AttributeError):
                    continue
                ch_result = await db.execute(
                    select(NovelChapter).where(
                        NovelChapter.id == cid,
                        NovelChapter.project_id == project.id,
                    )
                )
                ch = ch_result.scalar_one_or_none()
                if ch:
                    chapters_data.append({
                        "id": str(ch.id),
                        "chapter_num": ch.chapter_num,
                        "title": ch.title or f"Chapter {ch.chapter_num}",
                        "content": ch.content or "",
                        "summary": ch.summary or "",
                        "tags": [],
                    })

            if not chapters_data:
                execution.status = "failed"
                execution.logs = "No valid chapters to publish"
                execution.steps.append({"step": "no_chapters", "ts": datetime.utcnow().isoformat()})
                await db.commit()
                return

            # Load credentials
            credentials: dict[str, str] = {}
            if account_id:
                try:
                    aid = uuid.UUID(account_id)
                    acct_result = await db.execute(
                        select(PlatformAccount).where(
                            PlatformAccount.id == aid,
                            PlatformAccount.user_id == project.user_id,
                        )
                    )
                    acct = acct_result.scalar_one_or_none()
                    if acct:
                        import json as _json
                        from app.api.platform_accounts import decrypt_credentials
                        raw = decrypt_credentials(acct.encrypted_credentials)
                        credentials = _json.loads(raw)
                except Exception as e:
                    execution.status = "failed"
                    execution.logs = f"平台账号凭证解密失败: {type(e).__name__}: {e}"
                    execution.steps.append({"step": "credentials_error", "ts": datetime.utcnow().isoformat(), "error": str(e)})
                    await db.commit()
                    return

            # Execute publish via Playwright
            from app.services.playwright_publisher import publish_to_platform

            all_results = []
            all_screenshots: list[str] = []
            all_logs: list[str] = []

            for chapter in chapters_data:
                result = await publish_to_platform(
                    platform=platform,
                    account_credentials=credentials,
                    chapter=chapter,
                    headless=headless,
                )
                all_results.append(result)
                all_screenshots.extend(result.get("screenshots", []))
                all_logs.append(result.get("logs", ""))

            # Update execution record
            succeeded = [r for r in all_results if r.get("status") == "success"]
            execution.status = "success" if len(succeeded) == len(all_results) else (
                "partial" if succeeded else "failed"
            )
            execution.screenshots = all_screenshots
            execution.logs = "\n---\n".join(all_logs)
            execution.steps.append({
                "step": "completed",
                "ts": datetime.utcnow().isoformat(),
                "results": all_results,
            })

        except Exception as e:
            execution.status = "failed"
            execution.logs = f"Exception: {type(e).__name__}: {e}"
            execution.steps.append({
                "step": "error",
                "ts": datetime.utcnow().isoformat(),
                "error": str(e),
            })

        await db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{project_id}/execute", response_model=PublishExecuteResponse)
async def execute_publish(
    project_id: str,
    req: PublishExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发 Playwright 发布，创建 publish_executions 记录"""
    project = await get_user_project(project_id, user, db)
    validated_chapter_ids = await _validate_publish_scope(
        db, project=project, user=user, chapter_ids=req.chapter_ids, account_id=req.account_id
    )

    execution = PublishExecution(
        id=uuid.uuid4(),
        project_id=project.id,
        platform=req.platform,
        chapters=[str(cid) for cid in validated_chapter_ids],
        status="pending",
        steps=[],
        logs="Queued for execution",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 生产级任务派发：使用 Celery 队列，避免 API 进程重启导致发布任务丢失。
    from app.tasks.pipeline import celery_app

    try:
        celery_app.send_task(
            "publish_execution_task",
            args=[str(execution.id), req.platform, [str(cid) for cid in validated_chapter_ids], req.headless, req.account_id],
            queue="publish",
        )
    except Exception as e:
        # Redis/Celery 不可用时不能留下永久 pending 任务；明确回写入队失败状态。
        execution.status = "failed_enqueue"
        execution.logs = f"Celery enqueue failed: {type(e).__name__}: {e}"
        execution.steps = [{"step": "enqueue_failed", "ts": datetime.utcnow().isoformat(), "error": str(e)}]
        await db.commit()
        raise HTTPException(503, "发布任务入队失败，请检查 Redis/Celery 服务") from e

    return PublishExecuteResponse(
        execution_id=str(execution.id),
        status="pending",
        message=f"Publish execution queued for platform: {req.platform}",
    )


@router.get("/execution/{execution_id}", response_model=PublishExecutionOut)
async def get_execution_status(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询发布执行状态（含截图 + 步骤日志）"""
    try:
        eid = uuid.UUID(execution_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "无效的执行 ID")

    result = await db.execute(
        select(PublishExecution)
        .join(NovelProject, PublishExecution.project_id == NovelProject.id)
        .where(PublishExecution.id == eid, NovelProject.user_id == user.id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(404, "发布执行记录不存在")

    return PublishExecutionOut(
        id=execution.id,
        project_id=execution.project_id,
        platform=execution.platform,
        chapters=execution.chapters,
        status=execution.status,
        steps=execution.steps,
        screenshots=execution.screenshots,
        logs=execution.logs,
        created_at=execution.created_at,
    )


@router.get("/{project_id}/executions")
async def list_executions(
    project_id: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出项目的发布执行历史"""
    project = await get_user_project(project_id, user, db)

    stmt = select(PublishExecution).where(PublishExecution.project_id == project.id)
    if status:
        stmt = stmt.where(PublishExecution.status == status)
    stmt = stmt.order_by(PublishExecution.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    executions = result.scalars().all()

    return {
        "executions": [
            {
                "id": str(e.id),
                "platform": e.platform,
                "chapters": e.chapters,
                "status": e.status,
                "screenshot_count": len(e.screenshots or []),
                "created_at": str(e.created_at),
            }
            for e in executions
        ],
        "total": len(executions),
    }
