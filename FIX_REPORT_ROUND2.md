# NovelCraft 第二轮修复报告

## 本轮修复范围

1. 强多租户初始化
   - `backend/schema_v8.sql` 中 `novel_projects.user_id` 改为 `NOT NULL REFERENCES users(id) ON DELETE CASCADE`。
   - 修正 `backend/migrations/002_user_id.sql`。
   - 新增 `backend/migrations/004_csrf_ai_settings_generation_publish.sql`，用于已有库补齐强约束和 AI 设置表。

2. Cookie 认证 CSRF 防护
   - 登录/注册/刷新时设置 `csrf_token` 非 httpOnly cookie。
   - 新增 `CSRFMiddleware`，认证态写请求必须携带 `X-CSRF-Token`。
   - 前端 `api()` 统一为 POST/PUT/PATCH/DELETE 注入 CSRF header。

3. DeepSeek API Key 后端加密保存
   - 新增 `user_ai_settings` 表和 ORM。
   - 新增 `/api/v1/ai-settings` GET/PUT。
   - 前端设置页不再写入 `localStorage`，Key 只提交一次且不回显。
   - DeepSeek 调用从服务端用户配置读取，不再信任 `X-DeepSeek-API-Key` header。

4. AI 生成去长事务
   - `_generate_single_chapter()` 改成短事务预留章节号与占位章节，提交后再调用模型。
   - 模型返回后再短事务写回正文、伏笔、字数与 token 统计。
   - AI 失败时占位章节标记为 `failed`，避免长时间锁项目行。

5. Celery 入队失败兜底
   - `publish_executions.execute_publish()` 对 `send_task()` 增加 try/except。
   - Redis/Celery 不可用时，执行记录更新为 `failed_enqueue`，不再永久停留在 `pending`。

## 验证结果

- 后端：`python3 -m compileall app` 通过。
- 前端：`npm ci && npm run build` 通过。
- 注意：`npm audit` 仍提示 1 个 moderate、1 个 high 依赖漏洞，未自动 `npm audit fix --force`，因为可能引入破坏性升级。
- Docker 未验证：当前执行环境没有 Docker daemon。

## 仍建议后续处理

- 引入 Alembic，替代手写 SQL migration。
- 补 token ledger/预扣费机制。
- 为 CSRF、越权、AI 设置、发布入队失败补自动化测试。
- 处理前端依赖漏洞，优先评估 `npm audit` 详情后做定向升级。
