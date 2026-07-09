-- 010_user_is_admin.sql: 管理员角色字段 (P1-1)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;
