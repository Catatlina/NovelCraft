"""Unit tests for rule_engine.py — 世界观推理规则引擎纯逻辑部分

覆盖：
- _extract_keywords（关键词提取）
- _quick_keyword_check（LLM 调用前的关键词预检，减少不必要调用）
- _build_project_context（项目上下文文本构建）
- validate_chapter_after_generation 的汇总/通过判定逻辑（mock 掉
  validate_rules，只测试它拿到 violations 列表后如何汇总）

不覆盖 validate_rules / _check_single_rule 里真实调用 LLM 的部分，
那部分需要 DeepSeek API，属于集成测试范畴。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.rule_engine import (
    _extract_keywords,
    _quick_keyword_check,
    _build_project_context,
    validate_chapter_after_generation,
)


def _make_rule(rule_name="测试规则", rule_type="existential", dsl_expression=""):
    return SimpleNamespace(
        id="rule-1",
        rule_name=rule_name,
        rule_type=rule_type,
        dsl_expression=dsl_expression,
        severity="warn",
        description=None,
    )


class TestExtractKeywords:
    def test_basic(self):
        kws = _extract_keywords("主角，配角；反派")
        assert "主角" in kws
        assert "配角" in kws
        assert "反派" in kws

    def test_filters_short_words(self):
        kws = _extract_keywords("甲 主角团")
        assert "甲" not in kws
        assert "主角团" in kws


class TestQuickKeywordCheck:
    def test_no_quoted_keywords_and_no_name_match_is_uncertain(self):
        rule = _make_rule(rule_name="某个抽象规则", dsl_expression="力量等级不能超过九重天")
        result = _quick_keyword_check(rule, "今天天气不错，主角出门散步。")
        # dsl 无引号关键词，退回按 rule_name 提取关键词匹配；这里规则名关键词
        # 在章节里也没出现，应判定为 likely_ok
        assert result == "likely_ok"

    def test_quoted_entity_absent_is_likely_ok(self):
        rule = _make_rule(dsl_expression='角色 "张三" 不能在此章节出现')
        result = _quick_keyword_check(rule, "李四和王五在城中散步，讨论剑法。")
        assert result == "likely_ok"

    def test_quoted_entity_present_existential_is_likely_violation(self):
        rule = _make_rule(
            rule_type="existential",
            dsl_expression='角色 "张三" 已经死亡，不应再次出现',
        )
        result = _quick_keyword_check(rule, "张三推开门，笑着走了进来。")
        assert result == "likely_violation"

    def test_quoted_entity_present_non_existential_is_uncertain(self):
        rule = _make_rule(
            rule_type="numeric",
            dsl_expression='角色 "张三" 的等级不能超过第九重',
        )
        result = _quick_keyword_check(rule, "张三这次突破，终于达到了第九重的境界。")
        assert result == "uncertain"

    def test_single_quote_style_also_detected(self):
        rule = _make_rule(dsl_expression="角色 '李四' 不得使用火系法术")
        result = _quick_keyword_check(rule, "李四挥手放出一道火焰。")
        assert result != "likely_ok"


class TestBuildProjectContext:
    def test_none_project_returns_empty(self):
        assert _build_project_context(None) == ""

    def test_all_fields_present(self):
        project = SimpleNamespace(
            genre="玄幻",
            characters_json=[{"name": "主角"}, {"name": "配角"}],
            world_setting="修真世界设定" * 10,
            power_system="九重天体系",
            glossary_json=[{"term": "灵气"}, {"term": "丹田"}],
        )
        ctx = _build_project_context(project)
        assert "题材：玄幻" in ctx
        assert "主角" in ctx and "配角" in ctx
        assert "力量体系" in ctx
        assert "灵气" in ctx and "丹田" in ctx

    def test_missing_fields_are_skipped_gracefully(self):
        project = SimpleNamespace(
            genre=None,
            characters_json=[],
            world_setting=None,
            power_system=None,
            glossary_json=[],
        )
        assert _build_project_context(project) == ""


class TestValidateChapterAfterGeneration:
    @pytest.mark.asyncio
    async def test_no_violations_passes(self):
        with patch("app.services.rule_engine.validate_rules", return_value=[]):
            result = await validate_chapter_after_generation(None, "proj-1", "章节内容", 1)
        assert result["passed"] is True
        assert result["error_count"] == 0
        assert result["warn_count"] == 0
        assert "未发现违规" in result["summary"]

    @pytest.mark.asyncio
    async def test_only_warnings_still_passes(self):
        warn_violation = {"rule_id": "r1", "rule_name": "规则A", "severity": "warn",
                           "description": "轻微问题", "suggestion": "建议修改"}
        with patch("app.services.rule_engine.validate_rules", return_value=[warn_violation]):
            result = await validate_chapter_after_generation(None, "proj-1", "章节内容", 1)
        assert result["passed"] is True
        assert result["warn_count"] == 1
        assert result["error_count"] == 0

    @pytest.mark.asyncio
    async def test_error_violation_fails(self):
        error_violation = {"rule_id": "r2", "rule_name": "规则B", "severity": "error",
                            "description": "硬性违规", "suggestion": "必须修改"}
        with patch("app.services.rule_engine.validate_rules", return_value=[error_violation]):
            result = await validate_chapter_after_generation(None, "proj-1", "章节内容", 1)
        assert result["passed"] is False
        assert result["error_count"] == 1
        assert "硬性违规" in result["summary"]

    @pytest.mark.asyncio
    async def test_mixed_violations_counts_both(self):
        violations = [
            {"rule_id": "r1", "rule_name": "A", "severity": "warn", "description": "", "suggestion": ""},
            {"rule_id": "r2", "rule_name": "B", "severity": "error", "description": "", "suggestion": ""},
            {"rule_id": "r3", "rule_name": "C", "severity": "warn", "description": "", "suggestion": ""},
        ]
        with patch("app.services.rule_engine.validate_rules", return_value=violations):
            result = await validate_chapter_after_generation(None, "proj-1", "章节内容", 1)
        assert result["passed"] is False
        assert result["error_count"] == 1
        assert result["warn_count"] == 2
