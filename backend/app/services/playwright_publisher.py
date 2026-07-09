"""
Playwright 自动发布 — 支持 6 个海外平台。
Phase 6.3: login → navigate → fill_form → submit → verify_online

所有发布器继承 BasePublisher，每步截图 + 记录日志，失败重试最多3次。
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 截图保存目录 — 懒初始化，避免模块导入时因权限问题导致 Celery worker 无法启动
_SCREENSHOT_DIR: Path | None = None

def _get_screenshot_dir() -> Path:
    global _SCREENSHOT_DIR
    if _SCREENSHOT_DIR is None:
        _SCREENSHOT_DIR = Path(os.environ.get("PUBLISH_SCREENSHOT_DIR", "/tmp/novelcraft_screenshots"))
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return _SCREENSHOT_DIR


class BasePublisher(ABC):
    """发布器基类 — 定义发布流程骨架。"""

    platform_name: str = "unknown"

    async def login(self, page, credentials: dict) -> bool:
        """登录目标平台（子类必须实现）。"""
        raise NotImplementedError

    async def navigate_to_publish(self, page) -> bool:
        """导航到发布页面（子类必须实现）。"""
        raise NotImplementedError

    async def fill_form(self, page, chapter_data: dict) -> bool:
        """填充发布表单（子类必须实现）。"""
        raise NotImplementedError

    async def submit(self, page) -> bool:
        """提交发布（子类必须实现）。"""
        raise NotImplementedError

    async def verify_online(self, page) -> bool:
        """验证章节已上线（子类必须实现）。"""
        raise NotImplementedError

    async def screenshot(self, page, step_name: str) -> str:
        """截取当前页面并保存为 PNG，返回文件路径。"""
        filename = f"{self.platform_name}_{step_name}_{uuid.uuid4().hex[:8]}.png"
        filepath = _get_screenshot_dir() / filename
        await page.screenshot(path=str(filepath), full_page=True)
        return str(filepath)


# ================================================================
# 各平台发布器实现
# ================================================================


class WebnovelPublisher(BasePublisher):
    """Webnovel (起点国际) 发布器。"""
    platform_name = "webnovel"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://www.webnovel.com/signin", wait_until="networkidle")
        # 使用 Cookie 注入方式登录
        if "cookies" in credentials:
            await page.context.add_cookies(credentials["cookies"])
            await page.goto("https://www.webnovel.com", wait_until="networkidle")
            return True
        # OAuth 方式 — 填充账号密码
        await page.fill('input[name="email"]', credentials.get("email", ""))
        await page.fill('input[name="password"]', credentials.get("password", ""))
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        return "signin" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://www.webnovel.com/author/works/new", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "Untitled")
        content = chapter_data.get("content", "")
        await page.fill('input[name="chapterTitle"]', title)
        # Webnovel 使用富文本编辑器，切换到源码模式填入
        await page.click('button[data-mode="source"]')
        await page.fill("textarea.editor-source", content)
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('button:has-text("Publish")')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "success" in page.url or "published" in (await page.content()).lower()


class AmazonKDPPublisher(BasePublisher):
    """Amazon KDP 发布器。"""
    platform_name = "amazon_kdp"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://kdp.amazon.com/signin", wait_until="networkidle")
        await page.fill('input[name="email"]', credentials.get("email", ""))
        await page.fill('input[name="password"]', credentials.get("password", ""))
        await page.click('input[type="submit"]')
        await page.wait_for_timeout(5000)
        return "signin" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://kdp.amazon.com/bookshelf", wait_until="networkidle")
        await page.click('a:has-text("Create")')
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "")
        content = chapter_data.get("content", "")
        await page.fill('input[name="title"]', title)
        await page.fill("textarea.description", content[:4000])  # KDP 描述有长度限制
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('button:has-text("Save and Continue")')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "bookshelf" in page.url


class NarouPublisher(BasePublisher):
    """小説家になろう (Narou) 发布器。"""
    platform_name = "narou"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://syosetu.com/login/", wait_until="networkidle")
        await page.fill('input[name="id"]', credentials.get("user_id", ""))
        await page.fill('input[name="pass"]', credentials.get("password", ""))
        await page.click('input[type="submit"]')
        await page.wait_for_timeout(3000)
        return "login" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://syosetu.com/usernovelmanage/novelep/top/", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "")
        content = chapter_data.get("content", "")
        await page.fill('input[name="subtitle"]', title)
        await page.fill("textarea#novel", content)
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('input[value="投稿する"]')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "confirm" in page.url or "complete" in page.url


class MunpiaPublisher(BasePublisher):
    """Munpia (문피아) 发布器。"""
    platform_name = "munpia"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://www.munpia.com/login", wait_until="networkidle")
        await page.fill('input[name="id"]', credentials.get("user_id", ""))
        await page.fill('input[name="pw"]', credentials.get("password", ""))
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        return "login" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://www.munpia.com/author/write", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "")
        content = chapter_data.get("content", "")
        await page.fill('input[name="title"]', title)
        await page.fill("textarea#content", content)
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('button:has-text("등록")')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "view" in page.url or "complete" in page.url


class DreamePublisher(BasePublisher):
    """Dreame 发布器。"""
    platform_name = "dreame"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://www.dreame.com/login", wait_until="networkidle")
        if "cookies" in credentials:
            await page.context.add_cookies(credentials["cookies"])
            await page.goto("https://www.dreame.com", wait_until="networkidle")
            return True
        await page.fill('input[name="email"]', credentials.get("email", ""))
        await page.fill('input[name="password"]', credentials.get("password", ""))
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        return "login" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://www.dreame.com/author/write", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "")
        content = chapter_data.get("content", "")
        await page.fill('input[name="chapter_title"]', title)
        await page.fill("div.editor textarea", content)
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('button:has-text("Publish")')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "published" in page.url or "chapter" in page.url


class RoyalRoadPublisher(BasePublisher):
    """Royal Road 发布器。"""
    platform_name = "royalroad"

    async def login(self, page, credentials: dict) -> bool:
        await page.goto("https://www.royalroad.com/account/login", wait_until="networkidle")
        await page.fill('input[name="email"]', credentials.get("email", ""))
        await page.fill('input[name="password"]', credentials.get("password", ""))
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        return "login" not in page.url

    async def navigate_to_publish(self, page) -> bool:
        await page.goto("https://www.royalroad.com/fiction/create", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        return True

    async def fill_form(self, page, chapter_data: dict) -> bool:
        title = chapter_data.get("title", "")
        content = chapter_data.get("content", "")
        # Royal Road 使用 CKEditor — 先切换源码模式
        await page.click('a.cke_button__source')
        await page.fill("textarea.cke_source", content)
        await page.fill('input[name="chapter_title"]', title)
        await page.wait_for_timeout(500)
        return True

    async def submit(self, page) -> bool:
        await page.click('button:has-text("Publish Chapter")')
        await page.wait_for_timeout(3000)
        return True

    async def verify_online(self, page) -> bool:
        await page.wait_for_timeout(2000)
        return "fiction" in page.url and "chapter" in page.url.lower()


# ================================================================
# 平台注册表
# ================================================================

PLATFORM_SCRIPTS: dict[str, type[BasePublisher]] = {
    "webnovel": WebnovelPublisher,
    "amazon_kdp": AmazonKDPPublisher,
    "narou": NarouPublisher,
    "munpia": MunpiaPublisher,
    "dreame": DreamePublisher,
    "royalroad": RoyalRoadPublisher,
}

MAX_RETRIES = 3


async def publish_chapter(
    platform: str,
    credentials: dict,
    chapter_data: dict,
    headless: bool = True,
) -> dict:
    """
    发布单个章节到目标平台。

    Args:
        platform: 目标平台标识（webnovel / amazon_kdp / narou / munpia / dreame / royalroad）
        credentials: 平台登录凭证（字典）
        chapter_data: 章节数据 {title, content, ...}
        headless: 是否使用无头浏览器模式（服务器模式默认 True）

    Returns:
        {
            "success": bool,
            "steps": [{"step": str, "status": str, "message": str, "screenshot": str|None, "timestamp": str}, ...],
            "screenshots": [str, ...],
            "published_url": str,
            "error": str|None,
        }
    """
    publisher_cls = PLATFORM_SCRIPTS.get(platform)
    if publisher_cls is None:
        return {
            "success": False,
            "steps": [],
            "screenshots": [],
            "published_url": "",
            "error": f"不支持的目标平台: {platform}。支持: {', '.join(PLATFORM_SCRIPTS)}",
        }

    publisher = publisher_cls()
    steps: list[dict[str, Any]] = []
    screenshot_paths: list[str] = []

    # 尝试导入 Playwright；若未安装则报错
    try:
        from playwright.async_api import async_playwright  # type: ignore[import-untyped]
    except ImportError:
        return {
            "success": False,
            "steps": [],
            "screenshots": [],
            "published_url": "",
            "error": "playwright 未安装。请运行: pip install playwright && playwright install chromium",
        }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        # 流程编排
        flow = [
            ("login", lambda: publisher.login(page, credentials)),
            ("navigate_to_publish", lambda: publisher.navigate_to_publish(page)),
            ("fill_form", lambda: publisher.fill_form(page, chapter_data)),
            ("submit", lambda: publisher.submit(page)),
            ("verify_online", lambda: publisher.verify_online(page)),
        ]

        final_success = True
        for step_name, step_fn in flow:
            success = False
            last_error = ""
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    success = await step_fn()
                    if success:
                        break
                    last_error = f"步骤返回 False（第 {attempt} 次尝试）"
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2)
            # 每步截图
            ss_path = None
            try:
                ss_path = await publisher.screenshot(page, step_name)
                screenshot_paths.append(ss_path)
            except Exception:
                pass

            step_record = {
                "step": step_name,
                "status": "success" if success else "failed",
                "message": last_error if not success else "",
                "screenshot": ss_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            steps.append(step_record)

            if not success and step_name != "verify_online":
                # login / navigate / fill / submit 失败则终止
                final_success = False
                break

        published_url = page.url if final_success else ""
        await browser.close()

    return {
        "success": final_success,
        "steps": steps,
        "screenshots": screenshot_paths,
        "published_url": published_url,
        "error": None if final_success else "发布流程未完成",
    }


async def publish_to_platform(
    platform: str,
    account_credentials: dict,
    chapter: dict,
    headless: bool = True,
) -> dict:
    """
    发布单个章节到目标平台（供 publish_executions 后台任务调用）。

    Args:
        platform: 目标平台标识
        account_credentials: 平台登录凭证
        chapter: 章节数据 {id, chapter_num, title, content, summary, tags}
        headless: 无头模式

    Returns:
        {status, screenshots, logs, url}
    """
    result = await publish_chapter(
        platform=platform,
        credentials=account_credentials,
        chapter_data={
            "title": chapter.get("title", ""),
            "content": chapter.get("content", ""),
            "chapter_num": chapter.get("chapter_num", 0),
        },
        headless=headless,
    )
    return {
        "status": "success" if result["success"] else "failed",
        "screenshots": result.get("screenshots", []),
        "logs": "\n".join(
            f"[{s['step']}] {s['status']}: {s.get('message', '')}"
            for s in result.get("steps", [])
        ),
        "url": result.get("published_url", ""),
    }
