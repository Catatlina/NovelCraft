# NovelCraft Round 4 全量修复报告

## 本轮修复

1. 修复 AI 生成失败污染章节号和 total_chapters：失败时删除占位章节并重算章节统计。
2. 增加 TokenLedger 成本账本：生成前预留额度，成功结算，失败释放，避免并发超预算。
3. 禁止质量审查自动覆盖正文：/quality/review 只写评分和低分维度，用户主动 /quality/rewrite 才改正文。
4. 补齐世界观知识库 API：chunk list/create/update/delete/rebuild/search，支持 embedding 检索和关键词降级。
5. 前端质量面板改为调用真实 API，移除模拟质量数据和随机重写兜底。
6. 前端项目选择器改为真实项目列表，移除示例项目。
7. 爆款分析中心移除内置模拟榜单和随机评分，改为真实后端分析结果。
8. 扫榜 API 移除 /mock 演示端点和 mock 降级数据。
9. 补齐 aiosqlite 测试依赖。
10. 新增 GitHub Actions CI：后端编译/测试，前端构建/audit。
11. 新增迁移脚本 backend/migrations/005_hardening_round4.sql。

## 验证结果

- 后端 compileall：通过
- 后端 pytest：106 passed
- 前端 npm run build：通过
- 前端 npm audit --audit-level=moderate：0 vulnerabilities

## 仍需生产环境自行配置

- SECRET_KEY、ADMIN_PASSWORD、DB_PASSWORD、REDIS_PASSWORD、ACCOUNT_ENCRYPTION_KEY 必须在 .env 中设置强随机值。
- 生产必须启用 HTTPS，并设置 COOKIE_SECURE=true。
- 首次部署会执行 schema_v8.sql；已有数据库需要按 migrations 顺序执行 SQL。
