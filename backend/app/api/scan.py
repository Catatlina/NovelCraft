"""扫榜分析 API — 13平台实时/缓存扫榜
对接 prompts.py 的 novel-scan 引擎进行结构化解析。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_scan_messages,
    parse_novel_scan_response,
)
from app.services.scanner import get_platform_list, scan_all, scan_all_mock

router = APIRouter(prefix="/api/v1/scan", tags=["scan"])


class ScanRequest(BaseModel):
    platforms: list[str] | None = None  # None = all 14 platforms


class ScanRawDataRequest(BaseModel):
    """支持原始榜单文本的扫描请求 — 对接 novel-scan Prompt 引擎"""
    platforms: list[str]
    raw_data: str = ""


@router.get("/platforms")
async def list_platforms(user: User = Depends(get_current_user)):
    """列出支持的扫榜平台"""
    platforms = get_platform_list()
    return {"platforms": platforms, "total": len(platforms)}


@router.post("/run")
async def run_scan(
    req: ScanRequest = ScanRequest(),
    user: User = Depends(get_current_user),
):
    """执行扫榜 — 优先真实爬取，无结果时回退到 mock 数据"""
    results = await scan_all(req.platforms)

    total_books = sum(len(r.books) for r in results)
    errors = [{"platform": r.platform, "error": r.error} for r in results if r.error]

    # 如果真实爬取全部失败，回退到 mock 数据
    if total_books == 0:
        results = await scan_all_mock(req.platforms)
        total_books = sum(len(r.books) for r in results)
        errors = []

    return {
        "total_platforms": len(results),
        "total_books": total_books,
        "errors": errors,
        "results": [
            {
                "platform": r.platform,
                "region": r.region,
                "count": len(r.books),
                "books": r.books[:10],
                "error": r.error,
            }
            for r in results
        ],
    }


@router.get("/mock")
async def scan_mock(
    platforms: str | None = None,
    user: User = Depends(get_current_user),
):
    """获取模拟扫榜数据（演示模式，不爬取真实平台）"""
    platform_list = platforms.split(",") if platforms else None
    results = await scan_all_mock(platform_list)
    return {
        "total_platforms": len(results),
        "total_books": sum(len(r.books) for r in results),
        "results": [
            {"platform": r.platform, "region": r.region, "count": len(r.books), "books": r.books[:10]}
            for r in results
        ],
    }


@router.post("/analyze")
async def analyze_scan_data(
    req: ScanRawDataRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    用 LLM 解析榜单原始数据，提取结构化书籍信息。
    对接 novel-scan Prompt 引擎。
    """
    messages = build_novel_scan_messages(
        platforms=req.platforms,
        raw_data=req.raw_data,
    )
    try:
        r = await chat_completion(messages, temperature=0.3)
        books = parse_novel_scan_response(r["content"])
        return {"books": books, "total": len(books)}
    except DeepSeekError:
        raise HTTPException(502, "AI 扫榜服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")
