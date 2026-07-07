"""
Phase 6: Prompt 优化日志 API — 记录 Prompt 参数调整历史。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import PromptOptimizationLog, User
from app.schemas import PromptOptimizationLogCreate, PromptOptimizationLogOut

router = APIRouter(prefix="/api/v1/prompt-optimization", tags=["prompt_optimization"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/log", response_model=PromptOptimizationLogOut)
async def log_prompt_change(
    req: PromptOptimizationLogCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """记录 Prompt 参数变更"""
    # Validate project ownership
    await get_user_project(str(req.project_id), user, db)

    entry = PromptOptimizationLog(
        id=uuid.uuid4(),
        project_id=req.project_id,
        prompt_name=req.prompt_name,
        params_before=req.params_before,
        params_after=req.params_after,
        reason=req.reason,
        quality_impact=req.quality_impact,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return PromptOptimizationLogOut(
        id=entry.id,
        project_id=entry.project_id,
        prompt_name=entry.prompt_name,
        params_before=entry.params_before,
        params_after=entry.params_after,
        reason=entry.reason,
        quality_impact=entry.quality_impact,
        applied_at=entry.applied_at,
    )


@router.get("/project/{project_id}")
async def get_optimization_history(
    project_id: str,
    prompt_name: str | None = Query(default=None, description="按 Prompt 名称过滤"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查看项目的 Prompt 优化历史"""
    await get_user_project(project_id, user, db)

    stmt = select(PromptOptimizationLog).where(
        PromptOptimizationLog.project_id == project_id
    )
    if prompt_name:
        stmt = stmt.where(PromptOptimizationLog.prompt_name == prompt_name)
    stmt = stmt.order_by(PromptOptimizationLog.applied_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    logs = result.scalars().all()

    # Count total for pagination
    count_stmt = select(func.count(PromptOptimizationLog.id)).where(
        PromptOptimizationLog.project_id == project_id
    )
    if prompt_name:
        count_stmt = count_stmt.where(PromptOptimizationLog.prompt_name == prompt_name)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    return {
        "project_id": project_id,
        "total": total,
        "history": [
            {
                "id": str(entry.id),
                "prompt_name": entry.prompt_name,
                "params_before": entry.params_before,
                "params_after": entry.params_after,
                "reason": entry.reason,
                "quality_impact": entry.quality_impact,
                "applied_at": str(entry.applied_at),
            }
            for entry in logs
        ],
    }


@router.get("/log/{log_id}")
async def get_log_detail(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查看单条优化日志详情"""
    try:
        lid = uuid.UUID(log_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "无效的日志 ID")

    result = await db.execute(
        select(PromptOptimizationLog).where(PromptOptimizationLog.id == lid)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, "优化日志不存在")

    return PromptOptimizationLogOut(
        id=entry.id,
        project_id=entry.project_id,
        prompt_name=entry.prompt_name,
        params_before=entry.params_before,
        params_after=entry.params_after,
        reason=entry.reason,
        quality_impact=entry.quality_impact,
        applied_at=entry.applied_at,
    )


@router.get("/stats/{project_id}")
async def get_optimization_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取项目 Prompt 优化统计"""
    await get_user_project(project_id, user, db)

    result = await db.execute(
        select(PromptOptimizationLog).where(
            PromptOptimizationLog.project_id == project_id
        ).order_by(PromptOptimizationLog.applied_at.desc())
    )
    logs = result.scalars().all()

    total = len(logs)
    quality_impacts = [l.quality_impact for l in logs if l.quality_impact is not None]
    avg_impact = sum(quality_impacts) / len(quality_impacts) if quality_impacts else 0.0

    prompt_counts: dict[str, int] = {}
    for l in logs:
        prompt_counts[l.prompt_name] = prompt_counts.get(l.prompt_name, 0) + 1

    return {
        "project_id": project_id,
        "total_optimizations": total,
        "average_quality_impact": round(avg_impact, 4),
        "optimizations_by_prompt": prompt_counts,
        "latest_optimization": str(logs[0].applied_at) if logs else None,
    }
