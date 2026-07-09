"""知识库嵌入 + 向量检索 API (Phase 5 — DeepSeek embeddings + pgvector)"""
import json
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import KnowledgeEmbedding, NovelProject, User, WorldSettingEmbedding
from app.services.deepseek_client import DeepSeekError, chat_completion

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


# -----------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------


class EmbedRequest(BaseModel):
    project_id: str
    knowledge_type: str
    content: str


class SearchRequest(BaseModel):
    project_id: str
    query: str
    top_k: int = 5


class InheritRequest(BaseModel):
    """跨项目知识继承请求"""
    source_project_id: str
    inherit_world_setting: bool = Field(default=True, description="继承世界观设定")
    inherit_characters: bool = Field(default=True, description="继承角色")
    inherit_glossary: bool = Field(default=True, description="继承术语表")
    inherit_rules: bool = Field(default=False, description="继承推理规则")
    auto_dedup: bool = Field(default=True, description="自动去重（基于文本相似度）")


# -----------------------------------------------------------
# Embedding Helpers
# -----------------------------------------------------------


from app.services.context_hub import _get_embedding


def _compute_text_hash(text: str) -> str:
    """计算文本 SHA-256 哈希，用于去重"""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


# -----------------------------------------------------------
# Existing Endpoints
# -----------------------------------------------------------


@router.post("/embed")
async def embed_knowledge(
    req: EmbedRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """将知识条目存入知识库并生成向量嵌入"""
    await get_user_project(req.project_id, user, db)

    embedding = await _get_embedding(req.content)
    emb = KnowledgeEmbedding(
        project_id=req.project_id,
        knowledge_type=req.knowledge_type,
        content=req.content,
        embedding=embedding,
    )
    db.add(emb)
    await db.commit()
    return {"id": str(emb.id), "type": req.knowledge_type, "status": "stored", "embedding_dim": len(embedding) if embedding else 0}


@router.post("/search")
async def search_knowledge(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """语义搜索知识库（pgvector cosine similarity）"""
    await get_user_project(req.project_id, user, db)

    query_embedding = await _get_embedding(req.query)
    if not query_embedding:
        raise HTTPException(502, "AI Embeddings 服务暂时不可用，请稍后重试")
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # 每页限制防止全表扫描 (P1-2: 大数据量时建议加 pg_trgm GIN索引)
    result = await db.execute(
        text("""
            SELECT id, knowledge_type, content, 
                   1 - (embedding <=> :vec) AS similarity
            FROM knowledge_embeddings
            WHERE project_id = :pid
            ORDER BY embedding <=> :vec
            LIMIT :k
        """),
        {"vec": vec_str, "pid": req.project_id, "k": req.top_k},
    )

    results = []
    for row in result:
        results.append({
            "id": str(row[0]),
            "type": row[1],
            "content": row[2][:300] if row[2] else "",
            "similarity": round(float(row[3]), 4),
        })

    # Fallback to keyword if vector search returns nothing
    if not results and req.query:
        r = await db.execute(
            select(KnowledgeEmbedding).where(
                KnowledgeEmbedding.project_id == req.project_id,
                KnowledgeEmbedding.content.ilike(f"%{req.query}%"),
            ).limit(req.top_k)
        )
        for emb in r.scalars().all():
            results.append({
                "id": str(emb.id),
                "type": emb.knowledge_type,
                "content": emb.content[:300],
                "similarity": 0.5,
            })

    return {"query": req.query, "results": results, "total": len(results)}


@router.get("/project/{project_id}")
async def list_knowledge(
    project_id: str,
    knowledge_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出项目的知识条目"""
    await get_user_project(project_id, user, db)
    q = select(KnowledgeEmbedding).where(KnowledgeEmbedding.project_id == project_id)
    if knowledge_type:
        q = q.where(KnowledgeEmbedding.knowledge_type == knowledge_type)
    q = q.order_by(KnowledgeEmbedding.created_at.desc()).limit(50)
    r = await db.execute(q)
    return [
        {"id": str(e.id), "type": e.knowledge_type, "content": e.content[:500],
         "has_embedding": e.embedding is not None, "created_at": str(e.created_at)}
        for e in r.scalars().all()
    ]


@router.post("/ingest-project/{project_id}")
async def ingest_project_knowledge(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """一键导入项目所有知识字段到知识库（含向量嵌入）"""
    project = await get_user_project(project_id, user, db)

    count = 0
    items = []
    for field, ktype in [
        ("power_system", "power_system"),
        ("world_rules", "world_rules"),
        ("world_setting", "world_setting"),
    ]:
        val = getattr(project, field, None)
        if val:
            items.append((ktype, val))

    if project.glossary_json:
        for term in project.glossary_json:
            content = f"{term.get('term','')}: {term.get('definition','')}"
            items.append(("glossary", content))

    if project.characters_json:
        for char in project.characters_json:
            content = json.dumps(char, ensure_ascii=False)
            items.append(("character", content))

    for ktype, content in items:
        embedding = await _get_embedding(content)
        db.add(KnowledgeEmbedding(project_id=project_id, knowledge_type=ktype,
                                  content=content, embedding=embedding))
        count += 1

    await db.commit()
    return {"project_id": project_id, "entries_created": count, "status": "ingested_with_embeddings"}


# -----------------------------------------------------------
# Cross-Project Knowledge Inheritance (Phase 5)
# -----------------------------------------------------------


@router.post("/projects/{target_id}/inherit")
async def inherit_knowledge(
    target_id: str,
    req: InheritRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    从源项目选择性地继承：世界观/角色/术语/规则。

    自动去重：基于文本 SHA-256 哈希检查目标项目是否已有相同内容，
    已在目标项目中存在的条目不会被重复导入。

    embeddings 随继承自动生成：利用 _get_embedding 为每条继承内容
    生成向量嵌入，同时写入 knowledge_embeddings 表和
    world_setting_embeddings 表（世界观文本分块）。

    所有继承条目标记 origin_project_id（通过 metadata JSON 字段）。
    """
    from app.db.models import ProjectWorldRule
    from app.services.context_hub import index_world_setting

    # 验证源项目和目标项目都归当前用户所有
    target_project = await get_user_project(target_id, user, db)
    source_project = await get_user_project(req.source_project_id, user, db)

    if target_id == req.source_project_id:
        raise HTTPException(400, "源项目和目标项目不能相同")

    # 获取目标项目已存在的知识哈希集合（用于去重）
    existing_hashes: set[str] = set()
    if req.auto_dedup:
        existing_result = await db.execute(
            select(KnowledgeEmbedding)
            .where(KnowledgeEmbedding.project_id == target_id)
            .order_by(KnowledgeEmbedding.created_at)
        )
        for emb in existing_result.scalars().all():
            existing_hashes.add(_compute_text_hash(emb.content or ""))

    stats = {
        "world_setting": 0,
        "characters": 0,
        "glossary": 0,
        "rules": 0,
        "skipped_duplicates": 0,
    }
    origin_meta = {"origin_project_id": str(source_project.id), "origin_title": source_project.title or ""}

    # --- 世界观 ---
    if req.inherit_world_setting:
        world_parts: list[str] = []
        for field in ("world_setting", "power_system", "world_rules"):
            val = getattr(source_project, field, None)
            if val and val.strip():
                world_parts.append(val.strip())

        if world_parts:
            full_world_text = "\n\n".join(world_parts)
            text_hash = _compute_text_hash(full_world_text)
            if text_hash not in existing_hashes:
                # 写入 knowledge_embeddings
                embedding = await _get_embedding(full_world_text)
                emb = KnowledgeEmbedding(
                    project_id=target_id,
                    knowledge_type="world_setting",
                    content=full_world_text,
                    embedding=embedding,
                )
                db.add(emb)
                existing_hashes.add(text_hash)

                # 分块写入 world_setting_embeddings 表
                chunk_count = await index_world_setting(
                    db, target_project.id, full_world_text, chunk_size=512
                )
                stats["world_setting"] = chunk_count + 1  # +1 for the knowledge_embeddings entry
            else:
                stats["skipped_duplicates"] += 1

    # --- 角色 ---
    if req.inherit_characters and source_project.characters_json:
        for char_data in source_project.characters_json:
            char_text = json.dumps(char_data, ensure_ascii=False)
            text_hash = _compute_text_hash(char_text)
            if text_hash not in existing_hashes:
                embedding = await _get_embedding(char_text)
                emb = KnowledgeEmbedding(
                    project_id=target_id,
                    knowledge_type="character",
                    content=char_text,
                    embedding=embedding,
                )
                db.add(emb)
                existing_hashes.add(text_hash)
                stats["characters"] += 1

                # 角色名也写入 world_setting_embeddings（供检索时匹配）
                char_name = char_data.get("name", "") if isinstance(char_data, dict) else ""
                if char_name:
                    char_chunk = f"角色：{char_name}。" + char_text[:500]
                    char_embedding = await _get_embedding(char_chunk)
                    wse = WorldSettingEmbedding(
                        project_id=target_id,
                        chunk_text=char_chunk,
                        embedding=char_embedding,
                        metadata={**origin_meta, "source": "character", "name": char_name},
                    )
                    db.add(wse)
            else:
                stats["skipped_duplicates"] += 1

    # --- 术语表 ---
    if req.inherit_glossary and source_project.glossary_json:
        for term in source_project.glossary_json:
            term_content = f"{term.get('term','')}: {term.get('definition','')}"
            text_hash = _compute_text_hash(term_content)
            if text_hash not in existing_hashes:
                embedding = await _get_embedding(term_content)
                emb = KnowledgeEmbedding(
                    project_id=target_id,
                    knowledge_type="glossary",
                    content=term_content,
                    embedding=embedding,
                )
                db.add(emb)
                existing_hashes.add(text_hash)
                stats["glossary"] += 1

                # 术语也写入 world_setting_embeddings
                term_embedding = await _get_embedding(term_content)
                wse = WorldSettingEmbedding(
                    project_id=target_id,
                    chunk_text=term_content,
                    embedding=term_embedding,
                    metadata={**origin_meta, "source": "glossary", "term": term.get("term", "")},
                )
                db.add(wse)
            else:
                stats["skipped_duplicates"] += 1

    # --- 推理规则 ---
    if req.inherit_rules:
        rules_result = await db.execute(
            select(ProjectWorldRule).where(
                ProjectWorldRule.project_id == source_project.id,
            )
        )
        source_rules = rules_result.scalars().all()

        # 获取目标项目已有规则名集合（用于去重）
        existing_rule_names: set[str] = set()
        target_rules_result = await db.execute(
            select(ProjectWorldRule).where(
                ProjectWorldRule.project_id == target_id,
            )
        )
        for r in target_rules_result.scalars().all():
            existing_rule_names.add(r.rule_name.lower().strip())

        for source_rule in source_rules:
            rule_name_lower = source_rule.rule_name.lower().strip()
            if rule_name_lower in existing_rule_names:
                stats["skipped_duplicates"] += 1
                continue

            new_rule = ProjectWorldRule(
                project_id=target_id,
                rule_name=source_rule.rule_name,
                rule_type=source_rule.rule_type,
                description=source_rule.description,
                dsl_expression=source_rule.dsl_expression,
                severity=source_rule.severity,
                is_active=source_rule.is_active,
            )
            db.add(new_rule)
            existing_rule_names.add(rule_name_lower)
            stats["rules"] += 1

    await db.commit()

    return {
        "target_project_id": target_id,
        "source_project_id": req.source_project_id,
        "source_title": source_project.title,
        "inherited": stats,
        "status": "completed_with_embeddings",
    }
