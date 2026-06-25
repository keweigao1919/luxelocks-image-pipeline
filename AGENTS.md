# AGENTS.md → 共用的开发指南

> **你是 Claude Code / Claude / Codex 三方协作中的一员。**
> 唯一权威指南 → `CLAUDE.md`
> 活动看板 → `WORKING.md`

---

## 开始工作前（三步）

```
1. 读 WORKING.md → 有没有人在干活？有就等
2. 读 CLAUDE.md → 数据库结构 + 业务逻辑 + 末尾变更记录
3. git log --oneline -3 → 最近的提交
```

## 查入（告诉别人你在干活）

```
编辑 WORKING.md → 写上 "| Claude Code | 修XXX bug | 14:30 |"
git add WORKING.md && git commit -m "checkin: ..."
```

## 完成后（三步）

```
1. 更新 CLAUDE.md 末尾 [变更记录] 表格
2. 清除 WORKING.md 中自己的行
3. git add -A && git commit -m "Claude Code: 修了XXX"
```

## 协作铁律

- **开发前先读 WORKING.md + CLAUDE.md 变更记录**
- **不要和另一个 AI 同时编辑同一个文件**
- **每次改动后必须更新 CLAUDE.md 变更记录 + git commit**
- **改了不提交 = 没改（别人看不到）**
