"""
Prompt 版本注册中心 — 从 DB prompt_templates 表加载，
支持运行时热更新、在线编辑、版本回滚。

v2: 从进程内 dict 升级为 DB 驱动 (P1-1)
v3: 修复 P0-1 回归 — 恢复 get_prompt_registry() 兼容接口
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TemplateRef:
    """Prompt 模板的运行时引用"""
    __slots__ = ("name", "version", "system_prompt", "user_prompt_template",
                 "temperature", "max_tokens", "description")

    def __init__(self, name: str, version: int, system_prompt: str,
                 user_prompt_template: str = "", temperature: float = 0.9,
                 max_tokens: int = 4000, description: str = ""):
        self.name = name
        self.version = version
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.description = description


class PromptRegistry:
    """向后兼容的单例：管理所有 Prompt 的版本查询。

    使用方式:
        registry = await get_prompt_registry()
        tpl = registry.get("novel-write")  # → TemplateRef
    """

    def __init__(self, templates: dict[str, TemplateRef] | None = None):
        self._templates: dict[str, TemplateRef] = templates or dict(_HARDCODED_FALLBACKS)

    def get(self, name: str) -> TemplateRef | None:
        return self._templates.get(name)

    def get_or_default(self, name: str) -> TemplateRef:
        return self._templates.get(name) or TemplateRef(name, name, "", "", 0.9, 4000)

    def list_all(self) -> dict[str, TemplateRef]:
        return dict(self._templates)

    async def log_auto_optimization(
        self, db: AsyncSession, project_id=None, prompt_name: str = "",
        previous_score: float = 0, new_score: float = 0, context: str = "",
    ):
        """质量审查后自动记录优化日志（向后兼容 quality.py 调用）。"""
        from app.db.models import PromptOptimizationLog
        import uuid as _uuid
        diff = new_score - previous_score
        if abs(diff) < 2.0:
            return None
        direction = "提升" if diff > 0 else "下降"
        reason = f"自动: 质量审查分从 {previous_score:.1f} {direction}到 {new_score:.1f} (Δ{diff:+.1f})"
        if context:
            reason += f" — {context[:200]}"
        entry = PromptOptimizationLog(
            id=_uuid.uuid4(),
            project_id=project_id,
            prompt_name=prompt_name,
            params_before={"quality_score": previous_score},
            params_after={"quality_score": new_score},
            reason=reason,
            quality_impact=diff,
            applied_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        return entry


# ── 硬编码降级副本（与 prompts.py 真实内容对齐, DB 不可用时使用） ──
_HARDCODED_FALLBACKS: dict[str, TemplateRef] = {
    "novel-write": TemplateRef("novel-write", 0,
        "你是一名专业网络小说写手，正在为付费连载平台撰写正文。"
        "你必须严格遵守下面提供的上下文设定，不能自行发明与设定冲突的内容。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"title": "本章标题", "content": "本章正文（2000-3500字）", '
        '"summary": "本章100字以内摘要，供后续续写使用", '
        '"new_foreshadows": [{"description": "...", "expected_payoff_range": "如10-20章"}], '
        '"resolved_foreshadow_ids": ["本章回收的伏笔id，对应上下文中layer_5_open_foreshadows的id"]}',
        "{context_json}", 0.9, 4000, "novel-write 降级"),
    "novel-review": TemplateRef("novel-review", 0,
        "你是一名资深编辑，请从以下7个维度审查小说章节："
        "1)逻辑一致性 2)人物弧光 3)节奏起伏 4)情感层次"
        "5)市场吸引力 6)原创性 7)伏笔管理。"
        "输出JSON格式：{\"overall_score\": int, \"dimension_scores\": {...}, \"issues\": [...], \"suggestions\": [...]}",
        "请审查以下章节：\n{content}", 0.3, 4000, "novel-review 降级"),
    "novel-translate": TemplateRef("novel-translate", 0,
        "你是一名专业文学翻译，请将以下中文小说翻译为目标语言。"
        "保持文学性、风格一致性和对话语气。",
        "Title: {title}\nContent: {content}\nPlatform: {platform}", 0.3, 16384, "novel-translate 降级"),
    "novel-deslop": TemplateRef("novel-deslop", 0,
        "你是一名专业编辑，需要去除文本中的AI写作痕迹，"
        "使表达更自然、更有人味，同时保持原意不变。",
        "{content}", 0.7, 4000, "novel-deslop 降级"),
    "novel-scan": TemplateRef("novel-scan", 0,
        "你是一名市场分析师，需要分析网络小说榜单趋势，"
        "提取热门题材、叙事模式和读者偏好。",
        "{scan_data}", 0.3, 4000, "novel-scan 降级"),
    "novel-analyze": TemplateRef("novel-analyze", 0,
        "你是一名文学评论家，需要深度分析爆款小说的成功要素，"
        "包括叙事结构、人物塑造、情感节奏和市场定位。",
        "{analysis_target}", 0.3, 4000, "novel-analyze 降级"),
    "novel-short-write": TemplateRef("novel-short-write", 0,
        "你是一名短篇小说作家，根据以下提示创作一个完整的短篇故事。"
        "输出JSON格式：{\"title\": \"...\", \"content\": \"...\"}",
        "{prompt}", 0.9, 16384, "novel-short-write 降级"),
}

# 进程级缓存
_registry_cache: PromptRegistry | None = None


async def get_prompt_registry(db: AsyncSession | None = None) -> PromptRegistry:
    """获取 PromptRegistry 单例（向后兼容，兼容旧调用方）。

    首次调用时尝试从 DB 加载活跃模板；后续调用返回缓存实例。
    如果 db 为 None 且缓存为空，使用硬编码降级副本。
    """
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache
    if db is not None:
        templates = await load_all_active(db)
        _registry_cache = PromptRegistry(templates)
        return _registry_cache
    _registry_cache = PromptRegistry()
    return _registry_cache


async def load_template(db: AsyncSession, name: str) -> TemplateRef:
    """从 DB 加载活跃模板，不可用时返回硬编码降级"""
    try:
        from app.db.models import PromptTemplate
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == name, PromptTemplate.is_active == True)
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return TemplateRef(
                name=row.name, version=row.version,
                system_prompt=row.system_prompt,
                user_prompt_template=row.user_prompt_template or "",
                temperature=row.temperature or 0.9,
                max_tokens=row.max_tokens or 4000,
                description=row.description or "",
            )
    except Exception:
        logger.warning("prompt_registry: DB load failed for %s, using fallback", name,
                       exc_info=True)
    return _HARDCODED_FALLBACKS.get(name) or TemplateRef(name, 0, "", "", 0.9, 4000)


async def load_all_active(db: AsyncSession) -> dict[str, TemplateRef]:
    """批量加载所有活跃模板"""
    try:
        from app.db.models import PromptTemplate
        from sqlalchemy import and_, func as sa_func
        sub = (
            select(
                PromptTemplate.name,
                sa_func.max(PromptTemplate.version).label("max_ver"))
            .where(PromptTemplate.is_active == True)
            .group_by(PromptTemplate.name)
            .subquery()
        )
        result = await db.execute(
            select(PromptTemplate).join(
                sub,
                and_(
                    PromptTemplate.name == sub.c.name,
                    PromptTemplate.version == sub.c.max_ver,
                )
            )
        )
        loaded: dict[str, TemplateRef] = {}
        for row in result.scalars().all():
            loaded[row.name] = TemplateRef(
                name=row.name, version=row.version,
                system_prompt=row.system_prompt,
                user_prompt_template=row.user_prompt_template or "",
                temperature=row.temperature or 0.9,
                max_tokens=row.max_tokens or 4000,
                description=row.description or "",
            )
        return loaded or dict(_HARDCODED_FALLBACKS)
    except Exception:
        logger.warning("prompt_registry: bulk load failed, using all fallbacks",
                       exc_info=True)
        return dict(_HARDCODED_FALLBACKS)


async def invalidate_cache(db: AsyncSession | None = None) -> None:
    """清除缓存，强制下次 get_prompt_registry 重新从 DB 加载"""
    global _registry_cache
    _registry_cache = None
