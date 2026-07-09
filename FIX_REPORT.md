# NovelCraft 修复说明（V8.0 Hotfix）

本次修复重点面向商业 SaaS 上线前的 P0/P1 风险：认证、越权、多租户、任务可靠性、生产部署。

## 已修复

1. **Access/Refresh Token 类型隔离**
   - 文件：`backend/app/api/deps.py`
   - 修复：业务 API 只接受 `type=access` 的 JWT，refresh token 不能再直接访问业务接口。

2. **发布执行接口越权修复**
   - 文件：`backend/app/api/publish_executions.py`
   - 修复：执行发布前校验章节必须属于当前项目，平台账号必须属于当前用户。
   - 修复：查询发布执行详情时 join 项目表校验 `NovelProject.user_id == current_user.id`。
   - 修复：Celery 执行阶段二次校验章节归属和账号归属。

3. **发布任务从 BackgroundTasks 迁移到 Celery**
   - 文件：`backend/app/tasks/pipeline.py`
   - 新增：`publish_execution_task`，进入 `publish` 队列。
   - 价值：API 容器重启时不会直接丢失发布任务。

4. **多租户强归属**
   - 文件：`backend/app/db/models.py`、`backend/schema_v8.sql`
   - 修复：`novel_projects.user_id` 改为 `NOT NULL + ON DELETE CASCADE`。
   - 新增迁移：`backend/migrations/003_multitenant_hardening.sql`。

5. **Cookie 认证与 CORS 修复**
   - 文件：`backend/app/api/auth.py`、`backend/main.py`、`frontend/src/types/auth.ts`
   - 修复：登录/注册不再把 access/refresh token 返回给前端 JS，只设置 httpOnly cookie。
   - 修复：CORS 增加 `allow_credentials=True`，支持跨域 cookie。

6. **生产前端容器化**
   - 新增：`frontend/Dockerfile`、`frontend/nginx.conf`
   - 修改：`docker-compose.yml` 增加 `web` 服务，端口 `8080:80`，Nginx 反代 `/api` 到后端。

7. **Redis 生产可靠性增强**
   - 文件：`docker-compose.yml`
   - 修复：Redis 开启 AOF 持久化，增加 healthcheck 和 `redisdata` volume。

8. **环境变量模板安全化**
   - 文件：`backend/.env.example`
   - 修复：移除弱口令示例，改为强密码/随机密钥占位。

## 已验证

- Python 语法编译：通过 `python3 -m compileall -q backend/app backend/main.py`。
- 前端生产构建：执行 `npm ci && npm run build`，构建成功。

## 未完全解决但已标记为下一步

1. Alembic 尚未完整接入；目前提供 SQL 迁移脚本。
2. AI Token 账本/预扣额度机制尚未完全实现。
3. 生成章节期间的 DB 锁持有问题仍建议在下一版拆成“占位记录 + 异步生成 + 短事务写回”。
4. CSRF 双提交 token 尚未完整实现；当前依赖 SameSite=Lax + httpOnly cookie，正式多域名部署建议继续补 CSRF。
5. 作品知识库/RAG 的 chunk 版本、来源追踪、重建索引仍需继续完善。

## 部署提示

首次部署：

```bash
cp .env.example .env
# 填写 DB_PASSWORD、REDIS_PASSWORD、SECRET_KEY、ADMIN_PASSWORD、DEEPSEEK_API_KEY

docker compose up -d --build
```

已有数据库升级：

```bash
# 先备份数据库
# 再执行：backend/migrations/003_multitenant_hardening.sql
```
