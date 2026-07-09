"""爆款分析系统 API (Phase 7)
对接 prompts.py 的 novel-analyze 和 novel-scan 引擎。
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_analyze_messages,
    build_novel_scan_messages,
    parse_novel_analyze_response,
    parse_novel_scan_response,
)

router = APIRouter(prefix="/api/v1/hit-analysis", tags=["hit_analysis"])


class AnalyzeRequest(BaseModel):
    title: str
    genre: str | None = None
    first_chapter: str = ""
    platform: str = "起点"


class BatchScanRequest(BaseModel):
    platforms: list[str] | None = None


@router.post("/analyze")
async def analyze_hit_potential(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """评估作品爆款潜力 — 调用 novel-analyze 引擎"""
    from app.services.prompt_registry import load_template
    tpl = await load_template(db, "novel-analyze")
    messages = build_novel_analyze_messages(
        title=req.title,
        chapters_text=req.first_chapter,
        template=tpl,
    )
    try:
        r = await chat_completion(messages, temperature=0.3)
        return parse_novel_analyze_response(r["content"])
    except DeepSeekError:
        raise HTTPException(502, "AI 分析服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")


@router.post("/batch-scan")
async def batch_scan_platforms(
    req: BatchScanRequest = BatchScanRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量扫榜（基于AI分析，非实时爬虫）— 调用 novel-scan 引擎"""
    target_platforms = req.platforms or ["起点", "番茄", "晋江", "纵横"]

    messages = build_novel_scan_messages(
        platforms=target_platforms,
        raw_data="请基于你的知识库，分析上述平台当前热门趋势。",
        template=await load_template(db, "novel-scan"),
    )
    try:
        r = await chat_completion(messages, temperature=0.5, max_tokens=3000)
        books = parse_novel_scan_response(r["content"])
        return {
            "platforms": target_platforms,
            "books": books,
            "total": len(books),
        }
    except DeepSeekError:
        raise HTTPException(502, "AI 扫榜服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")


# ═══ 质量系统基准数据 — Phase 7 反哺 Phase 3 ═══

_QUALITY_BENCHMARKS = {
    "起点": {
        "hype_density_threshold": 1.2,    # 爽点/千字
        "hook_min_score": 7,
        "dialogue_ratio_ideal": 0.35,
        "description": "起点男频，竞争激烈，对爽点密度和钩子要求最高",
    },
    "番茄": {
        "hype_density_threshold": 1.0,
        "hook_min_score": 8,               # 免费阅读，钩子更关键
        "dialogue_ratio_ideal": 0.40,
        "description": "番茄小说免费阅读模式，前3章钩子决定留存",
    },
    "晋江": {
        "hype_density_threshold": 0.8,
        "hook_min_score": 6,
        "dialogue_ratio_ideal": 0.45,
        "description": "晋江女频，对话推动剧情，人物关系重于爽点密度",
    },
}


@router.get("/benchmarks")
async def quality_benchmarks(
    platform: str = "起点",
    user: User = Depends(get_current_user),
):
    """获取质量系统评分基准（供7维质量系统参考）"""
    bm = _QUALITY_BENCHMARKS.get(platform, _QUALITY_BENCHMARKS["起点"])
    return {"platform": platform, "benchmarks": bm}
