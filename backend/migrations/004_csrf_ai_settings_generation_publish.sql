-- 004: CSRF + AI settings + harden new deployments

CREATE TABLE IF NOT EXISTS user_ai_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    encrypted_deepseek_api_key TEXT,
    deepseek_model TEXT DEFAULT 'deepseek-chat',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Make existing deployments match the hardened SaaS data model.
DELETE FROM novel_projects WHERE user_id IS NULL;
ALTER TABLE novel_projects ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE novel_projects DROP CONSTRAINT IF EXISTS novel_projects_user_id_fkey;
ALTER TABLE novel_projects
    ADD CONSTRAINT novel_projects_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Optional states used by the Celery enqueue fallback and generation reservation flow.
COMMENT ON TABLE user_ai_settings IS 'Per-user encrypted AI provider settings. API keys are never returned to frontend.';
