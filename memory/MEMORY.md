# MEMORY.md -> 请先读 WORKING.md + CLAUDE.md

本文件不是第二份开发指南。

Claude Code、Claude 和 Codex 的唯一权威开发指南是项目根目录的 `CLAUDE.md`。
实时活动看板是项目根目录的 `WORKING.md`。

开始任何开发、修复或排查前，请按顺序读取：

1. `../WORKING.md`：确认是否有人正在干活，避免撞文件
2. `../CLAUDE.md`：读取数据库结构、业务逻辑、协作规则和末尾「变更记录」
3. `git log --oneline -5`：确认最近提交

完成后必须更新 `../CLAUDE.md` 变更记录，清除 `../WORKING.md` 中自己的行，并 git commit。
