"""
单章生成接口 —— Phase 2 最小写作闭环的落地点。
串联：状态机校验 -> Context Hub 组装7层上下文 -> novel-write Prompt -> DeepSeek -> 解析落库 -> 伏笔池更新

这是验证"Context Hub 是否真正解决断片问题"的关键接口（对应 v7.0 路线图 Phase 2 验收标准）。
批量生成（走五级调度队列）在 Phase 4 实现，会复用这里的 generate_single_chapter() 核心逻辑，
不重复写生成逻辑，队列层只负责编排循环调用。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import ForeshadowPool, NovelChapter, NovelProject, User
from app.schemas import ChapterOut, GenerateChapterRequest
from app.services import context_hub, prompts
from app.services.deepseek_client import DeepSeekError, chat_completion

router = APIRouter(prefix="/api/v1/projects", tags=["generation"])


@router.post("/{project_id}/chapters/generate", response_model=ChapterOut)
async def generate_chapter(
    project_id: uuid.UUID, payload: GenerateChapterRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(NovelProject).where(NovelProject.id == project_id, NovelProject.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    if project.status not in ("writing", "world"):
        raise HTTPException(
            409,
            f"项目当前状态为 {project.status}，只有 world/writing 状态下才能生成章节。"
            "请先通过 /transition 接口迁移到 writing 状态。",
        )

    chapter = await _generate_single_chapter(db, project, payload.mode)
    await db.commit()
    await db.refresh(chapter)
    return chapter


async def _generate_single_chapter(db: AsyncSession, project: NovelProject, mode: str) -> NovelChapter:
    """核心生成逻辑，供单章接口和未来的批量队列(Phase4)共同调用。"""
    target_chapter_num = project.total_chapters + 1

    # 并发安全：SELECT FOR UPDATE 锁住 project 行防止编号冲突
    await db.execute(
        text("SELECT 1 FROM novel_projects WHERE id = :pid FOR UPDATE"),
        {"pid": str(project.id)},
    )

    context = await context_hub.assemble_context(db, project.id, target_chapter_num)
    messages = prompts.build_novel_write_messages(context, mode=mode)

    try:
        result = await chat_completion(messages)
    except DeepSeekError:
        raise HTTPException(502, "AI 服务暂时不可用，请稍后重试")

    try:
        parsed = prompts.parse_novel_write_response(result["content"])
    except ValueError:
        raise HTTPException(502, "AI 返回格式异常，请重试")

    chapter = NovelChapter(
        project_id=project.id,
        chapter_num=target_chapter_num,
        title=parsed["title"],
        content=parsed["content"],
        word_count=len(parsed["content"]),
        summary=parsed["summary"],
        status="draft",
    )
    db.add(chapter)

    # 伏笔埋点（❗③ 伏笔系统）：把模型新提出的伏笔写入 foreshadow_pool
    for fs in parsed.get("new_foreshadows", []):
        db.add(
            ForeshadowPool(
                project_id=project.id,
                description=fs.get("description", ""),
                planted_chapter=target_chapter_num,
                expected_payoff_range=fs.get("expected_payoff_range"),
                status="planted",
            )
        )

    # 伏笔回收：模型指出本章回收了哪些伏笔id，更新对应记录状态
    resolved_ids = parsed.get("resolved_foreshadow_ids", [])
    if resolved_ids:
        valid_uuids = []
        for rid in resolved_ids:
            try:
                valid_uuids.append(uuid.UUID(rid))
            except (ValueError, TypeError):
                continue  # 模型可能返回格式不对的id，跳过而不报错，避免整章生成失败
        if valid_uuids:
            result = await db.execute(select(ForeshadowPool).where(ForeshadowPool.id.in_(valid_uuids)))
            for fs_row in result.scalars().all():
                fs_row.status = "paid_off"
                fs_row.payoff_chapter = target_chapter_num

    # 更新项目统计
    project.total_chapters = target_chapter_num
    project.total_words = (project.total_words or 0) + chapter.word_count
    project.token_used = (project.token_used or 0) + result.get("usage", {}).get("total_tokens", 0)

    return chapter
