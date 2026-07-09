-- 003_multitenant_hardening.sql
-- 强化商业 SaaS 多租户隔离：项目必须归属于用户，删除用户时级联清理项目。
-- 执行前请确认没有 user_id 为空的历史项目；如有，请先人工归属或删除。

BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM novel_projects WHERE user_id IS NULL) THEN
        RAISE EXCEPTION 'novel_projects.user_id contains NULL rows; assign or delete orphan projects before migration';
    END IF;
END $$;

ALTER TABLE novel_projects
    ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE novel_projects
    DROP CONSTRAINT IF EXISTS novel_projects_user_id_fkey;

ALTER TABLE novel_projects
    ADD CONSTRAINT novel_projects_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_publish_executions_project_id ON publish_executions(project_id);
CREATE INDEX IF NOT EXISTS idx_platform_accounts_user_id ON platform_accounts(user_id);

COMMIT;
