# 星禾写作助手（NovelCraft）需求说明书 v8.0

> 编写日期：2026-07-09  
> 产品定位：AI 驱动的商业网文创作 SaaS 平台  
> 对标产品：番茄作家助手、Sudowrite、Jasper  
> 技术栈：FastAPI + React/TypeScript + PostgreSQL/pgvector + Celery + Redis  

---

## 一、系统架构概览

```
┌──────────┐  ┌─────────────┐  ┌────────────┐  ┌───────┐
│ Nginx 80 │→│ FastAPI:8100 │→│ PostgreSQL │  │ Redis │
│ (前端SPA) │  │ (REST API)  │  │ + pgvector │  │ 队列  │
└──────────┘  └──────┬──────┘  └────────────┘  └──┬────┘
                     ↓                             ↓
              ┌──────────────┐           ┌─────────────────┐
              │ Celery Worker│           │ DeepSeek API    │
              │ (5级任务队列)│←──────────│ (AI 推理)       │
              └──────────────┘           └─────────────────┘
```

---

## 二、功能模块清单（28 个 API 路由 + 8 个前端页面）

---

### 2.1 用户认证

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 1 | 注册 | POST /api/v1/auth/register | 用户名+密码+邮箱，scrypt KDF 哈希存储 |
| 2 | 登录 | POST /api/v1/auth/login | httpOnly Cookie 下发 access+refresh JWT |
| 3 | 刷新Token | POST /api/v1/auth/refresh | refresh token 换新 access，20次/分钟限流 |
| 4 | 登出 | POST /api/v1/auth/logout | 清除 Cookie + token_version+1 全局失效 |
| 5 | 获取当前用户 | GET /api/v1/auth/me | 返回用户信息+套餐 |

**安全特性：**
- scrypt KDF（N=16384）+ hmac.compare_digest 恒定时间比较防时序攻击
- JWT 双保险撤销：jti Redis 黑名单（单 token） + token_version（全局）
- CSRF 双提交 Cookie 中间件拦截所有写操作
- Access Token 15分钟 / Refresh Token 7天

---

### 2.2 项目管理

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 6 | 创建项目 | POST /api/v1/projects | 书名+简介+体裁，默认"构思"状态 |
| 7 | 项目列表 | GET /api/v1/projects | 按更新时间倒序 |
| 8 | 项目详情 | GET /api/v1/projects/{id} | 含章节数/字数/预算/状态 |
| 9 | 更新项目 | PUT /api/v1/projects/{id} | 修改书名/简介/体裁/预算 |
| 10 | 删除项目 | DELETE /api/v1/projects/{id} | 级联删除章节/伏笔/审查记录 |
| 11 | 更新大纲 | PUT /api/v1/projects/{id}/outline | 全书总纲文字 |
| 12 | 更新世界观 | PUT /api/v1/projects/{id}/world | 人物/力量体系/世界规则 |
| 13 | 状态迁移 | POST /api/v1/projects/{id}/transition | 构思→大纲→设定→创作→审核→发布 |

**状态机（6 阶段）：**
```
构思 → 大纲 → 设定 → 创作中 → 审核 → 发布
```
每阶段前置条件校验 + SELECT FOR UPDATE 行锁防 TOCTOU 竞态。

---

### 2.3 AI 章节生成（核心链路）

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 14 | 单章生成 | POST /api/v1/projects/{id}/chapters/generate | 续写/第一章两种模式 |
| 15 | 章节列表 | GET /api/v1/projects/{id}/chapters | 按章节号排序，分页 |
| 16 | 章节更新 | PUT /api/v1/chapters/{id} | 修改正文/标题 |

**生成流程（7层上下文装配）：**
```
1. 全书总纲（overall_outline，截断 8000 字符）
2. 当前卷大纲（chapter_tree JSONB 卷定位）
3. 人物状态（characters_json，截断 16000 字符）
4. 世界设定（pgvector 语义检索，top-5 chunks）
5. 开放伏笔（ForeshadowPool status=planted）
6. 近期摘要（前 5 章 summary）
7. 防崩提醒（人物OOC + 时间线 + 伏笔回收约束）
```

**防崩机制：**
- FOR UPDATE 占位（分配章节号）→ AI 调用（不持锁）→ 写回正文
- AI 失败自动删除占位 + 重算 total_chapters
- 伏笔索引扫描仅查 planted_chapter ≤ 当前-5
- 上下文 Token 预算守卫（layer_1 8000/layer_3 16000 字符上限 + 告警日志）

**Prompt 平台化：**
- 7 个 Prompt 引擎（续写/审查/翻译/去AI味/扫榜/拆文/短篇）存储在 `prompt_templates` 表
- 支持在线编辑/版本管理/激活/回滚
- DB 不可用时自动降级为代码内置硬编码
- 已完成 5/7 引擎接入：续写、审查、翻译、扫榜、拆文

**字数统计：** 商业网文口径（去除所有空白字符后计数）

---

### 2.4 批量生成流水线

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 17 | 批量生成 | POST /api/v1/pipeline/batch-generate | 一次生成 1-50 章，Celery chain 顺序执行 |
| 18 | 选题流水线 | POST /api/v1/pipeline/idea | 13 平台扫榜→去重→评分推荐 |
| 19 | 大纲流水线 | POST /api/v1/pipeline/outline | 基于选题+世界观批量生成大纲变体 |
| 20 | 任务状态 | GET /api/v1/pipeline/status | 5 队列任务统计 |
| 21 | 取消任务 | POST /api/v1/pipeline/{id}/cancel | 设置 cancel_requested + 链中任务检查 |

**队列架构（5级）：**
```
灵感队列 → 大纲队列 → 章节队列 → 审核队列 → 发布队列
```

**可靠性设计：**
- Celery chain() 严格顺序执行，杜绝并发乱序
- 502 瞬时错误 `self.retry()` 重试 / 402/409 终止错误标记失败停止链
- 跨 event loop 连接池 dispose 修复（第二个任务必现崩溃）
- Worker autoscale 8,2 + time-limit 300s
- 批次取消逐章检查 `cancel_requested` 状态

---

### 2.5 7维质量审查

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 22 | 质量审查 | POST /api/v1/quality/{chapter_id}/review | 7维度打分+问题列表+修改建议 |
| 23 | 审查历史 | GET /api/v1/quality/{chapter_id}/reviews | 历次审查记录对比 |
| 24 | 改写 | POST /api/v1/quality/{chapter_id}/rewrite | 按审查建议自动改写 |

**审查维度：**
```
一致性 | 人物弧光 | 节奏起伏 | 情感层次 | 市场吸引力 | 原创性 | 伏笔管理
```
每维度 0-10 分 + 问题列表 + 综合评价。生成后自动派发审查任务。

---

### 2.6 伏笔系统

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 25 | 伏笔列表 | GET /api/v1/foreshadows | 按状态筛选（已埋/已回收/超期） |
| 26 | 创建伏笔 | POST /api/v1/foreshadows | 描述+期望回收范围 |
| 27 | 回收伏笔 | POST /api/v1/foreshadows/{id}/payoff | 标记已回收 + 关联章节 |
| 28 | 超期标记 | 自动 | 种植章节距当前>5章 且未回收 → overdue |

**AI 生成联动：** 每章生成后模型自动提取新伏笔 + 回收伏笔（JSON 格式）→ 写入 ForeshadowPool。

---

### 2.7 扫榜分析

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 29 | AI 扫榜 | POST /api/v1/scan | 多平台榜单数据→ LLM 解析趋势 |
| 30 | 批量扫榜 | POST /api/v1/hit-analysis/batch-scan | 起点/番茄/晋江/纵横等平台 |
| 31 | 爆款评估 | POST /api/v1/hit-analysis/evaluate | 分析单书爆款潜力+可借鉴元素 |

**支持平台：** 起点中文网、番茄小说、晋江文学城、纵横中文网、飞卢、掌阅、QQ阅读、17k、创世、磨铁、黑岩阅读、豆瓣阅读、书旗小说（共 13 个）

---

### 2.8 世界观知识库（pgvector RAG）

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 32 | 索引世界观 | POST /api/v1/world-setting/{project_id}/index | 文本分块→向量化→入库 |
| 33 | 重建索引 | POST /api/v1/world-setting/{project_id}/rebuild | 先删除旧 chunk 再重新索引 |
| 34 | 语义搜索 | GET /api/v1/world-setting/{project_id}/search | 自然语言检索世界观片段 |

**检索降级策略（三级）：**
1. pgvector 语义向量检索（≤> 相似度排序）
2. 关键词 ILIKE 匹配（降级）
3. 数据库字段直接截取（终极降级）

每次降级均记录 logger.warning 日志。

---

### 2.9 翻译出海

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 35 | 翻译章节 | POST /api/v1/translate/{chapter_id} | 中文→英文/日文/韩文 |

**支持平台风格：** Webnovel、RoyalRoad、ScribbleHub、Wattpad（各平台标题/摘要/排版风格适配）

---

### 2.10 自动发布

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 36 | 创建执行 | POST /api/v1/publish-executions/{project_id}/execute | 指定章节+平台→执行发布 |
| 37 | 执行列表 | GET /api/v1/publish-executions/{project_id} | 发布历史 |
| 38 | 执行详情 | GET /api/v1/publish-executions/{execution_id} | 步骤日志+截图 |
| 39 | 平台账号管理 | CRUD /api/v1/platform-accounts | 邮箱/密码 Fernet 加密存储 |

**安全设计：**
- 凭据 Fernet 加密存储，不落盘明文
- 发布前双重校验：章节归属 + 账号归属
- Playwright 自动登录→导航→填充→提交→截图取证

---

### 2.11 其他功能

| 序号 | 功能 | 接口 | 说明 |
|------|------|------|------|
| 40 | 全局搜索 | GET /api/v1/search | 跨章节/伏笔/项目/角色全文搜索（ILIKE+转义） |
| 41 | 去AI味 | POST /api/v1/tools/deslop | 润色/洗稿/降重 |
| 42 | 拆文学习 | POST /api/v1/tools/analyze | 分析爆款书结构 |
| 43 | 短篇生成 | POST /api/v1/generate/short | 独立短篇/中篇创作 |
| 44 | 章节版本 | GET /api/v1/chapters/{id}/versions | 版本快照+diff |
| 45 | 章节反馈 | POST /api/v1/feedback | 读者反馈信号采集 |
| 46 | A/B 测试 | CRUD /api/v1/ab-tests | Prompt 参数对比测试 |
| 47 | Prompt 优化 | GET /api/v1/prompt-optimization | 优化历史日志 |
| 48 | Prompt 管理 | CRUD /api/v1/admin/prompts | 在线编辑模板+版本激活（管理员） |
| 49 | 质量基准 | GET /api/v1/quality-benchmarks | 平台热点质量基准 |
| 50 | 世界观规则 | CRUD /api/v1/projects/{id}/world-rules | 推理规则 DSL 配置 |
| 51 | 数据看板 | GET /api/v1/ops/dashboard | 总字数/项目数/质量分/伏笔率 KPI |
| 52 | 数据分析 | GET /api/v1/analytics | 埋点事件聚合分析 |
| 53 | AI 设置 | PUT /api/v1/ai-settings | 用户级 API Key+模型选择 |

---

## 三、前端页面清单

| 页面 | 路由 | 功能 |
|------|------|------|
| 登录/注册 | /login | 表单验证、记住我、第三方登录占位 |
| 总控驾驶舱 | / | KPI 卡片(~字数+项目数+质量分+伏笔率) + 6阶段状态机 + 项目列表 + 任务队列 + 快捷操作 |
| 创作工作台 | /write/:id | 左侧章节导航(Tree)+ 中间编辑器(textarea) + 右侧上下文面板(ContextHub 7层) + 状态机按钮 |
| 伏笔看板 | /foreshadows/:id | 三列看板(已埋/已回收/超期) + 筛选 + 统计 |
| 质量面板 | /quality/:id | 雷达图(7维) + 章节评分表(>排序) + 改写面板 |
| 翻译发布 | /translate | 平台选择 + 预览 + 字典配置 |
| 爆款分析 | /trends | 分析表单 + 题材趋势 + 爆款卡片 + 市场预测 + 选题建议 |
| 数据分析 | /analytics | 埋点事件聚合可视化 |
| 设置 | /settings | API Key配置+暗色模式+账户信息+登出 |

---

## 四、数据库核心表

| 表名 | 用途 |
|------|------|
| users | 用户(username/email/password_hash/is_admin/token_version) |
| novel_projects | 项目(标题/状态/大纲/世界观JSON/预算/字数) |
| novel_chapters | 章节(章节号/标题/正文/摘要/字数) |
| foreshadow_pool | 伏笔池(描述/种植章节/回收章节/状态) |
| chapter_versions | 章节版本快照(正文diff+prompt参数) |
| world_setting_embeddings | 世界观向量(pgvector 1536维) |
| knowledge_embeddings | 知识库向量(pgvector 1536维) |
| token_ledger | Token账本(reserved/settled/released三态) |
| prompt_templates | Prompt模板(名称/版本/system/user模板/温度/激活) |
| prompt_optimization_log | Prompt优化历史 |
| platform_accounts | 平台发布账号(Fernet加密存储) |
| publish_executions | 发布执行记录(步骤+截图URL) |
| quality_reviews | 质量审查记录(7维得分+问题+建议) |
| generation_tasks | 生成任务队列状态 |
| analytics_events | 埋点事件(JSONB) |

---

## 五、运维配置

| 项目 | 配置 |
|------|------|
| API 端口 | 8100 (仅监听 127.0.0.1) |
| 前端端口 | 80 (Nginx 反向代理) |
| 数据库 | PostgreSQL 16 + pgvector |
| 缓存 | Redis 7 (Celery broker/backend + JWT黑名单 + 限流) |
| 任务队列 | Celery 5级队列 + autoscale 8,2 |
| 健康检查 | /health (API) + celery inspect ping (Worker) |
| 日志 | journalctl + uvicorn access log |
| 备份 | 每日凌晨3点 pg_dump -Fc + 7天留存 |
| 监控 | Celery Flower :5555 (basic_auth) |

---

## 六、已知待实现（非阻塞）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P1 | 编辑器升级 | textarea→CodeMirror/Tiptap 虚拟滚动 |
| P1 | 翻译分段 | content[:8000]→chunked分段处理 |
| P1 | Prometheus 监控 | /metrics + Grafana + 告警规则 |
| P2 | tools.py/short_story.py 接 DB 模板 | 无 db session，需重构 |
| P2 | AI 响应缓存 | 相同上下文复用 DeepSeek 响应 |
| P2 | 多模型抽象 | LLMProvider 接口支持 Claude/GPT |

---

> 文档基于 `main` 分支 HEAD `ea8f7da`，实际部署于新加坡 VPS 43.156.17.78。
