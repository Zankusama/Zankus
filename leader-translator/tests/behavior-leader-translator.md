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

## 未知登记簿与穷尽三查（v5.13.0 断言组 U/T）
- 登记簿检查存在：`grep -nE "缺未知登记簿" scripts/stage-gate.sh && echo ✅ || echo ❌`
- 白名单状态机断言（v6.0.0 更新：原「待澄清」grep 已失效——v5.13.1 脚本移除该字符串，v5.13.1 升版漏改，v6.0.0 修复）：`grep -nE "已裁决｜BLOCKED" scripts/stage-gate.sh && echo ✅ || echo ❌`
- G2 三查断言存在：`grep -nE "穷尽三查" scripts/stage-gate.sh && echo ✅ || echo ❌`
- G4 三查断言存在（收口前独立 diff）：`grep -nE "收口前独立 diff" SKILL.md && echo ✅ || echo ❌`
- 模板文件存在且含路由规则：`grep -nE "查一·目标反推|查二·实体矩阵|查三·反方预演" references/unknowns-template.md && echo ✅ || echo ❌`
- BLOCKED 合法裁决态声明（防 DoR 瀑布化）：`grep -nE "BLOCKED 是合法裁决态|BLOCKED.*恒放行" references/unknowns-template.md && echo ✅ || echo ❌`
- SKILL 步骤2 死规矩：`grep -nE "穷尽三查·挖掘层" SKILL.md && echo ✅ || echo ❌`
- SKILL 语义核验死规矩：`grep -nE "语义核验 v5.13.0" SKILL.md && echo ✅ || echo ❌`
- SKILL 供料跟踪死规矩：`grep -nE "供料到货跟踪 v5.13.0" SKILL.md && echo ✅ || echo ❌`
- SKILL 领导侧收口问：`grep -nE "你觉得还有什么我该问但没问的" SKILL.md && echo ✅ || echo ❌`
- SKILL 执行预演三问：`grep -nE "执行预演（v5.13.0·管理者侧 pre-mortem）" SKILL.md && echo ✅ || echo ❌`
- SKILL Deviations 标准句：`grep -nE "Deviations 段，选保守选项继续" SKILL.md && echo ✅ || echo ❌`
- SKILL 验收回写：`grep -nE "验收回写 v5.13.0" SKILL.md && echo ✅ || echo ❌`

## v5.13.1 结果验收范式断言（组 R）
- 白名单状态机在脚本（两值终态）：`grep -nE "已裁决\|BLOCKED|已裁决｜BLOCKED" scripts/stage-gate.sh && echo ✅ || echo ❌`
- M 行证据锚点强制在脚本：`grep -nE "证据锚点" scripts/stage-gate.sh && echo ✅ || echo ❌`
- 三查归宿化校验在脚本：`grep -nE "→G2补查|→G3盲区|→G4候选" scripts/stage-gate.sh && echo ✅ || echo ❌`
- G6 登记簿终局对账：`grep -nE "终局对账" scripts/stage-gate.sh && echo ✅ || echo ❌`
- 模板白名单图例：`grep -nE "白名单" references/unknowns-template.md && echo ✅ || echo ❌`
- SKILL.md 结果验收范式声明：`grep -nE "结果验收范式" SKILL.md && echo ✅ || echo ❌`

## v6.0.0 四扇门与决策树断言（组 F，grilling 移植一期）
- 四扇门新章存在：`grep -nE "四扇门与决策树" SKILL.md && echo ✅ || echo ❌`
- 四门判据齐全：`grep -nE "门①可查已想到" SKILL.md && echo ✅ || echo ❌`
- 门③采访语义：`grep -nE "门③领导独知" SKILL.md && echo ✅ || echo ❌`
- 门④待原型：`grep -nE "门④未知的未知" SKILL.md && echo ✅ || echo ❌`
- 门牌纠错回路：`grep -nE "挂错顺手改挂" SKILL.md && echo ✅ || echo ❌`
- 粗树建在 G2 收口：`grep -nE "粗树建在 G2 收口" SKILL.md && echo ✅ || echo ❌`
- 查一输出两级树：`grep -nE "决策→所需事实" SKILL.md && echo ✅ || echo ❌`
- frontier 轮语义：`grep -nE "轮=一次重算到下次重算" SKILL.md && echo ✅ || echo ❌`
- 弹窗批定义：`grep -nE "弹窗批=单次交互组件" SKILL.md && echo ✅ || echo ❌`
- 塌缩防护：`grep -nE "frontier 非空不许宣布问完" SKILL.md && echo ✅ || echo ❌`
- 转向制：`grep -nE "转向制" SKILL.md && echo ✅ || echo ❌`
- 位图预算：`grep -nE "位图预算" SKILL.md && echo ✅ || echo ❌`
- 位图只对精树：`grep -nE "精树节点 N>25" SKILL.md && echo ✅ || echo ❌`
- 位图锚点校准协议：`grep -nE "P90 校准" SKILL.md && echo ✅ || echo ❌`
- prototype 判别式标签：`grep -nE "prototype 判别式标签" SKILL.md && echo ✅ || echo ❌`
- 判别式硬条件（V1 修复锁死）：`grep -nE "必要前提，不满足不标" SKILL.md && echo ✅ || echo ❌`
- 待原型挂 BLOCKED：`grep -nE "「待原型」挂 BLOCKED" SKILL.md && echo ✅ || echo ❌`
- G3 唯一出口定位：`grep -nE "主动开维的唯一出口" SKILL.md && echo ✅ || echo ❌`
- 三查对树推：`grep -nE "三查对着粗树推" SKILL.md && echo ✅ || echo ❌`
- 两种漏两种药口径：`grep -nE "两种漏两种药" SKILL.md && echo ✅ || echo ❌`
- 判别实验块：`grep -nE "判别实验" SKILL.md && echo ✅ || echo ❌`
- 判别实验基线注记（V8 修复锁死）：`grep -nE "估计值" SKILL.md && echo ✅ || echo ❌`
- 通用性约束节：`grep -nE "适用前提与通用性约束" SKILL.md && echo ✅ || echo ❌`
- 锚定剥离：`grep -nE "锚定剥离" SKILL.md && echo ✅ || echo ❌`
- 成本对称：`grep -nE "成本对称" SKILL.md && echo ✅ || echo ❌`
- 知识分权：`grep -nE "知识分权" SKILL.md && echo ✅ || echo ❌`
- 显式不做：`grep -nE "不做分任务类型的分叉流程" SKILL.md && echo ✅ || echo ❌`
- 供料=门③：`grep -nE "供料=门③" SKILL.md && echo ✅ || echo ❌`
- 门③采访三出口：`grep -nE "给/挂起/喊收" SKILL.md && echo ✅ || echo ❌`
- 无界追问=流程失败：`grep -nE "无界追问按流程失败" SKILL.md && echo ✅ || echo ❌`
- 事实节点非阻塞核查：`grep -nE "非阻塞核查" SKILL.md && echo ✅ || echo ❌`
- 答案作废显式重开：`grep -nE "显式重开分支" SKILL.md && echo ✅ || echo ❌`
- 过渡期声明（一期脚本零改动）：`grep -nE "过渡期声明" SKILL.md && echo ✅ || echo ❌`
- 模板门牌内联：`grep -nE "门牌" references/unknowns-template.md && echo ✅ || echo ❌`
- 模板第 7 字段依赖：`grep -nE "依赖.*U编号|U编号.*依赖" references/unknowns-template.md && echo ✅ || echo ❌`
- 模板判别实验块：`grep -nE "判别实验" references/unknowns-template.md && echo ✅ || echo ❌`
- ⛔ 旧硬上限已删（负断言，命中=回潮）：`grep -qE "全程提问累计 ≤15" SKILL.md && echo ❌ || echo ✅`
- ⛔ 旧 ≤12 问已删（负断言，命中=回潮）：`grep -qE "共 ≤12 问" SKILL.md && echo ❌ || echo ✅`
- ⛔ 旧「未收」状态词已废（负断言，命中=回潮）：`grep -qE "登记簿该行标「未收」" SKILL.md && echo ❌ || echo ✅`
- 闸门调用显式传参（subagent_03 接口裂缝 V16 修复锁死）：`grep -nE "stage-gate.sh 1 output/gate-1.txt" SKILL.md && echo ✅ || echo ❌`
- ⛔ 旧不带参调用已废（负断言，命中=回潮；用无反引号锚点防转义缺陷）：`grep -qE 'stage-gate\.sh [1-4]（过才进|确认 G1 产物在）' SKILL.md && echo ❌ || echo ✅`
- 模板白名单口径同步（待澄清残留已清）：`grep -qE "无「待澄清」残留" references/unknowns-template.md && echo ❌ || echo ✅`
- ⛔ 死指代已清（R1-N3 锁死，负断言）：`grep -qF "不计入 5 个问题限额" SKILL.md && echo ❌ || echo ✅`
- 判别式操作化阈值（R1-V1 补强锁死）：`grep -nE "连续两轮给不出实质答案" SKILL.md && echo ✅ || echo ❌`
- 定义层轮消歧（R1-V7 残尾锁死）：`grep -nE "与 frontier 轮不同义" SKILL.md && echo ✅ || echo ❌`
- 版本号 6.0.0：`grep -nE "^version: 6.0.0" SKILL.md && echo ✅ || echo ❌`
