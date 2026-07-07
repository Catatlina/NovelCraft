"""
Phase 5: 质量基准 API — 平台×品类基准的 CRUD + 查询 + 阈值。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import QualityBenchmark, User
from app.schemas import (
    BenchmarkOverride,
    QualityBenchmarkCreate,
    QualityBenchmarkOut,
    QualityBenchmarkUpdate,
    PlatformThresholdOut,
)

router = APIRouter(prefix="/api/v1/quality-benchmarks", tags=["quality_benchmarks"])

# ---------------------------------------------------------------------------
# Default thresholds by platform
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: dict[str, dict] = {
    "起点": {
        "hype_density_threshold": 1.2,
        "hook_min_score": 8,
        "dialogue_ratio_ideal": 0.30,
        "min_word_count_per_chapter": 2000,
        "pass_thresholds": {
            "overall_score_min": 7.0,
            "hype_max": 2.5,
            "dialogue_min": 0.20,
            "dialogue_max": 0.50,
        },
    },
    "创世": {
        "hype_density_threshold": 1.0,
        "hook_min_score": 7,
        "dialogue_ratio_ideal": 0.35,
        "min_word_count_per_chapter": 1500,
        "pass_thresholds": {
            "overall_score_min": 6.5,
            "hype_max": 2.0,
            "dialogue_min": 0.15,
            "dialogue_max": 0.55,
        },
    },
    "webnovel": {
        "hype_density_threshold": 1.3,
        "hook_min_score": 7,
        "dialogue_ratio_ideal": 0.33,
        "min_word_count_per_chapter": 1000,
        "pass_thresholds": {
            "overall_score_min": 6.5,
        },
    },
    "royalroad": {
        "hype_density_threshold": 1.0,
        "hook_min_score": 7,
        "dialogue_ratio_ideal": 0.35,
        "min_word_count_per_chapter": 1500,
        "pass_thresholds": {
            "overall_score_min": 7.0,
        },
    },
    "narou": {
        "hype_density_threshold": 0.9,
        "hook_min_score": 6,
        "dialogue_ratio_ideal": 0.40,
        "min_word_count_per_chapter": 1000,
        "pass_thresholds": {
            "overall_score_min": 6.0,
        },
    },
}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/benchmarks")
async def get_benchmarks(
    platform: str = Query(default="起点", description="平台名称"),
    genre: str | None = Query(default=None, description="品类（可选）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取平台×品类的质量基准值"""
    stmt = select(QualityBenchmark).where(QualityBenchmark.platform == platform)
    if genre:
        stmt = stmt.where(QualityBenchmark.genre == genre)

    result = await db.execute(stmt)
    benchmarks = result.scalars().all()

    if not benchmarks:
        # Return default thresholds when no custom benchmarks exist
        defaults = DEFAULT_THRESHOLDS.get(platform, DEFAULT_THRESHOLDS["起点"])
        return {
            "platform": platform,
            "genre": genre or "all",
            "benchmarks": [],
            "defaults": defaults,
            "source": "system_defaults",
        }

    return {
        "platform": platform,
        "genre": genre or "all",
        "benchmarks": [
            QualityBenchmarkOut(
                id=b.id,
                platform=b.platform,
                genre=b.genre,
                hype_density_threshold=b.hype_density_threshold,
                hook_min_score=b.hook_min_score,
                dialogue_ratio_ideal=b.dialogue_ratio_ideal,
                metadata=b.metadata,
                updated_at=b.updated_at,
            )
            for b in benchmarks
        ],
        "count": len(benchmarks),
        "source": "custom",
    }


@router.post("/benchmarks/override", response_model=QualityBenchmarkOut)
async def override_benchmark(
    req: BenchmarkOverride,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """作者手动覆盖质量基准（upsert）"""
    # Check if existing
    result = await db.execute(
        select(QualityBenchmark).where(
            and_(
                QualityBenchmark.platform == req.platform,
                QualityBenchmark.genre == req.genre,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update
        if req.hype_density_threshold is not None:
            existing.hype_density_threshold = req.hype_density_threshold
        if req.hook_min_score is not None:
            existing.hook_min_score = req.hook_min_score
        if req.dialogue_ratio_ideal is not None:
            existing.dialogue_ratio_ideal = req.dialogue_ratio_ideal
        if req.metadata is not None:
            existing.metadata = {**existing.metadata, **req.metadata} if existing.metadata else req.metadata
        benchmark = existing
    else:
        # Create
        benchmark = QualityBenchmark(
            id=uuid.uuid4(),
            platform=req.platform,
            genre=req.genre,
            hype_density_threshold=req.hype_density_threshold or 1.0,
            hook_min_score=req.hook_min_score or 7,
            dialogue_ratio_ideal=req.dialogue_ratio_ideal or 0.35,
            metadata=req.metadata or {},
        )
        db.add(benchmark)

    await db.commit()
    await db.refresh(benchmark)

    return QualityBenchmarkOut(
        id=benchmark.id,
        platform=benchmark.platform,
        genre=benchmark.genre,
        hype_density_threshold=benchmark.hype_density_threshold,
        hook_min_score=benchmark.hook_min_score,
        dialogue_ratio_ideal=benchmark.dialogue_ratio_ideal,
        metadata=benchmark.metadata,
        updated_at=benchmark.updated_at,
    )


@router.get("/benchmarks/thresholds", response_model=PlatformThresholdOut)
async def get_platform_thresholds(
    platform: str = Query(..., description="平台名称"),
    genre: str | None = Query(default=None, description="品类（可选）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取某平台的过稿阈值配置"""
    stmt = select(QualityBenchmark).where(QualityBenchmark.platform == platform)
    if genre:
        stmt = stmt.where(QualityBenchmark.genre == genre)

    result = await db.execute(stmt)
    benchmark = result.scalars().first()

    defaults = DEFAULT_THRESHOLDS.get(platform, DEFAULT_THRESHOLDS["起点"])

    if benchmark:
        return PlatformThresholdOut(
            platform=platform,
            genre=genre or benchmark.genre,
            hype_density_threshold=benchmark.hype_density_threshold,
            hook_min_score=benchmark.hook_min_score,
            dialogue_ratio_ideal=benchmark.dialogue_ratio_ideal,
            pass_thresholds=benchmark.metadata.get("pass_thresholds", defaults.get("pass_thresholds", {})),
        )

    return PlatformThresholdOut(
        platform=platform,
        genre=genre,
        hype_density_threshold=defaults.get("hype_density_threshold", 1.0),
        hook_min_score=defaults.get("hook_min_score", 7),
        dialogue_ratio_ideal=defaults.get("dialogue_ratio_ideal", 0.35),
        pass_thresholds=defaults.get("pass_thresholds", {}),
    )


@router.get("/benchmarks/list-all")
async def list_all_benchmarks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出所有已存储的质量基准"""
    result = await db.execute(
        select(QualityBenchmark).order_by(QualityBenchmark.platform, QualityBenchmark.genre)
    )
    benchmarks = result.scalars().all()

    platforms_seen: set[str] = set()

    items = []
    for b in benchmarks:
        platforms_seen.add(b.platform)
        items.append({
            "id": str(b.id),
            "platform": b.platform,
            "genre": b.genre,
            "hype_density_threshold": b.hype_density_threshold,
            "hook_min_score": b.hook_min_score,
            "dialogue_ratio_ideal": b.dialogue_ratio_ideal,
            "updated_at": str(b.updated_at),
        })

    # Add default entries for platforms without custom benchmarks
    for platform, defaults in DEFAULT_THRESHOLDS.items():
        if platform not in platforms_seen:
            items.append({
                "id": None,
                "platform": platform,
                "genre": "all (system defaults)",
                "hype_density_threshold": defaults["hype_density_threshold"],
                "hook_min_score": defaults["hook_min_score"],
                "dialogue_ratio_ideal": defaults["dialogue_ratio_ideal"],
                "updated_at": None,
            })

    return {"benchmarks": items, "total": len(items)}
