"""共享速率限制器 (P0-2: AI 生成类端点成本控制)

此前全仓库只有 auth.py 的注册/登录有限流，所有真正消耗 DeepSeek Token
的端点(生成/审查/翻译/短篇)完全不设防——任何登录用户可以无限并发触发
付费 AI 调用。limiter 原来定义在 auth.py 模块里，生成类端点要复用就得
反向 import auth.py，所以挪到这个独立模块，auth.py 和各生成端点都从
这里 import。

限流 key 的选择：优先用登录用户身份（JWT里的sub），未登录请求回落到
客户端IP。按用户比按IP更合理——多个用户可能共享同一个出口IP(公司/校园
网络)，纯按IP会误伤；而成本滥用的主体本来就是"某个账号"。
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import decode_token


def user_or_ip_key(request: Request) -> str:
    """优先按登录用户限流，未登录按IP。

    从 httpOnly cookie 里取 access_token 解出用户ID。这里只做"识别是谁"，
    不做鉴权(鉴权仍由各端点的 get_current_user 依赖负责)——即使 token
    过期，能解出 sub 也照样按这个用户计数，解不出就按IP。
    """
    token = request.cookies.get("access_token")
    if token:
        user_id = decode_token(token)
        if user_id:
            return f"user:{user_id}"
    return get_remote_address(request)


# 认证端点用纯IP限流(注册/登录时还没有用户身份可言)
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)

# AI 生成类端点用"用户优先"限流
ai_limiter = Limiter(key_func=user_or_ip_key, headers_enabled=True)
