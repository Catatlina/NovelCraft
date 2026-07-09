-- 007_token_version.sql: JWT 撤销机制
-- 新增 token_version 字段，改密/登出时 +1，旧 token 自动失效

ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 0;
