# Changelog

本项目遵循语义化版本（Semantic Versioning）。

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
