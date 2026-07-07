-- 星禾写作助手 v8.0 建表脚本（pgvector 版本）
-- Phase 3-9 基础设施：新增 9 张表 + pgvector 扩展

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- v7 原有表（保留不变）
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS novel_projects (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID REFERENCES users(id) ON DELETE SET NULL,
    title                  TEXT NOT NULL,
    genre TEXT,
    platform TEXT,
    status TEXT NOT NULL DEFAULT 'idea',
    state_history JSONB NOT NULL DEFAULT '[]',
    overall_outline TEXT,
    chapter_tree JSONB DEFAULT '[]',
    glossary_json JSONB DEFAULT '[]',
    power_system TEXT,
    world_rules TEXT,
    characters_json JSONB DEFAULT '[]',
    world_setting TEXT,
    total_chapters INT DEFAULT 0,
    total_words INT DEFAULT 0,
    token_budget INT,
    token_used INT DEFAULT 0,
    publish_accounts_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS novel_chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    chapter_num INT NOT NULL,
    title TEXT,
    content TEXT,
    word_count INT DEFAULT 0,
    outline TEXT,
    summary TEXT,
    review_score JSONB DEFAULT '{}',
    review_report JSONB DEFAULT '{}',
    status TEXT DEFAULT 'draft',
    version_history JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(project_id, chapter_num)
);

CREATE TABLE IF NOT EXISTS foreshadow_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    planted_chapter INT NOT NULL,
    expected_payoff_range TEXT,
    status TEXT DEFAULT 'planted',
    payoff_chapter INT,
    payoff_quality_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    knowledge_type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quality_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES novel_chapters(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    score NUMERIC,
    issues_json JSONB DEFAULT '[]',
    rewrite_applied BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS generation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    progress JSONB DEFAULT '{}',
    error_log TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS publish_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES novel_chapters(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    published_url TEXT,
    published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS feedback_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES novel_chapters(id) ON DELETE CASCADE,
    platform TEXT,
    read_count INT,
    retention_rate NUMERIC,
    collected_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- v8 新增表 (Phase 3-9 基础设施)
-- ============================================

-- Phase 3: 世界观知识增强 — 世界观 chunk + pgvector embedding
CREATE TABLE IF NOT EXISTS world_setting_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wse_project ON world_setting_embeddings(project_id);

-- Phase 3: 世界观推理规则存储
CREATE TABLE IF NOT EXISTS project_world_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('numeric','temporal','relational','existential','causal')),
    description TEXT,
    dsl_expression TEXT NOT NULL,
    severity TEXT DEFAULT 'warn' CHECK (severity IN ('error','warn')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 4: 加密存储平台凭证
CREATE TABLE IF NOT EXISTS platform_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    auth_method TEXT NOT NULL CHECK (auth_method IN ('oauth','cookie')),
    encrypted_credentials TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 4: 发布执行记录+步骤日志
CREATE TABLE IF NOT EXISTS publish_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    chapters JSONB DEFAULT '[]',
    status TEXT DEFAULT 'pending',
    steps JSONB DEFAULT '[]',
    screenshots TEXT[],
    logs TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 5: 各平台×品类质量基准
CREATE TABLE IF NOT EXISTS quality_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    genre TEXT NOT NULL,
    hype_density_threshold REAL DEFAULT 1.0,
    hook_min_score INTEGER DEFAULT 7,
    dialogue_ratio_ideal REAL DEFAULT 0.35,
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(platform, genre)
);

-- Phase 6: A/B 测试配置与结果
CREATE TABLE IF NOT EXISTS ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES novel_chapters(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    variants JSONB NOT NULL,
    metric TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    winner_variant TEXT,
    p_value REAL,
    results JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ
);

-- Phase 6: Prompt 参数调整记录
CREATE TABLE IF NOT EXISTS prompt_optimization_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    prompt_name TEXT NOT NULL,
    params_before JSONB,
    params_after JSONB,
    reason TEXT,
    quality_impact REAL,
    applied_at TIMESTAMPTZ DEFAULT now()
);

-- Phase 7: 章节版本快照
CREATE TABLE IF NOT EXISTS chapter_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES novel_chapters(id) ON DELETE CASCADE,
    version_num INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    diff_from_prev TEXT,
    quality_score REAL,
    created_by TEXT DEFAULT 'ai',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(chapter_id, version_num)
);

-- Phase 8: 埋点事件
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ae_project ON analytics_events(project_id);
CREATE INDEX IF NOT EXISTS idx_ae_type ON analytics_events(event_type);
