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
