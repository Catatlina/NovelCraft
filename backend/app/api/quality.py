"""质量系统 API — 7维审查 + 定向自动重写 + 历史对比 (Phase 3)
对接 prompts.py 的 novel-review 引擎。
"""
import json
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_chapter
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, QualityReview, User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_review_messages,
    parse_novel_review_response,
)

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])


class ReviewChapterRequest(BaseModel):
    chapter_id: str
    chapter_content: str
    outline: str = ""
    context: str = ""


class RewriteRequest(BaseModel):
    chapter_id: str
    dimension: str
    target_segment: str
    issue_description: str


class CompareRequest(BaseModel):
    chapter_id: str
    chapter_content: str
    outline: str = ""
    context: str = ""
    previous_review: dict | None = None


REWRITE_PROMPT = """你是网文精修编辑。针对{dim}维度问题定向重写。

问题: {issue}
原片段: {segment}
只输出重写后的片段，不要解释。"""


async def _do_7d_review(
    chapter_id: str,
    content: str,
    outline: str,
    ctx: str,
    db: AsyncSession,
    previous_review: dict | None = None,
) -> dict:
    """执行7维审查，可选历史对比。"""
    messages = build_novel_review_messages(
        chapter_content=content,
        chapter_outline=outline,
        context_summary=ctx,
        previous_review=previous_review,
    )
    try:
        r = await chat_completion(messages, temperature=0.3)
    except DeepSeekError:
        raise HTTPException(502, "AI 审查服务暂时不可用")

    try:
        data = parse_novel_review_response(r["content"])
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")

    # 持久化审查结果
    try:
        _uuid.UUID(chapter_id)
        for dim, dd in data.get("dimensions", {}).items():
            db.add(QualityReview(
                chapter_id=chapter_id,
                dimension=dim,
                score=dd.get("score"),
                issues_json=dd.get("issues", []),
            ))
        ch = await db.get(NovelChapter, chapter_id)
        if ch:
            ch.review_score = {
                dim: d.get("score", 0)
                for dim, d in data.get("dimensions", {}).items()
            }
            ch.review_report = data
            ch.status = "reviewed"
        await db.commit()
    except (ValueError, AttributeError):
        pass

    return data


@router.post("/review")
async def review_chapter_7d(
    req: ReviewChapterRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """7维质量审查 — 调用 novel-review 引擎"""
    await get_user_chapter(req.chapter_id, user, db)
    return await _do_7d_review(
        req.chapter_id, req.chapter_content, req.outline, req.context, db
    )


@router.post("/compare")
async def compare_reviews(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    对比审查 — 与前次审查结果做历史对比。
    调用 novel-review 引擎，传入 previous_review 做趋势分析。
    """
    await get_user_chapter(req.chapter_id, user, db)
    return await _do_7d_review(
        req.chapter_id,
        req.chapter_content,
        req.outline,
        req.context,
        db,
        previous_review=req.previous_review,
    )


@router.post("/rewrite")
async def rewrite_segment(
    req: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """定向重写 — 针对审查发现的问题维度进行局部重写"""
    await get_user_chapter(req.chapter_id, user, db)
    prompt = (
        REWRITE_PROMPT.replace("{dim}", req.dimension)
        .replace("{issue}", req.issue_description)
        .replace("{segment}", req.target_segment[:4000])
    )
    try:
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.7)
    except DeepSeekError:
        raise HTTPException(502, "AI 重写服务暂时不可用")
    qr = await db.execute(
        select(QualityReview)
        .where(
            QualityReview.chapter_id == req.chapter_id,
            QualityReview.dimension == req.dimension,
        )
        .order_by(QualityReview.created_at.desc())
        .limit(1)
    )
    qr_row = qr.scalar_one_or_none()
    if qr_row:
        qr_row.rewrite_applied = True
        await db.commit()
    return {"rewritten": r["content"], "dimension": req.dimension}
