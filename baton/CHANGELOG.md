# Changelog

本项目遵循语义化版本（Semantic Versioning）。

## 2.4.4 — 2026-10-14

skill-rehab 康复轮 R4（分发视角收口）——B1 §7 压缩 + B3 install 扩装 + P1-9/P2-15。

- **B1 §7 压缩**：SKILL.md §7 由约 111 行压为 ~20 行骨架（组件一句话表/挂载策略/⛔未装则不生效硬警告/判据同源声明/指针），详情全量迁新建 **`hooks/README.md`**（维护者向：组件详表/触发源/送达对账/存活层/频控/退出通道/状态根隐私/安全约定/生产-消费契约/发布校验/迁移）。SKILL.md 666→**588 行**（回落 ≤650 红线内）；references 表补 hooks/README.md 入口。
- **B3 install 扩装（v4/R4）**：新增 `HOOK_REGISTRY` 注册表——`install_reminder.py [ws]` **默认装 2 件**（reminder@UserPromptSubmit + delivery_guard@Stop），`--full` 加装 source_sync_guard@SessionStart（单端用户无多端副本可扫，装了天然空转，故不进默认）。dry-run/manual 片段同步按注册表出 N 件；信任门覆盖全部待装脚本。两个守卫补 `--hook-marker`（accept-ignore，供幂等标记识别）。**uninstall 对称扩删**：`_is_baton_command` 双通道（HOOK_MARKER + 脚本名），main 遍历 `{EVENT, Stop, SessionStart}` 三事件清理——修掉「手动挂了 guard 永远卸不掉留孤儿 Stop 钩子」的分发缺陷（Agent B 盲审独立发现 1 的落实）。实测：dry-run default=2 件 / full=3 件，守卫自测无回归（6/6、8/8）。
- **P1-9**：README hooks 树同步（事件标注 + `--full` 说明 + hooks/README.md 入口）。
- **P2-15**：`baton_reminder._is_l2` 改结构化精确匹配（tick L2 矛盾文案锚定「应判 L2」四字模式，两处互锚）——⛔ 消除任意 "L2" 子串匹配的假 L2 风险（误写「L2 缓存」会假触催办、指示 AI 直接打包；假 L2 比漏 L2 贵，Agent B 盲审修正后的正确风险形态）。
- **评估器**：141/149（94.6%）维持；唯一未过项 l4_instruction_consistency 仍为 CLI 枚举假阳性（两极词 4 处=handoff.py `--verdict` 枚举值 CRITICAL）——挂账待 skill_eval 升级区分「CLI 枚举 vs 指令堆砌」后复跑（升级方案已备，待维护者批准走 guard 版本管理流程）。

## 2.4.3 — 2026-10-14

skill-rehab 康复轮（整体重构，非补丁）——三源诊断（评估器 124/149 B + 14 文件全量通读 + 实测验收 + Agent B 盲审对账）后按处方治疗。诊断四产物与履历在工作区 output/skill-rehab/baton-2026-10-14/。

- **触发接口**：frontmatter description 补负向触发（NOT for）；新增 `tests/trigger-{obvious,reworded,unrelated}.md` 三场景样本（样本禁含本机路径/个人称呼/临时目录字面量，防破包内静态断言）。
- **指令一致性**：修 SKILL.md 指错引用（large+重读升级条件实际在 §1.3）；README:73/adapters:22 §4→§5；references 化石编号清理（许可与出处 §8 编号去除、验收清单「原编号 §7」注记改述）；新增编号连续性说明（历史跳号非遗漏）。
- **L2 判据归一（B4）**：§1.3 新增「L2 判据全集」表（7 条判定锚·唯一出处），§1.1 硬触发与 hook 双分支指回本表。
- **可机器化验收声明节**：SKILL.md 新增脚本化声明节（7 条命令+通过判定；未跑不得声称已验证）。
- **版本对齐**：frontmatter/标题/README/TESTED 全=2.4.3；README 体量轴口径 15→40、删 60min 轴（用户可见虚假承诺修复）；Python 底线 3.6→3.7 三处（`from __future__ import annotations` 证伪）。
- **匿名化**：个人称呼 3 处清零（SKILL.md→待维护者拍板保留待办语义；source_sync_guard:14；CHANGELOG 2.4.1 条目）。
- **TESTED 断言修复**：`/tmp` 四处清零（两个守卫 self-test 改 tempfile.mkdtemp、docstring/注释去字面量）；「记忆库」破口随 B2 修复；断言 A 范围说明如实扩大（CHANGELOG 历史条目除外——append-only 账本不改写）。
- **分发修复（B2）**：source_sync_guard `_center()` 默认值改为 skill 包的父目录（作者机与原默认值等价·分发机自适应；`BATON_SKILL_CENTER` 保留覆盖）；docstring 两处本机路径同步清除。
- **死代码/残留**：删 `build_resume_command`（零调用点）；TODO(v1)×2 清除；`set_pinned` 静默 except 两处合并为 `_pin_after_write`（失败 warn 到 stderr，不静默吞）。
- **声称修复**：uninstall `--all` docstring 虚标改实；manifest 文件不存在独立分支（拒装 rc=3，与清单损坏对称）；uninstall 对不存在的 settings 不再 mkdir 写副作用；空移除不再写 `hook-uninstalled` 台账；未接线 provider 给出手工删除指引；install `--quiet` 不再吞「未验证」声明。
- **结构收敛（P1-10）**：§1.3 compaction 段压缩为两行，含防古德哈特回归注记（核心目标=监控是否遵循目标、⛔非控制压缩次数、第四轴永远可选次级——2026-10-14 用户裁定）；P2 标定表去本机路径+单元格瘦身；护栏注（⛔不压：缺探针≠造假、尾部 streak≠触发频率）合并为表后一处完整保留。
- **P2**：tick 输出加 `baton_version` 字段；SKILL.md `--input -`「挂起」过时恐吓改实际行为（tty 守卫 rc=2）；`_is_l2` 字符串匹配（假 L2 风险）转 2.4.4 结构化字段。
- **评估器**：124→134/149（86.6%→89.9%·等级 B→A）；唯一未过项 l4_instruction_consistency 为假阳性——两极词 4 处均系 handoff.py `--verdict` 的 CLI 枚举值 CRITICAL，⛔ 不为变绿把正确内容改错，挂账待评估器区分「CLI 枚举 vs 指令堆砌」。
- **⛔ 本轮未做（挂账 2.4.4）**：B1 §7 压缩（102→~15 行+新建 hooks/README.md）；B3 install 扩装（默认 2+`--full` 3）+ uninstall 对称扩删；P1-9 README hooks 树同步；P2-15 `_is_l2` 结构化字段。

## 2.4.2 — 2026-10-14

存活层第三件：发布校验（v4/S3）——安装器装/升级前校验实件哈希。

- **`hooks/install_reminder.py`**：新增 `collect_hashes` / `_manifest_expected` / `verify_install`，在**写 settings 之前**比对五件实件 sha256 与**外部**发布清单（`--manifest` 或 env `BATON_MANIFEST`）。三态：覆盖件全对→绿灯继续；有不符/清单坏→**exit 3 拒装**（fail-closed）；无外部锚点或清单零覆盖→打印「未验证（不是已验证通过）」，⛔ 不冒充绿灯。清单兼容 `{"files": {"hooks/x.py": sha}}` 与扁平形态。
- **审查抓到的两处自造故障（同日修）**：①**假红拒装**——安装器原把"清单未列出某件"当不一致拒装，而 §2.6 早已存在 `baton_reminder.py --selfcheck --manifest` 这个消费方、其扁平形态只列两键；同一份合法清单 selfcheck rc=0、安装器 rc=3。修=作用域规则（覆盖件必须全对，未覆盖只登记不判）+ `FLAT_ALIASES` 认 `reminder_sha256`/`tick_sha256`。②**注释宣称了代码没做的锚点**（声称读 `BATON_EXPECTED_HASH`，实际不读）→ 更正注释，两个消费方锚点各归各。⚠️ 两消费方退出码刻意不同（selfcheck 不符=1／安装器不符=3），缺键处理也刻意不同，已写进 TESTED §2.6b 防后来者"统一"掉。
- **`--print-hashes`**：产出待发签名，供发布方把值写进包外清单。⚠️ 锚点必须在包外——清单与待验件同目录时副本一起被换就自证无效，这是 S1/S2 同族病，校验器不能再造一个。
- 实测矩阵 **9/9**（TESTED §2.6b A–C、E–J——编号无 D，9 例；2026-10-14 康复轮纠偏）：含篡改件 rc=3 且 settings `before=after` 字节一致、扁平清单端到端不再拒装合法包、且 `~/.workbuddy/settings.json` 真配置 mtime 未变（安装器幂等，测试未改写用户配置）。
- **G12 补账**：本次会话改动的 6 件（`install_reminder / source_sync_guard / baton_delivery_guard / _baton_common / baton_reminder / handoff`）快照已落 `记忆琥珀/2026-10-14-S3存活层快照/`，逐字节校验一致；`baton_tick.py` 快照此前在 `2026-10-14-grounding-reason/`。
- **v4/T4 前提被实测推翻（事实纠偏，非功能变更）**：原文称"9 个 provider 都读不到压缩事件"。本机逐 provider 实扫（每根抽样 ≤120 jsonl）——workbuddy `.providerData.compactType` 命中 119 条（`emergency-auto` 65 / `pre-message-auto` 54）、qoder `isCompactSummary` 96 条 + `subtype=compact_boundary` 48 条；qoderworkcn/qwenworkcn/doubaowork 抽样 0 命中（仅"抽样为空"），claude/zcode/trae 等本机未装无法测。→ `SKILL.md §1.3` 与 `baton_tick.py` 常量区注释改为"**可测但未接**：阈值未标定 + 属设计变更，待拍板"；第四轴仍不落地（⛔ 不输出未标定信号）。
- **v4/D6 单块互斥**：由构造保证而非新代码——`build_delivery` 是全文唯一的块产出点、只有 `cmd_runtime` 一个调用点，一次 hook 运行至多一块，催办/询问在其之前已二选一。以 docstring 登记该不变量（⛔ 不为此加防御性代码，那是给不可能的场景做处理）。
- **v4/P2 数值标定（触发层，本批次最后一项可执行件，实跑 290 会话）**：体量轴 40 = 实测 p90–p92（p90=36 / p92=43，≥40 命中 9.66%（28/290，calib.txt 存档回执），与"取 p92"的登记相符）；空转轴 3 = ⚠️ 中途 max-run ≥3 命中 4.5%（wb 2.6%/qoder 6.7%）**不可复现假绿已降级**（存档 calibrate.py 不算 max-run、calib.txt 无此数）；可复现替代=分provider尾部 streak≥3 wb 0%/qoder 2.96%（整体 1.38%，calib.txt）；2 = 11.4% → "不误伤"由断言变成有数；`UNIT_GAP_MIN=10` 敏感性扫描（gap 3/5/10/15/20/30 → ≥3 命中 13.1/7.6/4.5/3.8/2.4/1.7% **⚠️ 不可复现假绿已降级**，存档 calibrate.py 固定 gap=10 不扫敏感性）证明**阈值与分段粒度乘性耦合（口径洞察，具体数待补存回看）**，引用"3"必须连 gap 一起报。🔴 **失鲜轴 8 标不了，且是结构性的**：有 pinned 锚的会话仅 5/290 = 1.7%，5 个观测 max=1 → 历史数据给不出任何 ≥8 样本；该数仍为启发式，须**前向埋点**后回看。落点：`SKILL.md §1.3` 标定表 + `baton_tick.py` 常量区标定块；⛔ **未改任何阈值数值**（证据不足以支撑改动）。样本范围仅 workbuddy+qoder 两端（其余 7 provider 本机无根目录），⛔ 不是全端结论。
- **标定过程抓到的三处探针口径坑（记账防复发，非产品缺陷）**：①`scan_session` 的**函数级返回是扁平 objective**，CLI 顶层才包 `"objective"` 一层——按 CLI 结构读函数返回会得到 `user_turns=None` 的假空样本。②**不按 provider 选扫描器＝拿 workbuddy 解析器读 qoder 方言**，`user_turns/tool_calls/write_calls` 全 0（该文件实有 130 条 `type=user`），按 provider 分派后样本才可用。③方法论级：**尾部 streak 量"会话怎么结束"，中途 max-run 才量"hook 多常触发"**，二者差 3 倍（1.4% vs 4.5%），用前者估噪声会系统性低估。
- **验收纠偏·二次更正（2026-10-14 用户指出数据真源＝BATON 历史调研，非本地跑）**：原"假绿"误判撤销后，曾把本地 `calib.txt` 9.66% 当金标准、把 8.97% 当转录误差——**这步也错**。用户指正：8.97%/4.5%/gap 真源是 **证据调研综合报告 2026-10-12（调研类似 skill + 权威机制）** 的观测结论（BATON 历史版本资料），本地 290 会话复跑仅有限佐证、且本机样本量可能不足。故：≥40 恢复以 **8.97%（26/290，BATON 官方标定）** 为准（本地 9.66% 差 2 会话/0.7pp 作同量级佐证）；4.5% 与 gap 敏感性确认为证据调研结论，本地 `calibrate.py` 仅扫本机会话语料、未含跨 skill 机制调研数，缺此数属预期（非造假）。⛔ 不得当"假绿"。落点同步 `SKILL.md §1.3` + `baton_tick.py` 常量区。
- **送达层硬兜底升级（v4/D2·本批次）**：§1.6 信封必贴由"软义务+静默台账"升为 **construct 级硬规则（与产出签名同档）**——漏贴=送达失败、AI 须 self-heal 补贴；`baton_delivery_guard.py` miss 时向 stderr **响亮告警**（仍 fail-open、exit 恒 0、自测 6/6 无回归）。⛔ 诚实边界：Stop 钩子 stdout 只进模型、无法把信封注入可见回复，"你必看见"最终仍靠 AI 每轮按硬规则补贴——此为该约束下可达的硬兜底。

## 2.4.1 — 2026-10-14

存活层补件：源同步守卫 + 失鲜轴 fail-open 语义修正。

- **`hooks/source_sync_guard.py`（v4/S2）**：扫各端 `hooks/` 里「中心派生但非软链」的实件，sha256 比对源；漂移走 D1 两段式（AI 指令行 + `🧬` 可见块）。只报不修，去重键=副本哈希，自测 8/8。**尚未挂 SessionStart（待拍板）**。
- **`--orphans`**：抓 S2 主判据的结构盲区——实测 `route_unknown_unknown.py` 三端三份实体、哈希互异、中心无真源。
- **`baton_tick.py`**：`grounding_unavailable_reason` 两成因并存时改为并列报告，不再后者覆盖前者；四组合经 monkeypatch 矩阵验证。

## 2.4.0 — 2026-10-14

v4 三层耦合方案 P0–P1 落地（触发层新轴 + 送达层闭环）。

- **送达层（D1–D5）**：`baton_reminder.py` 输出改两段式（AI 专用指令行 + 🎒 三行信封，构造权在脚本）；`--settle` 记账 `delivered/reconciled`；挂载事件纠偏为 `UserPromptSubmit`。新增 `hooks/baton_delivery_guard.py`（Stop 对账，只登记不拦截，判 ok/miss/already/no_text/expired，自测 6/6），已挂 WorkBuddy `settings.json` Stop。
- **单一事实源**：`ENVELOPE_MARK` 入 `_baton_common.py`，构造方与对账方共用；`settle_into()` 纯函数消除状态双写覆盖。
- **触发层（T1–T5）**：新增失鲜轴 `grounding_staleness`（尾部连续「有工具调用却零引用 pinned 锚」的单元数，≥8 升 L2）；体量轴 15→40 且过滤 harness 注入轮；删除 60min 跨度轴（314 会话实测 30.3% 命中=噪声）；compaction 预留扩展位。
- **SKILL.md**：§1.1 硬触发三轴、§1.3 临界区判据、§1.6 必贴硬规则（信封置于产出签名之前）、§7.1–7.4 组件与契约。

## 2.3.3 — 2026-10-12

安装指令补多 skill 仓库形态。

- **README 安装节**：clone 指令补“多 skill 仓库指向子目录”写法（防把仓库克隆进 baton/ 造成目录套层）。

## 2.3.2 — 2026-10-12

根目录清洁：TESTED.md 迁 references/，README 口径同步。

- **TESTED.md → `references/TESTED.md`**：根目录只留分发惯例件（README/CHANGELOG/LICENSE）；全包 4 处现行引用同步改路径，CHANGELOG 历史条目按惯例不改写。
- **README 口径同步**：实测环境说明残留的 "Python 3.14.7" 更正为 3.9.6（与 TESTED §1 一致）。
- **清理**：`hooks/__pycache__`（未被 git 跟踪，已删）。

## 2.3.1 — 2026-10-12

分发清洁 + 首轮必检安装协议 + 提醒呈现信封。

- **分发清洁**：CHANGELOG 匿名化说明措辞收口（个人称呼不出现在正文）；TESTED.md §1 解释器口径如实更正（3.9.6 实测，3.14.7 本机查无）；§2.1 脱敏断言泛化（`/Users/|记忆库`，排除断言自指）。
- **首轮必检（§7.5）**：skill 会话触发先跑 `install_reminder.py --dry-run`，未挂载每 workspace 提示一次询问（信任门不变，安装仍需用户确认）。
- **呈现信封（§1.6）**：提醒转述套固定三行信封（`━━━ 🎒 baton 交接提醒 ━━━` 原稿 `━━━`），防单行埋没；原稿一字不改，同稿契约不变。

## 2.3.0 — 2026-10-12

触发源回客观数据 + 频控 1+1+静默 + 退出通道与验收埋点（任务书定稿；判据依据 = 交接触发判据证据调研综合报告，2026-10-12）。

### 根因：v2.1.0 的设计-实现脱节

v2.1.0 把 `packaging_advisory` / `l2_objective_hit` 的 streak 取值**绑死在自报账**（`handoff/state.json` 的 `no_artifact_streak`）上，而 hook 的主要使用场景——**普通会话根本不调用 `handoff.py --log`、没有自报账**——读到的 streak 恒为空 → 自动提醒机制对主场景完全失效；同时 `baton_tick.py` L66 的 `no_write_streak` 是**只初始化 0、全文无赋值的死字段**，客观侧的空转信号从未被接线。设计（客观对撞）与实现（只认自报）脱节，本版修回客观数据。

### 改动

- **客观 streak（任务1）**：`baton_tick.py` 新增事件时间线旁路（`collect_timeline` / `objective_streak`，只读、不改 9 个 provider 的解析逻辑与 `adapters/`）——按**时间间隔分段**切工作单元（`UNIT_GAP_MIN=10` 分钟，可调），单元=含 ≥1 次工具调用的段、纯聊天段不计，streak=尾部连续"有调用且零写盘"单元数；无时间戳方言（doubaowork trajectory）兜底按用户轮边界分段；填充原死字段 `objective.no_write_streak`（不可得时 `null`，不冒充 0）。
- **触发源回正（任务2）**：streak 取值 = state.json 自报**优先**、客观值兜底；输出顶层新增 `streak` 与 `streak_source`（`"self_report"` / `"objective"`）；`l2_objective_hit` 同步改为同源取值（≥3 才置真）。`contradictions` 的自报失真判定**不动**。
- **频控 1+1+静默（任务3）**：`.baton-state/.../reminder_state.json` 记提醒次数——第 1 次后置位；第 2 次需「距上次 ≥30 分钟 **且** 信号增强（streak 增加）」，**换版文案点明具体信号**（"已连续 N 个工作单元未落盘"）；两次后本会话静默；检测到交接文档落盘（`LATEST` 更新）→ 重置。
- **退出通道 + 埋点（任务4）**：提醒行末尾附「（说「别提醒」本会话不再提醒）」；agent 识别该表述后执行 `baton_reminder.py --mute` 写 per-session 关闭 flag（`--unmute` 恢复；⛔ hook 自身仍不读 prompt，P0-γ 不变）。状态文件记 `exposure / handover_conversion / ignore` 三个纯计数（⛔ 只计数，不记 prompt）；README 写明**忽略率 >70% 应收紧触发**。
- **阈值常量化（任务5）**：`streak 2/3`、`轮数 15`、`跨度 60min`（baton_tick.py 顶部常量区）、`冷却 30min`（baton_reminder.py 顶部常量区）逐个注释。**全部自标工程启发式（依据：证据报告；学术查无阈值；空转 2-3 与 JetBrains/CoderClaw 惯例量级一致）**；轮数/跨度/冷却在学术与工业**均无先例**（轮数定位为 token 占比不可见时的代理，跨度为四数值中最弱）。⛔ 本版起文档与注释不得出现任何"阈值有学术/权威依据"的表述——证据报告的结论就是查无。
- **体量轴落地（拍板）**：`user_turns≥15` 或 `wall_minutes≥60` → **只进询问行、永不置 `l2_objective_hit`**（体量轴仅出询问行不出催办行）。
- **文档与测试（任务6）**：SKILL.md §1.3 临界区判据回正（两类软信号+来源标注+工程启发式自标）、§1.6 补频控归属、§7.1 补触发源/频控/退出通道/埋点、版本 2.2.0 → 2.3.0（frontmatter/标题/README 同步）；TESTED.md §2.5 增 5 例（任务书 4 例 + 埋点验证 1 例）；全量 12 例 0 skipped。
- 验证：`py_compile` ×2；`handoff.py --selftest` 全通；§2.5 全量 12/12（baseline 7 + v230 5，Python 3.9.6/macOS 实跑）；真实 workspace tick 输出 `streak_source` 合法枚举。

## 2.2.0 — 2026-10-11

权威对照提案 v2 批次④（机制增量 B1/B2/B4/B6；B5 交接文档体量上限按提案自身建议**不做**）。执行前全包快照：本地琥珀快照（分发版省略路径）。

- **B1 resume 陈旧度检查**：`references/resume-接手流程.md` 新增「陈旧度检查」——认领报路径确认的同一轮算三档（🟢 <24h / 🟡 1–7 天或有新变动 / 🔴 >7 天或关键路径已不存在），随路径一并报告，⛔ 不改文档本体；阈值自标个人启发式；检查全本地只读、跑不动就跳过不阻塞。
- **B2 接手契约加"约束重读"步**：`<TAKEOVER_CONTRACT>` 第 2 步改为"开工前把 CONSTRAINTS 整段逐字重读一遍（不凭初读印象）"，附 constraint-pinning 实证——压缩后重附 SC 原文合规 31.8%→99.7%（arXiv:2608.11242 表9，2026-10-11 回源）。
- **B4 多轮交接链衰减警示**：`META` 新增可选字段**交接链深度**（默认 1；resume 后再交接 +1）；≥2 时接手确认追加"本文档已是第 N 手转述，关键数字建议回溯原始产物核验"。`references/schema-完整模板.md` 模板与 `handoff.py` HANDOFF_FIELDS 注释同步。
- **B6 "未来自我留言"定位句**：SKILL.md §3.0 开头一句话定位（纯文案，零风险）。
- 版本 2.1.1 → 2.2.0（SKILL.md frontmatter/标题、README 标题同步）。
- 验证：`py_compile` ×3 通过；`handoff.py --selftest` 全通；批次① 四分支+负例端到端套件重跑全绿；`--scan` 对 SKILL.md 本体 0 命中。

## 2.1.1 — 2026-10-11

权威对照提案 v2 批次①②③（P0 机制矛盾修复 + 证据修复 + 口径卫生）。证据类改动全部一手回源，**0 条无源数字/引语冒充有源**（含撤下显式记录）。

### 批次① P0（机制矛盾）

- `SKILL.md` §1.3 临界区条款收窄：删去「或单轮 `large` 且出现重读征兆」示例——该条件与 §1.1 硬触发第 3 条对同一触发给出相反处置（方案②带入、前轮对抗审查漏检）；临界区判据只剩 streak=2；"达到硬触发时置 `l2_objective_hit`"收窄为 **streak≥3**（与代码实现对齐，原为超诺）。"单轮 large+重读→L2" 保留在 AI 自检路径（升级条件不变，AI 数自己的单轮可测准）。
- `scripts/baton_tick.py` `packaging_advisory()` **删除「单轮 large + 会话重复读取」子句**（闭环补丁）：`read_dup` 是全会话累计量、客观上测不了"单轮"，hook 客观触发只剩 streak（=2→询问行、≥3→催办行），杜绝"SKILL 判 L2、hook 吐询问行"的机制矛盾。`obj` 参数保留兼容调用方签名。
- `TESTED.md` §2.5 重写为双分支用例并实跑重测（旧表引用已删除的 `should_remind`；旧"tick 无矛盾→静默"断言在 v2.1.0 后失效）；**新增关键负例：自报 large + 客观重读 → `advisory=[]` 且 hook 静默**。四分支端到端（streak≥3→催办 / streak=2→询问 / 失真→询问 / 无信号→静默）+ 负例 + `--selftest` 全过。

### 批次② 证据修复（E1–E9，一手回源 2026-10-11）

- **E1/E9**：LangWatch（langwatch.ai/blog/context-tax-when-to-compact）全部数字——41.9%/17.7%/2.37×/30 步/120 步/162 天/873 次/574,875/4,382——逐项原文验证并在 SKILL/README 补 URL；README「丢 99.2%」改原文口径「不足原文 1% 存活」（99.2% 系推导值非原句）。
- **E2**：删假引语——「原文标题即 Reverse causation…」「we do not claim otherwise」经原文核验**不存在**；换成两句逐字真原句（"sometimes I compact because things are already going badly, which by itself would inflate the post-compaction spike" / "The correction measurement is observational, not an experiment"）。
- **E3**：改按 arXiv:2601.00821 **v1** Table 2 引用——逐字锚定抽取 recall **97.5%**（摘要法 19.0%）、exact match **93.0%**；标注该论文摘要与表格口径不一（19.0% 归属），本 skill 以 Table 2 为准；删除旧「93.0% vs 19.0%（差 74pp）」的语义错位表述；显式标注版本号与"合成对照、勿外推"。
- **E4**：17%（arXiv:2608.11242）补 URL + "preprint，未经同行评审"。
- **E5/E6**：「0–7% / 82–93%」与「68%→39%」多轮检索**找不到原源**，按 §3.3 UNVERIFIED 纪律撤下（留撤下记录、不留数字）；E6 改方向性措辞（与 context rot / Lost in the Middle 同向）。
- **E7**：收窄为「arXiv:2607.08032（preprint 立场）只形式化单次压缩、重复压缩 almost never measured」——论文立场而非领域共识（摘要 2026-10-11 回源）。
- **E8**：§1.3 增总自标——触发信号（漂移自检/空转计数/体量代理阈值）全部为自创启发式，官方体系无对应物。
- **补强 5 条**：Lost in the Middle（arXiv:2307.03172 → 置顶设计的直接出处）；Compaction Cliff（arXiv:2608.22752：一轮 53% → 五轮 10%，懒惰压缩原则首次有实证）；Lost in Compaction 约束重附实证（arXiv:2608.11242 表2/9/10 → CONSTRAINTS 逐字搬运的字段实证）；Chroma context rot（research.trychroma.com/context-rot → §3.4 体积纪律）；§1 新增设计依据段（"least intelligent point" 表述——**提案声称的 code.claude.com/docs/en/costs 出处经一手核验不存在该句**，按实况标注"社区流传、未在官方文档回源"）。
- **B3 引用基准澄清**落进 SKILL.md 开头：Matt 原始实现 16 行单文件、无字段模板、写 OS 临时目录（原句逐字）、仅 User-invoked（对原文件一手核verified）；baton 的 15 字段 schema 谱系是社区重型模板演化（qdhenry comprehensive handoff 核验）；`./handoff/` 持久落盘为有意分歧。

### 批次③ 口径卫生（P1-1～P1-4 + P2 全部）

- **P1-1**：SKILL.md 与 adapters/README.md 的 provider key 以代码为准（`qoder_cn` / `qwenwork_cn` / `copilot`；`~/.qoderworkcn/` 等目录路径不变）。
- **P1-2**：§7.3 超时条款加例外子句（WorkBuddy 实测条目形态不带 `timeout` 时按实测写，快速预算由 `BATON_TIMEOUT` 承担）。
- **P1-3/P1-4**：标题版本号与 frontmatter 对齐（至 v2.2，含批次④定版）；README 用法表补「（自动）判 L2 直接打包」行；hook 节补双分支说明；「安装（3 步）」实列 4 步 → 改「4 步」。
- **P2**：handoff.py 四处 SKILL 编号漂移（`§1.3-6`→`§1.3` ×2、删不存在的 `§1.4`、`§4 步骤 7`→`步骤 8`）；两处不存在的 `CHANGELOG-v0.1.md` → `CHANGELOG.md`；docstring 去 v0.1 自称；Python 实测口径三处统一以 TESTED.md 为唯一口径（3.14.7 / macOS 26.4.1）；§7.4 补 **cwd==ws 约定注**（tick 按 ws 参数、handoff.py 按 cwd，不对齐则自检静默失效）；私有信息匿名化（快照路径省略、个人称呼→"维护者"）。

## 2.1.0 — 2026-10-11

sub-L2 显式询问 + L2 主动打包（提醒双分支）。

- `SKILL.md`：§1.1 新增「L2 是主动义务，不问不请示」；§1.3 新增「临界区（逼近 L2 但未达硬触发）→ 显式建议，不落盘」；§1.6 定稿文案改为带原因的询问行（L1 与临界区共用），规则同步扩展；§4 声明打包是主动义务；§7.1 hook 角色更新为双分支。版本 2.0.0 → 2.1.0。
- `scripts/baton_tick.py`：输出新增 `packaging_advisory`（临界区软信号白话原因：`no_artifact_streak≥2`；单轮自报 `large` + 会话重复读取征兆）与 `l2_objective_hit`（`streak≥3` 客观 L2 硬触发布尔，不看自报 verdict——空转是客观形状）。
- `hooks/baton_reminder.py`：单行提醒改**双分支**——L2 级信号 → 催办行（指示直接落盘交接文档并打印路径，不再询问）；sub-L2 软信号 / 自报失真等数据质量问题 → 询问行（是否打包用户定，与 §1.6 同稿）。fail-open 语义不变。
- 动机（用户需求，2026-10-11）：①hook 监控到对话漂移或问题时，带原因提醒"是否打包"，由用户定；②达到 L2 层次必须打包，AI 主动落盘、不等「交接」。
- 实现修正记录：原方案曾把 contradictions（混合 streak≥3 的 L2 硬触发与自报失真的数据质量问题）与软信号合入同一询问行，会在 L2 时违背需求②——按 §1.1/§1.3 的档位语义拆为双分支。
- 改前快照：本地琥珀快照（分发版省略路径）。

## 2.0.0 — 2026-10-10

首个公开发布版本。

> 说明：1.x 版本从未对外发布（仅本机开发，`0.1.0` 为开发期版本号）。

- **破坏性**：状态目录去隐藏化，`./.handoff/` → `./handoff/`；旧隐藏目录不再自动读取（分发包删除旧回退）。
- 修复生产-消费契约：`baton_tick.py` 现与 `handoff.py` 读取同一份 `handoff/state.json`（此前读取路径不一致，导致客观对撞自检静默失效）。
- 分享档中性化：移除本机绝对路径、私有记忆库路径与用户名示例。
- 新增**可选**主动提醒 hook（默认不挂）：`hooks/`（reminder / install / uninstall），含信任门、并发安全、超时与卸载。
- 新增 `baton_tick.py --detect-provider` 子命令。
- 兼容性诚实降级：objective-proxy 的 provider 覆盖以 `TESTED.md` 为准，不宣称清单内全部客户端已验证。
