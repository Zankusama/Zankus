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
