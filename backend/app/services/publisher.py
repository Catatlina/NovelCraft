"""Playwright 自动发布脚本 (Phase 6)

使用方法 (部署时):
    python -m app.services.publisher publish <chapter_id> <platform>

支持的平台和自动化策略:
- Webnovel: 登录 → 进入作者后台 → 创建新章节 → 粘贴内容 → 发布
- Royal Road: 登录 → Author Dashboard → New Chapter → 粘贴 → Publish
- Wattpad: 登录 → Write → New Part → 粘贴 → Publish

前置条件:
    pip install playwright && playwright install chromium
    在 .env 中配置各平台账号密码
"""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import NovelChapter, PublishRecord

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


PLATFORM_CONFIGS = {
    "webnovel": {
        "name": "Webnovel",
        "login_url": "https://www.webnovel.com",
        "dashboard_url": "https://www.webnovel.com/author/dashboard",
        "create_url": "https://www.webnovel.com/author/create",
        "selectors": {
            "login_btn": "a[href*='login'], button:has-text('Log In')",
            "email_input": "input[type='email'], input[name='email']",
            "password_input": "input[type='password']",
            "submit_btn": "button[type='submit'], button:has-text('Log In')",
            "new_chapter_btn": "a:has-text('New'), button:has-text('Create')",
            "title_input": "input[name='title'], input[placeholder*='title']",
            "content_editor": "div[contenteditable], textarea[name='content']",
            "publish_btn": "button:has-text('Publish'), button:has-text('Submit')",
        },
    },
    "royalroad": {
        "name": "Royal Road",
        "login_url": "https://www.royalroad.com/account/login",
        "dashboard_url": "https://www.royalroad.com/author/dashboard",
        "create_url": "https://www.royalroad.com/fiction/add",
        "selectors": {
            "login_btn": "a[href*='login']",
            "email_input": "input[name='email']",
            "password_input": "input[name='password']",
            "submit_btn": "button[type='submit']",
            "new_chapter_btn": "a:has-text('New Chapter')",
            "title_input": "input[name='title']",
            "content_editor": "textarea[name='body'], div[contenteditable]",
            "publish_btn": "button:has-text('Publish')",
        },
    },
    "wattpad": {
        "name": "Wattpad",
        "login_url": "https://www.wattpad.com/login",
        "dashboard_url": "https://www.wattpad.com/myworks",
        "create_url": "https://www.wattpad.com/write",
        "selectors": {
            "login_btn": "a[href*='login']",
            "email_input": "input[name='username'], input[type='email']",
            "password_input": "input[name='password']",
            "submit_btn": "button[type='submit']",
            "new_chapter_btn": "a:has-text('New Part'), button:has-text('Write')",
            "title_input": "input[placeholder*='title'], input[name='title']",
            "content_editor": "div[contenteditable], div[role='textbox']",
            "publish_btn": "button:has-text('Publish'), button:has-text('Save')",
        },
    },
}


async def publish_chapter_to_platform(
    chapter_id: str, platform: str, email: str = "", password: str = ""
) -> dict:
    """使用 Playwright 自动登录并发布章节到指定平台"""
    if not HAS_PLAYWRIGHT:
        return {"status": "skipped", "reason": "Playwright 未安装。部署时运行: pip install playwright && playwright install chromium"}

    if platform not in PLATFORM_CONFIGS:
        return {"status": "error", "reason": f"不支持的平台: {platform}"}

    async with AsyncSessionLocal() as db:
        chapter = await db.get(NovelChapter, chapter_id)
        if not chapter:
            return {"status": "error", "reason": "章节不存在"}
        title = chapter.title or f"Chapter {chapter.chapter_num}"
        content = chapter.content or ""

    cfg = PLATFORM_CONFIGS[platform]
    env_prefix = platform.upper().replace("-", "_")
    email = email or os.getenv(f"{env_prefix}_EMAIL", "")
    password = password or os.getenv(f"{env_prefix}_PASSWORD", "")

    if not email or not password:
        return {"status": "error", "reason": f"未配置 {platform} 账号密码"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(cfg["login_url"], wait_until="networkidle")
            await page.fill(cfg["selectors"]["email_input"], email)
            await page.fill(cfg["selectors"]["password_input"], password)
            await page.click(cfg["selectors"]["submit_btn"])
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            await page.goto(cfg["create_url"], wait_until="networkidle")
            await asyncio.sleep(1)
            await page.fill(cfg["selectors"]["title_input"], title)
            await page.fill(cfg["selectors"]["content_editor"], content)
            await page.click(cfg["selectors"]["publish_btn"])
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            published_url = page.url

            async with AsyncSessionLocal() as db:
                rec = await db.execute(
                    select(PublishRecord).where(
                        PublishRecord.chapter_id == chapter_id,
                        PublishRecord.platform == platform,
                    ).order_by(PublishRecord.published_at.desc()).limit(1)
                )
                rec_row = rec.scalar_one_or_none()
                if rec_row:
                    rec_row.status = "published"
                    rec_row.published_url = published_url
                    rec_row.published_at = datetime.now(timezone.utc)
                    await db.commit()

            return {"status": "published", "platform": platform, "url": published_url}
        except Exception as e:
            return {"status": "failed", "reason": str(e)[:500]}
        finally:
            await browser.close()
