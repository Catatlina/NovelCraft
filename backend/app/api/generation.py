"""
单章生成接口 —— Phase 2 最小写作闭环的落地点。
串联：状态机校验 -> Context Hub 组装7层上下文 -> novel-write Prompt -> DeepSeek -> 解析落库 -> 伏笔池更新

这是验证"Context Hub 是否真正解决断片问题"的关键接口（对应 v7.0 路线图 Phase 2 验收标准）。
批量生成（走五级调度队列）在 Phase 4 实现，会复用这里的 generate_single_chapter() 核心逻辑，
不重复写生成逻辑，队列层只负责编排循环调用。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.core.ratelimit import ai_limiter
from app.core.config import settings
from app.api.deps import get_current_user
from app.db.database import get_db
from datetime import datetime, timezone

from app.db.models import ForeshadowPool, NovelChapter, NovelProject, TokenLedger, User
from app.schemas import ChapterOut, GenerateChapterRequest
from app.services import context_hub, prompts
from app.services.deepseek_client import DeepSeekError, chat_completion

router = APIRouter(prefix="/api/v1/projects", tags=["generation"])


@router.post("/{project_id}/chapters/generate", response_model=ChapterOut)
@ai_limiter.limit("10/minute")
async def generate_chapter(
    request: Request,
    response: Response,
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

    # P0-3 fix: 生成完成后自动派发质量审查任务(review_queue此前定义了但从未被
    # 任何地方调用，是一段孤儿代码)。放在commit之后派发，避免worker在事务
    # 提交前就去读取还看不到的章节数据。审查是异步的，不阻塞生成接口返回。
    try:
        from app.tasks.pipeline import celery_app
        celery_app.send_task("review_queue", args=[str(chapter.id)], queue="review")
    except Exception:
        # 生成正文已经成功提交，质量审查入队失败不能让用户看到生成失败。
        # 后续可通过质量审查页面手动重试。
        import logging
        logging.getLogger("novelcraft.generation").exception("Failed to enqueue review task for chapter %s", chapter.id)

    return chapter


async def _generate_single_chapter(db: AsyncSession, project: NovelProject, mode: str) -> NovelChapter:
    """核心生成逻辑，供单章生成接口和批量 chapter_queue 共同调用。

    第二轮修复：不再在 SELECT FOR UPDATE 行锁内调用 AI。这里只用短事务预留章节号
    和占位章节，提交后再调用模型；模型返回后再用短事务写回正文、伏笔和统计。
    """
    # 1) 短事务：锁项目、分配章节号、写入占位章节并提交，避免 AI 调用期间持锁。
    await db.execute(
        text("SELECT 1 FROM novel_projects WHERE id = :pid FOR UPDATE"),
        {"pid": str(project.id)},
    )
    await db.refresh(project)

    if project.status not in ("writing", "world"):
        raise HTTPException(409, f"项目当前状态为 {project.status}，不能生成章节")

    estimated_tokens = max(1000, settings.max_chapter_tokens)
    reserved_result = await db.execute(
        select(func.coalesce(func.sum(TokenLedger.estimated_tokens), 0)).where(
            TokenLedger.project_id == project.id,
            TokenLedger.status == "reserved",
        )
    )
    reserved_tokens = reserved_result.scalar() or 0
    if project.token_budget and (project.token_used or 0) + reserved_tokens + estimated_tokens > project.token_budget:
        raise HTTPException(402, "Token 预算不足，请在项目设置中增加预算。")

    ledger = TokenLedger(
        project_id=project.id,
        user_id=project.user_id,
        task_type="chapter_generate",
        model=settings.deepseek_model,
        estimated_tokens=estimated_tokens,
        status="reserved",
    )
    db.add(ledger)

    # 失败的占位章节不参与下一章编号，避免 AI 失败后长期跳号。
    max_chapter_result = await db.execute(
        select(func.max(NovelChapter.chapter_num)).where(
            NovelChapter.project_id == project.id,
            NovelChapter.status != "failed",
        )
    )
    target_chapter_num = (max_chapter_result.scalar() or 0) + 1
    chapter = NovelChapter(
        project_id=project.id,
        chapter_num=target_chapter_num,
        title=f"第{target_chapter_num}章（生成中）",
        content="",
        word_count=0,
        summary="AI 生成中",
        status="generating",
    )
    db.add(chapter)
    project.total_chapters = target_chapter_num
    await db.flush()
    await db.commit()
    await db.refresh(chapter)

    # 2) 长耗时操作：不持有项目行锁。
    context = await context_hub.assemble_context(db, project.id, target_chapter_num)
    messages = prompts.build_novel_write_messages(context, mode=mode)

    try:
        result = await chat_completion(messages)
        parsed = prompts.parse_novel_write_response(result["content"])
    except DeepSeekError as e:
        # 删除失败占位并重算项目统计，避免污染章节序号和 total_chapters。
        await db.delete(chapter)
        ledger.status = "released"
        ledger.settled_at = datetime.now(timezone.utc)
        max_chapter_result = await db.execute(
            select(func.max(NovelChapter.chapter_num)).where(
                NovelChapter.project_id == project.id,
                NovelChapter.status != "failed",
            )
        )
        project.total_chapters = max_chapter_result.scalar() or 0
        await db.commit()
        raise HTTPException(502, "AI 服务暂时不可用，请稍后重试") from e
    except ValueError as e:
        await db.delete(chapter)
        ledger.status = "released"
        ledger.settled_at = datetime.now(timezone.utc)
        max_chapter_result = await db.execute(
            select(func.max(NovelChapter.chapter_num)).where(
                NovelChapter.project_id == project.id,
                NovelChapter.status != "failed",
            )
        )
        project.total_chapters = max_chapter_result.scalar() or 0
        await db.commit()
        raise HTTPException(502, "AI 返回格式异常，请重试") from e

    # 3) 短事务：写回正文、伏笔和统计。
    await db.execute(
        text("SELECT 1 FROM novel_projects WHERE id = :pid FOR UPDATE"),
        {"pid": str(project.id)},
    )
    await db.refresh(project)
    await db.refresh(chapter)

    chapter.title = parsed["title"]
    chapter.content = parsed["content"]
    chapter.word_count = len(parsed["content"])
    chapter.summary = parsed["summary"]
    chapter.status = "draft"

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

    resolved_ids = parsed.get("resolved_foreshadow_ids", [])
    if resolved_ids:
        valid_uuids = []
        for rid in resolved_ids:
            try:
                valid_uuids.append(uuid.UUID(rid))
            except (ValueError, TypeError):
                continue
        if valid_uuids:
            fs_query_result = await db.execute(
                select(ForeshadowPool).where(
                    ForeshadowPool.id.in_(valid_uuids),
                    ForeshadowPool.project_id == project.id,
                )
            )
            for fs_row in fs_query_result.scalars().all():
                fs_row.status = "paid_off"
                fs_row.payoff_chapter = target_chapter_num

    await _auto_mark_overdue_foreshadows(db, project.id, target_chapter_num)

    usage = result.get("usage", {}) or {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)
    used_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
    # Conservative default DeepSeek cost placeholders; production can override through billing config later.
    unit_price_input = 0.0
    unit_price_output = 0.0
    cost_usd = (input_tokens / 1_000_000 * unit_price_input) + (output_tokens / 1_000_000 * unit_price_output)
    project.total_words = (project.total_words or 0) + chapter.word_count
    project.token_used = (project.token_used or 0) + used_tokens
    ledger.input_tokens = input_tokens
    ledger.output_tokens = output_tokens
    ledger.actual_tokens = used_tokens
    ledger.unit_price_input = unit_price_input
    ledger.unit_price_output = unit_price_output
    ledger.cost_usd = cost_usd
    ledger.cost_cny = None
    ledger.status = "settled"
    ledger.settled_at = datetime.now(timezone.utc)

    return chapter

async def _auto_mark_overdue_foreshadows(db: AsyncSession, project_id: uuid.UUID, current_chapter_num: int) -> None:
    """自动标记超期伏笔：超过预期回收范围 5 章以上仍未回收的伏笔标记为 overdue"""
    import re
    planted_result = await db.execute(
        select(ForeshadowPool).where(
            ForeshadowPool.project_id == project_id,
            ForeshadowPool.status == "planted",
        )
    )
    for fs in planted_result.scalars().all():
        expected_max = fs.planted_chapter + 5
        if fs.expected_payoff_range:
            nums = re.findall(r'\d+', fs.expected_payoff_range)
            if len(nums) >= 2:
                expected_max = int(nums[1])
            elif len(nums) == 1:
                expected_max = int(nums[0])
        if current_chapter_num > expected_max + 5:
            fs.status = "overdue"
