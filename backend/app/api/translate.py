"""翻译出海 API (Phase 3)
对接 prompts.py 的 novel-translate 引擎，支持6平台格式适配。
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import ai_limiter
from app.api.deps import get_current_user, get_user_chapter
from app.db.database import get_db
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    PLATFORM_TRANSLATE_CONFIGS,
    build_novel_translate_messages,
    parse_novel_translate_response,
)
from app.services.prompt_registry import load_template

router = APIRouter(prefix="/api/v1/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    # content 通常留空，直接翻译该章节在数据库里的正文；
    # 传了就用传入的内容覆盖(例如翻译一段还没保存的草稿)
    content: str | None = None
    target_platform: str = "webnovel"
    glossary: dict[str, str] | None = None


@router.get("/platforms")
async def list_translate_platforms(user: User = Depends(get_current_user)):
    """列出支持的翻译平台及配置"""
    return {
        "platforms": [
            {"key": k, "lang": v["lang"], "style": v["style"]}
            for k, v in PLATFORM_TRANSLATE_CONFIGS.items()
        ]
    }


@router.post("/chapter/{chapter_id}")
@ai_limiter.limit("10/minute")
async def translate_chapter(
    request: Request,
    response: Response,
    chapter_id: str,
    req: TranslateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    翻译章节到目标平台格式。
    调用 novel-translate Prompt 引擎。

    P0-4同类修复: 此前这个接口只把 chapter_id 原样塞进返回结果里，
    从未查询数据库校验这个章节是否存在、是否属于当前用户——任何登录用户
    传任意 chapter_id 都会被处理。现在接入 get_user_chapter 做归属校验
    (与其他章节相关接口的模式保持一致)，并且既然已经正确取到了章节，
    默认直接用它的真实正文做翻译源，而不是继续信任客户端重复传的内容。
    """
    if req.target_platform not in PLATFORM_TRANSLATE_CONFIGS:
        raise HTTPException(
            400,
            f"不支持的平台: {req.target_platform}。"
            f"支持: {list(PLATFORM_TRANSLATE_CONFIGS.keys())}",
        )

    chapter = await get_user_chapter(chapter_id, user, db)
    content = req.content if req.content is not None else (chapter.content or "")
    if not content:
        raise HTTPException(400, "章节内容为空，无法翻译")

    messages = build_novel_translate_messages(
        title=chapter.title or f"Chapter {chapter.chapter_num}",
        content=content,
        target_platform=req.target_platform,
        glossary=req.glossary,
        template=await load_template(db, "novel-translate"),
    )
    try:
        r = await chat_completion(messages, temperature=0.3, max_tokens=16384)
        return {
            "chapter_id": chapter_id,
            "platform": req.target_platform,
            **parse_novel_translate_response(r["content"]),
        }
    except DeepSeekError:
        raise HTTPException(502, "AI 翻译服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")
