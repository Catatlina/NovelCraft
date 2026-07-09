"""反馈学习闭环 — 数据分析 + Prompt优化 (Phase 8)"""
from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import (
    FeedbackSignal,
    NovelChapter,
    NovelProject,
    PromptOptimizationLog,
    QualityReview,
    User,
)
from app.services.deepseek_client import DeepSeekError, chat_completion

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


@router.post("/analyze-feedback")
async def analyze_feedback(project_id: str, db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)):
    await get_user_project(project_id, user, db)
    chapters = await db.execute(select(NovelChapter).where(NovelChapter.project_id == project_id).order_by(NovelChapter.chapter_num))
    ch_list = [(str(c.id), c.chapter_num, c.title or "", c.word_count) for c in chapters.scalars().all()]
    if not ch_list:
        raise HTTPException(404, "项目无章节")
    ch_ids = [c[0] for c in ch_list]
    sigs = await db.execute(select(FeedbackSignal).where(FeedbackSignal.chapter_id.in_(ch_ids)))
    sigs_by_ch = {}
    for s in sigs.scalars().all():
        cid = str(s.chapter_id); sigs_by_ch.setdefault(cid, {"reads": 0, "ret": 0, "n": 0})
        sigs_by_ch[cid]["reads"] += s.read_count or 0
        sigs_by_ch[cid]["ret"] += s.retention_rate or 0; sigs_by_ch[cid]["n"] += 1
    chapter_data = [{"chapter_num": num, "title": title, "word_count": wc,
                     "reads": sigs_by_ch.get(cid, {}).get("reads", 0),
                     "avg_retention": round(sigs_by_ch.get(cid, {}).get("ret", 0) /
                     max(sigs_by_ch.get(cid, {}).get("n", 1), 1) * 100, 1)}
                    for cid, num, title, wc in ch_list]
    try:
        prompt = (
            "分析以下章节阅读数据并生成3条Prompt优化建议:\n"
            + json.dumps(chapter_data, ensure_ascii=False)[:6000]
            + "\n输出JSON: {best_chapter, worst_chapter, correlations, prompt_suggestions, summary}"
        )
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
        raw = r["content"].strip()
        if raw.startswith("```"): raw = raw.strip("`").removeprefix("json").strip()
        analysis = json.loads(raw)
    except (DeepSeekError, json.JSONDecodeError):
        analysis = {"summary": "AI分析暂不可用", "prompt_suggestions": []}
    return {"total_chapters": len(chapter_data), "has_feedback": bool(sigs_by_ch), "analysis": analysis}


@router.post("/apply-prompt-suggestion")
async def apply_prompt_suggestion(suggestion: dict, db: AsyncSession = Depends(get_db),
                                  user: User = Depends(get_current_user)):
    project_id = suggestion.get("project_id")
    if not project_id: raise HTTPException(400, "缺少 project_id")
    project = await get_user_project(project_id, user, db)
    project.state_history = [*(project.state_history or []), {
        "type": "prompt_optimization", "change": suggestion.get("change", ""),
        "reason": suggestion.get("reason", ""), "applied_by": user.username}]
    await db.commit()
    return {"status": "applied"}


# ---------------------------------------------------------------------------
# Auto-Optimize Prompt (Bayesian Optimization — simplified)
# ---------------------------------------------------------------------------

# Candidate parameter space for random search
PARAM_SPACE: dict[str, list] = {
    "temperature": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "top_p": [0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0],
    "frequency_penalty": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
    "presence_penalty": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
    "max_tokens": [2000, 2500, 3000, 3500, 4000, 5000, 6000],
}


class AutoOptimizeRequest(BaseModel):
    project_id: str = Field(..., description="项目 ID")
    lookback_days: int = Field(default=30, ge=7, le=90)
    consecutive_below_threshold: int = Field(default=5, ge=2, le=20)
    sigma_threshold: float = Field(default=1.0, ge=0.5, le=3.0)
    auto_apply: bool = Field(default=False, description="是否自动应用推荐参数")


class AutoOptimizeResponse(BaseModel):
    project_id: str
    current_params: dict
    recommended_params: dict
    reason: str
    auto_applied: bool
    quality_trend: list[dict]


@router.post("/auto-optimize-prompt", response_model=AutoOptimizeResponse)
async def auto_optimize_prompt(
    req: AutoOptimizeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    基于反馈数据自动调整 prompt 参数：
    1. 读取最近 30 天 quality score + 读者反馈
    2. 如果连续 5 次低于均值 1σ，排除当前参数组合
    3. 用 Bayesian Optimization 推荐新参数（简化版：随机搜索 + 记录）
    4. 写入 prompt_optimization_log
    """
    project = await get_user_project(req.project_id, user, db)

    # Step 1: Read recent quality scores
    cutoff = datetime.now(timezone.utc) - timedelta(days=req.lookback_days)
    scores_result = await db.execute(
        select(QualityReview)
        .join(NovelChapter, QualityReview.chapter_id == NovelChapter.id)
        .where(
            NovelChapter.project_id == project.id,
            QualityReview.created_at >= cutoff,
        )
        .order_by(QualityReview.created_at.asc())
    )
    reviews = scores_result.scalars().all()

    if not reviews:
        return AutoOptimizeResponse(
            project_id=req.project_id,
            current_params={},
            recommended_params={},
            reason="No quality review data available in the lookback period",
            auto_applied=False,
            quality_trend=[],
        )

    # Build quality trend
    scores = [r.score for r in reviews if r.score is not None]
    if not scores:
        return AutoOptimizeResponse(
            project_id=req.project_id,
            current_params={},
            recommended_params={},
            reason="No valid scores found",
            auto_applied=False,
            quality_trend=[],
        )

    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_score = math.sqrt(variance) if variance > 0 else 0.0

    quality_trend = [
        {
            "dimension": r.dimension,
            "score": r.score,
            "date": str(r.created_at),
            "below_mean_1sigma": (
                r.score is not None
                and r.score < (mean_score - req.sigma_threshold * std_score)
            ),
        }
        for r in reviews
    ]

    # Step 2: Check for consecutive decline
    below_flags = [t["below_mean_1sigma"] for t in quality_trend]
    consecutive_below = 0
    max_consecutive = 0
    for flag in below_flags:
        if flag:
            consecutive_below += 1
            max_consecutive = max(max_consecutive, consecutive_below)
        else:
            consecutive_below = 0

    should_optimize = max_consecutive >= req.consecutive_below_threshold

    # Get current params from latest optimization log
    current_params_result = await db.execute(
        select(PromptOptimizationLog)
        .where(PromptOptimizationLog.project_id == project.id)
        .order_by(PromptOptimizationLog.applied_at.desc())
        .limit(1)
    )
    latest_log = current_params_result.scalar_one_or_none()
    current_params = latest_log.params_after if latest_log else {
        "temperature": 0.7,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
        "max_tokens": 4000,
    }

    if not should_optimize:
        return AutoOptimizeResponse(
            project_id=req.project_id,
            current_params=current_params,
            recommended_params=current_params,
            reason=f"Not optimizing: max consecutive below threshold = {max_consecutive} (< {req.consecutive_below_threshold})",
            auto_applied=False,
            quality_trend=quality_trend[-10:],
        )

    # Step 3: Random search for new parameters (simplified Bayesian Optimization)
    # Exclude current parameter combination and select new random candidates
    recommended_params = dict(current_params)
    excluded_keys = set()

    for key, candidates in PARAM_SPACE.items():
        if key not in current_params:
            continue
        if len(candidates) <= 1:
            continue
        # Randomly select a different value
        available = [c for c in candidates if c != current_params.get(key)]
        if available:
            recommended_params[key] = random.choice(available)
        else:
            recommended_params[key] = random.choice(candidates)

    # Step 4: Log the change
    optimization_log = PromptOptimizationLog(
        id=uuid.uuid4(),
        project_id=project.id,
        prompt_name="generation_prompt",
        params_before=current_params,
        params_after=recommended_params,
        reason=f"Auto-optimized: {max_consecutive} consecutive scores below {req.sigma_threshold}σ from mean ({mean_score:.2f})",
        quality_impact=None,
    )
    db.add(optimization_log)

    if req.auto_apply:
        project.state_history = [*(project.state_history or []), {
            "type": "auto_prompt_optimization",
            "params_before": current_params,
            "params_after": recommended_params,
            "reason": f"Auto-optimized: {max_consecutive} consecutive below threshold",
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }]

    await db.commit()

    return AutoOptimizeResponse(
        project_id=req.project_id,
        current_params=current_params,
        recommended_params=recommended_params,
        reason=f"Auto-optimized: {max_consecutive} consecutive scores below {req.sigma_threshold}σ from mean ({mean_score:.2f} ± {std_score:.2f})",
        auto_applied=req.auto_apply,
        quality_trend=quality_trend[-10:],
    )
