-- P0-1: 新增 AI 生成累计成本字段（人民币 ¥），由 generation 接口按真实单价结算
-- 幂等：可重复执行
ALTER TABLE novel_projects ADD COLUMN IF NOT EXISTS cost_cny NUMERIC(12,4) NOT NULL DEFAULT 0;
