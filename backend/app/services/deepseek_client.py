"""
DeepSeek API 客户端。所有 7 Prompt 引擎都通过这里调用模型。
支持从环境变量或前端 X-DeepSeek-API-Key header 读取密钥。
"""
from __future__ import annotations

import httpx
from contextvars import ContextVar

from app.core.config import settings

# 请求级上下文：FastAPI middleware 从 X-DeepSeek-API-Key / X-DeepSeek-Model header 写入
_request_api_key: ContextVar[str | None] = ContextVar("deepseek_api_key", default=None)
_request_model: ContextVar[str | None] = ContextVar("deepseek_model", default=None)


def set_request_api_key(key: str | None) -> None:
    _request_api_key.set(key)


def set_request_model(model: str | None) -> None:
    _request_model.set(model)


class DeepSeekError(Exception):
    pass


async def chat_completion(
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    temperature: float = 0.9,
    api_key: str | None = None,
) -> dict:
    """
    调用 DeepSeek /chat/completions。
    api_key 优先级：参数 > 请求上下文(X-DeepSeek-API-Key) > 环境变量
    model 优先级：参数 > 请求上下文(X-DeepSeek-Model) > 环境变量
    """
    key = api_key or _request_api_key.get() or settings.deepseek_api_key
    model = _request_model.get() or settings.deepseek_model
    if not key:
        raise DeepSeekError("未配置 DEEPSEEK_API_KEY，请在设置页面填入或在 .env 中配置")

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens or settings.max_chapter_tokens,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(base_url=settings.deepseek_base_url, timeout=120) as client:
        try:
            resp = await client.post("/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise DeepSeekError(f"DeepSeek 返回错误: {e.response.status_code} {e.response.text[:500]}") from e
        except httpx.RequestError as e:
            raise DeepSeekError(f"DeepSeek 请求失败: {e}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise DeepSeekError(f"DeepSeek 返回格式异常: {str(data)[:500]}") from e

    usage = data.get("usage", {})
    return {"content": content, "usage": usage}
