---
name: adversarial-absolute-output
description: 红队夹具 · 故意 --output 跟绝对路径（违反死规矩5 + v1.8.3 修复）
version: 0.0.1
---
# 红队测试 skill（故意写烂，勿当真）

跑评估器并落盘到绝对路径：

```bash
python3 scripts/skill_eval.py --base <技能目录> --output /Users/zankus/WorkBuddy/skill/output/skill-rehab/
```

`--output` 跟绝对路径违反死规矩5（包内零绝对路径）与 v1.8.3 修复（应相对工作区），应被 redteam 抓出。
