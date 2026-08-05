---
name: g56
description: 测试样本——声明验收脚本但脚本不存在（l4_judgeable_acceptance 反例）
version: 0.0.1
disable: true
---

## 任务
- 按步骤执行，最后验收。

## 验收标准
- 运行 `python3 scripts/check_ghost.py` 验证输出，退出码 0 才算通过。
- 用 grep 断言产出物存在。
- 未过项判定：验收命令存在且可执行。
