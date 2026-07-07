"""
Context Hub 统一记忆中枢 ❗②
requirements_v7.md 2.2 节：解决长篇生成中 AI 断片 / 人物OOC / 设定冲突的核心组件。

所有生成请求（单章续写 / 批量生成）必须经过 assemble_context()，
不允许业务代码直接拼 prompt 字符串。

组装的 7 层上下文，对应文档 2.2 节：
    1. 全书总纲摘要
    2. 当前卷/阶段大纲
    3. 人物状态
    4. 世界设定（pgvector 语义向量检索，不可用时降级为关键词检索）
    5. 伏笔池
    6. 前N章摘要
    7. 防崩提醒

Phase 5：pgvector 语义检索已上线，_retrieve_relevant_world_setting()
改为对 world_setting_embeddings 表做 cosine similarity 检索，按
target_chapter 相关的关键词/实体做 top-k 召回。pgvector 不可用时降级
为关键词截断检索。
"""
from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ForeshadowPool, NovelChapter, NovelProject, WorldSettingEmbedding


async def _get_embedding(text: str) -> list[float] | None:
    """调用 DeepSeek Embeddings API 生成语义向量。
    
    失败时返回 None，调用方应降级到关键词检索。
    """
    import httpx
    from app.services.deepseek_client import _request_api_key
    key = _request_api_key.get() or settings.deepseek_api_key
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.deepseek_base_url}/embeddings",
                json={"model": "deepseek-chat", "input": text},
                headers={"Authorization": f"Bearer {key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception:
        return None


async def assemble_context(
    db: AsyncSession, project_id: uuid.UUID, target_chapter_num: int
) -> dict:
    """组装7层上下文，供所有生成请求使用。

    Args:
        db: 数据库 session（pgvector 检索需要）
        project_id: 项目 ID
        target_chapter_num: 目标章节号

    Returns:
        包含 7 层上下文 + meta 的结构化 dict
    """
    project = await db.get(NovelProject, project_id)
    if project is None:
        raise ValueError(f"项目不存在: {project_id}")

    # 6. 前N章摘要（优先用summary，没有summary就退化用content前200字，避免上下文爆炸）
    prev_result = await db.execute(
        select(NovelChapter)
        .where(NovelChapter.project_id == project_id, NovelChapter.chapter_num < target_chapter_num)
        .order_by(NovelChapter.chapter_num.desc())
        .limit(settings.context_prev_chapters)
    )
    prev_chapters = list(reversed(prev_result.scalars().all()))
    recent_summaries = [
        {
            "chapter_num": c.chapter_num,
            "title": c.title,
            "summary": c.summary or (c.content[:200] + "..." if c.content else ""),
        }
        for c in prev_chapters
    ]

    # 5. 伏笔池：本章相关的未回收伏笔（埋点章节 <= 目标章节，且未回收）
    fs_result = await db.execute(
        select(ForeshadowPool).where(
            ForeshadowPool.project_id == project_id,
            ForeshadowPool.status != "paid_off",
            ForeshadowPool.planted_chapter <= target_chapter_num,
        )
    )
    open_foreshadows = [
        {
            "id": str(f.id),
            "description": f.description,
            "planted_chapter": f.planted_chapter,
            "expected_payoff_range": f.expected_payoff_range,
            "status": f.status,
        }
        for f in fs_result.scalars().all()
    ]

    # 4. 世界设定：pgvector 语义向量检索（不可用时降级为关键词检索）
    world_setting_excerpt = await _retrieve_relevant_world_setting(
        project, recent_summaries, db
    )

    # 7. 防崩提醒：基于人物状态和伏笔池自动生成的硬性约束
    anti_crash_reminders = _build_anti_crash_reminders(project, open_foreshadows)

    return {
        "layer_1_overall_outline": project.overall_outline or "",
        "layer_2_current_arc_outline": _extract_current_arc(project.overall_outline, target_chapter_num),
        "layer_3_characters": project.characters_json or [],
        "layer_4_world_setting_excerpt": world_setting_excerpt,
        "layer_5_open_foreshadows": open_foreshadows,
        "layer_6_recent_chapter_summaries": recent_summaries,
        "layer_7_anti_crash_reminders": anti_crash_reminders,
        "meta": {
            "title": project.title,
            "genre": project.genre,
            "target_chapter_num": target_chapter_num,
        },
    }


async def _retrieve_relevant_world_setting(
    project: NovelProject,
    recent_summaries: list[dict],
    db: AsyncSession,
) -> str:
    """pgvector 语义向量检索：对 world_setting_embeddings 表做 cosine similarity 检索。

    流程：
        1. 从 recent_summaries 提取最近3章的关键词/主题作为 query
        2. 调用 DeepSeek Embeddings API 生成 query embedding
        3. 查询 world_setting_embeddings 表做 cosine similarity
        4. 取 top-5，拼接返回
        5. Embeddings API 不可用时降级为关键词检索

    Args:
        project: 当前项目
        recent_summaries: 最近章节摘要列表
        db: 数据库 session

    Returns:
        拼接后的世界观设定摘要文本
    """
    # 1. 从 recent_summaries 提取关键词/主题作为 query
    query_parts: list[str] = []
    for summary_entry in recent_summaries[-3:]:
        title = summary_entry.get("title", "")
        summary = summary_entry.get("summary", "")
        if title:
            query_parts.append(title)
        if summary:
            query_parts.append(summary[:100])

    query_text = " ".join(query_parts).strip()

    if not query_text:
        return _fallback_world_setting(project)

    # 2. 调用 DeepSeek Embeddings API 生成真实语义向量
    query_embedding = await _get_embedding(query_text)

    if query_embedding is None:
        # Embeddings API 不可用，降级为关键词检索
        return await _keyword_fallback_retrieval(project, query_text, db)

    # 3. pgvector cosine similarity 检索
    try:
        vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        result = await db.execute(
            text("""
                SELECT chunk_text, metadata,
                       1 - (embedding <=> :vec) AS similarity
                FROM world_setting_embeddings
                WHERE project_id = :pid
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :vec
                LIMIT :k
            """),
            {"vec": vec_str, "pid": str(project.id), "k": 5},
        )
        rows = result.fetchall()

        if rows:
            parts: list[str] = []
            for row in rows:
                chunk_text = row[0] or ""
                meta = row[1] or {}
                similarity = round(float(row[2]), 4)
                source_label = meta.get("source", "世界观")
                parts.append(
                    f"【{source_label}】[相似度:{similarity:.2f}]\n{chunk_text[:800]}"
                )
            return (
                "\n\n".join(parts)
                if parts
                else _fallback_world_setting(project)
            )
    except Exception:
        pass

    # 降级：关键词模糊匹配
    return await _keyword_fallback_retrieval(project, query_text, db)


async def _keyword_fallback_retrieval(
    project: NovelProject, query_text: str, db: AsyncSession
) -> str:
    """pgvector 不可用时的关键词降级检索方案。

    在 world_setting_embeddings 表内做文本模糊匹配 + 从项目字段中截取相关内容。
    """
    # 提取查询关键词
    keywords = _extract_keywords(query_text)

    if not keywords:
        return _fallback_world_setting(project)

    # 对每个关键词在 world_setting_embeddings 表内做模糊匹配
    parts: list[str] = []
    seen_ids: set[str] = set()

    for kw in keywords[:5]:
        try:
            result = await db.execute(
                select(WorldSettingEmbedding).where(
                    WorldSettingEmbedding.project_id == project.id,
                    WorldSettingEmbedding.chunk_text.ilike(f"%{kw}%"),
                ).limit(3)
            )
            for row in result.scalars().all():
                if str(row.id) not in seen_ids:
                    seen_ids.add(str(row.id))
                    source_label = (row.extra or {}).get("source", "世界观")
                    parts.append(f"【{source_label}】\n{row.chunk_text[:800]}")
        except Exception:
            continue

    if parts:
        return "\n\n".join(parts[:5])

    return _fallback_world_setting(project)


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取中文关键词（简易实现）"""
    import re

    # 按常见分隔符拆分，取长度 >= 2 的词
    words = re.split(r"[，,。；;！!？?\s]+", text)
    keywords: list[str] = []
    for w in words:
        w = w.strip()
        if len(w) >= 2 and w not in keywords:
            keywords.append(w)
    return keywords[:10]


def _fallback_world_setting(project: NovelProject) -> str:
    """最终降级方案：截取项目字段中的世界观内容"""
    parts = []
    for field_name, label in [
        ("power_system", "力量体系"),
        ("world_rules", "世界规则"),
        ("world_setting", "世界设定"),
    ]:
        val = getattr(project, field_name, None)
        if val:
            snippet = val if len(val) <= 800 else val[:800] + "...(已截断)"
            parts.append(f"【{label}】\n{snippet}")
    return "\n\n".join(parts) if parts else "（知识库暂无内容）"


def _keyword_vector(text: str, dims: int = 1536) -> list[float]:
    """关键词特征向量（DeepSeek embeddings 不可用时的降级方案）。

    基于 SHA-256 哈希生成确定性伪向量，确保相同输入得到相同向量。
    """
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    vec = []
    for i in range(min(dims, len(h) * 4)):
        b = h[i % len(h)]
        vec.append((b / 255.0) * 2 - 1)
    return vec + [0.0] * (dims - len(vec)) if dims > len(vec) else vec[:dims]


async def index_world_setting(
    db: AsyncSession,
    project_id: uuid.UUID,
    text: str,
    chunk_size: int = 512,
) -> int:
    """将世界观文本分块并生成 embedding 入库。

    Args:
        db: 数据库 session
        project_id: 项目 ID
        text: 世界观全文
        chunk_size: 每个 chunk 的最大字符数

    Returns:
        入库的 chunk 数量
    """
    if not text:
        return 0

    # 按 chunk_size 将文本分块（尽量在句号/换行处切分）
    chunks = _split_text_into_chunks(text, chunk_size)

    count = 0
    for i, chunk in enumerate(chunks):
        embedding = await _get_embedding(chunk)
        wse = WorldSettingEmbedding(
            project_id=project_id,
            chunk_text=chunk,
            embedding=embedding,
            metadata={"source": f"world_setting_chunk_{i+1}", "chunk_index": i},
        )
        db.add(wse)
        count += 1

    await db.commit()
    return count


def _split_text_into_chunks(text: str, chunk_size: int = 512) -> list[str]:
    """将长文本按 chunk_size 分块，尽量在自然断句处切分。

    Args:
        text: 待分块文本
        chunk_size: 每个 chunk 的目标最大字符数

    Returns:
        分块后的文本列表
    """
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break

        # 在 chunk_size 附近找最近的句号/换行作为切分点
        cut_point = chunk_size
        for delimiter in ["\n\n", "\n", "。", "！", "？", ".", "!", "?"]:
            pos = remaining.rfind(delimiter, 0, chunk_size)
            if pos > chunk_size // 2:
                cut_point = pos + len(delimiter)
                break

        chunks.append(remaining[:cut_point].strip())
        remaining = remaining[cut_point:].strip()

    return chunks


def _extract_current_arc(overall_outline: str | None, target_chapter_num: int) -> str:
    """
    过渡实现：从总纲文本里截取"当前卷"相关描述。
    真正的实现应基于 chapter_tree（JSONB，卷->章节范围映射）精确定位，
    当前先返回总纲全文的摘要占位，Phase 2 后续迭代补充 chapter_tree 解析逻辑。
    """
    if not overall_outline:
        return "（总纲为空）"
    return overall_outline[:1500]


def _build_anti_crash_reminders(project: NovelProject, open_foreshadows: list[dict]) -> list[str]:
    reminders = ["严格遵守已设定的人物性格与关系，不得出现OOC", "时间线只能向前推进，不得出现已发生事件被重复或倒叙错乱"]
    if open_foreshadows:
        reminders.append(
            f"当前有 {len(open_foreshadows)} 个未回收伏笔，如本章适合回收请自然处理，"
            "不要强行回收破坏节奏，也不要引入与已有伏笔矛盾的新设定"
        )
    if project.characters_json:
        reminders.append("已死亡或已离场角色不得无解释地重新出现")
    return reminders
