# 星禾写作助手 — 需求规格说明书 v9.0（可执行版）

> **定位**：能跑、能用、能直接生成小说的最低实现标准  
> **合并来源**：原始需求 v7.0 + 实现现状 v8.0 + GitHub 开源方案  
> **核心目标**：一句话灵感 → 完整小说初稿，中间过程全自动

---

## 一、一句话功能定义

**用户输入一句话灵感，系统自动产出：** 书名 → 简介 → 全书大纲（5-8卷） → 前三章细纲 → 章节树 → 第一章正文。全程约 3-5 分钟，中间每一步用户可中断修改。

---

## 二、扫榜功能（❗真实数据驱动，非 LLM 幻觉）

### 2.1 数据来源

| 平台 | 榜型 | 实现方式 |
|------|------|----------|
| 起点中文网 | 月票榜/推荐榜/畅销榜 | 榜单页面为服务端渲染 HTML，用 `httpx` + `BeautifulSoup` 直接解析，非 JS 页面 |
| 番茄小说 | 热搜榜/完本榜 | 榜单页面为 SSR，用 `httpx` + `BeautifulSoup` 解析 |
| 晋江文学城 | 积分榜/霸王票榜 | HTML 解析 |
| 纵横中文网 | 月票榜/收藏榜 | HTML 解析 |

### 2.2 实现逻辑（参考 GitHub 开源思路）

参考 `AI_NovelGenerator`（5.5k⭐）的榜单监控思路，分三步：

**第一步：爬取榜单列表**
```python
# backend/app/services/scanner.py — 用 httpx + BeautifulSoup 替代旧的 mock 数据
async def fetch_trending_books(platform: str, limit: int = 20):
    """爬取指定平台榜单，返回书籍列表"""
    # 起点：https://www.qidian.com/rank/yuepiao/
    # 番茄：https://fanqienovel.com/rank
    # 返回: [{title, author, genre, description, word_count, rank}]
```

**第二步：LLM 聚合分析**
```
把 4 个平台的榜单前 20 名数据喂给 DeepSeek：
"分析以下榜单数据，提取本周热门题材 TOP5、热门叙事模式、新兴趋势"
→ 输出结构化 JSON：{topics, trends, recommendations}
```

**第三步：选题推荐**
```
用户选一个题材/趋势 → LLM 生成 3 个差异化灵感点子
→ 用户选一个或输入自己的想法 → 进入灵感生成流程
```

### 2.3 为什么不用 Puppeteer/Playwright
- 榜单页面大部分是 SSR（服务端渲染），不是 SPA
- HTML 直接解析比启动浏览器快 10 倍
- 符合"先跑起来再优化"原则
- 真实爬虫比 LLM 凭空编榜单数据靠谱

---

## 三、灵感生成功能（❗一句话 → 完整初稿，全链路串联）

### 3.1 输入方式

用户可通过三种方式触发：
1. **直接输入**：在灵感输入框写一句话（如"修真界数学老师用微积分破阵"）
2. **扫榜推荐**：从扫榜推荐结果中点"用这个灵感"
3. **已有项目**：在已有项目的"灵感"阶段修改 idea

### 3.2 自动生成流程（全链路）

```
用户输入灵感 (一句话)
    │
    ▼
[阶段1] 书名生成 (3个候选，用户选一个)
    调用 LLM: temperature=0.9
    根据灵感+题材 生成 3 个不同风格的书名
    │
    ▼
[阶段2] 简介生成
    调用 LLM: temperature=0.8
    150-200 字简介，含核心矛盾+世界观暗示+悬念钩子
    │
    ▼
[阶段3] 全书大纲 (5-8 卷)
    调用 LLM: temperature=0.7
    每卷 1 个主题 + 3-5 个关键事件
    输出 JSON: [{volume_num, title, theme, events: [...]}]
    │
    ▼
[阶段4] 前三章细纲
    调用 LLM: temperature=0.7
    每章 800-1200 字细纲（场景、人物动机、情感变化、伏笔埋设点）
    │
    ▼
[阶段5] 章节树生成 (chapter_tree)
    按卷→章的结构自动生成完整章节树
    输出 JSON: [{volume, title, chapters: [{num, title, summary}]}]
    │
    ▼
[阶段6] 第一章正文 (2000-3500 字)
    调用 LLM: temperature=0.9
    经 Context Hub 组装上下文：
    - 全书大纲
    - 前三章细纲
    - 角色设定
    → 生成第一章完整正文（含标题、摘要、伏笔标注）
```

### 3.3 API 设计

```
POST /api/v1/projects/quick-start
Body: {
  "idea": "修真界数学老师用微积分破阵",
  "genre": "修真",
  "platform": "起点"
}
Response: {
  "project_id": "xxx",
  "titles": ["书名1", "书名2", "书名3"],
  "steps_completed": ["title", "synopsis", "outline", "detailed_outline", "chapter_tree"],
  "current_step": "awaiting_title_selection",
  "first_chapter": null  // 选完书名后才生成
}
```

```
POST /api/v1/projects/{id}/quick-start/select-title
Body: { "title_index": 0 }
Response: 触发后续生成 → 返回完整第一章节
```

### 3.4 前端界面

```
┌──────────────────────────────────────┐
│  🚀 快速开始                           │
│                                      │
│  💡 写下一句话灵感...       [生成]     │
│  ┌─────────────────────────┐         │
│  │ 修真界数学老师用微积分破阵 │         │
│  └─────────────────────────┘         │
│                                      │
│  📖 或从扫榜推荐中选：                  │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │重生+修仙│ │都市兵王│ │远古神祇│ │
│  │ 4.2k🔥 │ │ 3.8k🔥 │ │ 3.1k🔥 │ │
│  └─────────┘ └─────────┘ └────────┘ │
│                                      │
│  ═══════ 生成结果 ═══════             │
│  ┌─ 可选书名 ──────────────────┐      │
│  │ ○ 数学修仙传                │      │
│  │ ○ 微积分破阵实录             │      │
│  │ ○ 算尽苍穹                  │      │
│  └────────────────────────────┘      │
│                                      │
│  📖 简介:                             │
│  "数学系教授穿越修真界，发现这个世界... │
│                                      │
│  📚 全书大纲 (6卷)                     │
│  卷一：初入异界 (1-150章)             │
│  卷二：宗门崛起 (151-300章)            │
│  ...                                 │
│                                      │
│  📑 前三章细纲                         │
│  第1章：穿越第一课                    │
│  第2章：第一个公式                    │
│  第3章：被发现了                      │
│                                      │
│  📖 第一章正文 (预览)                    │
│  "李明睁开眼睛，发现自己躺在一座古老...  │
│                                      │
│  [✏️ 修改大纲] [📝 编辑第一章] [▶️ 继续生成] │
└──────────────────────────────────────┘
```

---

## 四、4 个 GitHub 开源项目的实现参考

### 4.1 扫榜爬虫 — 参考 crawlee-python

| 项目 | 地址 | 取其思路 |
|------|------|----------|
| crawlee-python | github.com/apify/crawlee-python | 榜单 URL 队列管理 + 请求频率控制 + 反爬处理 |

**实现策略**：
```python
# 不要自己造轮子，直接用 httpx + bs4
# 4 个平台的榜单页面结构固定，不需要全自动爬虫
# 每个平台写一个 parser 函数，约 50 行/个

class PlatformParser:
    qidian: 解析起点月票榜 HTML
    fanqie: 解析番茄热搜榜 HTML
    jinjiang: 解析晋江积分榜 HTML
    zongheng: 解析纵横收藏榜 HTML
```

### 4.2 灵感到小说全链路 — 参考 AI_NovelGenerator (5.5k⭐)

**取其思路：** 多阶段 prompt chain，每阶段输出作为下一阶段输入

**关键差异：** 原项目用本地模型，我们全部用 DeepSeek API，不需要 GPU

### 4.3 批量生成调度 — 参考 AI-automatically-generates-novels (900⭐)

**取其思路：** 章节生成队列 + 断点续写

**我们的优势：** 已有 Celery chain + Context Hub，直接对接即可

### 4.4 拆书流水线 — 参考 harnessNovel (40⭐)

**取其思路：** DeepSeek 拆解爆款 → 提取结构特征 → 应用到新书生成

**实现位置：** `tools.py` 的 `analyze` 端点已有，需补充输出对接

---

## 五、剩余未实现功能的实现方案

### 5.1 定向自动重写（v7.0 ④ 的缺口）

| 当前 | 目标 |
|------|------|
| 审查输出分数+建议 | → | AI 精确定位问题片段（如"第3段对话生硬"）→ 只重写那 2-3 句 |

**API 设计：**
```
POST /api/v1/quality/{review_id}/targeted-rewrite
Body: { "target_fragments": ["原文片段1", "原文片段2"], "issues": ["对话生硬", "节奏拖沓"] }
Response: { "rewritten_fragments": ["重写后片段1", "重写后片段2"] }
```

### 5.2 伏笔 Payoff 检测（v7.0 ③ 的缺口）

| 当前 | 目标 |
|------|------|
| 只标记已回收 | → | 检测回收质量：是否水过、是否匹配预期回收范围 |

**实现：** 章节生成后自动调 LLM 判断："这个伏笔回收是否有效？"
```
POST /api/v1/foreshadows/{id}/check-payoff
Body: { "chapter_id": "xxx", "recovery_text": "回收段落内容" }
Response: { "is_valid": true, "quality_score": 8, "issues": [] }
```

### 5.3 推理规则引擎（v7.0 ⑧ 的缺口）

| 当前 | 目标 |
|------|------|
| world_rules 表有 DSL | → | 生成时自动校验是否违反规则 |

**实现：** 在 Context Hub 的 layer_7（防崩提醒）中增加"规则检查结果"
```
POST /api/v1/projects/{id}/world-rules/check
Body: { "chapter_content": "本章正文" }
Response: { "violations": [{"rule": "力量体系不可逆", "fragment": "...", "severity": "error"}] }
```

---

## 六、3 档优先级的完整需求清单

### 🔴 P0（阻塞"能用"——本周必做）

| # | 需求 | 父级 | 说明 |
|---|------|------|------|
| 1 | 真实扫榜爬虫（4 平台） | 4-1 | httpx + bs4 解析榜单页面，替代 LLM 幻觉数据 |
| 2 | 灵感→完整初稿全链路 | 4-2/4-3/4-4/4-5 | 一句话输入 → 书名+简介+大纲+细纲+章节树+第一章 |
| 3 | 快速开始页面 | UI | 灵感输入框 + 扫榜推荐卡片 + 生成进度 + 预览编辑 |

### 🟡 P1（提升质量——两周内）

| # | 需求 | 说明 |
|---|------|------|
| 4 | 定向自动重写 | 质量审查后精确定位问题片段局部重写 |
| 5 | 伏笔 Payoff 检测 | 回收质量评分 + 水过检测 |
| 6 | 推理规则引擎接入 | Context Hub layer_7 增加规则校验结果 |

### 🟢 P2（长期增强）

| # | 需求 | 说明 |
|---|------|------|
| 7 | 反馈学习闭环 | 发布→回读数据→分析→调Prompt（Phase 8） |
| 8 | 编辑器升级 | textarea→CodeMirror/Tiptap |
| 9 | 多模型切换 | LLMProvider 接口 |

---

## 七、技术实现优先级（本周可交付）

```
Day 1: 实现 4 个平台爬虫 (scanner.py 重构)
       httpx + BeautifulSoup → 返回结构化榜单数据

Day 2: 实现 quick-start API
       灵感 → 书名(3个) → 简介 → 大纲 → 细纲 → 章节树 → 第一章
       全链路 prompt chain

Day 3: 前端快速开始页面
       灵感输入 + 扫榜推荐 + 生成进度 + 预览 + 操作按钮

Day 4: 端到端测试 + 修复 + 部署
```
