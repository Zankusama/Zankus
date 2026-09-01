# skill-rehab 行为测试（结构闸门锁死）

> grep 断言风格，对齐 tests/trigger-*.md。锁死「双模式结构闸门」关键机制不丢，防确认闸回潮为软闸。
> 跑法：`bash -c 'grep -nE "诊断/体检模式|治疗模式|re-read 处方产物|对抗式验证闸|Agent B|run_redteam.py" SKILL.md && echo ✅ || echo ❌'`

## 结构闸门（死规矩10 硬升级）
- 双模式关键词存在：`grep -nE "诊断/体检模式|治疗模式" SKILL.md && echo ✅ || echo ❌`
- 治疗前 re-read 处方：`grep -n "re-read 处方产物" SKILL.md && echo ✅ || echo ❌`
- 诊断模式禁写文件工具：`grep -n "严禁调用任何写文件工具" SKILL.md && echo ✅ || echo ❌`
- 治疗须显式触发词：`grep -nE "显式说出治疗触发词|治疗触发词" SKILL.md && echo ✅ || echo ❌`

## 对抗式验证闸（v1.9.0 新增 · 防同源自欺回潮）
- 保底闸 A 接入：`grep -nE "run_redteam.py|盲区召回" SKILL.md && echo ✅ || echo ❌`
- 盲审 B 接入：`grep -nE "Agent B|盲审" SKILL.md && echo ✅ || echo ❌`
- 真盲约束（不传推理链）：`grep -n "不传主 agent 推理链" SKILL.md && echo ✅ || echo ❌`
- 诊断交付物四部分：`grep -nE "评估器分|盲区召回结果|分歧矩阵|可能自证" SKILL.md && echo ✅ || echo ❌`

## 收敛终端
- 诊断产物锁（防静默跳项）：`grep -n "check_rehab_report.py --dir" SKILL.md && echo ✅ || echo ❌`
- 修复履历 schema 独立校验：`grep -n "check_rehab_report.py <履历文件>" SKILL.md && echo ✅ || echo ❌`

## v2.0 新增（治理最小化 · 防指标游戏回潮）
- 指挥意图锚（诊断先绑定用户真实结果）：`grep -n "指挥意图锚" SKILL.md && echo ✅ || echo ❌`
- 反身性体检（防评估器自我维护错误·评估器自我维护探测）：`grep -nE "反身性体检|评估合作|评估器自我维护" SKILL.md && echo ✅ || echo ❌`
- 实测验收改名（设计评审→实测验收，版本记录区除外）：`grep -q "设计评审" <(sed -n '1,238p' SKILL.md) && echo ❌ || echo "✅ 无设计评审残留"`
- G 层次升级已在 design-review.md 落地（执行者与判官分离 / 结构化 trace / 语义质量）: `grep -q "执行者与判官分离" references/design-review.md && grep -q "语义质量评估" references/design-review.md && grep -q "物化执行 trace" references/design-review.md && echo ✅ || echo ❌`
- 评估分降级为证据（方向对错不由分判）：`grep -n "方向对错不由分判" SKILL.md && echo ✅ || echo ❌`

## v2.0 疗程可靠性 + goldens 防固化（防过早完成/防删测试作弊/防基准固化）
- 待修项立验收（默认 failing→逐项 passing）：`grep -n "待修项立验收\|默认 failing\|flip 成 passing" SKILL.md && echo ✅ || echo ❌`
- 禁删/改验证用例图绿（防作弊硬约束）：`grep -n "禁删/改验证用例\|remove or edit tests\|改标准凑达标" SKILL.md && echo ✅ || echo ❌`
- 幂等续跑（只处理未 passing 项）：`grep -n "幂等续跑\|rehab-progress" SKILL.md && echo ✅ || echo ❌`
- goldens 防固化（新鲜重标 + 人工裁决）：`grep -n "goldens 防固化\|新真值冲突\|conflicts.md\|人工裁决" SKILL.md && echo ✅ || echo ❌`
