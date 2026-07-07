"""工具 API — 拆文/去AI味/审查 (Phase 2)
对接 prompts.py 引擎，不再内嵌 prompt 字符串。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_analyze_messages,
    build_novel_deslop_messages,
    parse_novel_analyze_response,
    parse_novel_deslop_response,
)

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class AnalyzeRequest(BaseModel):
    title: str
    chapters: str
    depth: str = "deep"


class DeslopRequest(BaseModel):
    content: str
    mode: str = "deslop"


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, user: User = Depends(get_current_user)):
    """拆文分析 — 调用 novel-analyze 引擎"""
    messages = build_novel_analyze_messages(
        title=req.title,
        chapters_text=req.chapters,
    )
    try:
        r = await chat_completion(messages, temperature=0.3)
        return parse_novel_analyze_response(r["content"])
    except DeepSeekError:
        raise HTTPException(502, "AI 分析服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")


@router.post("/deslop")
async def deslop(req: DeslopRequest, user: User = Depends(get_current_user)):
    """去AI味/润色 — 调用 novel-deslop 引擎"""
    messages = build_novel_deslop_messages(
        content=req.content,
        mode=req.mode,
    )
    try:
        r = await chat_completion(messages, temperature=0.7)
        return parse_novel_deslop_response(r["content"])
    except DeepSeekError:
        raise HTTPException(502, "AI 处理服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")


# ═══ 4-2: 自动书名生成 ═══

class AutoTitleRequest(BaseModel):
    genre: str
    platform: str = "起点"
    count: int = 5


@router.post("/auto/generate-title")
async def auto_generate_title(req: AutoTitleRequest, user: User = Depends(get_current_user)):
    """自动书名生成 — 根据题材+平台生成候选书名"""
    prompt = f"""你是网文书名专家。为以下信息生成{req.count}个爆款书名：
题材：{req.genre}
平台：{req.platform}

要求：
1. 4-7字最优
2. 命中高搜索量关键词（如：重生/系统/开局/修仙/反派）
3. 优先使用爆款句式（XX之XX、从XX开始、我XX等）
4. 独特易记易搜索

输出 JSON 数组：["书名1", "书名2", ...]"""
    try:
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.8)
        import json
        raw = r["content"].strip()
        if raw.startswith("```"): raw = raw.strip("`").removeprefix("json").strip()
        titles = json.loads(raw) if raw.startswith("[") else [raw]
        return {"genre": req.genre, "platform": req.platform, "titles": titles}
    except DeepSeekError:
        raise HTTPException(502, "AI 服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")


# ═══ 4-6: 灵感一键生成 ═══

class AutoInspirationRequest(BaseModel):
    idea: str
    genre: str = "玄幻"
    platform: str = "起点"


@router.post("/auto/inspiration-to-chapter")
async def auto_inspiration_to_chapter(req: AutoInspirationRequest, user: User = Depends(get_current_user)):
    """灵感一键生成 — 一句话 idea → 书名+大纲+第一章"""
    prompt = f"""你是网文创作专家。根据以下灵感，生成完整的创作方案：

灵感：{req.idea}
题材：{req.genre}
平台：{req.platform}

请输出 JSON：
{{
  "title": "生成的爆款书名（4-7字）",
  "synopsis": "100字内简介",
  "outline": "全书大纲（含5-8卷结构，每卷核心冲突）",
  "golden_three_outline": "黄金三章细纲（第1章钩子+第2章期待感+第3章爽点设计）",
  "first_chapter": "第1章正文（2000-3000字）"
}}"""
    try:
        r = await chat_completion([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=4000)
        import json
        raw = r["content"].strip()
        if raw.startswith("```"): raw = raw.strip("`").removeprefix("json").strip()
        return json.loads(raw)
    except DeepSeekError:
        raise HTTPException(502, "AI 服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")
