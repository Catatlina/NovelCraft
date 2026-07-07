"""翻译出海 API (Phase 3)
对接 prompts.py 的 novel-translate 引擎，支持6平台格式适配。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    PLATFORM_TRANSLATE_CONFIGS,
    build_novel_translate_messages,
    parse_novel_translate_response,
)

router = APIRouter(prefix="/api/v1/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    content: str
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
async def translate_chapter(
    chapter_id: str,
    req: TranslateRequest,
    user: User = Depends(get_current_user),
):
    """
    翻译章节到目标平台格式。
    调用 novel-translate Prompt 引擎。
    """
    if req.target_platform not in PLATFORM_TRANSLATE_CONFIGS:
        raise HTTPException(
            400,
            f"不支持的平台: {req.target_platform}。"
            f"支持: {list(PLATFORM_TRANSLATE_CONFIGS.keys())}",
        )

    messages = build_novel_translate_messages(
        content=req.content,
        target_platform=req.target_platform,
        glossary=req.glossary,
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
