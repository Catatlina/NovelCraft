"""Unit tests for prompts.py — 7 Prompt engines and JSON parsing"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.prompts import (
    _clean_json_response,
    parse_novel_write_response,
    parse_novel_analyze_response,
    parse_novel_scan_response,
    parse_novel_review_response,
    parse_novel_deslop_response,
    parse_novel_short_write_response,
    build_novel_write_messages,
    build_novel_deslop_messages,
    build_novel_review_messages,
    build_novel_short_write_messages,
    build_novel_analyze_messages,
    build_novel_scan_messages,
)


class TestCleanJsonResponse:
    def test_plain_json(self):
        assert _clean_json_response('{"a":1}') == {"a": 1}

    def test_markdown_code_block(self):
        assert _clean_json_response('```json\n{"a":1}\n```') == {"a": 1}

    def test_markdown_no_lang(self):
        assert _clean_json_response('```\n{"a":1}\n```') == {"a": 1}

    def test_invalid_json_returns_empty(self):
        assert _clean_json_response("not json") == {}

    def test_empty_string(self):
        assert _clean_json_response("") == {}

    def test_nested_objects(self):
        d = _clean_json_response('{"a":{"b":[1,2,3]},"c":"hello"}')
        assert d["a"]["b"] == [1, 2, 3]


class TestParseNovelWriteResponse:
    def test_valid(self):
        d = parse_novel_write_response(
            '{"title":"第1章","content":"正文内容","summary":"摘要","new_foreshadows":[],"resolved_foreshadow_ids":[]}'
        )
        assert d["title"] == "第1章"
        assert d["content"] == "正文内容"

    def test_missing_field_raises(self):
        import pytest
        with pytest.raises(ValueError, match="必要字段"):
            parse_novel_write_response('{"title":"x"}')

    def test_invalid_json_raises(self):
        import pytest
        with pytest.raises(ValueError, match="合法JSON"):
            parse_novel_write_response("not json at all")

    def test_defaults_added(self):
        d = parse_novel_write_response('{"title":"t","content":"c","summary":"s"}')
        assert d["new_foreshadows"] == []
        assert d["resolved_foreshadow_ids"] == []

    def test_markdown_wrapped(self):
        d = parse_novel_write_response(
            '```json\n{"title":"第1章","content":"正文","summary":"摘要"}\n```'
        )
        assert d["title"] == "第1章"


class TestParseOtherPrompts:
    def test_analyze(self):
        d = parse_novel_analyze_response('{"hype_score":85}')
        assert d["hype_score"] == 85
        assert "learnable_elements" in d

    def test_review(self):
        d = parse_novel_review_response('{"overall_score":80,"dimensions":{},"summary":"good"}')
        assert d["overall_score"] == 80

    def test_deslop(self):
        d = parse_novel_deslop_response('{"result":"改写后文本"}')
        assert d["result"] == "改写后文本"

    def test_scan_empty(self):
        d = parse_novel_scan_response("not json")
        assert d == []

    def test_short_write(self):
        d = parse_novel_short_write_response('{"sections":[]}')
        assert d["sections"] == []


class TestBuildMessages:
    def test_write_messages(self):
        ctx = {
            "meta": {"title": "测试", "genre": "玄幻", "target_chapter_num": 3},
            "layer_1_overall_outline": "大纲",
            "layer_2_current_arc_outline": "弧线",
            "layer_3_characters": [],
            "layer_4_world_setting_excerpt": "世界观",
            "layer_5_open_foreshadows": [],
            "layer_6_recent_chapter_summaries": [],
            "layer_7_anti_crash_reminders": ["不要OOC"],
        }
        msgs = build_novel_write_messages(ctx)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert "网络小说写手" in msgs[0]["content"]

    def test_deslop_modes(self):
        for mode in ("polish", "deslop", "rewrite"):
            msgs = build_novel_deslop_messages("原文内容", mode=mode)
            assert len(msgs) == 2

    def test_review_7_dims(self):
        msgs = build_novel_review_messages("正文", "大纲", "前文")
        dims = ["一致性", "AI味检测", "节奏", "人物OOC", "爽点密度", "对话质量", "结尾钩子"]
        for d in dims:
            assert d in msgs[0]["content"], f"Missing dimension: {d}"

    def test_analyze_kwargs(self):
        msgs = build_novel_analyze_messages(title="星辰之主", chapters_text="第一章...", genre="玄幻")
        assert len(msgs) == 2
        assert "星辰之主" in msgs[1]["content"]

    def test_scan_kwargs(self):
        msgs = build_novel_scan_messages(platforms=["起点", "番茄"], raw_data="分析")
        assert len(msgs) == 2
        assert "起点" in msgs[1]["content"]
