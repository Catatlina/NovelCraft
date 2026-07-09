"""限流端点契约测试。

slowapi 的 @limiter.limit 装饰器有两个隐性要求，违反时不会在导入期报错，
而是在【运行时】才炸：
  1. 端点函数必须有名为 request 的参数(类型 Request)——否则限流根本不生效
  2. 当 limiter 开了 headers_enabled=True，端点必须有名为 response 的参数
     (类型 Response)——否则【成功】响应在注入限流头时抛异常变成500
第2点尤其阴险：只有成功路径才触发，测"触发429"的用例反而发现不了。
这个测试用签名内省把这两个要求固化下来，改动限流端点时能立刻发现遗漏，
不需要起数据库做完整集成测试。
"""
import inspect
import os

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")

from app.api import generation, pipeline, quality, short_story, translate  # noqa: E402


# (模块, 函数名) —— 所有加了 @ai_limiter.limit 的 AI 生成类端点
RATE_LIMITED_ENDPOINTS = [
    (generation, "generate_chapter"),
    (quality, "review_chapter_7d"),
    (quality, "rewrite_segment"),
    (translate, "translate_chapter"),
    (short_story, "generate_short"),
    (pipeline, "batch_generate"),
]


def _param_names(func) -> list[str]:
    # 装饰器可能包了一层，用 unwrap 拿到原始函数签名
    return list(inspect.signature(inspect.unwrap(func)).parameters.keys())


def test_rate_limited_endpoints_have_request_param():
    """每个限流端点必须有 request 参数，否则 slowapi 限流不生效。"""
    for module, name in RATE_LIMITED_ENDPOINTS:
        func = getattr(module, name)
        params = _param_names(func)
        assert "request" in params, f"{name} 缺少 request 参数，限流不会生效"


def test_rate_limited_endpoints_have_response_param():
    """每个限流端点必须有 response 参数，否则成功响应注入限流头时会 500。"""
    for module, name in RATE_LIMITED_ENDPOINTS:
        func = getattr(module, name)
        params = _param_names(func)
        assert "response" in params, (
            f"{name} 缺少 response 参数，headers_enabled=True 时成功请求会 500"
        )
