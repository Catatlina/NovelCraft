"""
7 Prompt 引擎 —— 自研实现（requirements_v7.md 第五节：脱离 AI Workbench 依赖）。
本文件实现全部 7 个 Prompt（novel-write/scan/analyze/short-write/
deslop/translate/review），接口约定见文件末尾。

设计原则：所有 Prompt 函数只接受 Context Hub 组装好的结构化 dict（见 context_hub.py），
不直接读数据库，保持"生成逻辑"与"数据访问"分离。
"""
from __future__ import annotations

import json


# ============================================================
# novel-write
# ============================================================


def build_novel_write_messages(context: dict, mode: str = "continue", template=None) -> list[dict]:
    """
    novel-write Prompt 引擎。
    mode: "continue"（续写下一章） | "first_chapter"（第一章） | "imitate"（仿写，Phase4补充）

    如果传入 template (TemplateRef)，使用 DB 模板的 system_prompt/temperature；
    否则使用硬编码默认值（降级路径）。
    """
    system_prompt = template.system_prompt if template else (
        "你是一名专业网络小说写手，正在为付费连载平台撰写正文。"
        "你必须严格遵守下面提供的上下文设定，不能自行发明与设定冲突的内容。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"title": "本章标题", "content": "本章正文（2000-3500字）", '
        '"summary": "本章100字以内摘要，供后续续写使用", '
        '"new_foreshadows": [{"description": "...", "expected_payoff_range": "如10-20章"}], '
        '"resolved_foreshadow_ids": ["本章回收的伏笔id，对应上下文中layer_5_open_foreshadows的id"]}'
    )

    user_prompt = _render_context_as_prompt(context, mode)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _render_context_as_prompt(context: dict, mode: str) -> str:
    meta = context["meta"]
    mode_instruction = {
        "continue": f"请撰写第 {meta['target_chapter_num']} 章正文。",
        "first_chapter": "请撰写全书第一章正文（黄金三章的开篇，需要在2000-3500字内建立强钩子）。",
    }.get(mode, f"请撰写第 {meta['target_chapter_num']} 章正文。")

    return f"""
【作品信息】书名：{meta['title']} | 题材：{meta.get('genre') or '未指定'}

【第1层-全书总纲】
{context['layer_1_overall_outline'] or '（暂无总纲，请根据书名和题材合理推进剧情）'}

【第2层-当前卷大纲】
{context['layer_2_current_arc_outline']}

【第3层-人物状态】
{json.dumps(context['layer_3_characters'], ensure_ascii=False, indent=2) if context['layer_3_characters'] else '（暂无人物设定）'}

【第4层-世界设定摘录】
{context['layer_4_world_setting_excerpt']}

【第5层-未回收伏笔池】
{json.dumps(context['layer_5_open_foreshadows'], ensure_ascii=False, indent=2) if context['layer_5_open_foreshadows'] else '（暂无待回收伏笔）'}

【第6层-前文摘要（最近{len(context['layer_6_recent_chapter_summaries'])}章）】
{json.dumps(context['layer_6_recent_chapter_summaries'], ensure_ascii=False, indent=2) if context['layer_6_recent_chapter_summaries'] else '（这是本书第一章，无前文）'}

【第7层-防崩提醒（硬性约束，禁止违反）】
{chr(10).join('- ' + r for r in context['layer_7_anti_crash_reminders'])}

【任务】
{mode_instruction}
请严格按 system prompt 中约定的 JSON 格式输出。
""".strip()


def parse_novel_write_response(raw_content: str) -> dict:
    """
    解析模型返回的 JSON。做了基本容错（模型偶尔会在JSON外包一层```json```代码块）。
    解析失败时抛 ValueError，上层（api/generation.py）应捕获并计入失败重试。
    """
    data = _clean_json_response(raw_content)
    if not data:
        raise ValueError(f"模型返回内容不是合法JSON\n原始内容前200字: {raw_content[:200]}")

    required_keys = {"title", "content", "summary"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"模型返回缺少必要字段: {missing}")

    data.setdefault("new_foreshadows", [])
    data.setdefault("resolved_foreshadow_ids", [])
    return data


# ============================================================
# novel-scan: 扫榜分析 Prompt
# ============================================================


def build_novel_scan_messages(platform_results: list[dict] | None = None, *, platforms: list[str] | None = None, raw_data: str = "") -> list[dict]:
    """
    novel-scan Prompt 引擎：对众平台扫榜结果做聚合分析和趋势识别。

    支持两种调用方式：
    1. build_novel_scan_messages([{"platform": "...", "books": [...], "region": "..."}, ...])
    2. build_novel_scan_messages(platforms=["起点","番茄"], raw_data="分析这些平台...")

    platform_results: list of {"platform": str, "books": [{"title": str}, ...], "region": str}
    返回的系统提示要求模型输出该轮扫榜的趋势总结。
    """
    if platform_results is None:
        if platforms:
            platform_results = [
                {"platform": p, "books": [], "region": "国内" if p not in ("Webnovel Trending", "Royal Road Best", "Wattpad Hot", "ScribbleHub Latest", "NovelUpdates Ranking") else "海外"}
                for p in platforms
            ]
        else:
            platform_results = []
    system_prompt = (
        "你是一名资深网络文学市场分析师，正在基于多个平台的榜单数据进行趋势研判。"
        "请分析以下榜单数据，识别当前热门题材、叙事模式、读者偏好变化趋势。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"trends": [{"trend_name": "趋势名", "description": "描述", "confidence": 0-10}], '
        '"common_genres": ["题材1", "题材2"], '
        '"regional_differences": "区域差异分析", '
        '"summary": "一句话总结"}'
    )

    platforms_summary = "\n".join(
        f"- {r['platform']}（{r.get('region', '未知')}）：{len(r.get('books', []))} 本上榜"
        for r in platform_results
    )
    book_samples: list[str] = []
    for r in platform_results:
        for book in r.get("books", [])[:5]:
            book_samples.append(f"  - [{r['platform']}] {book.get('title', '未知书名')}")
    books_text = "\n".join(book_samples[:50])

    user_prompt = f"""【本轮扫榜概况】
{platforms_summary}

【样本数据（各平台前5）】
{books_text}
{chr(10) + '【原始数据/附加上下文】' + chr(10) + raw_data[:3000] if raw_data else ''}
请分析当前市场的热门趋势和读者偏好，按 system prompt 格式输出 JSON。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ============================================================
# novel-analyze: 拆文学习 Prompt
# ============================================================


def build_novel_analyze_messages(book: dict | None = None, *, title: str = "", platform: str = "起点", region: str = "国内", chapters_text: str = "", genre: str = "") -> list[dict]:
    """
    novel-analyze Prompt 引擎：分析单本书的爆款潜力、市场契合度、可借鉴元素。

    支持两种调用方式：
    1. build_novel_analyze_messages({"title": "...", "platform": "...", "region": "..."})
    2. build_novel_analyze_messages(title="...", chapters_text="...")
    """
    if book is None:
        book = {"title": title, "platform": platform, "region": region}
    if chapters_text:
        book["first_chapter"] = chapters_text[:500]
    if genre:
        book["genre"] = genre
    system_prompt = (
        "你是一名资深网文编辑，正在评估一本书的爆款潜力和可借鉴性。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"hype_score": 0-100, "market_fit": "市场契合度评价（一句话）", '
        '"reason": "爆款/非爆款原因", '
        '"suggested_genre": "建议归类题材", '
        '"learnable_elements": ["可借鉴元素1", "可借鉴元素2"], '
        '"risks": ["潜在风险1"]}'
    )

    user_prompt = f"""请分析以下书籍的爆款潜力：

书名：《{book.get('title', '未知')}》
来源平台：{book.get('platform', '未知')}
地区：{book.get('region', '未知')}
{chr(10) + '开篇内容：' + book.get('first_chapter', '')[:800] if book.get('first_chapter') else ''}
请根据书名和在榜单中的位置，推断其题材、目标读者、商业策略，并给出爆款评分。
严格按 system prompt 中约定的 JSON 格式输出。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def parse_novel_analyze_response(raw_content: str) -> dict:
    """解析 novel-analyze 返回的 JSON"""
    data = _clean_json_response(raw_content)
    data.setdefault("hype_score", 0)
    data.setdefault("market_fit", "")
    data.setdefault("reason", "")
    data.setdefault("suggested_genre", "")
    data.setdefault("learnable_elements", [])
    data.setdefault("risks", [])
    return data


# ============================================================
# novel-translate: 多平台格式适配 Prompt
# ============================================================

# 供 API 层 (app/api/translate.py) 展示可选平台列表 + 校验 target_platform 合法性。
# key 必须和下面 build_novel_translate_messages() 里 platform_style_guides 的 key 保持一致。
PLATFORM_TRANSLATE_CONFIGS: dict[str, dict[str, str]] = {
    "webnovel": {"lang": "en", "style": "流畅自然，保留东方修炼体系术语，适合移动端阅读"},
    "royalroad": {"lang": "en", "style": "文学性较强，LitRPG/Progression Fantasy 风格"},
    "wattpad": {"lang": "en", "style": "青春化表达，对话比例高，段落简短"},
    "scribblehub": {"lang": "en", "style": "介于 Webnovel 和 Royal Road 之间，接受日式轻小说元素"},
}


def build_novel_translate_messages(
    title: str = "",
    content: str = "",
    target_platform: str = "webnovel",
    glossary: dict | None = None,
) -> list[dict]:
    """
    novel-translate Prompt 引擎：将中文章节翻译为英文并适配目标平台风格。

    target_platform: "webnovel" | "royalroad" | "wattpad" | "scribblehub"
    glossary: 术语对照表 {"修炼": "cultivation", ...}
    """
    platform_style_guides: dict[str, str] = {
        "webnovel": (
            "Webnovel 风格：英文流畅自然，保留东方修炼体系术语（Cultivation/Dao/Immortal等），"
            "章节标题保持简练有力，段落不宜过长（3-5句为宜），适合移动端阅读。"
        ),
        "royalroad": (
            "Royal Road 风格：文学性稍强，允许较复杂句式。LitRPG/Progression Fantasy 读者群，"
            "需要清晰的等级系统和能力成长描写。蓝色文本框（系统提示）用【】表示。"
        ),
        "wattpad": (
            "Wattpad 风格：青春化表达，对话比例高，情绪描写细腻。"
            "适合第一人称或紧密第三人称，段落简短，适合手机快速滑动阅读。"
        ),
        "scribblehub": (
            "Scribble Hub 风格：介于 Webnovel 和 Royal Road 之间，"
            "接受更多日式轻小说元素，允许较长的内心独白和描写。"
        ),
    }

    style_guide = platform_style_guides.get(
        target_platform.lower(),
        "通用英文网络小说风格：流畅自然，保留原作韵味。",
    )

    glossary_text = ""
    if glossary:
        glossary_items = "\n".join(
            f"- {k}: {v}" for k, v in list(glossary.items())[:20]
        )
        glossary_text = f"\n【术语对照表】\n{glossary_items}\n"

    system_prompt = (
        f"你是一名专业网络小说翻译，正在将中文网文译为英文发布到 {target_platform}。\n"
        f"{style_guide}\n"
        "请完整翻译以下章节，保留原文分节结构。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"title": "英文标题", "content": "完整英文译文"}'
    )

    user_prompt = f"""【原章节标题】{title}
{glossary_text}
【原文】
{content[:8000]}

请完成翻译，按 system prompt 约定的 JSON 格式输出。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ============================================================
# novel-review: 7维质量审查 Prompt
# ============================================================


def build_novel_review_messages(
    chapter_content: str,
    chapter_outline: str = "",
    context_summary: str = "",
    previous_review: dict | None = None,
) -> list[dict]:
    """
    novel-review Prompt 引擎：7维质量审查（对齐 requirements_v7.md 3.2 节）。
    7维：一致性 | AI味检测 | 节奏 | 人物OOC | 爽点密度 | 对话质量 | 结尾钩子
    """
    prev_section = ""
    if previous_review:
        prev_section = f"""\n【前次审查结果（用于对比趋势）】
{json.dumps(previous_review, ensure_ascii=False, indent=2)[:1500]}
"""

    system_prompt = (
        "你是一名资深网文质检编辑，正在对一章网文正文做7维度质量审查。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"dimensions": {"一致性": {"score": 0-10, "issues": []}, '
        '"AI味检测": {"score": 0-10, "issues": []}, '
        '"节奏": {"score": 0-10, "issues": []}, '
        '"人物OOC": {"score": 0-10, "issues": []}, '
        '"爽点密度": {"score": 0-10, "issues": []}, '
        '"对话质量": {"score": 0-10, "issues": []}, '
        '"结尾钩子": {"score": 0-10, "issues": []}}, '
        '"overall_score": 0-100, '
        '"summary": "综合评价（一句话）"}'
        '\n\n各维度说明：'
        '\n- 一致性：人物设定/时间线/世界观是否自洽，前后无矛盾'
        '\n- AI味检测：是否存在AI生成的套路化表达（“于是/随后/突然/与此同时”等模板化转折、空洞的形容词堆砌）'
        '\n- 节奏：章节内张弛节奏是否合理，信息密度是否适中'
        '\n- 人物OOC：角色言行是否偏离设定性格（Out of Character），是否与人物卡描述一致'
        '\n- 爽点密度：单位字数内爽点/高潮/反转分布是否达标'
        '\n- 对话质量：对话是否自然、是否符合角色身份、是否推动剧情'
        '\n- 结尾钩子：章末是否有足够悬念或未解问题驱动读者翻页'
    )

    user_prompt = f"""【本章大纲】
{chapter_outline or '无'}

【前文上下文摘要】
{context_summary[:1500] or '无'}
{prev_section}
【本章正文】
{chapter_content[:5000]}

请执行7维质量审查，按 system prompt 约定的 JSON 格式输出。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ============================================================
# novel-deslop: 去AI味/洗稿/润色 Prompt
# ============================================================


def build_novel_deslop_messages(content: str, mode: str = "polish") -> list[dict]:
    """
    novel-deslop Prompt 引擎：去AI味、润色、洗稿。

    mode: "polish"（润色） | "deslop"（去AI味） | "rewrite"（深度重写）
    """
    mode_instructions = {
        "polish": "对以下文本进行润色，提升文笔但不改变内容结构和情节。修复不通顺的句子和重复表达。",
        "deslop": (
            "对以下文本进行去AI味处理：减少'于是/随后/接着/突然'等AI常用转折词，"
            "增加感官细节和场景氛围描写，让语言更有人情味和个性。保持原意不变。"
        ),
        "rewrite": "对以下文本进行深度重写：保留核心情节，但用更生动自然的语言重新表达，增加对话和细节。",
    }

    instruction = mode_instructions.get(mode, mode_instructions["polish"])

    system_prompt = (
        "你是一名专业网文编辑，负责对文本进行润色打磨。"
        "保留原文的核心情节和人物，只优化表达方式。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"result": "处理后的完整文本"}'
    )

    user_prompt = f"{instruction}\n\n【原文】\n{content[:8000]}\n\n请按 system prompt 约定的 JSON 格式输出。"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ============================================================
# novel-short-write: 短篇写作 Prompt
# ============================================================


def build_novel_short_write_messages(
    topic: str, genre: str = "", target_words: int = 5000, style: str = ""
) -> list[dict]:
    """
    novel-short-write Prompt 引擎：短篇/中篇独立创作。

    topic: 选题
    genre: 题材
    target_words: 目标字数
    style: 风格描述
    """
    system_prompt = (
        "你是一名专业短篇小说写手，正在创作一篇结构完整的短篇。"
        "你需要在一个有限篇幅内完成完整的起承转合。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"title": "标题", "content": "完整正文", "summary": "100字摘要"}'
    )

    user_prompt = f"""【选题】{topic}
【题材】{genre or '不限'}
【目标字数】约 {target_words} 字
【风格要求】{style or '不限'}

请创作一篇结构完整的短篇，按 system prompt 约定的 JSON 格式输出。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# ═══ Shared Utilities ═══

def _clean_json_response(raw: str) -> dict:
    """统一 JSON 清洗：去除 markdown code block 包装，解析 JSON。"""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}

# ═══ Parse Functions (容错 JSON 解析) ═══

def _safe_parse_json(raw: str):
    return _clean_json_response(raw)


def parse_novel_scan_response(raw_content: str) -> list[dict]:
    data = _safe_parse_json(raw_content)
    if isinstance(data, list): return data
    if isinstance(data, dict): return data.get("books", data.get("results", []))
    return []


def parse_novel_translate_response(raw_content: str) -> dict:
    data = _safe_parse_json(raw_content)
    if isinstance(data, dict) and "translated_text" in data: return data
    return {"translated_text": raw_content, "word_count": len(raw_content), "cultural_notes": []}


def parse_novel_review_response(raw_content: str) -> dict:
    data = _safe_parse_json(raw_content)
    if isinstance(data, dict) and "overall_score" in data: return data
    return {"overall_score": 7.0, "dimensions": {}, "summary": "解析失败"}


def parse_novel_deslop_response(raw_content: str) -> dict:
    data = _safe_parse_json(raw_content)
    if isinstance(data, dict) and "result" in data: return data
    return {"result": raw_content, "changes_summary": ""}


def parse_novel_short_write_response(raw_content: str) -> dict:
    data = _safe_parse_json(raw_content)
    if isinstance(data, dict) and "sections" in data: return data
    return {"title": "未命名", "sections": [{"heading": "", "content": raw_content}], "total_words": len(raw_content)}
