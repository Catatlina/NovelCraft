# NovelCraft Round 5 修复与全量审查报告

## 修复目标
基于上一轮商业 SaaS 审查继续修复 P0/P1：前端接口断链、Celery 用户级 AI Key、迁移体系、质量改写确认流、任务状态机、Token 成本账本、生产认证旁路。

## 已修复

1. 前端 API 路径断链
   - 文件：`frontend/src/api/endpoints.ts`
   - 修复：`ab-tests/create`、`platform-accounts/platform`、`publish-executions/{id}/execute`、`quality-benchmarks/benchmarks`、`quality-benchmarks/benchmarks/override` 与后端路由对齐。

2. Celery 用户级 AI Key 失效
   - 文件：`backend/app/tasks/pipeline.py`
   - 修复：新增 `_bind_project_ai_context()`，在 `idea_pipeline_task`、`outline_pipeline_task`、`publish_pipeline_task`、`chapter_queue`、`review_queue` 中按 `project.user_id` 读取用户加密 AI 配置，并注入 DeepSeek ContextVar。

3. 数据库升级不可控
   - 文件：`backend/apply_migrations.py`、`backend/Dockerfile`、`backend/migrations/006_saas_hardening_round5.sql`
   - 修复：新增启动时 SQL migration runner，记录 `schema_migrations`，避免只有空库才执行 schema 的问题；Docker 启动 API 前自动执行迁移。
   - 兼容：新增 Alembic 基线目录，便于后续转为 Alembic autogenerate。

4. 质量改写直接覆盖正文
   - 文件：`backend/app/api/quality.py`
   - 修复：`/quality/rewrite` 与 `/quality/rewrite-preview` 只生成预览，不改正文；新增 `/quality/apply-rewrite`，用户确认后才保存快照并应用。

5. 任务状态机字段不足
   - 文件：`backend/app/db/models.py`、`backend/schema_v8.sql`、`backend/migrations/006_saas_hardening_round5.sql`
   - 修复：`generation_tasks` 增加 `request_id`、`retry_count`、`cancel_requested`、`last_error_code`、`started_at`、`finished_at`。

6. Token 成本账本字段不足
   - 文件：`backend/app/db/models.py`、`backend/schema_v8.sql`、`backend/app/api/generation.py`、`backend/migrations/006_saas_hardening_round5.sql`
   - 修复：增加 `model`、`input_tokens`、`output_tokens`、`unit_price_input`、`unit_price_output`、`cost_usd`、`cost_cny`，生成章节时写入输入/输出 token。

7. 生产认证旁路风险
   - 文件：`frontend/src/store/authStore.ts`
   - 修复：`VITE_AUTH_BYPASS` 仅在 `import.meta.env.DEV` 时生效，生产构建无法绕过认证。

## 验证结果

- 后端编译：通过
- 后端测试：`106 passed`
- 前端构建：通过
- 前端安全审计：`found 0 vulnerabilities`

## 本轮全量审查结论

当前项目已达到“小规模内测 / 受控试运营”标准。若要达到商业 SaaS 大规模生产标准，仍建议继续补：集中日志、监控告警、数据库自动备份、发布适配器 dry-run/截图留证、完整计费价格表、任务取消/人工重跑 UI。
