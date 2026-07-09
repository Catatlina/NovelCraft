"""
推理规则引擎 — 半 LLM 实现（不实现完整 DSL 解释器）
支持 5 种规则类型：numeric / temporal / relational / existential / causal

设计思路：
    规则存储为自然语言 DSL 表达式（dsl_expression 字段），校验时逐条用 LLM
    零样本判断章节是否违反规则。这种方式比完整 DSL 解释器更灵活，能处理
    复杂的语义判断，代价是每次校验需要调用 LLM。

使用方式：
    violations = await validate_rules(db, project_id, chapter_text, chapter_num)
"""
from __future__ import annotations

import json
import re
import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NovelChapter, NovelProject, ProjectWorldRule


async def validate_rules(
    db: AsyncSession,
    project_id: _uuid.UUID,
    chapter_text: str,
    chapter_num: int,
) -> list[dict]:
    """
    读取项目所有 active 规则，用 LLM 零样本判断是否违反。
    返回违规列表 [{"rule_id", "rule_name", "severity", "description", "suggestion"}]

    Args:
        db: 数据库 session
        project_id: 项目 ID
        chapter_text: 章节正文
        chapter_num: 章节号

    Returns:
        违规列表，每条包含 rule_id, rule_name, severity, description, suggestion
    """
    # 1. 读取项目所有 active 规则
    result = await db.execute(
        select(ProjectWorldRule).where(
            ProjectWorldRule.project_id == project_id,
            ProjectWorldRule.is_active == True,
        )
    )
    rules = result.scalars().all()

    if not rules:
        return []

    # 2. 获取项目上下文（人物/世界观/术语表）
    project = await db.get(NovelProject, project_id)
    project_context = _build_project_context(project)

    # 3. 逐条校验规则
    violations: list[dict] = []
    for rule in rules:
        violation = await _check_single_rule(rule, chapter_text, chapter_num, project_context)
        if violation:
            violations.append(violation)

    return violations


async def _check_single_rule(
    rule: ProjectWorldRule,
    chapter_text: str,
    chapter_num: int,
    project_context: str,
) -> dict | None:
    """用 LLM 零样本判断单条规则是否被违反。

    Args:
        rule: 规则对象
        chapter_text: 章节正文
        chapter_num: 章节号
        project_context: 项目上下文描述

    Returns:
        如果违规，返回违规 dict；否则返回 None
    """
    from app.services.deepseek_client import chat_completion, DeepSeekError

    # 先做快速关键词预检，减少不必要的 LLM 调用
    quick_hint = _quick_keyword_check(rule, chapter_text)
    if quick_hint == "likely_ok":
        return None

    rule_type_descriptions = {
        "numeric": "数值类规则：涉及数字约束，如年龄/数量/等级/时间间隔等",
        "temporal": "时序类规则：涉及时间顺序、因果关系的前后约束",
        "relational": "关系类规则：涉及人物关系、地位、从属关系",
        "existential": "存在性规则：涉及某个事物/人物/能力是否存在",
        "causal": "因果类规则：涉及因果链条、触发条件",
    }

    rule_type_desc = rule_type_descriptions.get(rule.rule_type, "未知类型规则")

    system_prompt = (
        "你是一名专业小说编辑，负责检查章节内容是否违反了既定的世界观规则。"
        "请仔细阅读规则描述和章节内容，判断是否存在违规。"
        "注意：只报告明确的违规，不要对创作选择做主观评价。"
        "输出必须是合法 JSON，不要输出任何 JSON 之外的文字，格式如下：\n"
        '{"violated": true/false, "confidence": 0.0-1.0, '
        '"description": "违规描述（如果违规）", '
        '"suggestion": "修改建议（如果违规）"}'
    )

    user_prompt = (
        "【规则信息】\n"
        "- 名称：" + str(rule.rule_name) + "\n"
        "- 类型：" + str(rule_type_desc) + "\n"
        "- 严重性：" + str(rule.severity) + "（error=硬性违规, warn=建议性违规）\n"
        "- 描述：" + str(rule.description or '无额外描述') + "\n"
        "- DSL 表达式：" + str(rule.dsl_expression) + "\n"
        "\n"
        "【项目背景】\n"
        + str(project_context[:1000]) + "\n"
        "\n"
        "【章节 #" + str(chapter_num) + " 内容】\n"
        + str(chapter_text[:3000]) + "\n"
        "\n"
        "请判断本章节内容是否违反了上述规则。按 system prompt 约定的 JSON 格式输出。"
    )

    try:
        result = await chat_completion(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=500,
            temperature=0.1,
        )
        raw = result["content"].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)
    except (DeepSeekError, json.JSONDecodeError) as e:
        # LLM 不可用时，退回到纯关键词检查
        if quick_hint == "likely_violation":
            return {
                "rule_id": str(rule.id),
                "rule_name": rule.rule_name,
                "severity": rule.severity,
                "description": f"关键词预检怀疑违反规则：{rule.dsl_expression[:200]}",
                "suggestion": f"请人工核实章节内容是否违反规则「{rule.rule_name}」（LLM 校验服务不可用：{str(e)[:100]}）",
            }
        return None

    if data.get("violated", False):
        return {
            "rule_id": str(rule.id),
            "rule_name": rule.rule_name,
            "severity": rule.severity,
            "description": data.get("description", f"违反规则：{rule.rule_name}"),
            "suggestion": data.get("suggestion", "请根据规则修改相关内容"),
        }

    return None


def _quick_keyword_check(rule: ProjectWorldRule, chapter_text: str) -> str:
    """快速关键词预检，减少不必要的 LLM 调用。

    在发送给 LLM 前，先检查 dsl_expression 中的关键实体是否出现在章节文本中。
    如果完全无关，直接返回 likely_ok 跳过 LLM 调用。

    Returns:
        "likely_ok" | "likely_violation" | "uncertain"
    """
    dsl = rule.dsl_expression

    # 提取 DSL 中的引号内关键词（通常是实体名/角色名/特定术语）
    quoted = re.findall(r'["\u201c]([^"\u201d]+)["\u201d]', dsl)
    quoted += re.findall(r"'([^']+)'", dsl)

    # 如果没有引号关键词，无法做快速预检
    if not quoted:
        # 对于 existential 类型规则，尝试检查规则名中的关键词
        name_keywords = _extract_keywords(rule.rule_name)
        if name_keywords:
            has_match = any(
                kw in chapter_text for kw in name_keywords if len(kw) >= 2
            )
            return "uncertain" if has_match else "likely_ok"
        return "uncertain"

    # 检查章节中是否出现任何关键实体
    has_any_match = any(q in chapter_text for q in quoted if len(q) >= 2)

    if not has_any_match:
        return "likely_ok"

    # 对于 existential 规则，如果实体出现，大概率需要检查
    if rule.rule_type == "existential":
        return "likely_violation"

    return "uncertain"


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取中文关键词"""
    import re as _re

    words = _re.split(r"[，,。；;！!？?\s]+", text)
    return [w.strip() for w in words if len(w.strip()) >= 2]


def _build_project_context(project: NovelProject | None) -> str:
    """从项目对象构建上下文描述文本，供规则校验使用"""
    if not project:
        return ""

    parts: list[str] = []
    if project.genre:
        parts.append(f"题材：{project.genre}")
    if project.characters_json:
        char_names = [
            c.get("name", "") for c in project.characters_json if isinstance(c, dict)
        ]
        if char_names:
            parts.append(f"已登场角色：{', '.join(char_names[:20])}")
    if project.world_setting:
        parts.append(f"世界设定：{project.world_setting[:500]}")
    if project.power_system:
        parts.append(f"力量体系：{project.power_system[:300]}")
    if project.glossary_json:
        terms = [
            f"{t.get('term', '')}" for t in project.glossary_json if isinstance(t, dict)
        ]
        if terms:
            parts.append(f"术语表：{', '.join(terms[:20])}")

    return "\n".join(parts)


async def validate_chapter_after_generation(
    db: AsyncSession,
    project_id: _uuid.UUID,
    chapter_text: str,
    chapter_num: int,
) -> dict:
    """生成后自动校验：在章节生成完成后调用，返回校验结果。

    Args:
        db: 数据库 session
        project_id: 项目 ID
        chapter_text: 生成的章节正文
        chapter_num: 章节号

    Returns:
        {"passed": bool, "violations": [...], "summary": str}
    """
    violations = await validate_rules(db, project_id, chapter_text, chapter_num)

    error_violations = [v for v in violations if v.get("severity") == "error"]
    warn_violations = [v for v in violations if v.get("severity") == "warn"]

    passed = len(error_violations) == 0

    if not violations:
        summary = "所有规则校验通过，未发现违规。"
    elif passed:
        summary = (
            f"发现 {len(warn_violations)} 个建议性警告，无硬性违规。"
        )
    else:
        summary = (
            f"发现 {len(error_violations)} 个硬性违规、"
            f"{len(warn_violations)} 个建议性警告。"
        )

    return {
        "passed": passed,
        "violations": violations,
        "error_count": len(error_violations),
        "warn_count": len(warn_violations),
        "summary": summary,
    }
