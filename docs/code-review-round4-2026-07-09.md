# NovelCraft v8.1 — 审查报告（第四轮·2026-07-09）

> **审查方法**: 逐文件读取当前代码，不与历史报告交叉引用  
> **基准**: 商业 SaaS AI 写作平台  
> **评分**: **86/100**（85→86，微涨，发现新路径不匹配问题）

---

## 一、分数明细

| 维度 | 得分 | 满分 | 变化 |
|------|------|------|------|
| 架构设计 | 24 | 25 | +1 |
| 代码质量 | 18 | 20 | — |
| 安全性 | 14 | 15 | — |
| 数据库 | 9 | 10 | — |
| AI 专项 | 9 | 10 | — |
| 部署运维 | 7 | 10 | — |
| 前端 | 5 | 10 | — |
| **总分** | **86** | **100** | — |

---

## 二、本轮新发现

### P1: 前端 API 参数名与后端不匹配（3 处）

#### P1-4: `TransitionRequest` 字段名不匹配
- **前端** `types/project.ts:38-41`: `{ new_state, note }`
- **后端** `schemas.py:46-48`: `{ target_state, reason }`
- **调用点** `Dashboard.tsx:91`: `{ new_state: newState, note: ... }`
- **后果**: 前端发 `new_state` → 后端 Pydantic 忽略（无此字段）→ `target_state` 为空 → 状态迁移静默失败
- **修复**: 前端改为 `{ target_state, reason }`

#### P1-5: `ProjectOutlineUpdate` 字段名不匹配
- **前端** `types/project.ts:44-46`: `{ outline }`
- **后端** `schemas.py:22-23`: `{ overall_outline }`
- **后果**: 更新大纲功能不可用
- **修复**: 前端改为 `{ overall_outline }`

#### P1-6: `ExportRequest` 实现与 schema 不一致
- `endpoints.ts:289-292` 调用 `opsExport(projectId, format)` 只传两个参数
- 但后端 `/ops/export/{project_id}` (ops.py:209) 期望 `ExportRequest` body (含 `format/encoding/include_toc` 等)
- **后果**: 前端导出请求可能缺少必需参数
- **修复**: 检查调用方式，确认为 `POST` 且传 body

### P2: 新增发现

#### P2-8: `EXPORT_DIR.mkdir()` 模块导入时执行
- **文件** `ops.py:45-46`
- **问题**: 与 `playwright_publisher.py` 相同的模块级副作用。若目录创建失败 → ImportError → API 无法启动。
- **修复**: 移到首次导出时懒初始化。

#### P2-9: `learning.py` feedback 分析仍然使用 f-string
- **文件** `learning.py:51`
- **代码**: `f"分析以下章节阅读数据并生成3条Prompt优化建议:\n{json.dumps(chapter_data, ...)[:6000]}..."`  
- **问题**: `chapter_data` 含用户设置的章节标题，可能含有 `{}` 导致 KeyError。
- **修复**: 改为 `str()` 拼接。

#### P2-10: `rule_engine.py` 规则校验 f-string
- **文件** `rule_engine.py:114-127`
- **问题**: `rule.rule_name` 和 `chapter_text` 直接拼入 f-string，规则名和章节内容是用户可控的。
- **修复**: 改为字符串拼接。

#### P2-11: `ABTest archive_test` 空 variants 边界
- **文件** `ab_tests.py:252-253`
- **代码**: `test.winner_variant = variants[0].get("variant_name") if variants else "default"`
- **问题**: 如果 `variants` 非空但 `variants[0]` 为 `{}`（空 dict），`.get()` 返回 `None`，后续查找 winner 时 `None` 不匹配任何 variant_name。
- **风险**: 低，仅在极端边缘情况下触发。
- **修复**: 加 `or "default"` 兜底。

---

## 三、已修复/确认无问题的领域

| 检查项 | 状态 |
|--------|------|
| 多租户数据隔离 | ✅ CASCADE + NOT NULL + 全端点校验 |
| CSRF 防护 | ✅ 双中间件 + auth 端点豁免 |
| Token 类型隔离 | ✅ access≠refresh |
| API Key 加密存储 | ✅ Fernet + 不回显 |
| HTTP 重试 | ✅ 3次指数退避 + Retry-After |
| Celery chain 顺序 | ✅ 杜绝乱序跳号 |
| Health 真实检查 | ✅ SELECT 1 + Redis PING |
| ChapterVersion 自动快照 | ✅ 首版创建 + prompt 参数记录 |
| PromptRegistry | ✅ 7 prompts + auto-optimization |
| context_hub chapter_tree | ✅ 真实卷解析 |
| 伏笔索引扫描 | ✅ planted_chapter <= N-5 |
| chapter 分页列表 | ✅ ChapterSummaryOut + limit/offset |
| 多格式导出 | ✅ TXT/EPUB/DOCX/PDF |
| A/B 测试 t-test | ✅ scipy.stats.ttest_ind |

---

## 四、完整问题清单

| # | 级别 | 文件 | 问题 |
|---|------|------|------|
| P1-1 | P1 | `generation.py` | `_auto_mark_overdue_foreshadows` 已修复 ✅ |
| P1-2 | P1 | `publish_executions.py` | `datetime.utcnow()` 6处 (Python 3.12+废弃) |
| P1-3 | P1 | `playwright_publisher.py` | SCREENSHOT_DIR 模块导入时 mkdir |
| P1-4 | **P1** | `Dashboard.tsx:91` | `new_state`→应为`target_state`，`note`→应为`reason` |
| P1-5 | **P1** | `types/project.ts:45` | `outline`→应为`overall_outline` |
| P1-6 | **P1** | `endpoints.ts:289` | export 调用可能参数不匹配 |
| P2-1 | P2 | `context_hub.py` | _extract_current_arc 已修复 ✅ |
| P2-2 | P2 | `generation.py` | TokenLedger 单价硬编码0 ✅ |
| P2-3 | P2 | `Settings/index.tsx` | 假保存按钮 |
| P2-4 | P2 | `prompts.py` | Prompt 版本管理已集成 ✅ |
| P2-5 | P2 | `alembic/` | autogenerate 未接入 |
| P2-6 | P2 | `scanner.py` | MOCK_SCAN_BOOKS 仍存在 |
| P2-7 | P2 | CI | 无 DB/Redis 测试环境 |
| P2-8 | **P2** | `ops.py:45` | EXPORT_DIR.mkdir() 模块导入时执行 |
| P2-9 | **P2** | `learning.py:51` | feedback 分析 f-string 注入 |
| P2-10 | **P2** | `rule_engine.py:114` | 规则校验 f-string 注入 |

---

## 五、生产上线前检查清单

| # | 检查项 | 状态 |
|---|--------|------|
| 1 | 服务启动无 ImportError | ✅ |
| 2 | 所有端点有认证 | ✅ |
| 3 | CSRF 保护 | ✅ |
| 4 | Token 类型隔离 | ✅ |
| 5 | Docker 无硬编码 | ✅ |
| 6 | Health 真实检查 | ✅ |
| 7 | 前端 API 参数与后端对齐 | ❌ P1-4/5/6 |
| 8 | datetime.utcnow()→now(UTC) | ❌ P1-2 |
| 9 | 模块级副作用 | ❌ P1-3, P2-8 |
| 10 | f-string 残留 | ❌ P2-9, P2-10 |
| 11 | Alembic autogenerate | ❌ |
| 12 | Celery Flower 监控 | ❌ |
| 13 | DB 自动备份 | ❌ |

---

## 六、修复优先级

### 立即修复（用户可感知的 Bug）
1. **P1-4**: Dashboard 状态迁移参数名 (`new_state`→`target_state`)
2. **P1-5**: 大纲更新字段名 (`outline`→`overall_outline`)
3. **P1-6**: 导出参数对齐验证

### 灰度前修复
4. P1-2: `datetime.utcnow()` 6处替换
5. P1-3: SCREENSHOT_DIR 懒初始化
6. P2-8: EXPORT_DIR 懒初始化
7. P2-9: learning.py f-string 安全拼接
8. P2-10: rule_engine.py f-string 安全拼接

---

## 七、结论

**86/100** — 核心后端已非常扎实（认证/授权/CSRF/成本/任务队列/内容管理/Prompt 版本管理），本轮新发现的 3 个 P1 全部在前端→后端的参数对齐上 —— 这说明前端没有实际跑过完整的状态迁移和大纲更新流程。

修复这 3 个 P1 后，评分预计达到 **88-89/100**。
