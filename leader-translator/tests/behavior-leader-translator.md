# leader-translator 行为测试（关键机制锁死）

> grep 断言风格，对齐 tests/trigger-*.md。锁死「流程→任务书」关键机制不丢，防死规矩/闸门/防作弊防线回潮。
> 跑法：`bash -c 'grep -nE "..." SKILL.md && echo ✅ || echo ❌'`
> 目的：对话引导类核心交付=「模糊想法→可执行任务书」流程，脚本行为（G1-G6 闸门/KANO 链/防作弊）无回归保护时，改一次丢一处。行为测试把关键机制用 grep 断言锁死。

## 流程闸门（G1-G6 不丢）
- 六道闸门存在：`grep -nE "stage-gate.sh|G1-G6|六道闸门" SKILL.md && echo ✅ || echo ❌`
- 防跳步预检（物理强制）：`grep -nE "防跳步预检|G\(N\) 跑前先查" SKILL.md && echo ✅ || echo ❌`
- G6 自动调 coverage-check（防偷删物理接线）：`grep -nE "coverage-check|防偷删" SKILL.md && echo ✅ || echo ❌`
- 脚本化声明节（可机器化验收）：`grep -nE "可机器化验收|脚本化声明" SKILL.md && echo ✅ || echo ❌`

## KANO 降级链（未知管理机制不丢）
- 降级链存在：`grep -nE "KANO 降级链|M→O→I" SKILL.md && echo ✅ || echo ❌`
- 偏置铁律（不确定默认 M）：`grep -nE "宁多问不漏问|偏置" SKILL.md && echo ✅ || echo ❌`
- KANO 分类声明（G4 校验）：`grep -nE "KANO 分类声明" SKILL.md && echo ✅ || echo ❌`
- R 型禁问：`grep -nE "R 型禁问|这还用问我" SKILL.md && echo ✅ || echo ❌`

## 防作弊防线（guard/基线不可退不丢）
- 判卷冻结（防作弊主防线）：`grep -nE "guard.sh|判卷|基线不可退" SKILL.md && echo ✅ || echo ❌`
- 暗卷自留：`grep -nE "暗卷" SKILL.md && echo ✅ || echo ❌`
- 验收三问（出处锚定/防凑数/风险定档）：`grep -nE "acceptance-check|验收三问|出处锚定" SKILL.md && echo ✅ || echo ❌`

## 来源必带（调研/补盲证据链不丢）
- 工具强制+来源必带：`grep -nE "来源必带|无来源=没调研|待查清单" SKILL.md && echo ✅ || echo ❌`
- 外部知识分级（A 证据级/B 推断级）：`grep -nE "A 证据级|B 推断级|未验证" SKILL.md && echo ✅ || echo ❌`
- 补盲外部盲区优先：`grep -nE "外部盲区优先|💡" SKILL.md && echo ✅ || echo ❌`

## 危险操作防护（可逆性分级不丢）
- 分级存在：`grep -nE "🟢|🟡|🔴" SKILL.md && echo ✅ || echo ❌`
- 注入防护：`grep -nE "注入防护|当数据处理" SKILL.md && echo ✅ || echo ❌`

## 运行时校验脚本存在（行为层机器强制）
- stage-gate.sh 存在：`test -f scripts/stage-gate.sh && echo ✅ || echo ❌`
- goal-lint.sh 存在：`test -f scripts/goal-lint.sh && echo ✅ || echo ❌`
- guard.sh 存在：`test -f scripts/guard.sh && echo ✅ || echo ❌`
- coverage-check.sh 存在：`test -f scripts/coverage-check.sh && echo ✅ || echo ❌`
- G4 ⚠️ 清零判定词（v5.12.0 修复锁死）：`grep -nE "还需|仍需" scripts/stage-gate.sh && echo ✅ || echo ❌`
- G4 逐片段判定（v5.12.0 修复锁死）：`grep -nE "grep -oE '⚠️\[\^⚠️\]\*'" scripts/stage-gate.sh && echo ✅ || echo ❌`
- guard.sh 目录指纹（v5.12.0 修复锁死）：`grep -nE "dir_hash" scripts/guard.sh && echo ✅ || echo ❌`
- G6 真调 coverage-check（v5.12.0 修复锁死，防文档声称≠实现回潮）：`grep -nE 'coverage-check\.sh" "\$COVERAGE_FILE"' scripts/stage-gate.sh && echo ✅ || echo ❌`
- PROD_LINES 排除命令行（v5.12.0 修复锁死）：`grep -nE "命令行" scripts/goal-lint.sh && echo ✅ || echo ❌`
