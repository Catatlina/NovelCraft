"""
Phase 9.1: 数据分析看板 API — KPI 卡片 + 趋势图数据 + 平台对比。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import (
    AnalyticsEvent,
    NovelChapter,
    NovelProject,
    PublishRecord,
    QualityReview,
    User,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.post("/track")
async def track_event(
    project_id: str,
    event_type: str,
    event_data: dict = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录埋点事件。"""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(404, "项目不存在")
    await get_user_project(project_id, user, db)

    event = AnalyticsEvent(
        id=uuid.uuid4(),
        project_id=pid,
        event_type=event_type,
        event_data=event_data or {},
    )
    db.add(event)
    await db.commit()
    return {"detail": "事件已记录", "event_id": str(event.id)}


@router.get("/events")
async def query_events(
    project_id: str,
    event_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询埋点事件。"""
    await get_user_project(project_id, user, db)
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        pid = uuid.UUID(project_id)

    stmt = select(AnalyticsEvent).where(AnalyticsEvent.project_id == pid)
    if event_type:
        stmt = stmt.where(AnalyticsEvent.event_type == event_type)
    if start_date:
        stmt = stmt.where(AnalyticsEvent.created_at >= start_date)
    if end_date:
        stmt = stmt.where(AnalyticsEvent.created_at <= end_date)
    stmt = stmt.order_by(AnalyticsEvent.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "project_id": str(e.project_id),
            "event_type": e.event_type,
            "event_data": e.event_data,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/dashboard")
async def analytics_dashboard(
    project_id: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    KPI 卡片 + 趋势图数据 + 平台对比。
    若指定 project_id，返回该项目维度的数据；
    否则返回用户所有项目的聚合数据。
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 确定查询范围
    if project_id:
        await get_user_project(project_id, user, db)
        pids = [uuid.UUID(project_id)]
    else:
        pids_result = await db.execute(
            select(NovelProject.id).where(NovelProject.user_id == user.id)
        )
        pids = [r[0] for r in pids_result]

    if not pids:
        return _empty_dashboard()

    # KPI 卡片
    # 总字数
    word_result = await db.execute(
        select(func.sum(NovelChapter.word_count)).where(
            NovelChapter.project_id.in_(pids)
        )
    )
    total_words = word_result.scalar() or 0

    # 总章节数
    chapter_count_result = await db.execute(
        select(func.count(NovelChapter.id)).where(
            NovelChapter.project_id.in_(pids)
        )
    )
    total_chapters = chapter_count_result.scalar() or 0

    # 项目数
    total_projects = len(pids)

    # 趋势数据 — 按日期聚合新创建章节
    trend_result = await db.execute(
        select(
            func.date(NovelChapter.created_at).label("date"),
            func.count(NovelChapter.id).label("count"),
        )
        .where(
            NovelChapter.project_id.in_(pids),
            NovelChapter.created_at >= since,
        )
        .group_by(func.date(NovelChapter.created_at))
        .order_by("date")
    )
    trend_data = [
        {"date": str(row.date), "chapters_created": row.count}
        for row in trend_result
    ]

    # 发布记录统计
    pub_result = await db.execute(
        select(
            PublishRecord.platform,
            func.count(PublishRecord.id).label("count"),
        )
        .join(NovelChapter, PublishRecord.chapter_id == NovelChapter.id)
        .where(NovelChapter.project_id.in_(pids))
        .group_by(PublishRecord.platform)
    )
    platform_stats = {row.platform: row.count for row in pub_result}

    # 质量审查统计
    quality_result = await db.execute(
        select(
            QualityReview.dimension,
            func.avg(QualityReview.score).label("avg_score"),
        )
        .join(NovelChapter, QualityReview.chapter_id == NovelChapter.id)
        .where(NovelChapter.project_id.in_(pids))
        .group_by(QualityReview.dimension)
    )
    quality_stats = {
        row.dimension: {"avg_score": float(row.avg_score) if row.avg_score else 0}
        for row in quality_result
    }

    # 事件统计
    event_result = await db.execute(
        select(
            AnalyticsEvent.event_type,
            func.count(AnalyticsEvent.id).label("count"),
        )
        .where(
            AnalyticsEvent.project_id.in_(pids),
            AnalyticsEvent.created_at >= since,
        )
        .group_by(AnalyticsEvent.event_type)
    )
    event_stats = {row.event_type: row.count for row in event_result}

    return {
        "kpi": {
            "total_projects": total_projects,
            "total_chapters": total_chapters,
            "total_words": total_words,
            "avg_chapter_length": round(total_words / total_chapters, 1) if total_chapters > 0 else 0,
        },
        "trend": trend_data,
        "platform_comparison": platform_stats,
        "quality_breakdown": quality_stats,
        "event_breakdown": event_stats,
        "period_days": days,
    }


def _empty_dashboard() -> dict:
    """空数据看板。"""
    return {
        "kpi": {
            "total_projects": 0,
            "total_chapters": 0,
            "total_words": 0,
            "avg_chapter_length": 0,
        },
        "trend": [],
        "platform_comparison": {},
        "quality_breakdown": {},
        "event_breakdown": {},
        "period_days": 0,
    }
