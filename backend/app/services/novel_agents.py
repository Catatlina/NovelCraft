"""
多 Agent 小说生产协调器

架构参考：
- AI_NovelGenerator (5.5k⭐): 剧情节奏控制 + 伏笔衔接机制
- autonovel: 多 Agent 分工 (Planner→Writer→Reviewer→Editor)
- NovelGenerator: 章节目标分配 + 人物弧线追踪
- Writingway: 编辑器协同体验（前端层）

Agent 角色分工：
- Chief Planner: 扫榜→全书规划→章节目标分配
- Lead Writer: 按目标写正文 + 伏笔管理
- Continuity Checker: 一致性/伏笔/OOC 检查
- Quality Editor: 审查→定位问题→定向重写
"""
import asyncio
import json
import logging
import uuid as _uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deepseek_client import chat_completion

logger = logging.getLogger(__name__)


@dataclass
class ChapterTarget:
    """章节目标：写入之前先分配"""
    chapter_num: int
    must_happen: str          # 必须发生的事件
    character_focus: str      # 主要人物
    emotional_arc: str        # 情感走向 (上升/下降/转折)
    conflict_type: str        # 冲突类型 (外部/内部/人际)
    pacing: str               # 节奏 (快/中/慢)
    foreshadow_plant: str     # 需要埋的伏笔
    word_range: str           # 字数范围


@dataclass
class NovelPlan:
    """全书规划"""
    title: str
    genre: str
    synopsis: str
    overall_outline: str
    characters: list[dict] = field(default_factory=list)
    chapter_targets: list[ChapterTarget] = field(default_factory=list)
    world_rules: list[str] = field(default_factory=list)


class NovelAgents:
    """多 Agent 协调器 — 替代单次 LLM 调用，用多角色协作提升质量"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ═══════════════════════════════════════
    # Chief Planner: 全书规划
    # ═══════════════════════════════════════

    async def chief_planner(self, idea: str, genre: str, extra: str = "") -> NovelPlan:
        """Chief Planner Agent: 扫榜→全书规划→章节目标分配"""
        messages = [{
            "role": "system",
            "content": (
                "你是首席规划师（Chief Planner Agent）。"
                "你的职责：1) 分析扫榜趋势 2) 选出最佳选题 3) 规划全书结构 4) 为每章分配具体目标。"
                "输出纯 JSON，不要任何解释。"
            )
        }, {
            "role": "user",
            "content": f"""为以下选题做全书规划。

灵感: {idea}
题材: {genre}
额外要求: {extra or '强钩子高爽点开篇'}

输出JSON:
{{
  "title": "书名",
  "synopsis": "200字简介",
  "overall_outline": "3-5卷全书总纲",
  "characters": [{{"name":"","role":"","traits":"","arc":""}}],
  "chapter_targets": [  // 前10章每章目标
    {{"chapter_num":1,"must_happen":"","character_focus":"","emotional_arc":"","conflict_type":"","pacing":"fast/normal/slow","word_range":"2000-3000"}}
  ]
}}"""
        }]
        r = await chat_completion(messages, temperature=0.8, max_tokens=4000)
        data = json.loads(r["content"])
        return NovelPlan(
            title=data.get("title", f"{genre}:{idea[:20]}"),
            genre=genre,
            synopsis=data.get("synopsis", ""),
            overall_outline=data.get("overall_outline", ""),
            characters=data.get("characters", []),
            chapter_targets=[
                ChapterTarget(**ct) for ct in data.get("chapter_targets", [])
            ],
        )

    # ═══════════════════════════════════════
    # Lead Writer: 按目标写章节
    # ═══════════════════════════════════════

    async def lead_writer(self, target: ChapterTarget, plan: NovelPlan,
                          context: dict, previous_summaries: list[str]) -> str:
        """Lead Writer Agent: 按目标写章节正文 + 管理伏笔"""
        messages = [{
            "role": "system",
            "content": (
                "你是首席写手（Lead Writer Agent）。"
                "你的职责：1) 按章节目标写正文 2) 埋设伏笔 3) 回收前文伏笔。"
                "禁止出现'上一章''本章'等元文本。禁止AI腔。"
                "输出纯 JSON: {{\"content\":\"章节正文\",\"title\":\"章名\",\"summary\":\"150字摘要\"}}"
            )
        }, {
            "role": "user",
            "content": f"""写《{plan.title}》第{target.chapter_num}章的完整正文。

【本章目标】
- 必须发生: {target.must_happen}
- 主要人物: {target.character_focus}
- 情感走向: {target.emotional_arc}
- 冲突类型: {target.conflict_type}
- 节奏: {target.pacing}
- 需埋伏笔: {target.foreshadow_plant}
- 字数: {target.word_range}

【全书规划】
{plan.overall_outline[:1000]}

【前情摘要】
{chr(10).join(previous_summaries[-5:]) if previous_summaries else '无（第一章）'}

【硬性规则】
1. 章首必须有钩子
2. 章尾必须卡关键处
3. 对话有潜台词
4. 描述有画面感
5. 严格控制在字数范围内"""
        }]
        r = await chat_completion(messages, temperature=0.9, max_tokens=4000)
        return json.loads(r["content"])

    # ═══════════════════════════════════════
    # Continuity Checker: 一致性检查
    # ═══════════════════════════════════════

    async def continuity_checker(self, chapter_content: str, target: ChapterTarget,
                                  plan: NovelPlan, characters: list[dict],
                                  open_foreshadows: list[dict]) -> dict:
        """Continuity Checker Agent: 一致性/伏笔/OOC 检查"""
        messages = [{
            "role": "system",
            "content": (
                "你是连续性检查员（Continuity Checker Agent）。"
                "检查章节是否：1) 完成规定目标 2) 人物是否OOC 3) 时间线是否正确 4) 伏笔是否合规。"
                "输出纯 JSON: {{\"pass\":true/false,\"issues\":[{{\"type\":\"\",\"severity\":\"error/warn\",\"description\":\"\"}}],\"target_met\":true/false}}"
            )
        }, {
            "role": "user",
            "content": f"""检查《{plan.title}》第{target.chapter_num}章。

【章节目标】必须发生: {target.must_happen} | 主要人物: {target.character_focus}
【人物设定】{json.dumps(characters[:5], ensure_ascii=False)}
【开放伏笔】{json.dumps(open_foreshadows, ensure_ascii=False)}
【章节内容】{chapter_content[:3000]}"""
        }]
        r = await chat_completion(messages, temperature=0.3, max_tokens=1000)
        return json.loads(r["content"])

    # ═══════════════════════════════════════
    # Quality Editor: 审查→定向重写
    # ═══════════════════════════════════════

    async def quality_editor(self, chapter_content: str, issues: list[dict],
                              target: ChapterTarget) -> str:
        """Quality Editor Agent: 针对问题定向修改"""
        if not issues:
            return chapter_content
        errors = [i for i in issues if i.get("severity") == "error"]
        if not errors:
            return chapter_content

        messages = [{
            "role": "system",
            "content": (
                "你是质量编辑（Quality Editor Agent）。"
                "针对以下问题定向修改章节，只修改有问题的部分，其他保持原样。"
                "输出纯 JSON: {{\"content\":\"修改后的完整正文\"}}"
            )
        }, {
            "role": "user",
            "content": f"""修改《》第{target.chapter_num}章。

【需要修复的问题】
{json.dumps(errors, ensure_ascii=False, indent=2)}

【原文】
{chapter_content[:4000]}"""
        }]
        r = await chat_completion(messages, temperature=0.5, max_tokens=4000)
        return json.loads(r["content"]).get("content", chapter_content)

    # ═══════════════════════════════════════
    # 全流程编排
    # ═══════════════════════════════════════

    async def run(self, idea: str, genre: str = "修真", extra: str = "",
                  num_chapters: int = 10) -> dict:
        """多 Agent 全流程：规划→逐章写作→检查→修改→入库"""
        results = {"chapters": [], "plan": None, "issues_found": 0, "revisions": 0}

        # Phase 1: Chief Planner
        plan = await self.chief_planner(idea, genre, extra)
        results["plan"] = plan

        # Phase 2: For each chapter: Write→Check→Revise→Repeat
        summaries = []
        foreshadows = []
        for i in range(min(num_chapters, len(plan.chapter_targets))):
            target = plan.chapter_targets[i]
            context = {"title": plan.title, "genre": plan.genre}

            # Write
            draft = await self.lead_writer(target, plan, context, summaries)
            content = draft.get("content", "")

            # Check continuity
            check = await self.continuity_checker(
                content, target, plan, plan.characters, foreshadows)
            if check.get("issues"):
                results["issues_found"] += len(check["issues"])

            # Revise if needed
            if not check.get("pass", True):
                content = await self.quality_editor(content, check["issues"], target)
                results["revisions"] += 1

            summaries.append(draft.get("summary", ""))
            results["chapters"].append({
                "chapter_num": target.chapter_num,
                "title": draft.get("title", ""),
                "content": content,
                "summary": draft.get("summary", ""),
                "word_count": len(content),
                "target_met": check.get("target_met", True),
                "issues": check.get("issues", []),
            })

        return results


# 单例
_agents: NovelAgents | None = None


def get_novel_agents(db: AsyncSession) -> NovelAgents:
    return NovelAgents(db)
