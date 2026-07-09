"""Unit tests for scanner.py — 13(实际14)平台扫榜数据采集器

只覆盖不需要真实网络请求的纯逻辑：
- _is_valid_title 噪声过滤规则
- get_platform_list / PLATFORM_SOURCES 配置完整性

不覆盖 _scrape_platform / scan_all 的真实爬虫请求，那部分依赖外部网站
结构，容易因目标站点改版而失效，且需要网络访问，留给人工/集成测试。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio

from app.services.scanner import (
    _is_valid_title,
    get_platform_list,
    PLATFORM_SOURCES,
    NOISE_TEXTS,
)


class TestIsValidTitle:
    def test_valid_chinese_title(self):
        assert _is_valid_title("大奉打更人") is True
        assert _is_valid_title("我在修仙界搞房产") is True

    def test_valid_english_title(self):
        assert _is_valid_title("Shadow Slave") is True
        assert _is_valid_title("Mother of Learning") is True

    def test_too_short_rejected(self):
        assert _is_valid_title("") is False
        assert _is_valid_title("书") is False  # 单字，长度 < 2

    def test_too_long_rejected(self):
        assert _is_valid_title("书" * 51) is False

    def test_exactly_boundary_lengths_accepted(self):
        assert _is_valid_title("书名") is True  # 长度 2，下边界
        assert _is_valid_title("书" * 50) is True  # 长度 50，上边界

    def test_noise_text_rejected(self):
        for noise in ["首页", "登录", "更多", "Next", "Login", "Subscribe"]:
            assert _is_valid_title(noise) is False, f"{noise} 应被识别为噪声文本"

    def test_pure_numeric_rejected(self):
        assert _is_valid_title("12345") is False
        assert _is_valid_title("1,234") is False

    def test_pure_punctuation_rejected(self):
        assert _is_valid_title("……——") is False
        assert _is_valid_title("！？!?") is False

    def test_short_english_word_rejected(self):
        # 1-3 个字母的短英文单词通常是 UI 残留（如 "Top"、"No"），不是书名
        assert _is_valid_title("Top") is False
        assert _is_valid_title("No") is False

    def test_longer_english_word_accepted(self):
        # 4 个字母以上不再被短词规则拦截
        assert _is_valid_title("Slave") is True

    def test_whitespace_is_stripped_before_check(self):
        assert _is_valid_title("  大奉打更人  ") is True
        assert _is_valid_title("   ") is False


class TestPlatformConfig:
    def test_all_sources_have_required_fields(self):
        for name, cfg in PLATFORM_SOURCES.items():
            assert "url" in cfg, f"{name} 缺少 url"
            assert "selectors" in cfg and cfg["selectors"], f"{name} 缺少 selectors"
            assert cfg.get("region") in ("国内", "海外"), f"{name} region 字段异常"

    def test_get_platform_list_matches_sources(self):
        platforms = get_platform_list()
        assert len(platforms) == len(PLATFORM_SOURCES)
        names = {p["name"] for p in platforms}
        assert names == set(PLATFORM_SOURCES.keys())

    def test_platform_count_naming_consistency(self):
        """回归提示：模块文档字符串/历史命名里称"13平台"，但实际配置为 14 个。
        这不是功能性 bug，只是命名与实际数量不一致，此测试用于在数量再变化时
        提醒维护者同步更新文档，而不是让人在别处发现这个偏差。"""
        assert len(PLATFORM_SOURCES) == 14
