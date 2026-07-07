# 星禾写作助手 v8.0

AI 驱动的全流程小说写作平台：扫榜选题 → 百万字长篇生成 → 伏笔追踪 → 7维质量审查 → 出海翻译发布。

## 快速启动

```bash
# 1. 后端（Docker）
cp .env.example .env
docker compose up -d

# 2. 前端
cd frontend && npm install && npm run dev
```

## 账号
登录 admin / admin123

## 功能矩阵
- 6阶段状态机 + 7层Context Hub (pgvector)
- 7 Prompt引擎 (scan/analyze/write/short-write/deslop/translate/review)
- 5级Celery调度 (Idea/大纲/章节/审核/发布)
- 伏笔系统 + 7维质量审查 + 去AI味
- 13平台扫榜 + 爆款分析 + 反馈学习
- 6平台翻译出海 + Playwright发布
- A/B测试 + Prompt优化 + 分析看板

## 技术栈
前端: React 18 + TypeScript + Vite + Tailwind + TanStack Query + Zustand
后端: FastAPI + PostgreSQL 16 + pgvector + Redis + Celery
AI: DeepSeek API (前端可配任意兼容OpenAI的API)
