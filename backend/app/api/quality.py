"""质量系统 API — 7维审查 + 用户确认后定向重写 + 历史对比 (Phase 3)
对接 prompts.py 的 novel-review 引擎。
"""
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import ai_limiter
from app.api.chapter_versions import compute_diff
from app.api.deps import get_current_user, get_user_chapter
from app.db.database import get_db
from app.db.models import ChapterVersion, NovelChapter, QualityReview, User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_review_messages,
    parse_novel_review_response,
)

router = APIRouter(prefix="/api/v1/quality", tags=["quality"])

# 低分建议阈值：7维审查每维打分 0-10，低于此分视为需要自动重写
AUTO_REWRITE_SCORE_THRESHOLD = 6


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


class ApplyRewriteRequest(BaseModel):
    chapter_id: str
    target_segment: str
    rewritten: str
    dimension: str | None = None


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

WHOLE_CHAPTER_REWRITE_PROMPT = """你是网文精修编辑。以下章节在"{dim}"维度评分较低，请针对性优化整章，
保持原有情节走向和字数量级不变，只改善文字表达和该维度对应的问题，不要重新设计剧情。

【存在的问题】
{issues}

【原文】
{content}

只输出重写后的完整章节正文，不要输出任何解释或标记。"""


async def _snapshot_and_apply(
    db: AsyncSession, chapter: NovelChapter, new_content: str,
    created_by: str, quality_score: float | None = None,
) -> ChapterVersion:
    """把章节当前内容存成一个版本快照，再应用新内容——供 /rewrite 和自动重写共用，
    保证任何"AI 改写会真的动章节内容"的操作都是可回溯的，不会不留痕迹地覆盖原文。
    """
    old_content = chapter.content or ""
    max_ver_result = await db.execute(
        select(func.max(ChapterVersion.version_num)).where(ChapterVersion.chapter_id == chapter.id)
    )
    new_version = (max_ver_result.scalar() or 0) + 1
    diff_text, _, _ = compute_diff(old_content, new_content)

    snapshot = ChapterVersion(
        chapter_id=chapter.id, version_num=new_version,
        content=old_content, word_count=len(old_content),
        diff_from_prev=diff_text, quality_score=quality_score, created_by=created_by,
    )
    db.add(snapshot)

    chapter.content = new_content
    chapter.word_count = len(new_content)
    chapter.version_history = (chapter.version_history or []) + [{
        "action": "rewrite", "by": created_by, "to_version": new_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]
    return snapshot


async def _collect_low_score_dimensions(review_data: dict) -> list[str]:
    """只识别低分维度，不自动改写正文。

    商业写作产品不能在用户未确认时覆盖作品内容；自动审查只负责打分和
    返回问题维度，真正改写必须由用户主动调用 /rewrite 或版本应用接口。
    """
    dimensions = review_data.get("dimensions", {})
    return [
        dim for dim, dd in dimensions.items()
        if isinstance(dd.get("score"), (int, float)) and dd["score"] < AUTO_REWRITE_SCORE_THRESHOLD
    ]


async def _do_7d_review(
    chapter_id: str,
    content: str,
    outline: str,
    ctx: str,
    db: AsyncSession,
    previous_review: dict | None = None,
) -> dict:
    """执行7维审查，可选历史对比。"""
    from app.services.prompt_registry import load_template
    tpl = await load_template(db, "novel-review")
    messages = build_novel_review_messages(
        chapter_content=content,
        chapter_outline=outline,
        context_summary=ctx,
        previous_review=previous_review,
        template=tpl,
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
    low_score_dims: list[str] = []
    try:
        ch_uuid = _uuid.UUID(chapter_id)
        for dim, dd in data.get("dimensions", {}).items():
            db.add(QualityReview(
                chapter_id=ch_uuid,
                dimension=dim,
                score=dd.get("score"),
                issues_json=dd.get("issues", []),
            ))
        ch = await db.get(NovelChapter, ch_uuid)
        if ch:
            # 记录上次审查看板分数, 用于 Prompt 优化闭环
            prev_overall = (ch.review_score or {}).get("overall_score") if ch.review_score else None
            ch.review_score = {
                dim: d.get("score", 0)
                for dim, d in data.get("dimensions", {}).items()
            }
            ch.review_report = data
            ch.status = "reviewed"
            await db.flush()

            low_score_dims = await _collect_low_score_dimensions(data)

            # Prompt 优化闭环: 若总分变化 >= 2 分, 自动记录优化日志
            new_overall = data.get("overall_score")
            if prev_overall is not None and new_overall is not None:
                try:
                    from app.services.prompt_registry import get_prompt_registry
                    registry = await get_prompt_registry(db)
                    summary = data.get("summary", "")
                    await registry.log_auto_optimization(
                        db=db,
                        project_id=ch.project_id,
                        prompt_name="novel-review",
                        previous_score=float(prev_overall),
                        new_score=float(new_overall),
                        context=f"7维审查对比 (ch={ch.chapter_num}) - {summary}",
                    )
                except Exception:
                    pass  # 优化日志失败不影响审查主流程

        await db.commit()
    except (ValueError, AttributeError):
        pass

    data["auto_rewritten_dimensions"] = []
    data["low_score_dimensions"] = low_score_dims
    return data


@router.post("/review")
@ai_limiter.limit("10/minute")
async def review_chapter_7d(
    request: Request,
    response: Response,
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
@router.post("/rewrite-preview")
@ai_limiter.limit("10/minute")
async def rewrite_segment(
    request: Request,
    response: Response,
    req: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """定向重写预览。

    商业写作产品不能在用户未确认时覆盖作品正文。本接口只生成候选改写，
    不修改 NovelChapter.content。用户确认后再调用 /quality/apply-rewrite。
    """
    chapter = await get_user_chapter(req.chapter_id, user, db)
    prompt = (
        REWRITE_PROMPT.replace("{dim}", req.dimension)
        .replace("{issue}", req.issue_description)
        .replace("{segment}", req.target_segment[:4000])
    )
    try:
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.7)
    except DeepSeekError:
        raise HTTPException(502, "AI 重写服务暂时不可用")

    rewritten = r["content"].strip()
    return {
        "rewritten": rewritten,
        "dimension": req.dimension,
        "applied": False,
        "can_apply": req.target_segment in (chapter.content or ""),
        "message": "已生成改写预览，尚未修改章节正文。确认后调用 /quality/apply-rewrite。",
    }


@router.post("/apply-rewrite")
async def apply_rewrite(
    req: ApplyRewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户确认后应用改写，并保存可回滚版本快照。"""
    chapter = await get_user_chapter(req.chapter_id, user, db)
    original_content = chapter.content or ""
    if req.target_segment not in original_content:
        raise HTTPException(409, "原片段已变化，无法安全应用改写，请重新生成预览")
    new_content = original_content.replace(req.target_segment, req.rewritten, 1)
    snapshot = await _snapshot_and_apply(db, chapter, new_content, created_by="ai")

    if req.dimension:
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
    return {"applied": True, "version_id": str(snapshot.id), "word_count": chapter.word_count}
