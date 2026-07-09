"""
Phase 9: 全局全文搜索 API — 使用 pg_trgm + ILIKE 实现跨实体检索。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import (
    ForeshadowPool,
    KnowledgeEmbedding,
    NovelChapter,
    NovelProject,
    User,
)
from app.schemas import SearchResultItem

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("/")
async def global_search(
    q: str = Query(default="", min_length=1),
    type: str | None = Query(default=None, description="project | chapter | character | foreshadow | knowledge"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResultItem]:
    """
    全文搜索：书名/章节内容/角色/伏笔/知识条目。
    使用 ILIKE 做模糊匹配，结合 pg_trgm 加速（若已启用）。
    """
    if not q.strip():
        return []

    import re as _re
    escaped = _re.sub(r'([%_\\])', r'\\\1', q)
    pattern = f"%{escaped}%"
    results: list[SearchResultItem] = []

    # 获取用户所有项目 ID
    user_pids_result = await db.execute(
        select(NovelProject.id).where(NovelProject.user_id == user.id)
    )
    user_pids = [p[0] for p in user_pids_result]
    if not user_pids:
        return []

    # ---- 搜索项目（书名/类型） ----
    if type is None or type == "project":
        proj_result = await db.execute(
            select(NovelProject)
            .where(
                NovelProject.id.in_(user_pids),
                or_(
                    NovelProject.title.ilike(pattern),
                    NovelProject.genre.ilike(pattern),
                    NovelProject.overall_outline.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        for p in proj_result.scalars().all():
            results.append(
                SearchResultItem(
                    id=p.id,
                    type="project",
                    title=p.title,
                    snippet=(p.overall_outline or "")[:200],
                    project_id=p.id,
                    project_title=p.title,
                )
            )

    # ---- 搜索章节内容 ----
    if type is None or type == "chapter":
        ch_result = await db.execute(
            select(NovelChapter, NovelProject.title)
            .join(NovelProject, NovelChapter.project_id == NovelProject.id)
            .where(
                NovelChapter.project_id.in_(user_pids),
                or_(
                    NovelChapter.title.ilike(pattern),
                    NovelChapter.content.ilike(pattern),
                    NovelChapter.summary.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        for ch, proj_title in ch_result:
            # 提取匹配片段
            content = ch.content or ""
            idx = content.lower().find(q.lower())
            snippet = content[max(0, idx - 50):idx + 200] if idx >= 0 else content[:200]
            results.append(
                SearchResultItem(
                    id=ch.id,
                    type="chapter",
                    title=f"第{ch.chapter_num}章 {ch.title or ''}",
                    snippet=snippet,
                    project_id=ch.project_id,
                    project_title=proj_title,
                )
            )

    # ---- 搜索伏笔 ----
    if type is None or type == "foreshadow":
        f_result = await db.execute(
            select(ForeshadowPool, NovelProject.title)
            .join(NovelProject, ForeshadowPool.project_id == NovelProject.id)
            .where(
                ForeshadowPool.project_id.in_(user_pids),
                or_(
                    ForeshadowPool.description.ilike(pattern),
                    ForeshadowPool.payoff_quality_note.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        for fp, proj_title in f_result:
            results.append(
                SearchResultItem(
                    id=fp.id,
                    type="foreshadow",
                    title=f"伏笔 (第{fp.planted_chapter}章)",
                    snippet=fp.description[:200],
                    project_id=fp.project_id,
                    project_title=proj_title,
                )
            )

    # ---- 搜索知识条目 ----
    if type is None or type == "knowledge":
        k_result = await db.execute(
            select(KnowledgeEmbedding)
            .where(
                KnowledgeEmbedding.project_id.in_(user_pids),
                KnowledgeEmbedding.content.ilike(pattern),
            )
            .limit(limit)
        )
        for ke in k_result.scalars().all():
            results.append(
                SearchResultItem(
                    id=ke.id,
                    type="knowledge",
                    title=f"[{ke.knowledge_type}]",
                    snippet=ke.content[:200],
                    project_id=ke.project_id,
                    project_title=None,
                )
            )

    # ---- 搜索角色（从 characters_json） ----
    if type is None or type == "character":
        char_result = await db.execute(
            select(NovelProject)
            .where(
                NovelProject.id.in_(user_pids),
                # 使用 PostgreSQL JSONB 查询 characters_json
                text(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(characters_json) AS c "
                    "WHERE c->>'name' ILIKE :pat OR c->>'description' ILIKE :pat)"
                ).bindparams(pat=pattern),
            )
            .limit(limit)
        )
        for proj in char_result.scalars().all():
            # 从 characters_json 中提取匹配项
            characters = proj.characters_json or []
            for char in characters:
                name = char.get("name", "")
                desc = char.get("description", "")
                if q.lower() in name.lower() or q.lower() in desc.lower():
                    results.append(
                        SearchResultItem(
                            id=uuid.uuid4(),  # 角色没有独立表，使用虚拟 ID
                            type="character",
                            title=f"角色: {name}",
                            snippet=desc[:200],
                            project_id=proj.id,
                            project_title=proj.title,
                        )
                    )

    return results[:limit]
