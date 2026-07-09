-- P1-9: 为关键状态字段加 CHECK 约束，防止非法状态写入。
-- 使用 NOT VALID：跳过对现有数据的校验，仅约束未来写入，迁移安全可重复执行。
-- 各枚举值取自代码中的状态机 / 状态赋值（app/core/state_machine.py 等）。

DO $$
BEGIN
  -- novel_projects.status: 项目生命周期状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_novel_projects_status') THEN
    ALTER TABLE novel_projects
      ADD CONSTRAINT ck_novel_projects_status
      CHECK (status IN ('idea','outline','world','writing','review','publish')) NOT VALID;
  END IF;

  -- novel_chapters.status: 章节状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_novel_chapters_status') THEN
    ALTER TABLE novel_chapters
      ADD CONSTRAINT ck_novel_chapters_status
      CHECK (status IN ('draft','approved','published','reviewing')) NOT VALID;
  END IF;

  -- foreshadow_pool.status: 伏笔状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_foreshadow_pool_status') THEN
    ALTER TABLE foreshadow_pool
      ADD CONSTRAINT ck_foreshadow_pool_status
      CHECK (status IN ('planted','paid_off','overdue')) NOT VALID;
  END IF;

  -- generation_tasks.status: 生成/流水线任务状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_generation_tasks_status') THEN
    ALTER TABLE generation_tasks
      ADD CONSTRAINT ck_generation_tasks_status
      CHECK (status IN ('queued','running','done','failed')) NOT VALID;
  END IF;

  -- platform_accounts.status: 平台账号状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_platform_accounts_status') THEN
    ALTER TABLE platform_accounts
      ADD CONSTRAINT ck_platform_accounts_status
      CHECK (status IN ('active','refreshed')) NOT VALID;
  END IF;

  -- publish_executions.status: 发布执行状态
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_publish_executions_status') THEN
    ALTER TABLE publish_executions
      ADD CONSTRAINT ck_publish_executions_status
      CHECK (status IN ('pending','running','success','partial','failed')) NOT VALID;
  END IF;
END
$$;
