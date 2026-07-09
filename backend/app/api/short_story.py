"""短篇生成 API (Phase 3)
对接 prompts.py 的 novel-short-write 引擎。
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.core.ratelimit import ai_limiter
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
@ai_limiter.limit("5/minute")
async def generate_short(request: Request, response: Response, req: ShortStoryRequest, user: User = Depends(get_current_user)):
    """
    根据一句话梗概生成完整短篇（5000-20000字）。
    调用 novel-short-write Prompt 引擎。

    注意：底层 Prompt 引擎（build_novel_short_write_messages）目前只支持
    topic/genre/target_words/style 四个维度，不支持"接着写"（续写已有文本）。
    req.continue_from 字段暂时收下但不会被使用——如果需要真正的短篇续写能力，
    需要先给 build_novel_short_write_messages 增加对应参数，这里不做无依据的假设。
    """
    messages = build_novel_short_write_messages(
        topic=req.premise,
        style=", ".join(req.style_tags) if req.style_tags else "",
        target_words=req.target_words,
    )
    try:
        r = await chat_completion(messages, temperature=0.9, max_tokens=16384)
        return parse_novel_short_write_response(r["content"])
    except DeepSeekError:
        raise HTTPException(502, "AI 写作服务暂时不可用")
    except Exception:
        raise HTTPException(502, "AI 返回格式异常，请重试")
