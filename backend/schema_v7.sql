-- 星禾写作助手 v7.0 建表脚本（无 pgvector 版本）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
    embedding JSONB,
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
