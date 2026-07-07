"""短篇生成 API (Phase 3)
对接 prompts.py 的 novel-short-write 引擎。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import User
from app.services.deepseek_client import DeepSeekError, chat_completion
from app.services.prompts import (
    build_novel_short_write_messages,
    parse_novel_short_write_response,
)

router = APIRouter(prefix="/api/v1/generate", tags=["short_story"])


class ShortStoryRequest(BaseModel):
    premise: str
    style_tags: list[str] | None = None
    target_words: int = 10000
    continue_from: str = ""


@router.post("/short")
async def generate_short(req: ShortStoryRequest, user: User = Depends(get_current_user)):
    """
    根据一句话梗概生成完整短篇（5000-20000字）。
    调用 novel-short-write Prompt 引擎。
    """
    messages = build_novel_short_write_messages(
        premise=req.premise,
        style_tags=req.style_tags,
        target_words=req.target_words,
        continue_from=req.continue_from,
    )
    try:
        r = await chat_completion(messages, temperature=0.9, max_tokens=16384)
        return parse_novel_short_write_response(r["content"])
    except DeepSeekError:
        raise HTTPException(502, "AI 写作服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")
