-- Round 5 SaaS hardening: task state machine + cost fields + vector index guard
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS request_id TEXT UNIQUE;
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS cancel_requested BOOLEAN DEFAULT FALSE;
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS last_error_code TEXT;
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE generation_tasks ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON generation_tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_request_id ON generation_tasks(request_id);

ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS model TEXT;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS input_tokens INT DEFAULT 0;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS output_tokens INT DEFAULT 0;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS unit_price_input NUMERIC;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS unit_price_output NUMERIC;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS cost_usd NUMERIC;
ALTER TABLE token_ledger ADD COLUMN IF NOT EXISTS cost_cny NUMERIC;

CREATE INDEX IF NOT EXISTS idx_wse_embedding_hnsw
ON world_setting_embeddings USING hnsw (embedding vector_cosine_ops);
