"""
Prompt 版本注册中心 — 从 DB prompt_templates 表加载，
支持运行时热更新、在线编辑、版本回滚。

v2: 从进程内 dict 升级为 DB 驱动 (P1-1)
"""
from __future__ import annotations

import logging
import uuid
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


# ── 硬编码降级副本（DB 不可用时使用） ──
_HARDCODED_FALLBACKS: dict[str, TemplateRef] = {
    "novel-write": TemplateRef("novel-write", 0,
        "你是一名专业网络小说写手，正在为付费连载平台撰写正文。"
        "你必须严格遵守下面提供的上下文设定。",
        "{context_json}", 0.9, 4000, "novel-write 降级"),
    "novel-review": TemplateRef("novel-review", 0,
        "你是一名资深编辑，需要从7个维度审查小说章节质量。",
        "请审查以下章节：\n{content}", 0.3, 4000, "novel-review 降级"),
    "novel-translate": TemplateRef("novel-translate", 0,
        "你是一名专业文学翻译，需要将中文小说翻译为目标语言。",
        "Title: {title}\nContent: {content}\nPlatform: {platform}", 0.3, 16384, "novel-translate 降级"),
    "novel-deslop": TemplateRef("novel-deslop", 0,
        "你是一名专业编辑，需要去除AI写作痕迹，使文本更自然。",
        "{content}", 0.7, 4000, "novel-deslop 降级"),
    "novel-scan": TemplateRef("novel-scan", 0,
        "你是一名市场分析师，需要分析网络小说榜单趋势。",
        "{scan_data}", 0.3, 4000, "novel-scan 降级"),
    "novel-analyze": TemplateRef("novel-analyze", 0,
        "你是一名文学评论家，需要深度分析爆款小说的成功要素。",
        "{analysis_target}", 0.3, 4000, "novel-analyze 降级"),
    "novel-short-write": TemplateRef("novel-short-write", 0,
        "你是一名短篇小说作家，需要创作完整的短篇故事。",
        "{prompt}", 0.9, 16384, "novel-short-write 降级"),
}


async def _load_from_db(db: AsyncSession, name: str) -> TemplateRef | None:
    """从 DB 加载单一命名的活跃模板"""
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
    return None


async def load_template(db: AsyncSession, name: str) -> TemplateRef:
    """加载指定 Prompt 的活跃版本（DB 优先 → 硬编码降级）"""
    db_copy = await _load_from_db(db, name)
    if db_copy:
        return db_copy
    fallback = _HARDCODED_FALLBACKS.get(name)
    if fallback:
        return fallback
    return TemplateRef(name, 0, "", "", 0.9, 4000, "empty fallback")


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
        loaded = {}
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


async def invalidate_cache(name: str) -> None:
    """通知缓存失效（无状态 registry 无需操作，预留接口）"""
    pass
