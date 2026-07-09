"""
ORM 模型，字段与 schema_v8.sql 一一对应。
用 SQLAlchemy 2.0 风格（Mapped/mapped_column）。
pgvector 类型用 pgvector.sqlalchemy.Vector。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# pgvector: installed and active
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


# ============================================================
# v7 原有模型
# ============================================================


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # relationships (v8)
    platform_accounts: Mapped[list["PlatformAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ai_settings: Mapped["UserAISettings | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class NovelProject(Base):
    __tablename__ = "novel_projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="idea")
    state_history: Mapped[list] = mapped_column(JSONB, default=list)

    overall_outline: Mapped[str | None] = mapped_column(Text)
    chapter_tree: Mapped[list] = mapped_column(JSONB, default=list)
    glossary_json: Mapped[list] = mapped_column(JSONB, default=list)
    power_system: Mapped[str | None] = mapped_column(Text)
    world_rules: Mapped[str | None] = mapped_column(Text)
    characters_json: Mapped[list] = mapped_column(JSONB, default=list)
    world_setting: Mapped[str | None] = mapped_column(Text)

    total_chapters: Mapped[int] = mapped_column(default=0)
    total_words: Mapped[int] = mapped_column(default=0)

    token_budget: Mapped[int | None]
    token_used: Mapped[int] = mapped_column(default=0)
    publish_accounts_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # relationships
    chapters: Mapped[list["NovelChapter"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    foreshadows: Mapped[list["ForeshadowPool"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    # v8 new
    world_setting_embeddings: Mapped[list["WorldSettingEmbedding"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    world_rules_rel: Mapped[list["ProjectWorldRule"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    publish_executions: Mapped[list["PublishExecution"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    ab_tests: Mapped[list["ABTest"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    prompt_optimizations: Mapped[list["PromptOptimizationLog"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    analytics_events: Mapped[list["AnalyticsEvent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def as_context_dict(self) -> dict:
        """供 Context Hub 消费的字段视图"""
        return {
            "title": self.title,
            "genre": self.genre,
            "overall_outline": self.overall_outline,
            "power_system": self.power_system,
            "world_rules": self.world_rules,
            "world_setting": self.world_setting,
            "characters_json": self.characters_json,
            "glossary_json": self.glossary_json,
            "total_chapters": self.total_chapters,
        }


class NovelChapter(Base):
    __tablename__ = "novel_chapters"
    __table_args__ = (UniqueConstraint("project_id", "chapter_num"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    chapter_num: Mapped[int]
    title: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(default=0)
    outline: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    review_score: Mapped[dict] = mapped_column(JSONB, default=dict)
    review_report: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(Text, default="draft")
    version_history: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="chapters")
    # v8 new
    chapter_versions: Mapped[list["ChapterVersion"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )
    ab_tests: Mapped[list["ABTest"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")


class ForeshadowPool(Base):
    __tablename__ = "foreshadow_pool"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    planted_chapter: Mapped[int]
    expected_payoff_range: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="planted")  # planted/paid_off/overdue
    payoff_chapter: Mapped[int | None]
    payoff_quality_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="foreshadows")


class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    knowledge_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QualityReview(Base):
    __tablename__ = "quality_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_chapters.id", ondelete="CASCADE"))
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Numeric)
    issues_json: Mapped[list] = mapped_column(JSONB, default=list)
    rewrite_applied: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class GenerationTask(Base):
    __tablename__ = "generation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="queued")
    request_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[dict] = mapped_column(MutableDict.as_mutable(JSONB), default=dict)
    error_log: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_chapters.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")
    published_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None]


class FeedbackSignal(Base):
    __tablename__ = "feedback_signals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_chapters.id", ondelete="CASCADE"))
    platform: Mapped[str | None] = mapped_column(Text)
    read_count: Mapped[int | None]
    retention_rate: Mapped[float | None] = mapped_column(Numeric)
    collected_at: Mapped[datetime] = mapped_column(server_default=func.now())


# ============================================================
# v8 新增模型 (Phase 3-9)
# ============================================================


class WorldSettingEmbedding(Base):
    """Phase 3: 世界观知识 chunk + pgvector embedding 存储"""

    __tablename__ = "world_setting_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    extra: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="world_setting_embeddings")


class ProjectWorldRule(Base):
    """Phase 3: 世界观推理规则存储"""

    __tablename__ = "project_world_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    rule_name: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # numeric | temporal | relational | existential | causal
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dsl_expression: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, default="warn")  # error | warn
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="world_rules_rel")


class UserAISettings(Base):
    """用户级 AI 配置：服务端加密保存 API Key，前端只显示是否已配置。"""

    __tablename__ = "user_ai_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_deepseek_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    deepseek_model: Mapped[str | None] = mapped_column(Text, default="deepseek-chat")
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="ai_settings")


class PlatformAccount(Base):
    """Phase 4: 加密存储第三方平台凭证（OAuth Token / Cookie）"""

    __tablename__ = "platform_accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    auth_method: Mapped[str] = mapped_column(Text, nullable=False)  # oauth | cookie
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="active")
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="platform_accounts")


class PublishExecution(Base):
    """Phase 4: 发布执行记录 + 步骤日志 + 截图表"""

    __tablename__ = "publish_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    chapters: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(Text, default="pending")
    steps: Mapped[list] = mapped_column(JSONB, default=list)
    screenshots: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="publish_executions")


class QualityBenchmark(Base):
    """Phase 5: 各平台×品类的质量基准配置"""

    __tablename__ = "quality_benchmarks"
    __table_args__ = (UniqueConstraint("platform", "genre"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(Text, nullable=False)
    hype_density_threshold: Mapped[float] = mapped_column(Float, default=1.0)
    hook_min_score: Mapped[int] = mapped_column(Integer, default=7)
    dialogue_ratio_ideal: Mapped[float] = mapped_column(Float, default=0.35)
    extra: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ABTest(Base):
    """Phase 6: A/B 测试配置与结果"""

    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_chapters.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    variants: Mapped[list] = mapped_column(JSONB, nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="running")  # running | completed | cancelled
    winner_variant: Mapped[str | None] = mapped_column(Text, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    results: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)

    project: Mapped["NovelProject"] = relationship(back_populates="ab_tests")
    chapter: Mapped["NovelChapter"] = relationship(back_populates="ab_tests")


class PromptOptimizationLog(Base):
    """Phase 6: Prompt 参数调整记录"""

    __tablename__ = "prompt_optimization_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    prompt_name: Mapped[str] = mapped_column(Text, nullable=False)
    params_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    params_after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="prompt_optimizations")


class ChapterVersion(Base):
    """Phase 7: 章节版本快照（支持 diff 回溯）"""

    __tablename__ = "chapter_versions"
    __table_args__ = (UniqueConstraint("chapter_id", "version_num"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_chapters.id", ondelete="CASCADE"))
    version_num: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    diff_from_prev: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, default="ai")  # ai | user
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chapter: Mapped["NovelChapter"] = relationship(back_populates="chapter_versions")


class TokenLedger(Base):
    """AI Token 成本账本：预留、结算、释放，避免并发超预算。"""

    __tablename__ = "token_ledger"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)
    actual_tokens: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    unit_price_input: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit_price_output: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cost_cny: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="reserved")  # reserved | settled | released
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AnalyticsEvent(Base):
    """Phase 8: 埋点事件存储"""

    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["NovelProject"] = relationship(back_populates="analytics_events")


class PromptTemplate(Base):
    """Prompt 模板版本化存储 — 支持在线编辑/回滚/A/B测试 (P1-1)"""
    __tablename__ = "prompt_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.9)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4000)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
