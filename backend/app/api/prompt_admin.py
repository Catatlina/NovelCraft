"""Prompt 模板管理 API — CRUD + 激活/回滚/列表"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import PromptTemplate, User
from app.services.prompt_registry import invalidate_cache

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["admin-prompts"])


class PromptCreateRequest(BaseModel):
    name: str
    system_prompt: str
    user_prompt_template: str = ""
    temperature: float = 0.9
    max_tokens: int = 4000
    description: str = ""


class PromptUpdateRequest(BaseModel):
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    description: str | None = None
    is_active: bool | None = None


@router.get("/")
async def list_prompts(
    name: str | None = Query(None),
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """列出所有 Prompt 模板版本"""
    q = select(PromptTemplate)
    if name:
        q = q.where(PromptTemplate.name == name)
    if active_only:
        q = q.where(PromptTemplate.is_active == True)
    q = q.order_by(PromptTemplate.name, PromptTemplate.version.desc())
    result = await db.execute(q)
    return [{
        "id": str(r.id), "name": r.name, "version": r.version,
        "system_prompt": r.system_prompt,
        "user_prompt_template": r.user_prompt_template,
        "temperature": r.temperature, "max_tokens": r.max_tokens,
        "description": r.description, "is_active": r.is_active,
        "created_at": str(r.created_at),
    } for r in result.scalars().all()]


@router.post("/")
async def create_prompt(
    req: PromptCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """创建 Prompt 新版本（自动递增 version）"""
    result = await db.execute(
        select(PromptTemplate.version)
        .where(PromptTemplate.name == req.name)
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    new_version = (latest or 0) + 1

    tpl = PromptTemplate(
        name=req.name, version=new_version,
        system_prompt=req.system_prompt,
        user_prompt_template=req.user_prompt_template,
        temperature=req.temperature, max_tokens=req.max_tokens,
        description=req.description, is_active=True,
    )
    db.add(tpl)
    await db.commit()
    await invalidate_cache()
    return {"id": str(tpl.id), "name": tpl.name, "version": tpl.version,
            "status": "created"}


@router.patch("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    req: PromptUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """更新 Prompt 模板"""
    tpl = await db.get(PromptTemplate, prompt_id)
    if not tpl:
        raise HTTPException(404, "模板不存在")
    for field in ("system_prompt", "user_prompt_template", "temperature",
                  "max_tokens", "description", "is_active"):
        val = getattr(req, field, None)
        if val is not None:
            setattr(tpl, field, val)
    await db.commit()
    await invalidate_cache()
    return {"status": "updated"}


@router.post("/{prompt_id}/activate")
async def activate_prompt(
    prompt_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """激活指定版本并停用同名其他版本（原子操作）"""
    tpl = await db.get(PromptTemplate, prompt_id)
    if not tpl:
        raise HTTPException(404, "模板不存在")
    # 停用同名其他版本
    await db.execute(
        PromptTemplate.__table__.update()
        .where(and_(
            PromptTemplate.name == tpl.name,
            PromptTemplate.id != tpl.id,
        ))
        .values(is_active=False)
    )
    tpl.is_active = True
    await db.commit()
    await invalidate_cache()
    return {"name": tpl.name, "version": tpl.version, "status": "activated"}
