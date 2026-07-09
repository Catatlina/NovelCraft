"""Celery 调度流水线 — Phase 4 五级任务队列"""
import asyncio
import concurrent.futures
import uuid as _uuid
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


def _run_async(coro):
    """安全运行 async 协程，兼容 Celery 已运行 event loop 的场景。

    Celery worker 可能已在 event loop 中运行，此时 asyncio.run() 会抛 RuntimeError。
    此函数检测当前 loop 状态：无 loop 时直接 asyncio.run()，有 loop 时在新线程中运行。

    关键修复（本次验证 P0-2 时发现的系统性问题，影响本文件全部任务）：
    AsyncEngine/asyncpg 的连接是绑定在创建它们的 event loop 上的。每次任务调用
    都用 asyncio.run() 开一个全新的 loop，但 app.db.database 里的全局连接池是
    进程级单例——如果连接池跨这些不同的 loop 复用旧连接，会在同一个 worker
    进程处理完第一个任务后，从第二个任务开始必现
    'attached to a different loop' 崩溃(已用最小复现脚本验证过这个现象100%可复现)。
    每次任务执行完毕（无论成功还是异常）都主动 dispose 连接池，强制下一次任务
    重新建立全新连接，避免跨 event loop 复用。
    """
    async def _run_and_dispose():
        from app.db.database import engine as _db_engine
        try:
            return await coro
        finally:
            await _db_engine.dispose()

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run_and_dispose())
    # 已有 running loop，在新线程中执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _run_and_dispose()).result()


async def _bind_project_ai_context(db: AsyncSession, project) -> None:
    """Bind per-user AI credentials/model for Celery tasks.

    FastAPI requests get this through middleware, but Celery workers do not run
    request middleware. Every background task that calls DeepSeek must bind the
    project owner settings explicitly so user-level keys, model choice, cost
    attribution, and multi-tenant isolation work outside HTTP requests.
    """
    from app.api.user_ai_settings import load_user_deepseek_settings
    from app.services.deepseek_client import set_request_api_key, set_request_model

    user_id = getattr(project, "user_id", None)
    if not user_id:
        set_request_api_key(None)
        set_request_model(None)
        return
    key, model = await load_user_deepseek_settings(db, user_id)
    set_request_api_key(key)
    set_request_model(model)

celery_app = Celery(
    "novelcraft",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # 注意：task_routes 统一在文件末尾用真实注册任务名配置（此前这里有一份用
    # "app.tasks.pipeline.process_idea" 这类不存在的任务名写的路由表，从未生效，
    # 已删除以免误导 —— P0-1 修复的一部分）。
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)


async def enqueue_batch_generation(
    db: AsyncSession, project_id: str, chapter_count: int = 10
) -> str:
    """批量生成入口：串行入队 N 个章节生成任务。

    P0-2 fix: 此前用 for 循环把 N 个任务同时 send_task 到队列，Celery worker
    并发消费时会导致章节乱序生成——章节 N+1 可能在章节 N 还没提交时就开始
    组装上下文，读到不完整的前文；且 project.total_chapters 用 max() 更新，
    乱序完成时会让章节号出现永久性空洞。
    改为 celery chain()：同一批次的 N 个任务被串成一条链，前一个任务的
    结果回调之后，才会派发下一个任务，从根本上保证严格按顺序执行。
    章节号也不再预先计算，由每个任务运行时按 project.total_chapters+1
    动态获取（顺序执行下这样做是安全的，且更简单）。
    """
    from celery import chain
    from app.db.models import GenerationTask, NovelProject

    batch_id = _uuid.uuid4().hex[:8]
    project = await db.get(NovelProject, project_id)
    if not project:
        raise ValueError("项目不存在")

    if project.status not in ("writing", "world"):
        raise ValueError(f"项目状态 {project.status} 不允许批量生成")

    # P0-2(成本控制) fix: 同一项目同时只能有一个进行中的批次。
    # 虽然单次生成内部的 TOCTOU 竞态已经用 FOR UPDATE + refresh 修复，
    # 但"同一个项目同时跑两条独立的 chain"这种业务层面的并发此前没有
    # 任何限制——两条链会交替争抢同一个 total_chapters 计数、互相打乱
    # 对方的连续性，且让用户的 Token 消耗速度翻倍。
    existing = await db.execute(
        select(GenerationTask).where(
            GenerationTask.project_id == project_id,
            GenerationTask.type == "batch_chapter",
            GenerationTask.status.in_(("queued", "running")),
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        raise ValueError("该项目已有一个批量生成任务正在进行中，请等待完成或失败后再发起新批次")

    # Create batch task record
    task = GenerationTask(
        project_id=project_id,
        type="batch_chapter",
        status="queued",
        progress={"batch_id": batch_id, "total": chapter_count, "completed": 0, "current": 0},
    )
    db.add(task)
    await db.commit()

    # 串行链：chapter_queue 不再需要预先分配的章节号，每次调用时动态取号
    sig_chain = chain(*[
        chapter_queue.si(str(project_id), batch_id) for _ in range(chapter_count)
    ])
    sig_chain.apply_async()

    return batch_id


# ============================================================
# Phase 4.1: Idea 选题流水线
# ============================================================


@celery_app.task(bind=True, name="idea_pipeline_task", max_retries=3, default_retry_delay=60)
def idea_pipeline_task(
    self, project_id: str, platforms: list[str] | None = None
) -> dict:
    """
    流水线：扫描平台 → 去重 → 分析每本书 → 评分排序 → 选题推荐
    Phase 4.1：串联 novel-scan + novel-analyze prompts
    """
    import asyncio

    async def _run() -> dict:
        from app.db.database import AsyncSessionLocal
        from app.db.models import GenerationTask, NovelProject
        from app.services.prompts import (
            build_novel_scan_messages,
            build_novel_analyze_messages,
            parse_novel_analyze_response,
        )
        from app.services.scanner import scan_all
        from app.services.deepseek_client import chat_completion, DeepSeekError

        async with AsyncSessionLocal() as db:
            project = await db.get(NovelProject, project_id)
            if not project:
                return {"error": "项目不存在"}
            await _bind_project_ai_context(db, project)

            # Create generation task record
            task = GenerationTask(
                project_id=project_id,
                type="idea_pipeline",
                status="running",
                progress={"step": "scanning", "platforms": platforms or ["全部"]},
            )
            db.add(task)
            await db.commit()

            try:
                # 1. Call scanner to get ranking data
                task.progress = {"step": "scanning", "platforms": platforms or ["全部平台"]}
                await db.commit()

                scan_results = await scan_all(platforms)
                all_books: list[dict] = []
                for sr in scan_results:
                    for book in sr.books:
                        book_data = {
                            "title": book.get("title", ""),
                            "platform": sr.platform,
                            "region": sr.region,
                        }
                        all_books.append(book_data)

                # Deduplicate by title
                seen_titles: set[str] = set()
                deduped_books: list[dict] = []
                for book in all_books:
                    title_key = book["title"].strip().lower()
                    if title_key and title_key not in seen_titles:
                        seen_titles.add(title_key)
                        deduped_books.append(book)

                if not deduped_books:
                    task.status = "done"
                    task.progress = {"step": "completed", "total_books": 0, "results": []}
                    await db.commit()
                    return {"status": "done", "total_books": 0, "results": []}

                # 2. Analyze each book with batch scoring
                task.progress = {"step": "analyzing", "total": len(deduped_books), "completed": 0}
                await db.commit()

                scored_books: list[dict] = []
                batch_size = 5
                for batch_start in range(0, len(deduped_books), batch_size):
                    batch = deduped_books[batch_start : batch_start + batch_size]

                    for book in batch:
                        try:
                            analyze_messages = build_novel_analyze_messages(book)
                            result = await chat_completion(analyze_messages, temperature=0.3)
                            analyzed = parse_novel_analyze_response(result["content"])
                            scored_books.append(
                                {
                                    "title": book["title"],
                                    "platform": book["platform"],
                                    "region": book["region"],
                                    "hype_score": analyzed.get("hype_score", 0),
                                    "market_fit": analyzed.get("market_fit", ""),
                                    "reason": analyzed.get("reason", ""),
                                    "suggested_genre": analyzed.get("suggested_genre", ""),
                                }
                            )
                        except (DeepSeekError, ValueError) as e:
                            scored_books.append(
                                {
                                    "title": book["title"],
                                    "platform": book["platform"],
                                    "region": book["region"],
                                    "hype_score": 0,
                                    "market_fit": "",
                                    "reason": f"分析失败: {str(e)[:100]}",
                                    "suggested_genre": "",
                                }
                            )

                    task.progress["completed"] = min(
                        batch_start + batch_size, len(deduped_books)
                    )
                    await db.commit()

                # 3. Sort by hype score, generate recommendation list
                scored_books.sort(key=lambda b: b.get("hype_score", 0), reverse=True)
                top_recommendations = scored_books[:20]

                task.status = "done"
                task.progress = {
                    "step": "completed",
                    "total_scanned": len(deduped_books),
                    "total_analyzed": len(scored_books),
                    "top_recommendations": top_recommendations,
                }
                await db.commit()

                return {
                    "status": "done",
                    "project_id": project_id,
                    "total_scanned": len(deduped_books),
                    "total_analyzed": len(scored_books),
                    "recommendations": top_recommendations[:10],
                }

            except Exception as e:
                task.status = "failed"
                task.error_log = str(e)[:1000]
                task.progress = {"step": "error", "error": str(e)[:200]}
                await db.commit()
                raise

    return _run_async(_run())


# ============================================================
# Phase 4.2: Outline 大纲流水线
# ============================================================


@celery_app.task(bind=True, name="outline_pipeline_task", max_retries=2)
def outline_pipeline_task(
    self,
    project_id: str,
    topic: str,
    world_setting: str = "",
    target_words: int = 1000000,
    outline_count: int = 3,
) -> dict:
    """
    流水线：基于选题+世界观 → 批量生成大纲变体 → 校验一致性 → 评分排序
    Phase 4.2
    """
    import asyncio
    import json as _json

    async def _run() -> dict:
        from app.db.database import AsyncSessionLocal
        from app.db.models import GenerationTask, NovelProject
        from app.services.deepseek_client import chat_completion, DeepSeekError

        async with AsyncSessionLocal() as db:
            project = await db.get(NovelProject, project_id)
            if not project:
                return {"error": "项目不存在"}
            await _bind_project_ai_context(db, project)

            # Create generation task record
            task = GenerationTask(
                project_id=project_id,
                type="outline_pipeline",
                status="running",
                progress={
                    "step": "generating",
                    "total": outline_count,
                    "completed": 0,
                },
            )
            db.add(task)
            await db.commit()

            try:
                # 1. Generate multiple outline variants using novel-write prompt approach
                outlines: list[dict] = []
                for idx in range(outline_count):
                    system_prompt = (
                        "你是一名资深网络小说编辑和策划，正在为一本新书设计大纲。"
                        "你需要基于选题和世界观设定，创作一个结构完整、转折清晰的大纲。"
                        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
                        '{"title": "大纲标题", "outline": "完整大纲文本（包含分卷结构、主要剧情线、关键转折点）", '
                        '"innovation_score": 0-10, "pacing_quality": "节奏评价", '
                        '"commercial_potential": "商业潜力分析"}'
                    )

                    variant_hint = ""
                    if idx == 0:
                        variant_hint = "请给出一个经典三幕结构的大纲，节奏稳健，商业指向明确。"
                    elif idx == 1:
                        variant_hint = "请给出一个快节奏、多反转的创新大纲，注重开局爆点和连续高潮。"
                    else:
                        variant_hint = "请给出一个慢热型、重世界观铺陈的大纲，注重新奇感和深度。"

                    user_prompt = (
                        "【选题】" + str(topic) + "\n\n"
                        "【世界观设定】" + (str(world_setting) if world_setting else "（未提供，请根据选题合理发挥）") + "\n\n"
                        "【目标字数】" + str(target_words) + " 字\n\n"
                        + str(variant_hint) + "\n\n"
                        "请严格按 system prompt 中约定的 JSON 格式输出。"
                    )

                    try:
                        result = await chat_completion(
                            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                            temperature=0.9,
                        )
                        raw = result["content"].strip()
                        if raw.startswith("```"):
                            raw = raw.strip("`")
                            if raw.startswith("json"):
                                raw = raw[4:]
                            raw = raw.strip()
                        data = _json.loads(raw)

                        # 2. Check logical consistency
                        consistency_issues = await _check_outline_consistency(
                            data.get("outline", ""), topic, world_setting
                        )

                        outlines.append(
                            {
                                "variant": idx + 1,
                                "title": data.get("title", f"大纲方案{idx+1}"),
                                "outline": data.get("outline", ""),
                                "innovation_score": data.get("innovation_score", 5),
                                "pacing_quality": data.get("pacing_quality", ""),
                                "commercial_potential": data.get("commercial_potential", ""),
                                "consistency_issues": consistency_issues,
                            }
                        )
                    except (DeepSeekError, ValueError, _json.JSONDecodeError) as e:
                        outlines.append(
                            {
                                "variant": idx + 1,
                                "title": f"大纲方案{idx+1}（生成失败）",
                                "outline": "",
                                "innovation_score": 0,
                                "pacing_quality": "",
                                "commercial_potential": "",
                                "consistency_issues": [f"生成失败: {str(e)[:100]}"],
                            }
                        )

                    task.progress["completed"] = idx + 1
                    await db.commit()

                # 3. Score and sort
                def _score_outline(o: dict) -> float:
                    score = float(o.get("innovation_score", 5)) * 2.0
                    score -= len(o.get("consistency_issues", [])) * 3.0
                    return score

                outlines.sort(key=_score_outline, reverse=True)

                task.status = "done"
                task.progress = {
                    "step": "completed",
                    "topic": topic,
                    "world_setting": world_setting[:200],
                    "outline_count": len(outlines),
                    "outlines": outlines,
                }
                await db.commit()

                return {
                    "status": "done",
                    "project_id": project_id,
                    "topic": topic,
                    "outlines": outlines,
                    "best_outline": outlines[0] if outlines else None,
                }

            except Exception as e:
                task.status = "failed"
                task.error_log = str(e)[:1000]
                task.progress = {"step": "error", "error": str(e)[:200]}
                await db.commit()
                raise

    return _run_async(_run())


async def _check_outline_consistency(
    outline: str, topic: str, world_setting: str
) -> list[str]:
    """校验大纲的逻辑一致性，返回问题列表"""
    from app.services.deepseek_client import chat_completion, DeepSeekError

    if not outline:
        return ["大纲为空"]

    check_prompt = (
        "请检查以下小说大纲是否存在逻辑一致性或前后矛盾的问题。\n\n"
        "【选题】" + str(topic) + "\n"
        "【世界观】" + (str(world_setting) if world_setting else "无") + "\n"
        "【大纲】\n"
        + str(outline[:3000]) + "\n\n"
        "请列出发现的所有逻辑问题，每条以 \"- \" 开头。如果没有问题，回复\"无\"。\n"
        "只列出现实性逻辑问题（前后矛盾、时间线冲突、设定自洽性），不要评价创意好坏。"
    )

    try:
        result = await chat_completion(
            [{"role": "user", "content": check_prompt}],
            max_tokens=500,
            temperature=0.1,
        )
        issues_text = result["content"].strip()
        if issues_text == "无" or not issues_text:
            return []
        issues = [
            line.strip("- ").strip()
            for line in issues_text.split("\n")
            if line.strip().startswith("-")
        ]
        return issues if issues else []
    except DeepSeekError:
        return ["一致性检查服务暂时不可用"]


# ============================================================
# Phase 4.3: Publish 发布流水线
# ============================================================


@celery_app.task(bind=True, name="publish_pipeline_task", max_retries=3)
def publish_pipeline_task(
    self,
    project_id: str,
    target_platforms: list[str],
    chapters: list[int] | None = None,
    glossary: dict | None = None,
) -> dict:
    """
    流水线：选择章节 → 翻译 → 格式适配 → 发布 → 验证
    Phase 4.3：串联 novel-translate + Playwright 发布
    """
    import asyncio

    async def _run() -> dict:
        from app.db.database import AsyncSessionLocal
        from app.db.models import (
            GenerationTask,
            NovelChapter,
            NovelProject,
            PublishExecution,
            PublishRecord,
        )
        from app.services.prompts import build_novel_translate_messages
        from app.services.deepseek_client import chat_completion, DeepSeekError
        from app.services.publisher import publish_chapter_to_platform

        async with AsyncSessionLocal() as db:
            project = await db.get(NovelProject, project_id)
            if not project:
                return {"error": "项目不存在"}
            await _bind_project_ai_context(db, project)

            # Determine which chapters to publish
            if chapters:
                chapter_objs_result = await db.execute(
                    select(NovelChapter).where(
                        NovelChapter.project_id == project_id,
                        NovelChapter.chapter_num.in_(chapters),
                    ).order_by(NovelChapter.chapter_num)
                )
            else:
                # Default: all approved/draft chapters
                chapter_objs_result = await db.execute(
                    select(NovelChapter).where(
                        NovelChapter.project_id == project_id,
                        NovelChapter.status.in_(["draft", "approved"]),
                    ).order_by(NovelChapter.chapter_num)
                )

            chapter_objs = chapter_objs_result.scalars().all()
            if not chapter_objs:
                return {"status": "done", "message": "没有可发布的章节", "published": []}

            # Create overall generation task
            task = GenerationTask(
                project_id=project_id,
                type="publish_pipeline",
                status="running",
                progress={
                    "step": "publishing",
                    "platforms": target_platforms,
                    "total_chapters": len(chapter_objs),
                    "completed": 0,
                },
            )
            db.add(task)
            await db.commit()

            try:
                results: list[dict] = []
                for idx, ch in enumerate(chapter_objs):
                    ch_results = {"chapter_num": ch.chapter_num, "title": ch.title, "platforms": []}

                    for platform_key in target_platforms:
                        platform_lower = platform_key.lower()

                        # Translate if needed (海外平台)
                        content_to_publish = ch.content or ""
                        if platform_lower in ("webnovel", "royalroad", "wattpad", "scribblehub"):
                            translate_messages = build_novel_translate_messages(
                                ch.title or f"Chapter {ch.chapter_num}",
                                content_to_publish,
                                platform_lower,
                                glossary,
                            )
                            try:
                                trans_result = await chat_completion(translate_messages, temperature=0.3)
                                translated = trans_result["content"].strip()
                                content_to_publish = translated
                            except DeepSeekError:
                                # Fallback: use original content
                                pass

                        # Publish via Playwright or direct API
                        # Create PublishExecution record
                        execution = PublishExecution(
                            project_id=project_id,
                            platform=platform_key,
                            chapters=[ch.chapter_num],
                            status="running",
                        )
                        db.add(execution)
                        await db.commit()

                        pub_result = await publish_chapter_to_platform(
                            str(ch.id), platform_key
                        )

                        # Update execution record
                        execution.status = pub_result.get("status", "failed")
                        execution.logs = pub_result.get("reason", "")
                        if pub_result.get("url"):
                            execution.steps = [{"step": "published", "url": pub_result["url"]}]
                        await db.commit()

                        # Create PublishRecord for the chapter
                        pub_rec = PublishRecord(
                            chapter_id=ch.id,
                            platform=platform_key,
                            status=pub_result.get("status", "failed"),
                            published_url=pub_result.get("url", ""),
                            published_at=datetime.now(timezone.utc)
                            if pub_result.get("status") == "published"
                            else None,
                        )
                        db.add(pub_rec)

                        ch_results["platforms"].append(
                            {
                                "platform": platform_key,
                                "status": pub_result.get("status", "failed"),
                                "url": pub_result.get("url", ""),
                                "reason": pub_result.get("reason", ""),
                            }
                        )

                    await db.commit()
                    results.append(ch_results)

                    task.progress["completed"] = idx + 1
                    await db.commit()

                task.status = "done"
                task.progress = {
                    "step": "completed",
                    "platforms": target_platforms,
                    "total_chapters": len(chapter_objs),
                    "published_count": sum(
                        1
                        for r in results
                        for p in r["platforms"]
                        if p["status"] == "published"
                    ),
                    "results": results,
                }
                await db.commit()

                return {
                    "status": "done",
                    "project_id": project_id,
                    "platforms": target_platforms,
                    "total_chapters": len(chapter_objs),
                    "results": results,
                }

            except Exception as e:
                task.status = "failed"
                task.error_log = str(e)[:1000]
                task.progress = {"step": "error", "error": str(e)[:200]}
                await db.commit()
                raise

    return _run_async(_run())


# ============================================================
# Existing Chapter + Review Queues
# ============================================================


async def _mark_batch_failed(project_id: str, batch_id: str, error_msg: str) -> None:
    """用独立 session 把批次标记为失败并记录错误，供 chapter_queue 异常路径调用。"""
    from app.db.database import AsyncSessionLocal
    from app.db.models import GenerationTask

    async with AsyncSessionLocal() as db:
        bt = await db.execute(
            select(GenerationTask).where(
                GenerationTask.project_id == project_id,
                GenerationTask.type == "batch_chapter",
            ).order_by(GenerationTask.created_at.desc()).limit(1)
        )
        bt_row = bt.scalar_one_or_none()
        if bt_row:
            bt_row.status = "failed"
            bt_row.error_log = error_msg[:2000]
            await db.commit()


async def _update_batch_progress(project_id: str, batch_id: str, chapter_num: int) -> None:
    """用独立 session 更新批次进度，供 chapter_queue 成功路径调用。"""
    from app.db.database import AsyncSessionLocal
    from app.db.models import GenerationTask

    async with AsyncSessionLocal() as db:
        bt = await db.execute(
            select(GenerationTask).where(
                GenerationTask.project_id == project_id,
                GenerationTask.type == "batch_chapter",
            ).order_by(GenerationTask.created_at.desc()).limit(1)
        )
        bt_row = bt.scalar_one_or_none()
        if bt_row:
            p = bt_row.progress or {}
            p["completed"] = p.get("completed", 0) + 1
            p["current"] = chapter_num
            bt_row.progress = p
            if p["completed"] >= p.get("total", 0):
                bt_row.status = "done"
            await db.commit()


@celery_app.task(name="chapter_queue", bind=True, max_retries=2, default_retry_delay=60)
def chapter_queue(self, project_id: str, batch_id: str):
    """章节队列任务：复用单章生成接口的核心逻辑(_generate_single_chapter)，
    而不是自己重新实现一遍——此前两处逻辑各自维护，导致批量路径缺失伏笔回收
    和超期自动标记（单章接口有，批量没有）。现在统一走一份实现，两条路径
    行为自动保持一致。

    P0-2 fix: 不再需要外部传入预先分配的章节号——章节号由
    _generate_single_chapter 内部按 project.total_chapters+1 动态决定。
    配合 enqueue_batch_generation 里改用 celery chain() 严格顺序执行，
    每个任务开始时上一章必然已经完整提交，天然保证连续性、杜绝漏章。

    错误处理：此前失败时 return {"error": ...}，Celery 会把这当作任务成功，
    chain() 也就不会真正停下来，AI失败了还会继续生成下一章(读到的上下文缺了
    上一章)。现在区分：AI服务暂时不可用(502)是瞬时性错误，用 self.retry()
    真正重试；token预算超限(402)/项目状态不对(409)是终止性错误，直接标记
    批次失败并 raise，chain 后续任务不会再被执行。
    """
    from fastapi import HTTPException
    from app.db.database import AsyncSessionLocal
    from app.db.models import NovelProject

    async def _run():
        async with AsyncSessionLocal() as db:
            project = await db.get(NovelProject, project_id)
            if not project:
                raise ValueError(f"项目 {project_id} 不存在，批次 {batch_id} 终止")
            await _bind_project_ai_context(db, project)

            from app.api.generation import _generate_single_chapter

            try:
                chapter = await _generate_single_chapter(db, project, mode="continue")
                await db.commit()
            except HTTPException as e:
                await db.rollback()
                if e.status_code in (402, 409):
                    # 终止性错误：重试没有意义，标记批次失败，chain 不再继续
                    await _mark_batch_failed(project_id, batch_id, str(e.detail))
                    raise ValueError(str(e.detail)) from e
                # 502等瞬时性错误：值得重试；重试耗尽后 self.retry 会重新抛出原异常，
                # 由外层 _run_async 冒泡给 Celery，chain 同样会正确停止
                await _mark_batch_failed(project_id, batch_id, str(e.detail))
                raise self.retry(exc=e, countdown=60)

            # P0-3 fix: 批量路径同样自动派发质量审查，与单章接口行为保持一致
            celery_app.send_task("review_queue", args=[str(chapter.id)])

            await _update_batch_progress(project_id, batch_id, chapter.chapter_num)
            return {"chapter_num": chapter.chapter_num, "title": chapter.title, "words": chapter.word_count}

    return _run_async(_run())


@celery_app.task(name="review_queue", bind=True, max_retries=1, default_retry_delay=120)
def review_queue(self, chapter_id: str):
    """审核队列任务：执行7维质量审查"""
    import asyncio

    async def _run():
        from app.db.database import AsyncSessionLocal
        from app.db.models import NovelChapter, NovelProject
        from app.services import context_hub
        from app.api.quality import _do_7d_review

        async with AsyncSessionLocal() as db:
            chapter = await db.get(NovelChapter, chapter_id)
            if not chapter:
                return {"error": "chapter not found"}
            project = await db.get(NovelProject, chapter.project_id)
            if not project:
                return {"error": "project not found"}
            await _bind_project_ai_context(db, project)

            context = await context_hub.assemble_context(db, chapter.project_id, chapter.chapter_num)
            ctx_str = str(context.get("layer_6_recent_chapter_summaries", ""))[:1500]
            result = await _do_7d_review(
                str(chapter_id), chapter.content or "", chapter.outline or "", ctx_str, db
            )
            return {"overall_score": result.get("overall_score"), "chapter_id": chapter_id}

    return _run_async(_run())


@celery_app.task(name="publish_execution_task", bind=True, max_retries=3, default_retry_delay=120)
def publish_execution_task(
    self,
    execution_id: str,
    platform: str,
    chapter_ids: list[str],
    headless: bool = True,
    account_id: str | None = None,
) -> dict:
    """可靠发布执行任务。

    替代 FastAPI BackgroundTasks：任务进入 Redis/Celery 队列，由 worker 消费；
    API 容器重启不会造成任务直接丢失。发布执行内部仍会根据 execution.project_id
    和 project.user_id 进行章节、平台账号二次校验。
    """
    async def _run() -> dict:
        from app.api.publish_executions import _run_publish_execution

        await _run_publish_execution(execution_id, platform, chapter_ids, headless, account_id)
        return {"status": "done", "execution_id": execution_id}

    try:
        return _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


celery_app.conf.task_routes = {
    "idea_pipeline_task": {"queue": "idea"},
    "outline_pipeline_task": {"queue": "outline"},
    "chapter_queue": {"queue": "chapter"},
    "review_queue": {"queue": "review"},
    "publish_pipeline_task": {"queue": "publish"},
    "publish_execution_task": {"queue": "publish"},
}
