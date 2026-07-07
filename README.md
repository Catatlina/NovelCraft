# 星禾写作助手 v8.0

AI 驱动的全流程小说写作平台 — 从扫榜选题、百万字长篇生成、伏笔追踪、7维质量审查，到出海翻译发布。

> 🎯 **零基础也能部署**：本文档假设你从未用过 Docker/Python/Node.js，每一步都有详细说明。

---

## 目录

- [你的电脑需要什么](#你的电脑需要什么)
- [第一步：安装必备软件](#第一步安装必备软件)
  - [macOS](#macos)
  - [Windows](#windows)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
- [第二步：获取 DeepSeek API Key](#第二步获取-deepseek-api-key)
- [第三步：下载项目](#第三步下载项目)
- [第四步：配置环境变量](#第四步配置环境变量)
- [第五步：启动后端](#第五步启动后端)
- [第六步：启动前端](#第六步启动前端)
- [第七步：打开使用](#第七步打开使用)
- [常见问题排查](#常见问题排查)
- [功能概览](#功能概览)
- [技术架构](#技术架构)
- [项目结构](#项目结构)

---

## 你的电脑需要什么

运行本项目需要以下软件（都是免费的）：

| 软件 | 用途 | 必须？ |
|------|------|--------|
| **Docker Desktop** | 一键运行数据库(PostgreSQL)+缓存(Redis)+后端 | ✅ 必须 |
| **Node.js 18+** | 运行前端页面 | ✅ 必须 |
| **Git**（可选） | 下载项目代码 | 推荐 |
| **DeepSeek API Key** | AI 生成小说需要 | ✅ 必须 |

> 💡 如果你不想装 Docker，也可以手动安装 PostgreSQL + Redis，但**强烈建议用 Docker**，一行命令全搞定，零配置。

---

## 第一步：安装必备软件

### macOS

#### 1. 安装 Homebrew（如果还没有）
打开"终端"（在"启动台 → 其他 → 终端"），粘贴以下命令，按回车：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
安装过程中会提示你按一次回车、输入电脑密码（输入时屏幕不显示字符，这是正常的）。

#### 2. 安装 Docker Desktop
```bash
brew install --cask docker
```
安装完成后，在"应用程序"文件夹找到 **Docker** 图标，双击打开。首次启动需要等待 Docker 引擎初始化（菜单栏出现鲸鱼图标且不再抖动即完成）。

> 国内用户如果下载慢，可以去 [Docker 官网](https://www.docker.com/products/docker-desktop/) 直接下载安装包。

#### 3. 安装 Node.js
```bash
brew install node
```
验证安装：
```bash
node --version   # 应该显示 v18.x 或更高
npm --version    # 应该显示 9.x 或更高
```

#### 4. 安装 Git（通常 macOS 自带）
```bash
git --version    # 验证是否已安装
```
如果没有，运行：`brew install git`

---

### Windows

#### 1. 安装 Docker Desktop
1. 访问 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. 点击 "Download for Windows" 下载安装包
3. 双击运行安装包，全部默认选项，一路"下一步"
4. 安装完成后重启电脑
5. 重启后 Docker 会自动启动，任务栏右下角出现鲸鱼图标

> ⚠️ Windows 需要开启虚拟化（Hyper-V / WSL2）。Docker 安装程序会自动提示你开启，按提示操作即可。

#### 2. 安装 Node.js
1. 访问 [Node.js 官网](https://nodejs.org/)
2. 点击左侧 "LTS" 版本的按钮下载（推荐 18.x 或 20.x）
3. 双击运行安装包，全部默认选项，一路"下一步"
4. 安装完成后，按 `Win + R` 输入 `cmd` 回车打开命令提示符，验证：
```cmd
node --version
npm --version
```

#### 3. 安装 Git
1. 访问 [Git for Windows](https://git-scm.com/download/win)
2. 下载并运行安装包，全部默认选项（可以一路"下一步"）
3. 安装完成后，在命令提示符中验证：
```cmd
git --version
```

---

### Linux (Ubuntu/Debian)

打开终端，依次运行以下命令：

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 退出终端重新登录，使 Docker 权限生效

# 2. 安装 Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. 安装 Git
sudo apt-get install -y git

# 验证
docker --version
node --version
git --version
```

---

## 第二步：获取 DeepSeek API Key

本项目使用 DeepSeek 作为 AI 引擎。你需要一个 API Key：

1. 打开 [platform.deepseek.com](https://platform.deepseek.com/)
2. 注册/登录账号（支持微信/手机号）
3. 点击左侧菜单 "API Keys"
4. 点击 "创建 API Key"，输入名称（如 `novelcraft`），复制生成的 Key

> 💰 DeepSeek 价格极低，**新用户注册赠送 500 万 tokens 免费额度**（约可生成 10-15 章小说正文），足够体验全部功能。

> 🔑 Key 格式类似 `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`，**请务必保存好**，只显示一次。

---

## 第三步：下载项目

打开终端（macOS/Linux）或命令提示符（Windows）：

```bash
# 进入你想放项目的目录，比如桌面
cd ~/Desktop

# 克隆项目
git clone https://github.com/Catatlina/NovelCraft.git

# 进入项目目录
cd NovelCraft
```

> 如果你没装 Git，也可以直接在 GitHub 页面点绿色的 "Code" → "Download ZIP"，解压后进入解压目录。

---

## 第四步：配置环境变量

项目根目录已有一个 `.env` 文件，但需要**填入你的 DeepSeek API Key**。

macOS/Linux：
```bash
nano .env
```

Windows（命令提示符）：
```cmd
notepad .env
```

找到 `deepseek_api_key` 这一行，把等号后面填上你在第二步获取的真实 Key（例如 `deepseek_api_key=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）。**其他配置不用改**。

> 💡 如果你不想改文件，也可以跳过这步：启动后在网页的设置页面（齿轮图标）填入 Key，两种方式任选其一。

---

## 第五步：启动后端

在项目根目录下运行：

```bash
docker compose up -d
```

首次运行会下载镜像（约 2-5 分钟，取决于网速）。你会看到类似输出：
```
[+] Running 4/4
 ✔ Network novelcraft_default    Created
 ✔ Container novelcraft-db       Started
 ✔ Container novelcraft-redis    Started
 ✔ Container novelcraft-backend  Started
```

**验证后端是否正常运行：**

浏览器打开 http://localhost:8100/health

看到 `{"status":"ok","version":"8.0.0"}` 就说明后端起来了。

### Docker 启动了什么？

| 容器 | 端口 | 作用 |
|------|------|------|
| `novelcraft-db` | 5432 | PostgreSQL 16 数据库 |
| `novelcraft-redis` | 6379 | Redis 缓存/任务队列 |
| `novelcraft-backend` | 8100 | FastAPI 后端服务 |

### 常用 Docker 命令

```bash
docker compose up -d       # 启动
docker compose down        # 停止
docker compose logs -f     # 查看实时日志
docker compose restart     # 重启
docker compose ps          # 查看运行状态
```

---

## 第六步：启动前端

打开一个**新的终端窗口**，进入项目目录下的 `frontend` 文件夹：

```bash
cd ~/Desktop/NovelCraft/frontend

# 安装依赖（首次运行需要，约 1-2 分钟）
npm install

# 启动前端开发服务器
npm run dev
```

看到以下输出即成功：
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## 第七步：打开使用

1. 浏览器打开 **http://localhost:5173**
2. 看到登录页面，输入：
   - 用户名：`admin`
   - 密码：`admin123`
3. 登录后进入设置页面（左下角齿轮图标），填入你的 **DeepSeek API Key** 和 **Model**（默认 `deepseek-chat`）
4. 点击"创建项目"，开始你的第一部 AI 小说！

### 创作流程

```
灵感输入 → 扫榜选题 → 书名生成 → 大纲撰写 → 世界观设定 → 章节生成 → 质量审查 → 发布
```

每一步 AI 都会辅助你，你只需做选择和微调。

---

## 常见问题排查

### ❌ Docker 启动失败

**现象**：`docker compose up -d` 报错 `Cannot connect to the Docker daemon`

**解决**：确保 Docker Desktop 已经完全启动（任务栏/菜单栏有鲸鱼图标且不抖动）。Windows 用户可能需要以管理员身份运行。

---

### ❌ 端口被占用

**现象**：启动报错 `port is already allocated`

**解决**：端口 5432 / 6379 / 8100 可能被其他程序占用。
```bash
# macOS/Linux 查看谁占用了端口
lsof -i :8100
# 关掉对应程序，或修改 docker-compose.yml 中的端口映射
```

---

### ❌ 前端 `npm install` 报错

**现象**：`npm ERR!` 或卡住不动

**解决**：
```bash
# 清理缓存重试
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

国内用户如果下载慢，可以设置镜像：
```bash
npm config set registry https://registry.npmmirror.com
```

---

### ❌ 前端报 `Network Error` 或无法连接后端

**检查清单**：
1. 后端 Docker 是否在运行？→ 浏览器打开 http://localhost:8100/health 确认
2. 后端和前端是否在同一台电脑？
3. 浏览器控制台（F12 → Console）是否有 CORS 错误？

---

### ❌ 生成章节报错 "未配置 API Key"

**解决**：在前端设置页面（齿轮图标）填入 DeepSeek API Key，或者在 `.env` 文件中配置 `DEEPSEEK_API_KEY` 后重启后端：
```bash
docker compose restart
```

---

### ❌ 提示 "AI 服务暂时不可用"

- 检查 API Key 是否正确
- 检查 DeepSeek 账户余额是否用完
- 检查网络是否能访问 `https://api.deepseek.com`

---

### ❌ 数据库报错

```bash
# 重置数据库（会丢失数据，仅开发环境）
docker compose down -v
docker compose up -d
```

---

## 功能概览

| 分类 | 功能 | 说明 |
|------|------|------|
| 🧠 **核心架构** | 6阶段状态机 | Idea→Outline→World→Writing→Review→Publish 严格管控 |
| | 7层Context Hub | 全书总纲/人物状态/世界观/伏笔池/前文摘要/防崩提醒 统一组装 |
| ✍️ **创作引擎** | 7 Prompt引擎 | 扫榜分析/拆文学习/长篇写作/短篇写作/去AI味/翻译出海/多视角审查 |
| | 灵感一键生成 | 一句话 idea → 书名+大纲+细纲+第1章 |
| | 单章续写 | Context Hub 组装上下文后精准续写 |
| | 批量生成 | 一次生成 10-50 章，五级队列调度 |
| 📊 **质量系统** | 7维审查 | 一致性/AI味检测/节奏/人物OOC/爽点密度/对话质量/结尾钩子 |
| | 自动重写 | 审查发现问题后 AI 定向局部重写 |
| 🎯 **伏笔系统** | 伏笔埋点 | 生成时 AI 自动标记新埋伏笔 |
| | 回收检测 | 自动比对伏笔池，检测回收状态 |
| | Payoff 检测 | 判断回收质量 防止"水过" |
| 🔥 **爆款分析** | 13平台扫榜 | 起点/番茄/晋江/Webnovel等 自动采集热榜 |
| | 趋势研判 | AI 分析市场趋势+选题推荐 |
| | 对标分析 | 拆解爆款标题/开头/节奏 |
| 🌍 **出海发布** | 6平台翻译 | Webnovel/RoyalRoad/Wattpad 等风格适配 |
| | Playwright 发布 | 自动登录海外平台发布章节 |
| 📈 **数据驱动** | 反馈学习 | 阅读数据回流 → 分析 → Prompt优化 → 再生成 |
| | A/B 测试 | 多版本章节对比测试 |
| | 分析看板 | 字数/质量/发布/成本 全维度可视化 |

---

## 技术架构

```
┌──────────────────────────────────────┐
│  浏览器 → http://localhost:5173        │  前端
│  React 18 + TypeScript + Vite          │
├──────────────────────────────────────┤
│  FastAPI → http://localhost:8100       │  后端
│  状态机校验 + API路由 (24个模块)        │
├──────────────────────────────────────┤
│  Context Hub 服务                      │  核心
│  7层上下文组装 + pgvector 语义检索      │
├──────────────────────────────────────┤
│  Celery + Redis                        │  调度
│  五级队列: Idea/大纲/章节/审核/发布     │
├──────────────────────────────────────┤
│  PostgreSQL 16 + pgvector              │  存储
│  数据 + 向量检索 + 世界规则引擎         │
├──────────────────────────────────────┤
│  DeepSeek API                          │  AI
│  Embeddings API (向量) + Chat API (文本)│
└──────────────────────────────────────┘
```

---

## 项目结构

```
NovelCraft/
├── .env                    # 环境配置（API Key 在这里填）
├── docker-compose.yml      # Docker 一键启动配置
├── README.md               # 本文件
├── docs/
│   └── requirements.md     # 需求规格说明书
├── backend/                # 后端 Python 代码
│   ├── main.py             # FastAPI 入口
│   ├── app/
│   │   ├── api/            # API 路由（24 个模块）
│   │   ├── core/           # 配置/安全/状态机
│   │   ├── db/             # 数据库模型
│   │   ├── services/       # 核心服务
│   │   │   ├── context_hub.py      # 7层上下文组装
│   │   │   ├── deepseek_client.py  # DeepSeek API 客户端
│   │   │   ├── prompts.py          # 7 Prompt 引擎
│   │   │   ├── scanner.py          # 13平台扫榜
│   │   │   └── rule_engine.py      # 世界观规则校验
│   │   ├── tasks/          # Celery 任务队列
│   │   └── ws/             # WebSocket
│   ├── schema_v8.sql       # 数据库建表脚本
│   └── requirements.txt    # Python 依赖
└── frontend/               # 前端 React 代码
    ├── src/
    │   ├── pages/          # 12 个页面
    │   ├── components/     # UI 组件
    │   ├── store/          # 状态管理
    │   └── types/          # TypeScript 类型定义
    └── package.json        # Node.js 依赖
```

---

## 默认账号

| 用户名 | 密码 | 说明 |
|--------|------|------|
| `admin` | `admin123` | 管理员账号 |

> ⚠️ **生产环境请务必修改默认密码**：在 `.env` 中修改 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`，然后重启 Docker。

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE) 文件。
