"""
Phase 4: 发布执行记录 API — 批量发布 + 步骤日志 + 截图管理。
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, PlatformAccount, PublishExecution, User
from app.schemas import PublishExecuteRequest, PublishExecuteResponse, PublishExecutionOut

router = APIRouter(prefix="/api/v1/publish-executions", tags=["publish_executions"])


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
            select(PublishExecution).where(PublishExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            return

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
                    select(NovelChapter).where(NovelChapter.id == cid)
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
                        select(PlatformAccount).where(PlatformAccount.id == aid)
                    )
                    acct = acct_result.scalar_one_or_none()
                    if acct:
                        import json as _json
                        from app.api.platform_accounts import decrypt_credentials
                        raw = decrypt_credentials(acct.encrypted_credentials)
                        credentials = _json.loads(raw)
                except Exception:
                    pass

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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """触发 Playwright 发布，创建 publish_executions 记录"""
    project = await get_user_project(project_id, user, db)

    execution = PublishExecution(
        id=uuid.uuid4(),
        project_id=project.id,
        platform=req.platform,
        chapters=req.chapter_ids,
        status="pending",
        steps=[],
        logs="Queued for execution",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Schedule background publish
    background_tasks.add_task(
        _run_publish_execution,
        execution_id=str(execution.id),
        platform=req.platform,
        chapter_ids=req.chapter_ids,
        headless=req.headless,
        account_id=req.account_id,
    )

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

    result = await db.execute(select(PublishExecution).where(PublishExecution.id == eid))
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
