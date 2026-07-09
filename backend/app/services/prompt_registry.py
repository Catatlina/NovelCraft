"""
Prompt 版本注册中心 — 管理 Prompt 版本, 记录优化历史, 驱动质量反馈闭环。

Phase 6: 将 PromptOptimizationLog 模型从"只记录"升级为"驱动选择"。
每次生成时记录使用的 Prompt 版本; 质量审查后若分差显著 (>2分),
自动记录优化建议到日志表, 供后续 A/B 测试使用。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PromptOptimizationLog


@dataclass
class PromptVersion:
    """单个 Prompt 的版本快照。"""
    name: str
    version: int = 1
    temperature: float = 0.9
    max_tokens: int = 4000
    description: str = ""
    quality_score: float | None = None  # 该版本的平均质量分


class PromptRegistry:
    """单例: 管理所有 Prompt 的版本注册、查询、优化记录。

    使用方式:
        registry = get_prompt_registry()
        registry.register("novel-write", version=1, temperature=0.9)
        v = registry.get("novel-write")  # → PromptVersion
        await registry.log_optimization(db, project_id, "novel-write", old, new, reason)
    """

    def __init__(self):
        self._prompts: dict[str, PromptVersion] = {}

    def register(
        self,
        name: str,
        *,
        version: int = 1,
        temperature: float = 0.9,
        max_tokens: int = 4000,
        description: str = "",
        quality_score: float | None = None,
    ) -> PromptVersion:
        pv = PromptVersion(
            name=name,
            version=version,
            temperature=temperature,
            max_tokens=max_tokens,
            description=description,
            quality_score=quality_score,
        )
        self._prompts[name] = pv
        return pv

    def get(self, name: str) -> PromptVersion | None:
        return self._prompts.get(name)

    def get_or_default(self, name: str) -> PromptVersion:
        return self._prompts.get(name) or PromptVersion(name=name)

    def list_all(self) -> dict[str, PromptVersion]:
        return dict(self._prompts)

    async def log_optimization(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        prompt_name: str,
        params_before: dict | None,
        params_after: dict | None,
        reason: str,
        quality_impact: float | None = None,
    ) -> PromptOptimizationLog:
        """写入优化日志并更新注册中心的质量分。"""
        entry = PromptOptimizationLog(
            id=uuid.uuid4(),
            project_id=project_id,
            prompt_name=prompt_name,
            params_before=params_before,
            params_after=params_after,
            reason=reason,
            quality_impact=quality_impact,
            applied_at=datetime.now(timezone.utc),
        )
        db.add(entry)

        # 更新注册中心内的质量分 (用于同进程内后续决策)
        if quality_impact is not None and prompt_name in self._prompts:
            pv = self._prompts[prompt_name]
            if pv.quality_score is None:
                pv.quality_score = quality_impact
            else:
                # 指数移动平均, 近期权重 0.3
                pv.quality_score = pv.quality_score * 0.7 + quality_impact * 0.3

        return entry

    async def log_auto_optimization(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        prompt_name: str,
        previous_score: float,
        new_score: float,
        context: str = "",
    ) -> PromptOptimizationLog | None:
        """质量审查后自动记录: 当分差 >= 2 时写入优化日志。

        返回创建的日志条目, 或 None (分差不足以记录)。
        """
        diff = new_score - previous_score
        if abs(diff) < 2.0:
            return None

        direction = "提升" if diff > 0 else "下降"
        reason = f"自动: 质量审查分从 {previous_score:.1f} {direction}到 {new_score:.1f} (Δ{diff:+.1f})"
        if context:
            reason += f" — {context[:200]}"

        return await self.log_optimization(
            db=db,
            project_id=project_id,
            prompt_name=prompt_name,
            params_before={"quality_score": previous_score},
            params_after={"quality_score": new_score},
            reason=reason,
            quality_impact=diff,
        )


# 进程级单例
_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
        # 注册默认 Prompt 版本
        _registry.register("novel-write", version=1, temperature=0.9, max_tokens=4000,
                           description="novel-write v1: 基础续写")
        _registry.register("novel-review", version=1, temperature=0.3, max_tokens=4000,
                           description="novel-review v1: 7维审查")
        _registry.register("novel-translate", version=1, temperature=0.3, max_tokens=16384,
                           description="novel-translate v1: 翻译出海")
        _registry.register("novel-deslop", version=1, temperature=0.7, max_tokens=4000,
                           description="novel-deslop v1: 去AI味")
        _registry.register("novel-scan", version=1, temperature=0.3, max_tokens=4000,
                           description="novel-scan v1: 扫榜分析")
        _registry.register("novel-analyze", version=1, temperature=0.3, max_tokens=4000,
                           description="novel-analyze v1: 拆文学习")
        _registry.register("novel-short-write", version=1, temperature=0.9, max_tokens=16384,
                           description="novel-short-write v1: 短篇生成")
    return _registry
