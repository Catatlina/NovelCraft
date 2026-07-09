"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ============================================================
# v7 原有 Schemas
# ============================================================


class ProjectCreate(BaseModel):
    title: str
    genre: str | None = None
    platform: str | None = None


class ProjectOutlineUpdate(BaseModel):
    overall_outline: str


class ProjectWorldUpdate(BaseModel):
    power_system: str | None = None
    world_rules: str | None = None
    world_setting: str | None = None
    glossary_json: list | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    genre: str | None
    platform: str | None
    status: str
    overall_outline: str | None
    total_chapters: int
    total_words: int
    created_at: datetime


class TransitionRequest(BaseModel):
    target_state: str
    reason: str


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    chapter_num: int
    title: str | None
    content: str | None
    word_count: int
    summary: str | None
    status: str
    # P0-1 fix: review_score 在 NovelChapter 模型里真实存在(P0-3 的质量审查
    # 闭环会往这里写数据)，但这里此前没有声明这个字段，导致审查分数
    # 存了但序列化时被丢弃，前端 QualityBall 组件永远显示"暂无"。
    review_score: dict | None = None
    # review_report 本身不直接对外暴露(内容较大且是内部结构)，只用来派生
    # 下面的 overall_score 计算字段。
    review_report: dict | None = Field(default=None, exclude=True)
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def overall_score(self) -> float | None:
        """0-100 综合评分，从 review_report 里取出，供前端展示单一分数
        (如 QualityBall 悬浮球)使用——review_score 是每个维度各自的分数
        字典，不适合直接当成"一个分数"展示。"""
        if isinstance(self.review_report, dict):
            val = self.review_report.get("overall_score")
            if isinstance(val, (int, float)):
                return float(val)
        return None


class ChapterSummaryOut(BaseModel):
    """章节摘要 — 列表接口使用，不含正文内容。
    字段和前端 types/chapter.ts 的 ChapterSummary 保持一致（前端这个类型和
    对应的分页参数其实早就设计好了，只是后端接口一直没有真正对接上）。"""
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    chapter_num: int
    title: str | None
    word_count: int
    summary: str | None
    status: str
    created_at: datetime
    # 不直接对外暴露，只用来派生下面的 overall_score 计算字段（和 ChapterOut 一致）
    review_report: dict | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def overall_score(self) -> float | None:
        if isinstance(self.review_report, dict):
            val = self.review_report.get("overall_score")
            if isinstance(val, (int, float)):
                return float(val)
        return None


class GenerateChapterRequest(BaseModel):
    mode: str = "continue"  # continue | first_chapter


# ============================================================
# v8 新增 Schemas (Phase 3-9)
# ============================================================


# --- WorldSettingEmbedding (Phase 3) ---

class WorldSettingEmbeddingCreate(BaseModel):
    """创建世界观 embedding chunk"""
    project_id: uuid.UUID
    chunk_text: str
    metadata: dict = Field(default_factory=dict)


class WorldSettingEmbeddingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    chunk_text: str
    metadata: dict
    created_at: datetime


class WorldSettingEmbeddingSearchRequest(BaseModel):
    """向量相似搜索请求"""
    project_id: uuid.UUID
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class WorldSettingEmbeddingSearchResult(BaseModel):
    """单条检索结果"""
    id: uuid.UUID
    chunk_text: str
    similarity: float
    metadata: dict


# --- ProjectWorldRule (Phase 3) ---

class ProjectWorldRuleCreate(BaseModel):
    """创建世界观推理规则"""
    project_id: uuid.UUID
    rule_name: str
    rule_type: str  # numeric | temporal | relational | existential | causal
    description: str | None = None
    dsl_expression: str
    severity: str = "warn"  # error | warn
    is_active: bool = True


class ProjectWorldRuleUpdate(BaseModel):
    """更新推理规则（部分字段可选）"""
    rule_name: str | None = None
    rule_type: str | None = None
    description: str | None = None
    dsl_expression: str | None = None
    severity: str | None = None
    is_active: bool | None = None


class ProjectWorldRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    rule_name: str
    rule_type: str
    description: str | None
    dsl_expression: str
    severity: str
    is_active: bool
    created_at: datetime


# --- PlatformAccount (Phase 4) ---

class PlatformAccountCreate(BaseModel):
    """创建/绑定平台账号"""
    user_id: uuid.UUID
    platform: str
    auth_method: str  # oauth | cookie
    encrypted_credentials: str
    expires_at: datetime | None = None


class PlatformAccountUpdate(BaseModel):
    """更新平台账号凭证"""
    encrypted_credentials: str | None = None
    status: str | None = None
    expires_at: datetime | None = None


class PlatformAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    platform: str
    auth_method: str
    status: str
    expires_at: datetime | None
    created_at: datetime


class PlatformAccountBindRequest(BaseModel):
    """绑定平台账号（接收原始凭证，服务端加密）"""
    platform: str
    auth_method: str  # oauth | cookie
    credentials: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


class PlatformAccountRefreshRequest(BaseModel):
    """刷新平台账号凭证"""
    credentials: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


# --- PublishExecution (Phase 4) ---

class PublishExecutionCreate(BaseModel):
    """创建发布执行任务"""
    project_id: uuid.UUID
    platform: str
    chapters: list = Field(default_factory=list)


class PublishExecutionUpdate(BaseModel):
    """更新发布执行状态/步骤"""
    status: str | None = None
    steps: list | None = None
    screenshots: list[str] | None = None
    logs: str | None = None


class PublishExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    platform: str
    chapters: list
    status: str
    steps: list
    screenshots: list[str] | None
    logs: str | None
    created_at: datetime


class PublishExecuteRequest(BaseModel):
    """触发 Playwright 发布请求"""
    platform: str
    chapter_ids: list[str] = Field(default_factory=list)
    headless: bool = True
    account_id: str | None = None


class PublishExecuteResponse(BaseModel):
    """发布执行响应"""
    execution_id: str
    status: str
    message: str


class PublishStepOut(BaseModel):
    """单个发布步骤结果"""
    step: str
    status: str  # success | failed | skipped
    message: str = ""
    screenshot: str | None = None
    timestamp: datetime | None = None


class PublishExecuteResult(BaseModel):
    """发布执行结果"""
    execution_id: uuid.UUID
    platform: str
    status: str
    steps: list = Field(default_factory=list)
    screenshots: list[str] = Field(default_factory=list)
    published_urls: list[str] = Field(default_factory=list)
    error: str | None = None


# --- QualityBenchmark (Phase 5) ---

class QualityBenchmarkCreate(BaseModel):
    """创建/覆盖平台×品类质量基准"""
    platform: str
    genre: str
    hype_density_threshold: float = 1.0
    hook_min_score: int = 7
    dialogue_ratio_ideal: float = 0.35
    metadata: dict = Field(default_factory=dict)


class QualityBenchmarkUpdate(BaseModel):
    """部分更新质量基准"""
    hype_density_threshold: float | None = None
    hook_min_score: int | None = None
    dialogue_ratio_ideal: float | None = None
    metadata: dict | None = None


class QualityBenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    platform: str
    genre: str
    hype_density_threshold: float
    hook_min_score: int
    dialogue_ratio_ideal: float
    metadata: dict
    updated_at: datetime


class BenchmarkOverride(BaseModel):
    """手动覆盖质量基准"""
    platform: str
    genre: str
    hype_density_threshold: float | None = None
    hook_min_score: int | None = None
    dialogue_ratio_ideal: float | None = None
    metadata: dict | None = None


class PlatformThresholdOut(BaseModel):
    """平台过稿阈值配置"""
    platform: str
    genre: str | None = None
    hype_density_threshold: float
    hook_min_score: int
    dialogue_ratio_ideal: float
    pass_thresholds: dict = Field(default_factory=dict)


# --- ABTest (Phase 6) ---

class ABTestVariant(BaseModel):
    """单个 A/B 变体"""
    variant_name: str
    content: str
    params: dict = Field(default_factory=dict)


class ABTestCreate(BaseModel):
    """创建 A/B 测试"""
    project_id: uuid.UUID
    chapter_id: uuid.UUID
    name: str
    variants: list[ABTestVariant]
    metric: str


class ABTestUpdate(BaseModel):
    """更新 A/B 测试结果"""
    status: str | None = None  # running | completed | cancelled
    winner_variant: str | None = None
    p_value: float | None = None
    results: dict | None = None
    ended_at: datetime | None = None


class ABTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    chapter_id: uuid.UUID
    name: str
    variants: list
    metric: str
    status: str
    winner_variant: str | None
    p_value: float | None
    results: dict
    started_at: datetime
    ended_at: datetime | None


# --- PromptOptimizationLog (Phase 6) ---

class PromptOptimizationLogCreate(BaseModel):
    """记录一次 Prompt 参数调整"""
    project_id: uuid.UUID
    prompt_name: str
    params_before: dict | None = None
    params_after: dict | None = None
    reason: str | None = None
    quality_impact: float | None = None


class PromptOptimizationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    prompt_name: str
    params_before: dict | None
    params_after: dict | None
    reason: str | None
    quality_impact: float | None
    applied_at: datetime


# --- ChapterVersion (Phase 7) ---

class ChapterVersionCreate(BaseModel):
    """创建章节版本快照"""
    chapter_id: uuid.UUID
    content: str
    word_count: int = 0
    diff_from_prev: str | None = None
    quality_score: float | None = None
    created_by: str = "ai"


class ChapterVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    chapter_id: uuid.UUID
    version_num: int
    content: str
    word_count: int
    diff_from_prev: str | None
    quality_score: float | None
    created_by: str
    created_at: datetime


class ChapterVersionDiffRequest(BaseModel):
    """请求对比两个版本"""
    version_a: int
    version_b: int


class ChapterVersionDiffOut(BaseModel):
    """版本 Diff 结果"""
    chapter_id: uuid.UUID
    version_a: int
    version_b: int
    diff_text: str
    added_lines: int
    removed_lines: int


# --- AnalyticsEvent (Phase 8) ---

class AnalyticsEventCreate(BaseModel):
    """创建埋点事件"""
    project_id: uuid.UUID
    event_type: str
    event_data: dict = Field(default_factory=dict)


class AnalyticsEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    event_type: str
    event_data: dict
    created_at: datetime


class AnalyticsEventQuery(BaseModel):
    """埋点事件查询过滤"""
    project_id: uuid.UUID | None = None
    event_type: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# --- Export (Phase 9) ---

class ExportRequest(BaseModel):
    """导出请求参数"""
    format: str = "txt"  # txt | epub | docx | pdf
    encoding: str = "utf-8"
    include_toc: bool = True
    include_cover: bool = False
    cover_text: str | None = None
    line_spacing: float = 1.5
    font_size: int = 12


class ExportResponse(BaseModel):
    """导出响应"""
    download_url: str
    format: str
    file_size: int
    total_words: int


# --- Search (Phase 9) ---

class SearchResult(BaseModel):
    """全局搜索结果条目（旧版兼容）"""
    id: str
    type: str  # project | chapter | foreshadow | knowledge
    title: str
    snippet: str
    project_id: str | None = None
    chapter_num: int | None = None
    highlights: list[str] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    """搜索结果条目（全局搜索 API 使用）"""
    id: uuid.UUID
    type: str  # project | chapter | character | foreshadow | knowledge
    title: str
    snippet: str = ""
    project_id: uuid.UUID | None = None
    project_title: str | None = None


class SearchResponse(BaseModel):
    """全局搜索响应"""
    query: str
    total: int
    results: list[SearchResult]


# --- Auto-Optimize (Phase 8) ---

class AutoOptimizeRequest(BaseModel):
    """自动优化 Prompt 请求"""
    project_id: str
    lookback_days: int = 30
    consecutive_below_threshold: int = 5
    sigma_threshold: float = 1.0


class AutoOptimizeResponse(BaseModel):
    """自动优化 Prompt 响应"""
    project_id: str
    previous_params: dict
    recommended_params: dict
    reason: str
    auto_applied: bool


# --- 通用分页 ---

class PaginatedResponse(BaseModel):
    """通用分页响应包装"""
    items: list
    total: int
    skip: int = 0
    limit: int = 50
