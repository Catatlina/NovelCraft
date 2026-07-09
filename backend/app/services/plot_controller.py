"""
剧情控制引擎 + 故事线程系统

参考：
- AI_NovelGenerator: 多线剧情管理 + 节奏控制
- NovelGenerator: 章节目标分配 + 人物弧线追踪 + 防崩

功能：
1. 多线剧情追踪 (story_threads)
2. 章节节奏分析 (pacing)
3. 人物弧线验证 (character_arc)
4. 一致性防崩检查
5. 自动返工循环 (评分<80→重写→再评分)
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deepseek_client import chat_completion

logger = logging.getLogger(__name__)


@dataclass
class StoryThread:
    """故事线程"""
    id: str
    name: str                    # 线程名 (主角线/科技线/感情线)
    status: str = "active"       # active/resolved/abandoned
    progress: float = 0.0        # 0.0-1.0
    next_event: str = ""         # 下一个关键事件
    last_updated_chapter: int = 0


@dataclass
class CharacterArc:
    """人物弧线"""
    name: str
    current_phase: str     # introduction/growth/crisis/transformation/resolution
    target_phase: str
    traits: list[str] = field(default_factory=list)
    ooc_warnings: list[str] = field(default_factory=list)


@dataclass
class PacingReport:
    """每章节奏报告"""
    chapter_num: int
    action_ratio: float      # 动作占比
    dialogue_ratio: float    # 对话占比
    exposition_ratio: float  # 说明占比
    conflict_intensity: int  # 1-10
    readability: str         # "紧张"/"舒缓"/"信息密集"


class PlotController:
    """剧情控制引擎 — 管理多线剧情 + 人物弧线 + 节奏"""

    def __init__(self):
        self.threads: list[StoryThread] = []
        self.characters: list[CharacterArc] = []
        self.pacing_history: list[PacingReport] = []

    async def analyze_pacing(self, chapter_content: str, chapter_num: int) -> PacingReport:
        """分析章节节奏"""
        r = await chat_completion([{
            "role": "system",
            "content": "你是节奏分析师。分析章节节奏，输出 JSON。"
        }, {
            "role": "user",
            "content": f"""分析第{chapter_num}章节奏，输出 JSON：
{{
  "action_ratio": 35,
  "dialogue_ratio": 40,
  "exposition_ratio": 25,
  "conflict_intensity": 7,
  "readability": "紧张"
}}

章节内容：
{chapter_content[:3000]}"""
        }], temperature=0.2, max_tokens=300)
        try:
            data = json.loads(r["content"])
        except json.JSONDecodeError:
            data = {"action_ratio": 30, "dialogue_ratio": 40, "exposition_ratio": 30,
                     "conflict_intensity": 5, "readability": "正常"}
        return PacingReport(
            chapter_num=chapter_num,
            action_ratio=data.get("action_ratio", 30),
            dialogue_ratio=data.get("dialogue_ratio", 40),
            exposition_ratio=data.get("exposition_ratio", 30),
            conflict_intensity=data.get("conflict_intensity", 5),
            readability=data.get("readability", "正常"),
        )

    async def check_character_arc(self, chapter_content: str, character: CharacterArc) -> dict:
        """检查人物是否OOC或弧线是否推进"""
        r = await chat_completion([{
            "role": "system",
            "content": "你是人物弧线分析师。检查章节中人物是否OOC，弧线是否有推进。输出 JSON。"
        }, {
            "role": "user",
            "content": f"""检查人物弧线：

人物: {character.name}
当前阶段: {character.current_phase}
目标阶段: {character.target_phase}
性格特征: {', '.join(character.traits)}

章节内容:
{chapter_content[:2500]}

输出 JSON:
{{
  "ooc_detected": false,
  "ooc_issues": [],
  "arc_progress": "推进了XX（具体变化）",
  "phase_change": false
}}"""
        }], temperature=0.3, max_tokens=500)
        return json.loads(r["content"])

    async def check_story_threads(self, chapter_content: str) -> dict:
        """检查各故事线程推进情况"""
        threads_json = json.dumps([{
            "name": t.name, "status": t.status,
            "next_event": t.next_event, "progress": t.progress,
        } for t in self.threads if t.status == "active"], ensure_ascii=False)

        r = await chat_completion([{
            "role": "system",
            "content": "你是剧情线程追踪器。检查本章是否推进了各条故事线。输出 JSON。"
        }, {
            "role": "user",
            "content": f"""活跃故事线程：
{threads_json}

章节内容：
{chapter_content[:2500]}

输出 JSON:
{{
  "threads_advanced": ["线程名"],
  "threads_stalled": ["线程名"],
  "threads_resolved": []
}}"""
        }], temperature=0.2, max_tokens=300)
        return json.loads(r["content"])

    async def consistency_check(self, chapter_content: str, context: dict) -> dict:
        """一致性防崩检查"""
        r = await chat_completion([{
            "role": "system",
            "content": "你是一致性检查员。检查章节是否违反已有设定。输出 JSON。"
        }, {
            "role": "user",
            "content": f"""检查一致性：

已有设定（不可违反）：
- 人物状态: {json.dumps(context.get('characters', []), ensure_ascii=False)}
- 世界规则: {json.dumps(context.get('world_rules', []), ensure_ascii=False)}
- 历史事件: {json.dumps(context.get('history', []), ensure_ascii=False)}

章节内容:
{chapter_content[:2500]}

输出 JSON:
{{
  "violations": [
    {{"type": "timeline/power_level/ooc", "severity": "error/warn", "description": ""}}
  ],
  "pass": true
}}"""
        }], temperature=0.2, max_tokens=400)
        return json.loads(r["content"])


class AutoRevisionLoop:
    """自动返工循环: 评分→判断→重写→再评分"""

    async def run(self, chapter_content: str, chapter_num: int,
                  context: dict, max_iterations: int = 3) -> dict:
        """自动返工循环，最多 3 轮"""
        result = {"content": chapter_content, "score": 0, "iterations": 0, "issues": []}

        for iteration in range(max_iterations):
            result["iterations"] = iteration + 1

            # Step 1: Quality review
            review = await self._review(result["content"], chapter_num, context)
            result["score"] = review.get("overall_score", 0)
            result["issues"] = review.get("issues", [])

            if result["score"] >= 80:
                break

            # Step 2: Targeted rewrite
            result["content"] = await self._targeted_rewrite(
                result["content"], review.get("issues", []), chapter_num)

        return result

    async def _review(self, content: str, chapter_num: int, context: dict) -> dict:
        r = await chat_completion([{
            "role": "system",
            "content": "你是小说质量审查员。7维评分，输出 JSON。"
        }, {
            "role": "user",
            "content": f"""审查第{chapter_num}章，7维评分(0-100):

{{
  "overall_score": 85,
  "dimensions": {{
    "consistency": 90,
    "ai_detection": 20,
    "pacing": 85,
    "ooc": 90,
    "thrill_density": 80,
    "dialogue_quality": 85,
    "ending_hook": 90
  }},
  "issues": [
    {{"type": "thrill", "severity": "warn", "description": "爽点密度不足", "fragment": "需要重写的段落"}}
  ]
}}

章节内容:
{content[:4000]}"""
        }], temperature=0.3, max_tokens=800)
        return json.loads(r["content"])

    async def _targeted_rewrite(self, content: str, issues: list[dict],
                                  chapter_num: int) -> str:
        """定向重写问题片段"""
        if not issues:
            return content
        errors = [i for i in issues if i.get("severity") == "error"]
        all_issues = errors or issues

        r = await chat_completion([{
            "role": "system",
            "content": "你是小说修改编辑。只修改问题部分，保持其他内容不变。输出 JSON: {{\"content\":\"修改后全文\"}}"
        }, {
            "role": "user",
            "content": f"""修改第{chapter_num}章以下问题：

{json.dumps(all_issues, ensure_ascii=False, indent=2)}

原文：
{content[:4000]}"""
        }], temperature=0.5, max_tokens=4000)
        return json.loads(r["content"]).get("content", content)
