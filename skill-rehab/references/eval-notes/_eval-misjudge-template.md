# 误判案例 {NN} — {误判类型：假阳性/假阴性}

> 本文件是**模板**：确认评估器误判后，复制本文件为 `eval-misjudge-{NN}.md` 填实例。
> 死规矩：「修正动作」必须是**已实施**的（指向具体文件改动），不许写「待办」。
> 未修的误判只留工作区 `output/` 工作记录，不入库。

- 日期：YYYY-MM-DD
- 评估器版本：包内 scripts/skill_eval.py（`__version__` + sha256 前缀至少 8 位）
- 误判类型：假阳性（判过但事实不符）/ 假阴性（该过的没判过）
- 涉及判定点：`{原理}.{检查项}`（如 `p8_apex.trigger_boundary`）

## 一、评估器判了什么

- 判定结果：passed=True/False
- 判定依据（关键词/正则命中）：贴出命中的词或模式

## 二、事实是什么

- 内容真实情况：为什么该判定与实际不符（一句话说清事实）
- 证据：贴样本内容/命令输出

## 三、修正动作（已实施）

- 改动文件：`scripts/skill_eval.py`（版本 x.y.z）或样本 `tests/golden/gNN_*/SKILL.md`
- 具体改动：改了什么（如「check_pattern 返回值取 [0]，修复元组恒 truthy」）
- 验证：guard.sh 四步（snapshot → 改 → check + run_goldens 全过 → snapshot 重置）+ 新增/调整的 golden 样本

## 四、复用要点

- 这类误判下次怎么防（检查同类调用处 / 审计清单项）
