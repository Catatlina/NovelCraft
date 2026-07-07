# Contributing to 星禾写作助手

## 开发环境

```bash
git clone https://github.com/YOUR_USERNAME/NovelCraft.git
cd NovelCraft
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链

## PR 流程

1. Fork 本仓库
2. 创建分支: `git checkout -b feat/my-feature`
3. 提交前确保代码导入无错误: `python -c "from app.main import app"`
4. 提交 PR，描述变更内容

## 安全

发现安全漏洞请勿公开 Issue，直接联系维护者。
