"""
Phase 3: 世界观推理规则 API — CRUD 管理 project_world_rules 表
+ 章节违规校验端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_project
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, ProjectWorldRule, User
from app.services.rule_engine import validate_rules, validate_chapter_after_generation

router = APIRouter(prefix="/api/v1/projects/{project_id}/world-rules", tags=["world-rules"])


# -----------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------


class RuleCreateRequest(BaseModel):
    """创建世界观推理规则"""
    rule_name: str
    rule_type: str = Field(
        ...,
        description="规则类型: numeric | temporal | relational | existential | causal",
    )
    description: str | None = None
    dsl_expression: str
    severity: str = Field(default="warn", description="error | warn")
    is_active: bool = True


class RuleUpdateRequest(BaseModel):
    """更新推理规则（所有字段可选）"""
    rule_name: str | None = None
    rule_type: str | None = None
    description: str | None = None
    dsl_expression: str | None = None
    severity: str | None = None
    is_active: bool | None = None


class ValidateChapterRequest(BaseModel):
    """校验章节是否违规"""
    chapter_id: str | None = None
    chapter_num: int | None = None
    chapter_text: str | None = None


class RuleOut(BaseModel):
    """规则响应"""
    id: str
    project_id: str
    rule_name: str
    rule_type: str
    description: str | None
    dsl_expression: str
    severity: str
    is_active: bool
    created_at: str | None


# -----------------------------------------------------------
# CRUD Endpoints
# -----------------------------------------------------------


@router.post("/rules")
async def create_rule(
    project_id: str,
    req: RuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建一条世界观推理规则"""
    project = await get_user_project(project_id, user, db)

    # Validate rule_type
    valid_types = {"numeric", "temporal", "relational", "existential", "causal"}
    if req.rule_type not in valid_types:
        raise HTTPException(
            400,
            f"无效的规则类型: {req.rule_type}，有效值为: {', '.join(sorted(valid_types))}",
        )

    valid_severities = {"error", "warn"}
    if req.severity not in valid_severities:
        raise HTTPException(400, f"无效的严重性: {req.severity}，有效值为: error, warn")

    rule = ProjectWorldRule(
        project_id=project.id,
        rule_name=req.rule_name,
        rule_type=req.rule_type,
        description=req.description,
        dsl_expression=req.dsl_expression,
        severity=req.severity,
        is_active=req.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return {
        "id": str(rule.id),
        "project_id": str(rule.project_id),
        "rule_name": rule.rule_name,
        "rule_type": rule.rule_type,
        "description": rule.description,
        "dsl_expression": rule.dsl_expression,
        "severity": rule.severity,
        "is_active": rule.is_active,
        "created_at": str(rule.created_at) if rule.created_at else None,
    }


@router.get("/rules")
async def list_rules(
    project_id: str,
    rule_type: str | None = Query(default=None, description="按类型过滤"),
    active_only: bool = Query(default=False, description="仅返回 active 规则"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出项目的所有世界观推理规则"""
    await get_user_project(project_id, user, db)

    q = select(ProjectWorldRule).where(ProjectWorldRule.project_id == project_id)
    if rule_type:
        q = q.where(ProjectWorldRule.rule_type == rule_type)
    if active_only:
        q = q.where(ProjectWorldRule.is_active == True)

    q = q.order_by(ProjectWorldRule.created_at.desc())
    result = await db.execute(q)
    rules = result.scalars().all()

    return {
        "project_id": project_id,
        "total": len(rules),
        "rules": [
            {
                "id": str(r.id),
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "description": r.description,
                "dsl_expression": r.dsl_expression,
                "severity": r.severity,
                "is_active": r.is_active,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rules
        ],
    }


@router.put("/rules/{rule_id}")
async def update_rule(
    project_id: str,
    rule_id: str,
    req: RuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新一条世界观推理规则"""
    await get_user_project(project_id, user, db)

    rule = await db.get(ProjectWorldRule, rule_id)
    if not rule or str(rule.project_id) != project_id:
        raise HTTPException(404, "规则不存在")

    if req.rule_name is not None:
        rule.rule_name = req.rule_name
    if req.rule_type is not None:
        valid_types = {"numeric", "temporal", "relational", "existential", "causal"}
        if req.rule_type not in valid_types:
            raise HTTPException(
                400,
                f"无效的规则类型: {req.rule_type}，有效值为: {', '.join(sorted(valid_types))}",
            )
        rule.rule_type = req.rule_type
    if req.description is not None:
        rule.description = req.description
    if req.dsl_expression is not None:
        rule.dsl_expression = req.dsl_expression
    if req.severity is not None:
        if req.severity not in ("error", "warn"):
            raise HTTPException(400, f"无效的严重性: {req.severity}")
        rule.severity = req.severity
    if req.is_active is not None:
        rule.is_active = req.is_active

    await db.commit()
    await db.refresh(rule)

    return {
        "id": str(rule.id),
        "project_id": str(rule.project_id),
        "rule_name": rule.rule_name,
        "rule_type": rule.rule_type,
        "description": rule.description,
        "dsl_expression": rule.dsl_expression,
        "severity": rule.severity,
        "is_active": rule.is_active,
        "created_at": str(rule.created_at) if rule.created_at else None,
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(
    project_id: str,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除一条世界观推理规则"""
    await get_user_project(project_id, user, db)

    rule = await db.get(ProjectWorldRule, rule_id)
    if not rule or str(rule.project_id) != project_id:
        raise HTTPException(404, "规则不存在")

    await db.delete(rule)
    await db.commit()

    return {"deleted": True, "rule_id": rule_id}


# -----------------------------------------------------------
# Validation Endpoint
# -----------------------------------------------------------


@router.post("/rules/validate")
async def validate_chapter_rules(
    project_id: str,
    req: ValidateChapterRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """校验章节是否违反项目的世界观规则。

    可通过 chapter_id（从数据库读取章节）、chapter_num（自动查找）或
    chapter_text（直接传入文本）指定要校验的章节。
    优先级：chapter_text > chapter_id > chapter_num
    """
    project = await get_user_project(project_id, user, db)

    chapter_text: str = ""
    chapter_num: int = 0

    if req.chapter_text:
        chapter_text = req.chapter_text
        chapter_num = req.chapter_num or 0
    elif req.chapter_id:
        chapter = await db.get(NovelChapter, req.chapter_id)
        if not chapter or str(chapter.project_id) != project_id:
            raise HTTPException(404, "章节不存在")
        chapter_text = chapter.content or ""
        chapter_num = chapter.chapter_num
    elif req.chapter_num:
        result = await db.execute(
            select(NovelChapter).where(
                NovelChapter.project_id == project_id,
                NovelChapter.chapter_num == req.chapter_num,
            )
        )
        chapter = result.scalar_one_or_none()
        if not chapter:
            raise HTTPException(404, f"第 {req.chapter_num} 章不存在")
        chapter_text = chapter.content or ""
        chapter_num = chapter.chapter_num
    else:
        raise HTTPException(400, "请提供 chapter_id、chapter_num 或 chapter_text")

    if not chapter_text:
        raise HTTPException(400, "章节内容为空，无法校验")

    # 调用规则引擎校验
    result = await validate_chapter_after_generation(
        db, project.id, chapter_text, chapter_num
    )

    return {
        "project_id": project_id,
        "chapter_num": chapter_num,
        "passed": result["passed"],
        "error_count": result["error_count"],
        "warn_count": result["warn_count"],
        "summary": result["summary"],
        "violations": result["violations"],
    }
