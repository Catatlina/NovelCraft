"""13平台扫榜数据采集器 (Phase 6 — 自研实现)

策略：httpx + BeautifulSoup/lxml 爬取各平台热榜，使用 CSS 选择器精确定位书名元素。
不依赖 AI Workbench 来源池，独立实现。
"""
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup

PLATFORM_SOURCES = {
    "起点月票榜": {
        "url": "https://www.qidian.com/rank/yuepiao/",
        "selectors": ["div.book-mid-info h2 a", "h2 a[data-bid]"],
        "region": "国内",
    },
    "起点畅销榜": {
        "url": "https://www.qidian.com/rank/hotsales/",
        "selectors": ["div.book-mid-info h2 a", "h2 a[data-bid]"],
        "region": "国内",
    },
    "番茄热门": {
        "url": "https://fanqienovel.com/rank/hot",
        "selectors": ["div.rank-book-name", "span.book-name", "a.book-name"],
        "region": "国内",
    },
    "晋江积分榜": {
        "url": "https://www.jjwxc.net/bookbase.php",
        "selectors": ["a[href*='onebook']", "span.title a"],
        "region": "国内",
    },
    "纵横热榜": {
        "url": "https://www.zongheng.com/rank.html",
        "selectors": ["div.rank-list div.book-name a", "a.rank-book-name"],
        "region": "国内",
    },
    "17K热榜": {
        "url": "https://www.17k.com/top/",
        "selectors": ["div.list div.book a", "a.book-title"],
        "region": "国内",
    },
    "书旗热榜": {
        "url": "https://www.shuqi.com/rank",
        "selectors": ["div.book-info h3 a", "a.book-title"],
        "region": "国内",
    },
    "飞卢热榜": {
        "url": "https://b.faloo.com/rank/",
        "selectors": ["div.rankList div.bookName a", "a.rank-book-name"],
        "region": "国内",
    },
    "刺猬猫热榜": {
        "url": "https://www.ciweimao.com/book-rank",
        "selectors": ["div.rank-item a.title", "a.rank-book-title"],
        "region": "国内",
    },
    "Webnovel Trending": {
        "url": "https://www.webnovel.com/ranking/power/1",
        "selectors": ["h3 a[href*='/book/']", "a.book-name", "a.g_thumb"],
        "region": "海外",
    },
    "Royal Road Best": {
        "url": "https://www.royalroad.com/fictions/best-rated",
        "selectors": ["h2.fiction-title a", "a[href*='/fiction/']"],
        "region": "海外",
    },
    "Wattpad Hot": {
        "url": "https://www.wattpad.com/stories/hot",
        "selectors": ["a.story-title", "div.story-info__title a", "h3 a[href*='/story/']"],
        "region": "海外",
    },
    "ScribbleHub Latest": {
        "url": "https://www.scribblehub.com/series-ranking/",
        "selectors": ["div.search_title a", "a[href*='/series/']"],
        "region": "海外",
    },
    "NovelUpdates Ranking": {
        "url": "https://www.novelupdates.com/ranking/",
        "selectors": ["div.search_title a", "a.series_title", "a[href*='/series/']"],
        "region": "海外",
    },
}

# 噪声文本黑名单：这些是导航/UI文本，不应被识别为书名
NOISE_TEXTS: set[str] = {
    "首页", "登录", "注册", "退出", "我的", "更多", "查看全部", "全部",
    "排行", "分类", "书架", "搜索", "设置", "关于", "帮助", "反馈",
    "首页", "上一页", "下一页", "末页", "跳转", "确定", "取消",
    "Next", "Prev", "Home", "Login", "Sign Up", "Logout", "More",
    "Ranking", "Category", "Search", "Settings", "About", "Help",
    "Previous", "Next Page", "Subscribe", "Download", "Read Now",
    "Start Reading", "Add to Library", "Follow", "Share", "Report",
}


@dataclass
class ScanResult:
    platform: str
    region: str
    books: list[dict] = field(default_factory=list)
    error: Optional[str] = None


def _is_valid_title(text: str) -> bool:
    """检查提取的文本是否可能是有效书名"""
    t = text.strip()
    if not t or len(t) < 2 or len(t) > 50:
        return False
    if t in NOISE_TEXTS:
        return False
    # 纯数字/纯符号不是书名
    if re.match(r'^[\d\s,.，。、！？!?…—\-·]+$', t):
        return False
    # 过短的英文单词（非中文）通常不是书名
    if re.match(r'^[a-zA-Z]{1,3}$', t):
        return False
    return True


async def _scrape_platform(name: str, config: dict, timeout: int = 15) -> ScanResult:
    """爬取单个平台榜单，使用 BeautifulSoup + CSS 选择器精确定位书名"""
    result = ScanResult(platform=name, region=config["region"])
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(config["url"], headers=headers)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "lxml")

        books: list[dict] = []
        seen: set[str] = set()

        # 按 CSS 选择器逐个尝试，直到找到足够的书名
        selectors = config.get("selectors", ["a"])
        for sel in selectors:
            elements = soup.select(sel)
            for el in elements:
                text = el.get_text(strip=True)
                if _is_valid_title(text) and text not in seen:
                    seen.add(text)
                    href = el.get("href", "")
                    books.append({"title": text, "url": str(href)})
                    if len(books) >= 30:
                        break
            if len(books) >= 30:
                break

        result.books = books[:30]
    except Exception as e:
        result.error = str(e)[:200]

    return result


async def scan_all(platforms: list[str] | None = None) -> list[ScanResult]:
    """并发扫榜所有平台（限制并发数防止触发目标站点限流）"""
    sources = PLATFORM_SOURCES
    if platforms:
        sources = {k: v for k, v in PLATFORM_SOURCES.items() if k in platforms}

    sem = asyncio.Semaphore(3)  # P1-4: 限制 3 并发
    async def _scrape_with_limit(name, config):
        async with sem:
            return await _scrape_platform(name, config)

    tasks = [_scrape_with_limit(name, config) for name, config in sources.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for r in results:
        if isinstance(r, Exception):
            output.append(ScanResult(platform="unknown", region="?", error=str(r)))
        else:
            output.append(r)
    return output


def get_platform_list() -> list[dict]:
    """返回可用平台列表"""
    return [
        {"name": name, "region": cfg["region"], "url": cfg["url"]}
        for name, cfg in PLATFORM_SOURCES.items()
    ]
