# AGENTS.md → 请先读 CLAUDE.md

> **共用开发指南**: 本文件指向 `CLAUDE.md`，那是唯一的开发指南来源。

## 开始工作前必做

1. **读取 CLAUDE.md** — 包含完整数据库结构、业务逻辑、开发约定
2. **读取 CLAUDE.md 末尾的 [变更记录]** — 了解最新改动
3. **读取 git log** — `git log --oneline -5` 看最近的提交

## 工作完成后必做

1. **更新 CLAUDE.md 的 [变更记录]** — 写清楚改了什么
2. **git commit** — 提交代码
3. **告诉另一个 AI** — 如果 Claude Code 在运行，通知它

## 协作规则

- 开发前先 `git pull` 获取最新代码
- 不要和 Claude Code 同时编辑同一个文件
- 每次修改后立即 commit，让另一方可见
