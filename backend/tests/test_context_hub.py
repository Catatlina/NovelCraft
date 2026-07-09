"""Unit tests for context_hub.py — Context Hub 纯逻辑辅助函数

只覆盖不需要数据库连接的纯函数：
- _extract_keywords / _split_text_into_chunks（pgvector 降级链路的关键部分）
- _fallback_world_setting / _build_anti_crash_reminders / _extract_current_arc

不覆盖 assemble_context / _retrieve_relevant_world_setting / index_world_setting，
这几个需要真实数据库 session，属于集成测试范畴。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from app.services.context_hub import (
    _extract_keywords,
    _split_text_into_chunks,
    _fallback_world_setting,
    _build_anti_crash_reminders,
    _extract_current_arc,
)


class TestExtractKeywords:
    def test_basic_split(self):
        kws = _extract_keywords("玄幻，热血；逆袭 修仙")
        assert "玄幻" in kws
        assert "热血" in kws
        assert "逆袭" in kws
        assert "修仙" in kws

    def test_dedup(self):
        kws = _extract_keywords("玄幻，玄幻，玄幻")
        assert kws.count("玄幻") == 1

    def test_filters_single_char(self):
        # 长度 < 2 的词应被过滤（如单个标点残留或单字）
        kws = _extract_keywords("修 玄幻")
        assert "修" not in kws
        assert "玄幻" in kws

    def test_max_ten_keywords(self):
        text = "，".join(f"关键词{i}" for i in range(20))
        kws = _extract_keywords(text)
        assert len(kws) <= 10

    def test_empty_text(self):
        assert _extract_keywords("") == []

    def test_mixed_delimiters(self):
        kws = _extract_keywords("主角穿越!世界观设定?伏笔回收。")
        assert "主角穿越" in kws
        assert "世界观设定" in kws
        assert "伏笔回收" in kws


class TestSplitTextIntoChunks:
    def test_short_text_single_chunk(self):
        text = "这是一段很短的文本。"
        chunks = _split_text_into_chunks(text, chunk_size=512)
        assert chunks == [text]

    def test_long_text_splits_at_sentence_boundary(self):
        # 构造一段刚好在 chunk_size 附近有句号的长文本
        sentence = "这是一句用于测试切分逻辑的示例句子。"
        text = sentence * 30  # 远超过默认 chunk_size
        chunks = _split_text_into_chunks(text, chunk_size=100)
        assert len(chunks) > 1
        # 每个 chunk 应该在句号处结尾（除了可能的最后一块）或至少不超过很多余量
        for c in chunks[:-1]:
            assert c.endswith("。")

    def test_no_data_loss_across_chunks(self):
        """关键回归点：分块前后拼接内容应完整无缺失、无重复（对应历史上的
        批量生成数据丢失 bug 的相邻风险点——分块逻辑本身必须不丢字）。"""
        sentence = "世界观设定：这个世界的力量体系分为九个等级。"
        text = sentence * 50
        chunks = _split_text_into_chunks(text, chunk_size=200)
        rejoined = "".join(chunks)
        # strip 逐块进行，拼接后与原文相比只应减少块间被 strip 掉的空白，
        # 不应该丢失任何非空白字符
        original_no_space = "".join(text.split())
        rejoined_no_space = "".join(rejoined.split())
        assert rejoined_no_space == original_no_space

    def test_falls_back_to_hard_cut_when_no_delimiter(self):
        # 没有任何分隔符的超长文本，应该硬切分而不报错或死循环
        text = "无标点无换行的超长连续文本" * 100
        chunks = _split_text_into_chunks(text, chunk_size=50)
        assert len(chunks) > 1
        assert all(chunks)  # 不应产生空块


class TestFallbackWorldSetting:
    def test_all_fields_present(self):
        project = SimpleNamespace(
            power_system="九重天力量体系",
            world_rules="时间只能向前",
            world_setting="修真世界",
        )
        result = _fallback_world_setting(project)
        assert "力量体系" in result
        assert "世界规则" in result
        assert "世界设定" in result
        assert "九重天力量体系" in result

    def test_all_fields_empty(self):
        project = SimpleNamespace(power_system=None, world_rules=None, world_setting=None)
        result = _fallback_world_setting(project)
        assert result == "（知识库暂无内容）"

    def test_long_field_gets_truncated(self):
        long_text = "设" * 1000
        project = SimpleNamespace(power_system=long_text, world_rules=None, world_setting=None)
        result = _fallback_world_setting(project)
        assert "已截断" in result
        assert len(result) < len(long_text) + 100


class TestBuildAntiCrashReminders:
    def test_base_reminders_always_present(self):
        project = SimpleNamespace(characters_json=[])
        reminders = _build_anti_crash_reminders(project, [])
        assert any("OOC" in r for r in reminders)
        assert any("时间线" in r for r in reminders)

    def test_open_foreshadows_adds_reminder(self):
        project = SimpleNamespace(characters_json=[])
        reminders = _build_anti_crash_reminders(project, [{"id": "1"}, {"id": "2"}])
        assert any("2 个未回收伏笔" in r for r in reminders)

    def test_characters_present_adds_reminder(self):
        project = SimpleNamespace(characters_json=[{"name": "主角"}])
        reminders = _build_anti_crash_reminders(project, [])
        assert any("已死亡或已离场角色" in r for r in reminders)


class TestExtractCurrentArc:
    def test_empty_outline(self):
        assert _extract_current_arc(None, 1) == "（总纲为空）"
        assert _extract_current_arc("", 1) == "（总纲为空）"

    def test_truncates_to_1500_chars(self):
        outline = "总纲内容" * 1000
        result = _extract_current_arc(outline, 5)
        assert len(result) == 1500
