"""Unit tests for state_machine — requirement 2.1"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.state_machine import (
    ProjectState,
    IllegalStateTransition,
    validate_transition,
    check_preconditions,
    build_history_entry,
)


class TestValidateTransition:
    def test_idea_to_outline(self):
        assert validate_transition("idea", "outline") == ProjectState.OUTLINE

    def test_outline_to_world(self):
        assert validate_transition("outline", "world") == ProjectState.WORLD

    def test_world_to_writing(self):
        assert validate_transition("world", "writing") == ProjectState.WRITING

    def test_writing_to_review(self):
        assert validate_transition("writing", "review") == ProjectState.REVIEW

    def test_review_to_publish(self):
        assert validate_transition("review", "publish") == ProjectState.PUBLISH

    def test_review_back_to_writing(self):
        """审查不通过可打回重写"""
        assert validate_transition("review", "writing") == ProjectState.WRITING

    def test_idea_to_writing_blocked(self):
        with pytest.raises(IllegalStateTransition):
            validate_transition("idea", "writing")

    def test_world_to_publish_blocked(self):
        with pytest.raises(IllegalStateTransition):
            validate_transition("world", "publish")

    def test_publish_final_state(self):
        """Publish 是终态，不能迁移到任何状态"""
        with pytest.raises(IllegalStateTransition):
            validate_transition("publish", "idea")
        with pytest.raises(IllegalStateTransition):
            validate_transition("publish", "writing")

    def test_unknown_state(self):
        with pytest.raises(IllegalStateTransition):
            validate_transition("nonexistent", "writing")

    def test_enum_values(self):
        assert ProjectState.IDEA.value == "idea"
        assert ProjectState.PUBLISH.value == "publish"


class TestCheckPreconditions:
    def test_world_requires_outline(self):
        err = check_preconditions(ProjectState.WORLD, {"overall_outline": ""})
        assert err is not None
        assert "总纲" in err

    def test_world_passes_with_outline(self):
        err = check_preconditions(ProjectState.WORLD, {"overall_outline": "本书大纲..."})
        assert err is None

    def test_writing_requires_world_fields(self):
        err = check_preconditions(ProjectState.WRITING, {"power_system": "", "world_rules": "", "world_setting": ""})
        assert err is not None
        assert "知识库" in err

    def test_writing_passes_with_power_system(self):
        err = check_preconditions(ProjectState.WRITING, {"power_system": "修真九境"})
        assert err is None

    def test_writing_passes_with_world_setting(self):
        err = check_preconditions(ProjectState.WRITING, {"world_setting": "修仙大陆"})
        assert err is None

    def test_publish_requires_chapters(self):
        err = check_preconditions(ProjectState.PUBLISH, {"total_chapters": 0})
        assert err is not None
        err2 = check_preconditions(ProjectState.PUBLISH, {"total_chapters": 10})
        assert err2 is None

    def test_idea_no_precondition(self):
        assert check_preconditions(ProjectState.IDEA, {}) is None


class TestBuildHistoryEntry:
    def test_entry_structure(self):
        entry = build_history_entry("idea", "outline", "用户提交大纲")
        assert entry["from"] == "idea"
        assert entry["to"] == "outline"
        assert entry["reason"] == "用户提交大纲"
        assert "at" in entry
