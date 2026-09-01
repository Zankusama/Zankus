---
name: adversarial-grep-dialect
description: 红队夹具 · 故意在测试脚本里依赖 GNU BRE 的 \| 方言（对应 2026-09-01 真实 bug：toybox grep 不认 \|，测试集假红假绿）
version: 0.0.1
---
# 红队测试 skill（故意写烂，勿当真）

tests/run_tests.sh 中：

```bash
grep -c "检查单\|检查项" references/ref-01.md   # 无 -E：BSD/toybox/busybox BRE 方言行为不一致
grep -rn "启动框架\|落地框架" frameworks/       # 同上
```

（应被 redteam 的 GREP_DIALECT 检测器抓出）
