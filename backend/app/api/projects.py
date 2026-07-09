"""
项目 CRUD + 状态机迁移接口。
状态迁移统一走 POST /{project_id}/transition，业务操作接口（如更新总纲）
在满足条件时可以顺带自动触发迁移（见 update_outline），避免用户手动多点一步。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.core.state_machine import (
    IllegalStateTransition,
    build_history_entry,
    check_preconditions,
    validate_transition,
)
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, User
from app.schemas import (
    ChapterSummaryOut,
    ProjectCreate,
    ProjectOut,
    ProjectOutlineUpdate,
    ProjectWorldUpdate,
    TransitionRequest,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = NovelProject(title=payload.title, genre=payload.genre, platform=payload.platform, user_id=user.id)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.user_id == user.id).order_by(NovelProject.created_at.desc()))
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    await db.delete(project)
    await db.commit()


@router.get("/{project_id}/chapters", response_model=list[ChapterSummaryOut])
async def list_chapters(
    project_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """章节列表——只返回摘要信息，不含正文。

    P0-1 fix: 此前这里用 ChapterOut（含完整正文）且没有分页，一次性把
    项目下全部章节的全文都序列化返回。小说写得越长，这个接口的响应体积
    就越大、没有上限，直接和"支持百万字级长篇"这个目标相悖。现在只
    返回摘要 + 分页；正文通过新增的 GET /api/v1/chapters/{chapter_id}
    按需获取。
    """
    # 防御性校验：项目归属
    await get_user_project(str(project_id), user, db)
    result = await db.execute(
        select(NovelChapter)
        .where(NovelChapter.project_id == project_id)
        .order_by(NovelChapter.chapter_num)
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def _do_transition(db: AsyncSession, project: NovelProject, target: str, reason: str):
    """状态机迁移的公共逻辑：校验 + 前置条件检查 + 写历史。抛 IllegalStateTransition / ValueError 由调用方处理。"""
    tgt_state = validate_transition(project.status, target)
    fail_reason = check_preconditions(
        tgt_state,
        {
            "overall_outline": project.overall_outline,
            "power_system": project.power_system,
            "world_rules": project.world_rules,
            "world_setting": project.world_setting,
            "total_chapters": project.total_chapters,
        },
    )
    if fail_reason:
        raise ValueError(fail_reason)

    project.state_history = [*(project.state_history or []), build_history_entry(project.status, tgt_state.value, reason)]
    project.status = tgt_state.value


@router.post("/{project_id}/transition", response_model=ProjectOut)
async def transition_project(project_id: uuid.UUID, payload: TransitionRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    try:
        await _do_transition(db, project, payload.target_state, payload.reason)
    except IllegalStateTransition as e:
        raise HTTPException(409, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    await db.commit()
    await db.refresh(project)
    return project


@router.put("/{project_id}/outline", response_model=ProjectOut)
async def update_outline(project_id: uuid.UUID, payload: ProjectOutlineUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    project.overall_outline = payload.overall_outline

    # 总纲填好后，如果当前处于 Idea 状态，自动尝试迁移到 Outline
    if project.status == "idea":
        try:
            await _do_transition(db, project, "outline", reason="总纲已生成，自动迁移")
        except (IllegalStateTransition, ValueError):
            pass  # 自动迁移失败不阻断保存总纲本身

    await db.commit()
    await db.refresh(project)
    return project


@router.put("/{project_id}/world", response_model=ProjectOut)
async def update_world(project_id: uuid.UUID, payload: ProjectWorldUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if payload.power_system is not None:
        project.power_system = payload.power_system
    if payload.world_rules is not None:
        project.world_rules = payload.world_rules
    if payload.world_setting is not None:
        project.world_setting = payload.world_setting
    if payload.glossary_json is not None:
        project.glossary_json = payload.glossary_json

    if project.status == "outline":
        try:
            await _do_transition(db, project, "world", reason="知识库字段已填写，自动迁移")
        except (IllegalStateTransition, ValueError):
            pass

    await db.commit()
    await db.refresh(project)
    return project
