"""
DeepSeek API 客户端。所有 7 Prompt 引擎都通过这里调用模型。
支持从用户级服务端加密配置或环境变量读取密钥。
"""
from __future__ import annotations

import asyncio
import logging

import httpx
from contextvars import ContextVar

from app.core.config import settings

logger = logging.getLogger("novelcraft.deepseek")

# 请求级上下文：FastAPI middleware 从用户级服务端加密配置写入
_request_api_key: ContextVar[str | None] = ContextVar("deepseek_api_key", default=None)
_request_model: ContextVar[str | None] = ContextVar("deepseek_model", default=None)

# P1-1: HTTP层重试策略。此前这里零重试——任何一次网络抖动/DeepSeek侧临时5xx
# 都会让整个生成请求直接失败。Celery任务层虽然有self.retry(60秒后重试)，
# 但那是"整个任务重来一遍"的粗粒度重试；HTTP层的细粒度退避(1s/2s)能把
# 大部分瞬时故障消化在一次任务内部，不浪费已经组装好的上下文。
# 429/5xx/网络错误值得重试；其他4xx(400参数错/401密钥错/402欠费)是请求
# 本身的问题，重试只会得到同样的失败，直接抛出。
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3          # 1次原始请求 + 最多2次重试
_BACKOFF_BASE_SECONDS = 1.0  # 重试间隔: 1s, 2s (指数退避)
_RETRY_AFTER_CAP_SECONDS = 30.0  # 429的Retry-After头最多等这么久，防止被恶意/异常大值卡死


def set_request_api_key(key: str | None) -> None:
    _request_api_key.set(key)


def set_request_model(model: str | None) -> None:
    _request_model.set(model)


class DeepSeekError(Exception):
    pass


def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
    """计算第 attempt 次重试前的等待秒数。429且带Retry-After头时尊重服务端要求。"""
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), _RETRY_AFTER_CAP_SECONDS)
            except ValueError:
                pass  # 非数字格式(HTTP-date)，回落到指数退避
    return _BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))


async def chat_completion(
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    temperature: float = 0.9,
    api_key: str | None = None,
) -> dict:
    """
    调用 DeepSeek /chat/completions，对瞬时故障(429/5xx/网络错误)自动指数退避重试。
    api_key 优先级：参数 > 请求上下文(用户级加密配置) > 环境变量
    model 优先级：请求上下文(用户级配置) > 环境变量
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
        resp: httpx.Response | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                resp = await client.post("/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                break  # 成功
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in _RETRYABLE_STATUS and attempt < _MAX_ATTEMPTS:
                    delay = _retry_delay(attempt, e.response)
                    logger.warning(
                        "DeepSeek 返回 %s，%.1fs 后重试 (第%d/%d次尝试)",
                        status, delay, attempt, _MAX_ATTEMPTS,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise DeepSeekError(
                    f"DeepSeek 返回错误: {status} {e.response.text[:500]}"
                ) from e
            except httpx.RequestError as e:
                # 网络层故障(超时/连接失败/DNS等)——瞬时故障的典型来源，值得重试
                if attempt < _MAX_ATTEMPTS:
                    delay = _retry_delay(attempt, None)
                    logger.warning(
                        "DeepSeek 请求失败 (%s: %s)，%.1fs 后重试 (第%d/%d次尝试)",
                        type(e).__name__, e, delay, attempt, _MAX_ATTEMPTS,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise DeepSeekError(f"DeepSeek 请求失败: {e}") from e

    if resp is None:  # 防御性检查：循环要么成功break要么raise，逻辑上不可达
        raise DeepSeekError("DeepSeek 请求未能完成")

    data = resp.json()
    try:
        choices = data.get("choices", [])
        if not choices:
            raise DeepSeekError("DeepSeek 返回空的 choices 数组")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise DeepSeekError("DeepSeek 返回空的 content")
    except (KeyError, IndexError, TypeError) as e:
        raise DeepSeekError(f"DeepSeek 返回格式异常: {str(data)[:500]}") from e

    usage = data.get("usage", {})
    return {"content": content, "usage": usage}
