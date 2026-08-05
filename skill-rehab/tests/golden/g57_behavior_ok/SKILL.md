---
name: g57
description: 测试样本——行为层正例（产出载体+收敛终端+运行时校验脚本）
version: 0.0.1
disable: true
---

## 任务
- 按步骤执行，最后必须产出画像。

## 产出载体
- 收敛后必出 `report.html` 画像，模板在 references/report_template.html。
- 单次对话轮次上限 12–15 轮，达根因即输出。

## 运行时行为校验
- 运行 `python3 scripts/check_rag.py` 校验出处，失守退出码 1。
- 验收：判定词满足 + grep 断言通过。
