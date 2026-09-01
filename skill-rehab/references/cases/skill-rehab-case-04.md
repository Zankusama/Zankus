# skill-rehab 康复案例 04（跨环境 grep 方言 · 三方审查收敛案例）

- 日期：2026-09-02
- 评估器：包内 scripts/skill_eval.py（v5.0.0，149 分制）
- 症状摘要：pm-strategist 诊断 128/149 A 级，AutoClaw/豆包 两轮对抗审查 + 三方四轮交叉验证，收敛出**总根因=双 grep 环境**（WorkBuddy Bash=toybox 0.8.13 不认 GNU BRE 的或逻辑，用户终端=BSD grep 认）——同一测试命令在不同宿主结果不同，测试假红假绿
- 分级：必改 4 项 / 建议 4 项（用户「全部都修」授权 8 项全做，路线 A：脚本接入运行时）

## 一、症状（修复前）

- 修复前评分：**128/149（A 级）**
- 三方审查暴露 8 项（含 3 个 P0 级必改）：
  - **P0-1 grep 方言**：run_tests.sh 用 GNU BRE 或逻辑，toybox 环境 74/6 红、BSD 80/0 绿——同一命令不同宿主结果不同，测试不可信（AutoClaw/豆包最初归因「AI 管道转义坏了」为误判，方向对但归因错）
  - **P0-2 DR 契约死锁**：decision-record.py 写死 DR-YYYYMMDD 字面量，check_output.py:53 正则要求 DR-数字8位 真日期 → 成品必 FAIL
  - **P0-3 脚本零挂载**：scripts/ 8 脚本不被 SKILL.md 引用，allowed-tools 无 Bash——脚本存在但不进流程=白写
  - P1 级：S4 口语不召回 / KANO 否定前缀被吞 / 僵尸文档（场景路由页.md v2 残留含本机路径）/ README-SKILL 版本失配 / trigger 悬空引用

## 二、修法（按机制，8 项修一验一）

| 未过项 | 分级 | 为什么修 | 对应机制 | 具体改动 |
|:---|:---:|:---|:---|:---|
| P0-1 grep 方言 | 必改 | 测试不可信=诊断结论不可信 | ①确定性转移 | run_tests.sh 行 44/72/79/81 改 `grep -E`；扫描范围补根目录 `*.md` |
| P0-2 DR 契约 | 必改 | 产出过不了自家校验=自相矛盾 | ⑤输出契约闭环 | decision-record.py 加 `DR_DATE=datetime.date.today()` 自动填当天 |
| P0-3 脚本挂载 | 必改 | 脚本存在但不进流程=白写 | ④流程挂载 | allowed-tools 加 Bash；4 核心脚本挂流程步骤；路由表挂 fm-02/05/06 |
| P1-1 S4 口语 | 建议 | 用户口语与关键词 gap=漏接 | ③关键词覆盖 | S4 kw 补「定多少价/什么价/定价多少」；同分并列→MIX |
| P1-2 KANO 否定 | 建议 | 否定被吞=分类反转 | ③语义边界 | norm() 加否定前缀优先，命中→D 档 |
| P1-3 僵尸文档 | 必改 | v2 残留+路径泄漏 | ②残留清零 | 删场景路由页.md；扫描范围补根目录 |
| P1-4 README 失配 | 建议 | 文档与实现脱节 | ⑦文档同步 | README 重写升 v3.0.0；依赖改 json/argparse/datetime |
| P1-6 trigger 悬空 | 建议 | 用例引用过期表述 | ⑦文档同步 | 改 v3 双轨分流表述 |

## 三、复查结果（修复后，五闸门全过）

- 修复后评分：**139/149（S 级，93.3%）**——139 ≥ 128 ✅ 分数无倒退，P0 全过
- ①评估器：139/149 S（剩 4 项非 P0 备选：l3_deterministic_guardrail / l4_alternatives / l4_output_carrier / l5_install_review，P1×3+P2×1 不阻断）
- ②完整性：C1-C5 全过，缺口 0（工具辅助类 + 对话引导特征，六零件骨架 6/6）
- ③实测验收：双环境 80/0 全绿 + 8 脚本 self 全过 + 触发变体 4 例全对 + DR 契约闭环 + grep 方言 0 残留
- ④运行时 R1-R5：run_runtime_tests 3 项全过 + R2 口语触发实测通过
- ⑤履历 schema：check_rehab_report.py 退出码 0 ✅

关键命令与输出：

```
$ env -i PATH=/usr/bin:/bin scripts/run_tests.sh  → 80/0 ALL GREEN（BSD）
$ scripts/run_tests.sh                            → 80/0 ALL GREEN（toybox，修复前 74/6 红）
$ python3 scripts/scene-router.py - <<< "帮我看看定价" → S4 定价与盈利 / B / mid
$ python3 scripts/decision-record.py ... | python3 scripts/check_output.py → 退出码 0 PASS
```

## 四、可复用要点

1. **跨环境实测结论不可直接互否**：任何「我实测 X 你说是 Y」的冲突，先对齐 `which grep` 与 `--version`（toybox vs BSD vs GNU），再谈对错——本案例三方四轮才收敛到总根因，两轮外部报告归因全错。
2. **测试用 `grep -E`，禁止依赖 GNU BRE 或逻辑**：toybox/busybox 不认，同一命令假红假绿=测试不可信；已固化为 skill-rehab run_redteam.py GREP_DIALECT 检测器 + checklist S11 铁律。
3. **P0 定级要跟失效模式绑定**：P0-1 初判「BSD 不认」被证伪，但「失效=漏报（假绿）」坐实，降级不撤——级别可以降，问题不能撤。
4. **路线 A（脚本接入运行时）是「脚本存在≠进流程」的解**：8 脚本从「目录里有」到「SKILL.md 挂载 + allowed-tools 授权 + 自检全过」才真正可机器化验收。
5. **修复履历表格内禁用竖线字面量**：check_rehab_report.py 按竖线 split 单元格，表格里写 `\|` 会拆裂字段致校验失败——改纯文字描述。
