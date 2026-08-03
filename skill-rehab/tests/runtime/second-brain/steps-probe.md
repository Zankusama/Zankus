# 跳步骤探测 · second-brain 强制步骤名

> 来源：SKILL.md「动作步序法」节第 135 行（实测）：Ingest Step 0（读 SCHEMA）→ Step 1（获取原始资料）→ Step 2（识别主题）**强依赖**，跳步 → 输出错误；SCHEMA.md 是宪法必须先加载。
> 用途：run_runtime_tests.py 检查 SKILL.md 是否声明了这些强制步骤名（存在与否 = 可机器判）。

## 强制步骤名（SKILL.md 必须出现）

- Ingest Step 0（读 SCHEMA 先行）
- Step 1（获取原始资料）
- Step 2（识别主题）
- SCHEMA.md（宪法，执行前必须先加载）

## 跳步拦截语义（人工复核用，非机器判）

- Ingest Step 0 → Step 1 → Step 2 强依赖，跳步 → 输出错误
- Query Step 1 内部 L1→L2→L3 禁止跳级
