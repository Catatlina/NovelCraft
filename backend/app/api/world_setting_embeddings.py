"""
Phase 3: 世界观 Embedding API — chunk 管理 + 向量相似检索。
"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/world-embeddings", tags=["world-embeddings"]
)

# 路由占位 — Phase 3 实现时填充具体的 chunk CRUD / search 端点
