"""
Phase 6: A/B 测试 API — 创建测试、收集结果、判定胜者（scipy t-test）。
Phase 8.2: Prompt 优化日志集成。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import ABTest, NovelChapter, NovelProject, User
from app.schemas import (
    ABTestCreate,
    ABTestOut,
    ABTestUpdate,
)

router = APIRouter(prefix="/api/v1/ab-tests", tags=["ab-tests"])


# ---- Helper ----


async def _check_project_owner(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> NovelProject:
    """校验项目归属。"""
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id, NovelProject.user_id == user.id
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


# ---- API Endpoints ----


@router.post("/create", response_model=ABTestOut)
async def create_ab_test(
    req: ABTestCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建A/B测试：选择章节 + 变体参数 + 目标指标。"""
    await _check_project_owner(req.project_id, user, db)

    # 验证章节归属
    ch_result = await db.execute(
        select(NovelChapter).where(
            NovelChapter.id == req.chapter_id,
            NovelChapter.project_id == req.project_id,
        )
    )
    chapter = ch_result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")

    # 序列化 variants
    variants_json = [v.model_dump() for v in req.variants]

    test = ABTest(
        id=uuid.uuid4(),
        project_id=req.project_id,
        chapter_id=req.chapter_id,
        name=req.name,
        variants=variants_json,
        metric=req.metric,
        status="running",
        results={},
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return ABTestOut.model_validate(test)


@router.get("/{test_id}", response_model=ABTestOut)
async def get_ab_test(
    test_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个 A/B 测试详情。"""
    try:
        tid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(404, "测试不存在")

    result = await db.execute(
        select(ABTest).join(NovelProject).where(
            ABTest.id == tid,
            NovelProject.user_id == user.id,
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(404, "测试不存在")
    return ABTestOut.model_validate(test)


@router.get("/{test_id}/result")
async def get_ab_result(
    test_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    计算 A/B 测试统计显著性（scipy.stats.ttest_ind）。
    对每个变体的指标值做独立样本 t 检验。
    """
    try:
        tid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(404, "测试不存在")

    result = await db.execute(
        select(ABTest).join(NovelProject).where(
            ABTest.id == tid,
            NovelProject.user_id == user.id,
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(404, "测试不存在")

    variants = test.variants or []
    # 提取每个变体的指标样本
    samples: dict[str, list[float]] = {}
    for v in variants:
        vname = v.get("variant_name", "unknown")
        metrics = v.get("params", {}).get("samples", [])
        if isinstance(metrics, list) and len(metrics) > 0:
            samples[vname] = [float(m) for m in metrics]

    # 计算 t-test
    try:
        from scipy import stats  # type: ignore[import-untyped]

        stats_result = None
        pairwise: list[dict] = []
        var_names = list(samples.keys())

        if len(var_names) >= 2:
            # 两两比较
            control = samples[var_names[0]]
            best_variant = var_names[0]
            best_pvalue = 1.0
            for i in range(1, len(var_names)):
                treatment = samples[var_names[i]]
                t_stat, p_val = stats.ttest_ind(control, treatment)
                pairwise.append(
                    {
                        "control": var_names[0],
                        "treatment": var_names[i],
                        "t_statistic": float(t_stat),
                        "p_value": float(p_val),
                        "significant": p_val < 0.05,
                    }
                )
                if p_val < best_pvalue:
                    best_pvalue = p_val
                    best_variant = var_names[i]

            # 判定胜出
            if best_pvalue < 0.05 and best_variant != var_names[0]:
                winner = best_variant
                test.winner_variant = winner
                test.p_value = float(best_pvalue)
                test.status = "completed"
                test.ended_at = datetime.now(timezone.utc)
            elif len(samples.get(var_names[0], [])) >= 10:
                # 样本量足够，但未达到显著差异
                winner = var_names[0]  # 默认保留对照组
            else:
                winner = None
        else:
            pairwise = []
            winner = None

        results_summary = {
            "variant_names": var_names,
            "sample_sizes": {k: len(v) for k, v in samples.items()},
            "pairwise_tests": pairwise,
            "winner_variant": winner,
            "method": "ttest_ind",
        }
        test.results = results_summary
        await db.commit()

        return {
            "test_id": str(test.id),
            "status": test.status,
            "winner_variant": test.winner_variant,
            "p_value": test.p_value,
            "results": results_summary,
        }
    except ImportError:
        return {
            "test_id": str(test.id),
            "status": test.status,
            "error": "scipy 未安装，无法计算 t-test。请运行: pip install scipy",
            "variants": variants,
        }


@router.post("/{test_id}/archive")
async def archive_test(
    test_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    测试结束，胜出版本 → 正式版本，败出版本 → 存档。
    将胜出变体内容应用到原章节。
    """
    try:
        tid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(404, "测试不存在")

    result = await db.execute(
        select(ABTest).join(NovelProject).where(
            ABTest.id == tid,
            NovelProject.user_id == user.id,
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(404, "测试不存在")

    if test.status == "cancelled":
        raise HTTPException(400, "测试已取消")

    # 如果没有 winner，先计算
    if not test.winner_variant and test.status == "running":
        # 尝试从 results 中判定
        results = test.results or {}
        winner = results.get("winner_variant")
        if winner:
            test.winner_variant = winner
        else:
            # 默认选第一个变体
            variants = test.variants or []
            test.winner_variant = variants[0].get("variant_name") if variants else "default"

    # 应用胜出变体到章节
    if test.winner_variant:
        variants = test.variants or []
        for v in variants:
            if v.get("variant_name") == test.winner_variant:
                # 更新章节内容
                chapter_result = await db.execute(
                    select(NovelChapter).where(NovelChapter.id == test.chapter_id)
                )
                chapter = chapter_result.scalar_one_or_none()
                if chapter and v.get("content"):
                    # 保存旧版本到 version_history
                    history = chapter.version_history or []
                    history.append(
                        {
                            "version_num": len(history) + 1,
                            "content_preview": (chapter.content or "")[:200],
                            "word_count": chapter.word_count,
                            "saved_from": f"ab_test_{test_id}",
                            "saved_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    chapter.version_history = history
                    chapter.content = v["content"]
                    chapter.word_count = len(v["content"])
                    await db.commit()
                break

    test.status = "completed"
    test.ended_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "detail": "A/B 测试已归档",
        "test_id": str(test.id),
        "winner_variant": test.winner_variant,
    }


@router.get("/", response_model=list[ABTestOut])
async def list_ab_tests(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出项目的所有 A/B 测试。"""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(404, "项目不存在")
    await _check_project_owner(pid, user, db)

    result = await db.execute(
        select(ABTest)
        .where(ABTest.project_id == pid)
        .order_by(ABTest.started_at.desc())
        .limit(50)
    )
    return [ABTestOut.model_validate(t) for t in result.scalars().all()]
