---
name: adversarial-cwd-conflict
description: 红队夹具 · 故意命令 cwd 互斥（对应 v1.8.5 真实 bug：P0-1）
version: 0.0.1
---
# 红队测试 skill（故意写烂，勿当真）

跑评估器（相对路径引用 + --output 相对工作区）：

```bash
python3 scripts/skill_eval.py --base <技能目录> --skills foo --output output/skill-rehab/
```

`scripts/` 相对路径需 cwd=skill 目录；`--output output/` 需 cwd=工作区 → 两条命令 cwd 互斥，照抄必落错目录，应被 redteam 抓出。
