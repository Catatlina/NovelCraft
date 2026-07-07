-- v7.0 PR #2: 数据隔离迁移
-- 为现有 novel_projects 表添加 user_id 外键
-- 已存在的项目将设置 user_id = NULL (管理员可访问)

ALTER TABLE novel_projects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;
