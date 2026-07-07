"""
小说状态机 ❗①
requirements_v7.md 2.1 节：

    Idea → Outline → World → Writing → Review → Publish

职责：
1. 定义合法状态与合法迁移路径
2. 校验每次迁移的前置条件（例如 World 阶段没填知识库核心字段就不能进 Writing）
3. 拦截非法跳转（例如直接从 Idea 跳到 Writing）
4. 每次迁移都要求调用方传入 reason，写入 state_history，方便以后排查"流程为什么乱了"

这个模块被 api/projects.py 和 api/generation.py 调用，本身不碰数据库，
只做纯逻辑校验，方便单独写单元测试。
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ProjectState(str, Enum):
    IDEA = "idea"
    OUTLINE = "outline"
    WORLD = "world"
    WRITING = "writing"
    REVIEW = "review"
    PUBLISH = "publish"


# 合法迁移表：key=当前状态, value=允许迁移到的状态集合
# Review -> Writing 是"审查不达标打回重写"的合法回退路径
_ALLOWED_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.IDEA: {ProjectState.OUTLINE},
    ProjectState.OUTLINE: {ProjectState.WORLD},
    ProjectState.WORLD: {ProjectState.WRITING},
    ProjectState.WRITING: {ProjectState.REVIEW},
    ProjectState.REVIEW: {ProjectState.WRITING, ProjectState.PUBLISH},
    ProjectState.PUBLISH: set(),  # 终态；如需再版，走"新建下一卷项目"而非状态回退
}


class IllegalStateTransition(Exception):
    """非法状态跳转，API 层应捕获并返回 409"""


def validate_transition(current: str, target: str) -> ProjectState:
    """校验状态迁移是否合法，合法则返回目标状态枚举，非法则抛异常。"""
    try:
        cur = ProjectState(current)
        tgt = ProjectState(target)
    except ValueError as e:
        raise IllegalStateTransition(f"未知状态: {e}") from e

    if tgt not in _ALLOWED_TRANSITIONS.get(cur, set()):
        raise IllegalStateTransition(
            f"不允许从 {cur.value} 迁移到 {tgt.value}。"
            f"合法迁移: {[s.value for s in _ALLOWED_TRANSITIONS.get(cur, set())]}"
        )
    return tgt


def check_preconditions(target: ProjectState, project: dict) -> Optional[str]:
    """
    检查迁移到目标状态前，项目数据是否满足前置条件。
    project: 项目字段字典（overall_outline / world_setting / power_system / world_rules 等）
    返回 None 表示通过；返回字符串表示未通过的原因。
    """
    if target == ProjectState.WORLD:
        if not project.get("overall_outline"):
            return "总纲为空，无法进入 World 阶段：请先生成/填写全书总纲"

    if target == ProjectState.WRITING:
        # 知识库核心字段至少要有一项非空，防止空白世界观直接开写导致后续设定漂移
        core_fields = ["power_system", "world_rules", "world_setting"]
        if not any(project.get(f) for f in core_fields):
            return "知识库核心字段（力量体系/世界规则/世界设定）全部为空，无法进入 Writing 阶段"

    if target == ProjectState.PUBLISH:
        if not project.get("total_chapters"):
            return "全书暂无任何章节，无法进入 Publish 阶段"

    return None


def build_history_entry(from_state: str, to_state: str, reason: str) -> dict:
    return {
        "from": from_state,
        "to": to_state,
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }
