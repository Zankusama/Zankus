---
name: adversarial-hardcoded-path
description: 红队夹具 · 故意含硬编码绝对路径（对应 v1.8.5 真实 bug：SKILL.md:145）
version: 0.0.1
---
# 红队测试 skill（故意写烂，勿当真）

产出写到 /Users/zankus/WorkBuddy/skill/output/foo/ 目录（硬编码绝对路径，应被 redteam 抓出）。

死规矩5 要求包内零绝对路径，本夹具故意违反，用于验证 run_redteam.py 的 HARDCODED_PATH 检测器。
