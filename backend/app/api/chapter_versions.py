"""
Phase 7: 章节版本 API — 版本快照保存 + diff 对比 + 回溯。
"""
from __future__ import annotations

import difflib
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_chapter, get_user_project
from app.db.database import get_db
from app.db.models import ChapterVersion, NovelChapter, User
from app.schemas import (
    ChapterOut,
    ChapterVersionCreate,
    ChapterVersionDiffOut,
    ChapterVersionOut,
)

router = APIRouter(prefix="/api/v1/chapters", tags=["chapter_versions"])


# ---------------------------------------------------------------------------
# 单章详情（P0-1 修复的一部分）
# ---------------------------------------------------------------------------
# 此前后端完全没有"查询单章详情(含正文)"这个接口——前端一直是靠章节
# 列表接口(GET /projects/{id}/chapters)顺带把全部章节的正文都带出来，
# 前端自己在内存里 find() 出当前要显示的那一章。这导致列表接口没法
# 瘦身成只返回摘要+分页(否则编辑器就没内容可显示了)。
# 现在补上这个接口，前端后续改造后可以：列表只拉摘要，点开某一章时
# 才用这个接口按需拉正文。
@router.get("/{chapter_id}", response_model=ChapterOut)
async def get_chapter(
    chapter_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单章完整详情（含正文），用于编辑器按需加载。"""
    return await get_user_chapter(chapter_id, user, db)


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------


def compute_diff(text_a: str, text_b: str) -> tuple[str, int, int]:
    """Compute unified diff between two texts; returns (diff_text, added_lines, removed_lines)."""
    if not text_a and not text_b:
        return "", 0, 0

    a_lines = text_a.splitlines(keepends=True)
    b_lines = text_b.splitlines(keepends=True)

    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="version_a", tofile="version_b", lineterm=""))
    diff_text = "\n".join(diff) if diff else "(no changes)"

    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))

    return diff_text, added, removed


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{chapter_id}/versions")
async def list_versions(
    chapter_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出章节的所有版本（时间轴）"""
    chapter = await get_user_chapter(chapter_id, user, db)

    stmt = (
        select(ChapterVersion)
        .where(ChapterVersion.chapter_id == chapter.id)
        .order_by(ChapterVersion.version_num.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    versions = result.scalars().all()

    count_result = await db.execute(
        select(func.count(ChapterVersion.id)).where(
            ChapterVersion.chapter_id == chapter.id
        )
    )
    total = count_result.scalar() or 0

    return {
        "chapter_id": chapter_id,
        "chapter_num": chapter.chapter_num,
        "title": chapter.title,
        "total_versions": total,
        "current_content_hash": hash(chapter.content) if chapter.content else None,
        "versions": [
            {
                "id": str(v.id),
                "version_num": v.version_num,
                "word_count": v.word_count,
                "quality_score": v.quality_score,
                "created_by": v.created_by,
                "created_at": str(v.created_at),
                "has_diff": v.diff_from_prev is not None,
            }
            for v in versions
        ],
    }


@router.get("/{chapter_id}/versions/{version_id}/diff", response_model=ChapterVersionDiffOut)
async def get_version_diff(
    chapter_id: str,
    version_id: str,
    compare_with: int | None = Query(default=None, description="与哪个版本号对比（默认与上一版本）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取两个版本的文本差异"""
    chapter = await get_user_chapter(chapter_id, user, db)

    try:
        vid = uuid.UUID(version_id)
    except (ValueError, AttributeError):
        # Support version_num as identifier
        result = await db.execute(
            select(ChapterVersion).where(
                and_(
                    ChapterVersion.chapter_id == chapter.id,
                    ChapterVersion.version_num == int(version_id),
                )
            )
        )
        target = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(ChapterVersion).where(ChapterVersion.id == vid)
        )
        target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(404, "版本不存在")

    # Determine comparison version
    compare_version = None
    if compare_with is not None:
        compare_result = await db.execute(
            select(ChapterVersion).where(
                and_(
                    ChapterVersion.chapter_id == chapter.id,
                    ChapterVersion.version_num == compare_with,
                )
            )
        )
        compare_version = compare_result.scalar_one_or_none()
    elif target.diff_from_prev:
        # Use the stored diff
        diff_lines = target.diff_from_prev.split("\n") if target.diff_from_prev else []
        added = sum(1 for d in diff_lines if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff_lines if d.startswith("-") and not d.startswith("---"))
        return ChapterVersionDiffOut(
            chapter_id=uuid.UUID(chapter_id),
            version_a=target.version_num - 1,
            version_b=target.version_num,
            diff_text=target.diff_from_prev,
            added_lines=added,
            removed_lines=removed,
        )
    else:
        # Compare with previous version
        prev_result = await db.execute(
            select(ChapterVersion)
            .where(
                and_(
                    ChapterVersion.chapter_id == chapter.id,
                    ChapterVersion.version_num == target.version_num - 1,
                )
            )
        )
        compare_version = prev_result.scalar_one_or_none()

    text_a = compare_version.content if compare_version else ""
    text_b = target.content

    diff_text, added, removed = compute_diff(text_a, text_b)

    return ChapterVersionDiffOut(
        chapter_id=uuid.UUID(chapter_id),
        version_a=compare_version.version_num if compare_version else 0,
        version_b=target.version_num,
        diff_text=diff_text,
        added_lines=added,
        removed_lines=removed,
    )


@router.post("/{chapter_id}/versions/{version_id}/restore")
async def restore_version(
    chapter_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回退到指定版本"""
    chapter = await get_user_chapter(chapter_id, user, db)

    try:
        vid = uuid.UUID(version_id)
    except (ValueError, AttributeError):
        result = await db.execute(
            select(ChapterVersion).where(
                and_(
                    ChapterVersion.chapter_id == chapter.id,
                    ChapterVersion.version_num == int(version_id),
                )
            )
        )
        target = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(ChapterVersion).where(ChapterVersion.id == vid)
        )
        target = result.scalar_one_or_none()

    if not target:
        raise HTTPException(404, "版本不存在")

    # Save current version as snapshot before restoring
    current_content = chapter.content or ""
    max_version_result = await db.execute(
        select(func.max(ChapterVersion.version_num)).where(
            ChapterVersion.chapter_id == chapter.id
        )
    )
    max_ver = max_version_result.scalar() or 0
    new_version = max_ver + 1

    diff_before, added, removed = compute_diff(current_content, target.content)

    snapshot = ChapterVersion(
        id=uuid.uuid4(),
        chapter_id=chapter.id,
        version_num=new_version,
        content=current_content,
        word_count=len(current_content),
        diff_from_prev=diff_before,
        quality_score=None,
        created_by="user",
    )
    db.add(snapshot)

    # Restore chapter content
    chapter.content = target.content
    chapter.word_count = target.word_count
    chapter.version_history = (chapter.version_history or []) + [{
        "action": "restore",
        "from_version": target.version_num,
        "to_version": new_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]
    await db.commit()

    return {
        "status": "restored",
        "chapter_id": chapter_id,
        "restored_from_version": target.version_num,
        "previous_version_saved_as": new_version,
        "message": f"Chapter restored to version {target.version_num}",
    }


@router.post("/{chapter_id}/snapshot", response_model=ChapterVersionOut)
async def create_snapshot(
    chapter_id: str,
    req: ChapterVersionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动创建版本快照（AI 生成/改写时自动调用）"""
    chapter = await get_user_chapter(chapter_id, user, db)

    # Get next version number
    max_ver_result = await db.execute(
        select(func.max(ChapterVersion.version_num)).where(
            ChapterVersion.chapter_id == chapter.id
        )
    )
    max_ver = max_ver_result.scalar() or 0
    next_ver = max_ver + 1

    # Get previous version for diff
    prev_result = await db.execute(
        select(ChapterVersion)
        .where(
            and_(
                ChapterVersion.chapter_id == chapter.id,
                ChapterVersion.version_num == max_ver,
            )
        )
    )
    prev_version = prev_result.scalar_one_or_none()
    prev_content = prev_version.content if prev_version else ""
    diff_text, _, _ = compute_diff(prev_content, req.content) if prev_content else ("(first version)", 0, 0)

    snapshot = ChapterVersion(
        id=uuid.uuid4(),
        chapter_id=chapter.id,
        version_num=next_ver,
        content=req.content,
        word_count=req.word_count or len(req.content),
        diff_from_prev=diff_text,
        quality_score=req.quality_score,
        created_by=req.created_by,
    )
    db.add(snapshot)

    # Update chapter content to latest
    chapter.content = req.content
    chapter.word_count = req.word_count or len(req.content)
    chapter.version_history = (chapter.version_history or []) + [{
        "version_num": next_ver,
        "created_by": req.created_by,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]
    await db.commit()
    await db.refresh(snapshot)

    return ChapterVersionOut(
        id=snapshot.id,
        chapter_id=snapshot.chapter_id,
        version_num=snapshot.version_num,
        content=snapshot.content,
        word_count=snapshot.word_count,
        diff_from_prev=snapshot.diff_from_prev,
        quality_score=snapshot.quality_score,
        created_by=snapshot.created_by,
        created_at=snapshot.created_at,
    )


@router.delete("/{chapter_id}/versions/{version_id}")
async def delete_version(
    chapter_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除指定版本快照（保留至少一个版本）"""
    chapter = await get_user_chapter(chapter_id, user, db)

    try:
        vid = uuid.UUID(version_id)
    except (ValueError, AttributeError):
        raise HTTPException(400, "无效的版本 ID")

    result = await db.execute(
        select(ChapterVersion).where(
            and_(ChapterVersion.id == vid, ChapterVersion.chapter_id == chapter.id)
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "版本不存在")

    # Check minimum versions
    count_result = await db.execute(
        select(func.count(ChapterVersion.id)).where(ChapterVersion.chapter_id == chapter.id)
    )
    count = count_result.scalar() or 0
    if count <= 1:
        raise HTTPException(400, "无法删除最后一个版本")

    await db.delete(version)
    await db.commit()

    return {"status": "deleted", "version_id": str(version.id), "version_num": version.version_num}
