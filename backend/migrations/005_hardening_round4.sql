-- Round 4 hardening: token ledger, no automatic content overwrite, world embedding API support.
CREATE TABLE IF NOT EXISTS token_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES novel_projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,
    estimated_tokens INT DEFAULT 0,
    actual_tokens INT DEFAULT 0,
    status TEXT DEFAULT 'reserved' CHECK (status IN ('reserved','settled','released')),
    created_at TIMESTAMPTZ DEFAULT now(),
    settled_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_token_ledger_project_status ON token_ledger(project_id, status);
CREATE INDEX IF NOT EXISTS idx_token_ledger_user_created ON token_ledger(user_id, created_at DESC);
