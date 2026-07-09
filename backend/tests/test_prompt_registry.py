"""回归测试：prompt_registry DB 加载 + 降级 + 009 幂等"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_get_prompt_registry_importable():
    """P0-1 回归防护：get_prompt_registry 可正常 import"""
    from app.services.prompt_registry import get_prompt_registry
    assert callable(get_prompt_registry)


def test_hardcoded_fallbacks_exist():
    """P0-3 回归：硬编码降级包含 7 个引擎且 novel-write 含 JSON 契约"""
    from app.services.prompt_registry import _HARDCODED_FALLBACKS
    assert "novel-write" in _HARDCODED_FALLBACKS
    f = _HARDCODED_FALLBACKS["novel-write"]
    assert "JSON" in f.system_prompt and "title" in f.system_prompt
    for name in ("novel-review", "novel-translate", "novel-deslop",
                 "novel-scan", "novel-analyze", "novel-short-write"):
        assert name in _HARDCODED_FALLBACKS, f"missing {name}"


def test_registry_get_or_default():
    """PromptRegistry.get() / get_or_default 接口完整"""
    from app.services.prompt_registry import PromptRegistry
    r = PromptRegistry()
    assert r.get("novel-write") is not None
    assert r.get_or_default("nonexistent").name == "nonexistent"


def test_context_truncate_noop():
    """_truncate_context_layer 不截断短文本"""
    from app.services.context_hub import _truncate_context_layer
    assert _truncate_context_layer("hello", 100, "test") == "hello"


def test_context_truncate_long():
    """_truncate_context_layer 截断超长文本"""
    from app.services.context_hub import _truncate_context_layer
    long_text = "x" * 20000
    result = _truncate_context_layer(long_text, 8000, "layer_1")
    assert len(result) == 8000


def test_009_migration_sql_valid():
    """009 迁移文件存在且含 UPDATE"""
    path = os.path.join(os.path.dirname(__file__), "..", "migrations", "009_fix_seed_prompts.sql")
    assert os.path.exists(path), "009 migration missing"
    with open(path) as f:
        sql = f.read()
    assert "UPDATE prompt_templates SET" in sql
    assert "novel-write" in sql and "novel-review" in sql
    assert "WHERE" in sql and "AND" in sql
