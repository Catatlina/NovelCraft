"""
世界观 Embedding API：chunk 管理、重建索引、相似检索。

说明：Embedding 生成依赖服务端配置的 DeepSeek key。若 embedding 服务不可用，
接口会保留 chunk 文本并降级为关键词检索，避免作品知识库完全不可用。
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import NovelProject, User, WorldSettingEmbedding
from app.services.context_hub import _get_embedding, rebuild_world_setting_embeddings

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/world-embeddings", tags=["world-embeddings"]
)


class ChunkCreate(BaseModel):
    chunk_text: str = Field(min_length=1, max_length=12000)
    metadata: dict = Field(default_factory=dict)


class ChunkUpdate(BaseModel):
    chunk_text: str | None = Field(default=None, min_length=1, max_length=12000)
    metadata: dict | None = None


class ChunkOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    chunk_text: str
    metadata: dict
    has_embedding: bool


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)


async def _get_user_project(project_id: uuid.UUID, user: User, db: AsyncSession) -> NovelProject:
    r = await db.execute(
        select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id)
    )
    project = r.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


def _chunk_out(row: WorldSettingEmbedding) -> ChunkOut:
    return ChunkOut(
        id=row.id,
        project_id=row.project_id,
        chunk_text=row.chunk_text,
        metadata=row.extra or {},
        has_embedding=row.embedding is not None,
    )


@router.get("", response_model=list[ChunkOut])
async def list_chunks(
    project_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_user_project(project_id, user, db)
    r = await db.execute(
        select(WorldSettingEmbedding)
        .where(WorldSettingEmbedding.project_id == project_id)
        .order_by(WorldSettingEmbedding.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_chunk_out(row) for row in r.scalars().all()]


@router.post("", response_model=ChunkOut)
async def create_chunk(
    project_id: uuid.UUID,
    req: ChunkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_user_project(project_id, user, db)
    embedding = await _get_embedding(req.chunk_text)
    row = WorldSettingEmbedding(
        project_id=project_id,
        chunk_text=req.chunk_text,
        embedding=embedding,
        extra=req.metadata,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _chunk_out(row)


@router.patch("/{chunk_id}", response_model=ChunkOut)
async def update_chunk(
    project_id: uuid.UUID,
    chunk_id: uuid.UUID,
    req: ChunkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_user_project(project_id, user, db)
    row = await db.get(WorldSettingEmbedding, chunk_id)
    if not row or row.project_id != project_id:
        raise HTTPException(404, "知识库 chunk 不存在")
    if req.chunk_text is not None:
        row.chunk_text = req.chunk_text
        row.embedding = await _get_embedding(req.chunk_text)
    if req.metadata is not None:
        row.extra = req.metadata
    await db.commit()
    await db.refresh(row)
    return _chunk_out(row)


@router.delete("/{chunk_id}")
async def delete_chunk(
    project_id: uuid.UUID,
    chunk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_user_project(project_id, user, db)
    r = await db.execute(
        delete(WorldSettingEmbedding).where(
            WorldSettingEmbedding.id == chunk_id,
            WorldSettingEmbedding.project_id == project_id,
        )
    )
    await db.commit()
    if r.rowcount == 0:
        raise HTTPException(404, "知识库 chunk 不存在")
    return {"deleted": True}


@router.post("/rebuild")
async def rebuild_chunks(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, user, db)
    await db.execute(delete(WorldSettingEmbedding).where(WorldSettingEmbedding.project_id == project_id))
    count = await rebuild_world_setting_embeddings(db, project)
    await db.commit()
    return {"project_id": str(project_id), "chunks_created": count}


@router.post("/search")
async def search_chunks(
    project_id: uuid.UUID,
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _get_user_project(project_id, user, db)
    embedding = await _get_embedding(req.query)
    if embedding:
        vec = "[" + ",".join(str(v) for v in embedding) + "]"
        r = await db.execute(
            text(
                """
                SELECT id, chunk_text, metadata, 1 - (embedding <=> :vec) AS similarity
                FROM world_setting_embeddings
                WHERE project_id = :project_id AND embedding IS NOT NULL
                ORDER BY embedding <=> :vec
                LIMIT :top_k
                """
            ),
            {"project_id": str(project_id), "vec": vec, "top_k": req.top_k},
        )
        rows = r.mappings().all()
        if rows:
            return [
                {
                    "id": str(row["id"]),
                    "chunk_text": row["chunk_text"],
                    "metadata": row["metadata"] or {},
                    "similarity": float(row["similarity"] or 0),
                    "mode": "vector",
                }
                for row in rows
            ]

    # 降级关键词检索：embedding 不可用或没有向量时仍可召回知识库。
    r = await db.execute(
        select(WorldSettingEmbedding)
        .where(
            WorldSettingEmbedding.project_id == project_id,
            WorldSettingEmbedding.chunk_text.ilike(f"%{req.query[:100]}%"),
        )
        .limit(req.top_k)
    )
    return [
        {
            "id": str(row.id),
            "chunk_text": row.chunk_text,
            "metadata": row.extra or {},
            "similarity": 0.0,
            "mode": "keyword",
        }
        for row in r.scalars().all()
    ]
