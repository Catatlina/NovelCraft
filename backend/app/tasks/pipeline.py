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
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # 已有 running loop，在新线程中执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()

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
    task_routes={
        "app.tasks.pipeline.process_idea": {"queue": "idea"},
        "app.tasks.pipeline.process_outline": {"queue": "outline"},
        "app.tasks.pipeline.process_chapter": {"queue": "chapter"},
        "app.tasks.pipeline.process_review": {"queue": "review"},
        "app.tasks.pipeline.process_publish": {"queue": "publish"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)


async def enqueue_batch_generation(
    db: AsyncSession, project_id: str, chapter_count: int = 10
) -> str:
    """批量生成入口：入队 N 个章节生成任务"""
    from app.db.models import GenerationTask, NovelProject

    batch_id = _uuid.uuid4().hex[:8]
    project = await db.get(NovelProject, project_id)
    if not project:
        raise ValueError("项目不存在")

    if project.status not in ("writing", "world"):
        raise ValueError(f"项目状态 {project.status} 不允许批量生成")

    # Create batch task record
    task = GenerationTask(
        project_id=project_id,
        type="batch_chapter",
        status="queued",
        progress={"batch_id": batch_id, "total": chapter_count, "completed": 0, "current": 0},
    )
    db.add(task)
    await db.commit()

    # Enqueue individual chapters
    start_num = project.total_chapters + 1
    for i in range(chapter_count):
        chapter_queue.delay(str(project_id), start_num + i, batch_id)

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

                    user_prompt = f"""【选题】{topic}

【世界观设定】{world_setting or "（未提供，请根据选题合理发挥）"}

【目标字数】{target_words} 字

{variant_hint}

请严格按 system prompt 中约定的 JSON 格式输出。"""

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

    check_prompt = f"""请检查以下小说大纲是否存在逻辑一致性或前后矛盾的问题。

【选题】{topic}
【世界观】{world_setting or "无"}
【大纲】
{outline[:3000]}

请列出发现的所有逻辑问题，每条以 "- " 开头。如果没有问题，回复"无"。
只列出现实性逻辑问题（前后矛盾、时间线冲突、设定自洽性），不要评价创意好坏。"""

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


@celery_app.task(name="chapter_queue", bind=True, max_retries=2, default_retry_delay=60)
def chapter_queue(self, project_id: str, chapter_num: int, batch_id: str):
    """章节队列任务：生成单章"""
    import asyncio
    from app.db.database import AsyncSessionLocal
    from app.db.models import GenerationTask

    async def _run():
        async with AsyncSessionLocal() as db:
            from app.db.models import NovelProject
            project = await db.get(NovelProject, project_id)
            if not project:
                return {"error": "project not found"}
            # 并发安全: FOR UPDATE 锁住行防止 token 竞态
            from sqlalchemy import text
            await db.execute(text("SELECT 1 FROM novel_projects WHERE id = :pid FOR UPDATE"), {"pid": project_id})
            await db.refresh(project)
            if project.token_budget and (project.token_used or 0) >= project.token_budget:
                return {"error": "token budget exceeded"}

            # Generate at the pre-assigned chapter number
            from app.services import context_hub, prompts
            from app.services.deepseek_client import chat_completion, DeepSeekError
            from app.db.models import ForeshadowPool, NovelChapter

            context = await context_hub.assemble_context(db, project.id, chapter_num)
            messages = prompts.build_novel_write_messages(context, mode="continue")
            try:
                result = await chat_completion(messages)
            except DeepSeekError as e:
                return {"error": str(e)}
            parsed = prompts.parse_novel_write_response(result["content"])

            ch = NovelChapter(
                project_id=project.id, chapter_num=chapter_num,
                title=parsed["title"], content=parsed["content"],
                word_count=len(parsed["content"]), summary=parsed["summary"],
                status="draft",
            )
            db.add(ch)
            for fs in parsed.get("new_foreshadows", []):
                db.add(ForeshadowPool(project_id=project.id, description=fs.get("description",""),
                    planted_chapter=chapter_num, expected_payoff_range=fs.get("expected_payoff_range"),
                    status="planted"))
            project.total_chapters = max(project.total_chapters, chapter_num)
            project.total_words = (project.total_words or 0) + ch.word_count
            project.token_used = (project.token_used or 0) + result.get("usage", {}).get("total_tokens", 0)

            # Update batch progress
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

            return {"chapter_num": chapter_num, "title": ch.title, "words": ch.word_count}

    return _run_async(_run())


@celery_app.task(name="review_queue", bind=True, max_retries=1, default_retry_delay=120)
def review_queue(self, chapter_id: str):
    """审核队列任务：执行7维质量审查"""
    import asyncio

    async def _run():
        from app.db.database import AsyncSessionLocal
        from app.db.models import NovelChapter
        from app.services import context_hub
        from app.api.quality import _do_7d_review

        async with AsyncSessionLocal() as db:
            chapter = await db.get(NovelChapter, chapter_id)
            if not chapter:
                return {"error": "chapter not found"}
            project = await db.get(NovelChapter, chapter.project_id)
            if not project:
                return {"error": "project not found"}

            context = await context_hub.assemble_context(db, chapter.project_id, chapter.chapter_num)
            ctx_str = str(context.get("layer_6_recent_chapter_summaries", ""))[:1500]
            result = await _do_7d_review(
                str(chapter_id), chapter.content or "", chapter.outline or "", ctx_str, db
            )
            return {"overall_score": result.get("overall_score"), "chapter_id": chapter_id}

    return _run_async(_run())


celery_app.conf.task_routes = {
    "idea_pipeline_task": {"queue": "idea"},
    "outline_pipeline_task": {"queue": "outline"},
    "chapter_queue": {"queue": "chapter"},
    "review_queue": {"queue": "review"},
    "publish_pipeline_task": {"queue": "publish"},
}
