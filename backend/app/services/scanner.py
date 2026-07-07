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
    """并发扫榜所有平台"""
    sources = PLATFORM_SOURCES
    if platforms:
        sources = {k: v for k, v in PLATFORM_SOURCES.items() if k in platforms}

    tasks = [_scrape_platform(name, config) for name, config in sources.items()]
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


# ═══ Mock 扫榜数据（演示用 / 爬虫失败时降级） ═══
MOCK_SCAN_BOOKS: list[dict] = [
    {"title": "星辰之主", "author": "逆苍天", "platform": "起点月票榜", "rank": 1, "hot_score": 98, "tags": ["玄幻", "热血", "逆袭"], "word_count": 2800000, "summary": "少年偶获星辰之力，从废物逆袭为诸天至尊。"},
    {"title": "大奉打更人", "author": "卖报小郎君", "platform": "起点畅销榜", "rank": 1, "hot_score": 96, "tags": ["仙侠", "侦探", "搞笑"], "word_count": 3500000, "summary": "警校毕业穿越古代，成为打更人，破案修仙两不误。"},
    {"title": "夜的命名术", "author": "会说话的肘子", "platform": "起点月票榜", "rank": 2, "hot_score": 94, "tags": ["科幻", "赛博朋克", "都市"], "word_count": 2200000, "summary": "赛博世界里，少年用代码改变命运。"},
    {"title": "我在修仙界搞房产", "author": "番茄第一深情", "platform": "番茄热门", "rank": 1, "hot_score": 92, "tags": ["修仙", "轻松", "经营"], "word_count": 1800000, "summary": "穿越修仙界搞房地产开发，成了修真界的许家印。"},
    {"title": "重生之都市仙尊", "author": "老鹰吃小鸡", "platform": "番茄热门", "rank": 2, "hot_score": 90, "tags": ["都市", "重生", "修仙"], "word_count": 4200000, "summary": "仙界至尊重生到地球高中生身上，扮猪吃老虎。"},
    {"title": "她的名字叫红豆", "author": "晋江文学城作者", "platform": "晋江积分榜", "rank": 1, "hot_score": 88, "tags": ["言情", "现言", "虐恋"], "word_count": 800000, "summary": "一场误会，两次错过。他说红豆最相思。"},
    {"title": "诸天投影", "author": "裴屠狗", "platform": "纵横热榜", "rank": 1, "hot_score": 85, "tags": ["无限流", "诸天"], "word_count": 1800000, "summary": "我是诸天的投影，万界的倒影。"},
    {"title": "道诡异仙", "author": "狐尾的笔", "platform": "起点月票榜", "rank": 3, "hot_score": 93, "tags": ["克苏鲁", "玄幻", "诡异"], "word_count": 2000000, "summary": "诡异修仙世界，清醒是一种病。"},
    {"title": "我的冰山美女老婆", "author": "青衫仗剑", "platform": "17K热榜", "rank": 1, "hot_score": 82, "tags": ["都市", "兵王", "爽文"], "word_count": 5600000, "summary": "兵王回归都市，发现多了个冰山总裁未婚妻。"},
    {"title": "大王饶命", "author": "会说话的肘子", "platform": "书旗热榜", "rank": 1, "hot_score": 80, "tags": ["灵气复苏", "搞笑"], "word_count": 1600000, "summary": "灵气复苏时代，靠怼人升级的主角。"},
    {"title": "轮回乐园", "author": "那一只蚊子", "platform": "飞卢热榜", "rank": 1, "hot_score": 78, "tags": ["无限流", "末世", "战斗"], "word_count": 3500000, "summary": "在轮回乐园中，只有强者才能活下去。"},
    {"title": "我加载了恋爱游戏", "author": "掠过的乌鸦", "platform": "刺猬猫热榜", "rank": 1, "hot_score": 75, "tags": ["恋爱", "日常", "轻小说"], "word_count": 900000, "summary": "普通高中生获得了攻略美少女就能变强的系统。"},
    {"title": "Shadow Slave", "author": "Guiltythree", "platform": "Webnovel Trending", "rank": 1, "hot_score": 95, "tags": ["dark fantasy", "litrpg"], "word_count": 2500000, "summary": "A cursed boy navigates a nightmare world ruled by gods and monsters."},
    {"title": "Mother of Learning", "author": "nobody103", "platform": "Royal Road Best", "rank": 1, "hot_score": 97, "tags": ["time loop", "magic", "progression"], "word_count": 800000, "summary": "A mage trapped in a month-long time loop must uncover the truth."},
    {"title": "The Mech Touch", "author": "Exlor", "platform": "Webnovel Trending", "rank": 2, "hot_score": 89, "tags": ["mecha", "scifi", "crafting"], "word_count": 5500000, "summary": "A mech designer rises to power through innovation and determination."},
]


async def scan_all_mock(platforms: list[str] | None = None) -> list[ScanResult]:
    """返回模拟扫榜数据（演示模式 / 爬虫失败降级）"""
    results = []
    for name, cfg in PLATFORM_SOURCES.items():
        if platforms and name not in platforms:
            continue
        matching = [b for b in MOCK_SCAN_BOOKS if b["platform"] == name]
        if not matching:
            matching = MOCK_SCAN_BOOKS[:5]
        results.append(ScanResult(platform=name, region=cfg["region"], books=matching))
    return results
