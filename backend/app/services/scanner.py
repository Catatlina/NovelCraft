"""
真实扫榜爬虫 — httpx + BeautifulSoup 爬4平台榜单
不再靠LLM凭空编榜单数据
"""
import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

PLATFORMS = {
    "qidian": {
        "name": "起点中文网",
        "url": "https://www.qidian.com/rank/yuepiao/",
        "selector": ".book-img-text li",
        "title_sel": "h2 a, .book-mid-info h2 a, h4 a",
        "author_sel": ".author a, .author .name",
        "desc_sel": ".intro",
    },
    "fanqie": {
        "name": "番茄小说",
        "url": "https://fanqienovel.com/rank/hot",
        "selector": ".book-list .book",
        "title_sel": ".book-name",
        "author_sel": ".author",
        "desc_sel": ".intro, .desc",
    },
    "zongheng": {
        "name": "纵横中文网",
        "url": "https://www.zongheng.com/rank.html",
        "selector": ".rank-list li, .rank-page-box li",
        "title_sel": ".bookname a, .tit a",
        "author_sel": ".author a, .book-author a",
        "desc_sel": ".intro, .desc",
    },
}


@dataclass
class TrendingBook:
    title: str
    author: str
    desc: str = ""
    platform: str = ""
    rank: int = 0


async def fetch_page(url: str) -> str:
    """获取页面HTML"""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=HEADERS) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_books(html: str, platform: str) -> list[TrendingBook]:
    """解析榜单页面"""
    cfg = PLATFORMS.get(platform, {})
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(cfg.get("selector", "li"))
    books = []

    for i, item in enumerate(items[:20]):
        title_el = item.select_one(cfg.get("title_sel", "a"))
        author_el = item.select_one(cfg.get("author_sel", ".author"))
        desc_el = item.select_one(cfg.get("desc_sel", ".intro"))

        title = title_el.get_text(strip=True) if title_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        desc = desc_el.get_text(strip=True)[:120] if desc_el else ""

        if title and len(title) > 1:
            books.append(TrendingBook(
                title=title, author=author, desc=desc,
                platform=platform, rank=i + 1,
            ))

    return books


async def scan_platforms(platforms: list[str] | None = None) -> dict:
    """扫描多个平台榜单"""
    if platforms is None:
        platforms = ["qidian", "fanqie", "zongheng"]

    results = {}
    for platform in platforms:
        cfg = PLATFORMS.get(platform)
        if not cfg:
            continue
        try:
            html = await fetch_page(cfg["url"])
            books = parse_books(html, platform)
            results[platform] = {
                "name": cfg["name"],
                "count": len(books),
                "books": [{"title": b.title, "author": b.author, "desc": b.desc, "rank": b.rank} for b in books],
            }
        except Exception as e:
            results[platform] = {"name": cfg.get("name", platform), "error": str(e), "books": []}

    return results
