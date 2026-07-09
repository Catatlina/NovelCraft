"""
灵感快速启动 — 一句话→完整小说初稿全链路。

POST /api/v1/projects/quick-start
输入灵感 + 题材 → 自动生成：书名(3个)→简介→全书大纲→细纲→章节树→第一章
"""
import asyncio
import json
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models import NovelChapter, NovelProject, TokenLedger, User
from app.services.context_hub import assemble_context
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.novel_agents import get_novel_agents
from app.services.plot_controller import AutoRevisionLoop, PlotController
from app.services.prompts import build_novel_write_messages

router = APIRouter(prefix="/api/v1/projects", tags=["quick-start"])


class QuickStartRequest(BaseModel):
    idea: str = Field(..., min_length=5, max_length=200, description="一句话灵感")
    genre: str = Field(default="修真", description="题材")
    target_words: int = Field(default=1_000_000, ge=100_000, le=5_000_000)


_PROMPT_TITLES = """你是一名资深网文编辑。根据以下灵感，生成3个不同风格的书名。

灵感：{idea}
题材：{genre}

要求：
- 3个书名风格差异大（如：一个直白型、一个意境型、一个脑洞型）
- 每个书名2-8个汉字
- 输出纯JSON数组：["书名1", "书名2", "书名3"]"""

_PROMPT_SYNOPSIS = """你是一名资深网文编辑。为以下小说写一段150-200字的简介。

书名：{title}
灵感：{idea}
题材：{genre}

要求：
- 第一句抛出核心矛盾/悬念
- 第二句暗示世界观特点
- 最后一句留钩子
- 输出纯文本，不要JSON"""  # 纯文本，150-200字

_PROMPT_OUTLINE = """你是一名网文大纲专家。为以下小说撰写全书大纲。

书名：{title}
简介：{synopsis}
题材：{genre}
目标字数：{target_words}字

要求：
- 分5-8卷，每卷1个主题+3-5个关键事件
- 每卷标注预期章节范围（如"1-120章"）
- 输出JSON：
[{{"volume": 1, "title": "卷名", "theme": "主题", "start_chapter": 1, "end_chapter": N, "events": ["事件1", "事件2", ...]}}]"""

_PROMPT_DETAILED_OUTLINE = """你是一名网文细纲专家。为以下小说的前3章撰写细纲。

书名：{title}
简介：{synopsis}
大纲第1卷：{volume1_outline}

要求：
- 每章1200-1500字细纲
- 包含：场景设置、人物出场/动机、情感变化、伏笔埋设点、章节结尾钩子
- 输出JSON：
[{{"chapter_num": 1, "title": "章名", "scene": "场景", "characters_involved": [], "motivation": "动机", "emotional_arc": "情感弧线", "foreshadow_plant": "伏笔", "ending_hook": "结尾钩子", "target_words": 2500}}]"""

_PROMPT_FIRST_CHAPTER = """你是一名专业网络小说写手，正在撰写第一章正文。

书名：{title}
简介：{synopsis}
题材：{genre}
细纲：{detailed_outline_ch1}

要求：
- 2000-3500字完整正文
- 黄金三章第一章必须有强钩子
- 文笔流畅自然，杜绝"AI味"
- 输出JSON：
{{"title": "本章标题", "content": "本章正文", "summary": "100字以内摘要"}}"""


def _parse_json_response(raw: str) -> dict | list:
    """从 LLM 返回中提取 JSON"""
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    # Try to find JSON boundaries
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        si = raw.find(start_char)
        ei = raw.rfind(end_char)
        if si >= 0 and ei > si:
            return json.loads(raw[si:ei + 1])
    return json.loads(raw)


async def _call_llm(prompt: str, temperature: float = 0.8, max_tokens: int = 4000, system: str = "") -> str:
    """调用 DeepSeek，返回纯文本"""
    messages = [{"role": "system", "content": system or "输出纯文本，不要 markdown 格式。"},
                {"role": "user", "content": prompt}]
    r = await chat_completion(messages, temperature=temperature, max_tokens=max_tokens)
    return r["content"].strip()


@router.post("/quick-start")
async def quick_start(
    req: QuickStartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    一句话灵感 → 完整小说初稿全链路生成。

    步骤：
    1. 生成3个候选书名
    2. 生成简介
    3. 生成全书大纲(5-8卷)
    4. 生成前三章细纲
    5. 构建章节树
    6. 创建项目+第一章
    """
    try:
        # ── Step 1: 书名 ──
        titles_raw = await _call_llm(
            _PROMPT_TITLES.format(idea=req.idea, genre=req.genre),
            temperature=0.9, max_tokens=500,
            system="你是网文起名专家。只输出JSON数组，不要任何解释。")
        titles = _parse_json_response(titles_raw)
        if not isinstance(titles, list) or len(titles) < 3:
            raise HTTPException(502, "AI 书名生成失败")

        # ── Step 2: 简介 ──
        title = titles[0]
        synopsis = await _call_llm(
            _PROMPT_SYNOPSIS.format(title=title, idea=req.idea, genre=req.genre),
            temperature=0.8, max_tokens=800,
            system="你是网文简介专家。只输出简介文字，不要JSON标记。")

        # ── Step 3: 大纲 ──
        outline_raw = await _call_llm(
            _PROMPT_OUTLINE.format(title=title, synopsis=synopsis, genre=req.genre,
                                     target_words=f"{req.target_words:,}"),
            temperature=0.7, max_tokens=4000,
            system="你是网文大纲专家。只输出JSON，不要任何解释。")
        outline = _parse_json_response(outline_raw)
        if not isinstance(outline, list) or len(outline) == 0:
            raise HTTPException(502, "AI 大纲生成失败")

        # ── Step 4: 细纲（前3章） ──
        vol1 = outline[0] if outline else {"title": "第一卷", "events": []}
        vol1_text = json.dumps(vol1, ensure_ascii=False)
        detailed_raw = await _call_llm(
            _PROMPT_DETAILED_OUTLINE.format(title=title, synopsis=synopsis, volume1_outline=vol1_text),
            temperature=0.7, max_tokens=4000,
            system="你是网文细纲专家。只输出JSON，不要任何解释。")
        detailed = _parse_json_response(detailed_raw)
        if not isinstance(detailed, list) or len(detailed) == 0:
            raise HTTPException(502, "AI 细纲生成失败")

        # ── Step 5: 构建章节树 ──
        chapter_tree = []
        for vol in outline:
            ch_start = vol.get("start_chapter", 1)
            ch_end = vol.get("end_chapter", ch_start + 100)
            chapters = []
            for i in range(ch_start, min(ch_start + 3, ch_end + 1)):
                chapters.append({"num": i, "title": f"第{i}章"})
            chapter_tree.append({
                "volume": vol.get("volume", len(chapter_tree) + 1),
                "title": vol.get("title", f"第{len(chapter_tree)+1}卷"),
                "theme": vol.get("theme", ""),
                "start_chapter": ch_start,
                "end_chapter": ch_end,
                "chapters": chapters,
            })

        # ── Step 6: 生成第一章 ──
        ch1_detail = detailed[0] if detailed else {"scene": "", "ending_hook": ""}
        ch1_text = json.dumps(ch1_detail, ensure_ascii=False)
        ch1_raw = await _call_llm(
            _PROMPT_FIRST_CHAPTER.format(title=title, synopsis=synopsis,
                                          genre=req.genre, detailed_outline_ch1=ch1_text),
            temperature=0.9, max_tokens=4000,
            system="你是专业网络小说写手。只输出JSON，不要任何解释。")
        ch1 = _parse_json_response(ch1_raw)
        if not isinstance(ch1, dict):
            raise HTTPException(502, "AI 第一章生成失败")

        # ── Step 7: 写入数据库 ──
        project = NovelProject(
            id=_uuid.uuid4(),
            user_id=user.id,
            title=title,
            genre=req.genre,
            status="writing",
            overall_outline=json.dumps(outline, ensure_ascii=False),
            description=synopsis,
            chapter_tree=chapter_tree,
            target_words=req.target_words,
            total_chapters=1,
            total_words=0,
        )
        db.add(project)
        await db.flush()

        chapter = NovelChapter(
            id=_uuid.uuid4(),
            project_id=project.id,
            chapter_num=1,
            title=ch1.get("title", "第一章"),
            content=ch1.get("content", ""),
            summary=ch1.get("summary", ""),
            word_count=len(ch1.get("content", "") or ""),
            status="draft",
        )
        db.add(chapter)
        await db.commit()

        return {
            "project_id": str(project.id),
            "titles": titles,
            "selected_title": title,
            "synopsis": synopsis,
            "outline": outline,
            "detailed_outline": detailed,
            "chapter_tree": chapter_tree,
            "first_chapter": {
                "chapter_id": str(chapter.id),
                "title": ch1.get("title"),
                "content": ch1.get("content", "")[:500] + "...",
                "summary": ch1.get("summary"),
                "word_count": chapter.word_count,
            },
        }

    except DeepSeekError as e:
        raise HTTPException(502, f"AI 服务暂时不可用: {e.detail if hasattr(e, 'detail') else str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(502, "AI 返回格式异常，请重试")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"生成失败: {str(e)[:200]}")


@router.get("/quick-start/{project_id}/resume")
async def resume_quick_start(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """恢复查看之前生成的快速开始结果"""
    # verify ownership
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    # Fetch chapters
    ch_result = await db.execute(
        select(NovelChapter).where(
            NovelChapter.project_id == project.id,
        ).order_by(NovelChapter.chapter_num).limit(1)
    )
    ch = ch_result.scalar_one_or_none()

    return {
        "project_id": str(project.id),
        "title": project.title,
        "synopsis": project.description,
        "outline": json.loads(project.overall_outline) if project.overall_outline else [],
        "chapter_tree": project.chapter_tree or [],
        "first_chapter": {
            "chapter_id": str(ch.id) if ch else None,
            "title": ch.title if ch else None,
            "content": (ch.content or "") if ch else "",
            "summary": ch.summary if ch else None,
            "word_count": ch.word_count if ch else 0,
        } if ch else None,
    }


# ══════════════════════════════════════════
# 全自动流水线 + 拆文仿写
# 参考: AI-Workbench backend/app/api/v1/novel.py
# ══════════════════════════════════════════

class AutoRequest(BaseModel):
    platform: str = "qidian"
    category: str = ""
    extra_prompt: str = ""


class ImitateRequest(BaseModel):
    url: str = ""
    text: str = ""
    chapter_count: int = Field(default=3, ge=1, le=10)


_AUTO_PLAN_PROMPT = """从以下扫榜报告中，选一个最易出爆款的选题方向，为该选题做全书规划。

扫榜报告：
{scan_text}

额外要求：{extra_prompt}

请严格按以下格式输出：

【书名建议】
给出3个备选书名，每行一个。第一个是你最推荐的。

【题材】
一句话描述题材方向

【全书总纲】
以3-5卷规划全书，每卷写清核心事件和情绪走向。

【人物系统】
主角（名字/年龄/身份/性格/核心驱动力）、主要配角（每人一行）

【章节树】
列出前10章每章一句话概要"""


@router.post("/auto")
async def auto_pipeline(
    req: AutoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """全自动流水线: 扫榜→全书规划→黄金三章细纲→三章正文→入库"""
    import re as _re
    step = "scan"
    try:
        scan_text = await _call_llm(
            f"分析{req.platform}平台{req.category or '热门'}榜单趋势。爆款题材TOP5、热门叙事模式。",
            temperature=0.7, max_tokens=2000)

        step = "plan"
        plan_text = await _call_llm(
            _AUTO_PLAN_PROMPT.format(
                scan_text=scan_text[:2500],
                extra_prompt=req.extra_prompt or "强钩子高爽点开篇"),
            temperature=0.8, max_tokens=4000)

        title = ""
        for pat in [r'【书名建议】\s*\n?\s*(.+?)(?:\n|$)', r'《(.+?)》']:
            m = _re.search(pat, plan_text, _re.MULTILINE)
            if m:
                title = _re.sub(r'【.*?】|《|》|备选书名|^\d+\.\s*', '', m.group(1)).strip(' -–,.。')[:40]
                if '、' in title: title = title.split('、')[0].strip()
                if len(title) >= 2: break
        if len(title) < 2: title = f"{req.category or '热门'}:重生逆袭"

        outline_match = _re.search(r'【全书总纲】\s*\n(.+)', plan_text, _re.DOTALL)
        overall_outline = outline_match.group(1).strip()[:3000] if outline_match else plan_text[:2000]

        chars_match = _re.search(r'【人物系统】\s*\n(.+)', plan_text, _re.DOTALL)
        characters_text = chars_match.group(1).strip()[:2000] if chars_match else ""

        step = "outlines"
        three_outlines = await _call_llm(
            f"基于以下全书规划，为《{title}》前三章各写一份详尽的细纲。"
            f"要求每章包含：核心事件、目标情绪、章首钩子、爽点设计、章尾钩子。\n\n{plan_text[:2500]}",
            temperature=0.8, max_tokens=4000)

        step = "chapters"
        chapters_content, chapter_titles = [], []
        for ch_num in [1, 2, 3]:
            ch_outline = _extract_section(three_outlines, f"第{ch_num}章细纲", 800)
            ch_content = await _call_llm(
                f"你是资深网文作者。写《{title}》第{ch_num}章的完整正文。"
                f"章首钩子，章尾卡关键处。1500-3000字。\n\n规划：{plan_text[:1500]}\n细纲：{ch_outline}",
                temperature=0.9, max_tokens=4000)
            chapters_content.append(ch_content)
            chapter_titles.append(_extract_chapter_title(ch_content) or f"第{ch_num}章")

        # Save to DB
        project = NovelProject(
            id=_uuid.uuid4(), user_id=user.id,
            title=title, genre=req.category or "自动生成", status="writing",
            overall_outline=overall_outline, description=plan_text[:500],
            characters_json=[{"name": c.strip()} for c in characters_text.split('\n') if c.strip()][:20],
            chapter_tree=[], target_words=1_000_000, total_chapters=3, total_words=0,
        )
        db.add(project); await db.flush()

        saved, total_words = [], 0
        for i, (c, name) in enumerate(zip(chapters_content, chapter_titles)):
            summary = await _call_llm(f"用150字总结:\n\n{c[:2500]}", temperature=0.3, max_tokens=300)
            ch = NovelChapter(id=_uuid.uuid4(), project_id=project.id,
                chapter_num=i+1, title=f"第{i+1}章 {name}",
                content=c, summary=summary, word_count=len(c or ""), status="draft")
            db.add(ch); total_words += len(c or "")
            saved.append({"chapter_num":i+1, "title":ch.title, "content_preview":c[:300]+"...", "word_count":len(c or "")})
        project.total_words = total_words
        await db.commit()

        return {"project_id":str(project.id), "title":title, "scan":scan_text,
                "plan":plan_text, "three_outlines":three_outlines, "chapters":saved}
    except Exception as e:
        raise HTTPException(502, f"流水线失败(step={step}): {str(e)[:200]}")


@router.post("/imitate")
async def imitate_novel(
    req: ImitateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """拆文仿写: 输入URL/文本→拆解分析→提取文风→仿写新章→入库"""
    import re as _re
    import httpx as _httpx
    step = "fetch"
    try:
        text = req.text
        if req.url and not text:
            async with _httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(req.url, headers={
                    "User-Agent": "Mozilla/5.0"})
                text = _re.sub(r"<[^>]+>", "", resp.text)
                text = _re.sub(r"\s+", " ", text)[:8000]
        if not text or len(text) < 100:
            raise HTTPException(400, "内容太短，至少100字")

        step = "analyze"
        analysis = await _call_llm(
            f"分析以下小说前{req.chapter_count}章: 文风特点、叙事节奏、爽点规律、人物模板、语言习惯。\n\n{text[:6000]}",
            temperature=0.5, max_tokens=3000)

        step = "write"
        chapter = await _call_llm(
            f"根据以下拆文分析，用对标书文风写全新第一章。题材不变，人设情节全新。\n"
            f"分析:{analysis[:3000]}\n原文文风参考:{text[:2000]}",
            temperature=0.9, max_tokens=4000)

        title = "仿写作品"
        m = _re.search(r"《(.+?)》|^#\s*(.+)", chapter, _re.MULTILINE)
        if m: title = _re.sub(r'AI生成|自动生成', '', (m.group(1) or m.group(2))).strip(' -–,.。')[:40]

        project = NovelProject(id=_uuid.uuid4(), user_id=user.id,
            title=title, genre="仿写", status="writing",
            overall_outline=analysis[:2000], total_chapters=1, total_words=len(chapter or ""))
        db.add(project); await db.flush()
        ch = NovelChapter(id=_uuid.uuid4(), project_id=project.id,
            chapter_num=1, title="仿写第一章", content=chapter,
            summary=analysis[:500], word_count=len(chapter or ""), status="draft")
        db.add(ch); await db.commit()

        return {"project_id":str(project.id), "title":title, "analysis":analysis, "imitation":chapter}
    except HTTPException: raise
    except Exception as e: raise HTTPException(502, f"拆文仿写失败(step={step}): {str(e)[:200]}")


class AgentRequest(BaseModel):
    idea: str = Field(..., min_length=5)
    genre: str = "修真"
    extra: str = ""
    chapters: int = Field(default=10, ge=3, le=50)


@router.post("/agents")
async def multi_agent_pipeline(
    req: AgentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """多 Agent 协作流水线：
    Chief Planner→Lead Writer→Continuity Checker→Quality Editor
    参考: autonovel + AI_NovelGenerator"""
    agents = get_novel_agents(db)
    result = await agents.run(req.idea, req.genre, req.extra, req.chapters)

    # Save to DB
    plan = result["plan"]
    project = NovelProject(
        id=_uuid.uuid4(), user_id=user.id,
        title=plan.title, genre=plan.genre or req.genre, status="writing",
        overall_outline=plan.overall_outline,
        description=plan.synopsis,
        characters_json=plan.characters,
        target_words=1_000_000,
        total_chapters=len(result["chapters"]),
        total_words=sum(c.get("word_count", 0) for c in result["chapters"]),
    )
    db.add(project); await db.flush()

    saved = []
    for c in result["chapters"]:
        ch = NovelChapter(
            id=_uuid.uuid4(), project_id=project.id,
            chapter_num=c["chapter_num"], title=c["title"],
            content=c["content"], summary=c["summary"],
            word_count=c["word_count"], status="draft",
        )
        db.add(ch)
        saved.append({"chapter_num": c["chapter_num"], "title": c["title"],
                       "word_count": c["word_count"], "target_met": c["target_met"],
                       "issues": len(c.get("issues", []))})
    await db.commit()

    return {
        "project_id": str(project.id),
        "title": plan.title,
        "synopsis": plan.synopsis,
        "characters": plan.characters[:10],
        "chapters": saved,
        "stats": {
            "chapters": len(result["chapters"]),
            "issues_found": result["issues_found"],
            "revisions": result["revisions"],
        },
    }


def _extract_section(text: str, header: str, max_len: int = 1000) -> str:
    import re as _re
    pat = _re.compile(rf'#+\s*{_re.escape(header)}\s*\n?(.+?)(?=\n#|\Z)', _re.DOTALL)
    m = pat.search(text)
    return m.group(1).strip()[:max_len] if m else text[:max_len]


def _extract_chapter_title(content: str) -> str:
    import re as _re
    m = _re.search(r"^#\s*第\d+章\s*[：:\s]*(.+)", content or "", _re.MULTILINE)
    if m: return m.group(1).strip()
    for line in (content or "").strip().split("\n"):
        line = line.strip("# ").strip()
        if line and not line.startswith("```"): return line[:40]
    return ""


# ══════════════════════════════════════════
# 剧情控制 + 自动返工闭环
# ══════════════════════════════════════════

class AutoReviseRequest(BaseModel):
    chapter_content: str
    chapter_num: int = 1
    context: dict = {}


class StoryThreadRequest(BaseModel):
    threads: list[dict] = []  # [{name, next_event, status}]
    chapter_content: str
    chapter_num: int


@router.post("/auto-revise")
async def auto_revision_loop(
    req: AutoReviseRequest,
    _user: User = Depends(get_current_user),
):
    """自动返工闭环: 评分→判断(<80)→定向重写→再评分，最多3轮"""
    loop = AutoRevisionLoop()
    result = await loop.run(req.chapter_content, req.chapter_num, req.context or {})
    return {
        "final_content": result["content"],
        "final_score": result["score"],
        "iterations": result["iterations"],
        "issues_found": len(result.get("issues", [])),
    }


@router.post("/story-threads")
async def analyze_story_threads(
    req: StoryThreadRequest,
    _user: User = Depends(get_current_user),
):
    """分析章节中各故事线程推进情况"""
    ctrl = PlotController()
    for t in req.threads:
        ctrl.threads.append(StoryThread(
            id=t.get("id", ""), name=t.get("name", ""),
            status=t.get("status", "active"),
            next_event=t.get("next_event", ""),
            progress=t.get("progress", 0),
        ))
    result = await ctrl.check_story_threads(req.chapter_content)
    pacing = await ctrl.analyze_pacing(req.chapter_content, req.chapter_num)
    return {
        "threads": result,
        "pacing": {
            "action_ratio": pacing.action_ratio,
            "dialogue_ratio": pacing.dialogue_ratio,
            "conflict_intensity": pacing.conflict_intensity,
            "readability": pacing.readability,
        },
    }
