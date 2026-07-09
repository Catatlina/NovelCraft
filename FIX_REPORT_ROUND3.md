# NovelCraft 第三轮全量审查与修复报告

## 本轮修复内容

1. **认证 Cookie 安全配置强化**
   - 新增 `COOKIE_SECURE`、`COOKIE_SAMESITE` 配置。
   - 禁止 `COOKIE_SAMESITE=none` 但 `COOKIE_SECURE=false` 的错误配置。
   - 避免生产 HTTPS / 跨站部署时 Cookie 行为不可控。

2. **CORS 安全兜底**
   - 启动时拒绝 `CORS_ORIGINS=*` 与 `allow_credentials=True` 同时使用。
   - 防止凭证型跨域被错误放开。

3. **AI 生成稳定性修复**
   - 章节生成成功后，质量审查任务入队失败不再导致生成接口返回失败。
   - 入队失败会写日志，用户可以后续手动审查。

4. **自动发布凭证错误修复**
   - 平台账号解密失败不再静默吞掉。
   - 发布执行会明确标记为 `failed` 并写入 `credentials_error` 步骤。

5. **前后端校验一致性修复**
   - 前端注册密码长度校验从 6 位改为 8 位，与后端一致。

6. **Docker Compose 生产化修复**
   - 移除 api/worker 的源码热更新 volume，避免生产镜像代码被宿主目录覆盖。
   - Postgres 健康检查改为使用实际 `POSTGRES_USER` / `POSTGRES_DB`。

7. **测试体系修复**
   - 新增 `backend/tests/conftest.py`，为测试提供安全本地默认环境变量。
   - 避免测试收集阶段因缺少 `.env` 直接失败。

8. **前端依赖安全修复**
   - Vite 升级到 `6.4.3`。
   - `esbuild` override 到 `0.25.11`。
   - `npm audit --audit-level=moderate` 已无漏洞。

## 本轮验证结果

- 后端 Python 编译：通过
- 后端测试：`108 passed`
- 前端构建：通过
- 前端依赖审计：`found 0 vulnerabilities`
- Docker：当前执行环境没有 docker 命令，未能实际 build/run 容器

## 仍需人工确认

1. 真实服务器上的 `.env` 必须设置强密码和固定密钥。
2. 如果使用 HTTPS 正式域名，建议设置：
   - `COOKIE_SECURE=true`
   - `COOKIE_SAMESITE=lax`
   - `CORS_ORIGINS=https://你的前端域名`
3. 已有旧数据库升级时，仍需手动执行 `backend/migrations/*.sql`；全新部署会使用最新 `schema_v8.sql`。
