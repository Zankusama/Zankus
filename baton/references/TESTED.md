# TESTED · baton 实测矩阵

> 诚实记录"测了什么、在什么环境测、什么没测"。版本与平台断言以本文件为准。
> 最后更新：2026-10-14（v2.4.3：skill-rehab 康复轮——触发测试集 tests/ 三场景 + 断言 A/B 复跑清零 + 版本四件对齐；§2.1 断言范围说明如实扩大：CHANGELOG 历史条目除外，append-only 账本不改写。前次 2026-10-12 · v2.3.0：触发源回正 + 1+1+静默频控）

## 1. 测试环境

| 项 | 值 |
| --- | --- |
| 操作系统 | macOS 26.4.1（arm64） |
| Python | 3.9.6（macOS 自带·2026-10-12 v2.3.0 实测口径，代码保持 3.9 兼容；历史条目所记 3.14.7 本机查无，如实更正。纯标准库，无第三方依赖） |
| 实测宿主 | DoubaoWork（客观解析器 `doubaowork`）；**WorkBuddy（`workbuddy`）= 2026-10-11 新增实测项** |
| settings 形态 | Claude Code 标准 `~/.claude/settings.json`（hooks 按事件分组，hook 条目含 `type/command/timeout`）；**WorkBuddy = `~/.workbuddy/settings.json`，事件组 `UserPromptSubmit`，条目仅 `type/command`（不带 `timeout`）** |
| 权限模型 | POSIX：状态目录 `700`、文件 `600` |

> ⚠️ **2026-10-12 复跑注**：本机 `python3` 实为 **3.9.6**（`/usr/bin/python3`，另有 `python3.12` 位于 `~/.local/bin`）；
> **全机未找到 3.14.7 解释器**（`command -v python3.14` 零命中、Python.framework 无该版本）——上表 3.14.7 口径
> 在本机**无法复现**，"查无"如实记录。v2.3.0 各用例的实测解释器以 **3.9.6** 为准（见 §2.5 注）；
> 代码保持 3.9 兼容（不使用 `X | Y` 运行时注解求值）。其余 macOS 26.4.1 / 纯 stdlib 口径不变。

## 2. 已通过的测试（均有实测输出）

### 2.1 脱敏与静态断言

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `handoff.py --selftest` | 13 保留 + 7 替换 + 3 不误伤 | ✅ 全通 |
| `grep -rnE '/Users/\|记忆库' . --exclude=TESTED.md --exclude-dir=.git` | 0（模式含断言自指；CHANGELOG 历史条目除外——append-only 账本不改写，新条目禁止出现） | ✅ 0（2026-10-14 复跑：仅 CHANGELOG 两条历史自述命中） |
| `grep -rn '/Users/<user>' .` | 0（机器特定路径，泛化为上行；本行留作历史口径） | ✅ 0 |
| `grep -rn '/tmp' hooks/` | 0 | ✅ 0 |
| `grep -rn '\.handoff' scripts/ README.md adapters/` | 0 | ✅ 0（CHANGELOG 中历史描述 1 处，属允许） |

### 2.2 客观对撞（P0-β）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `baton_tick.py --detect-provider <真实 ws>` | 0 + 唯一 provider | ✅ `doubaowork`（0） |
| `--detect-provider <不存在/非目录>` | 3 | ✅ 3 |
| `read_handoff_state` 与 `handoff.py` 同路径 | 三处一致 | ✅ 均解析 `$HANDOFF_DIR` > `<ws>/handoff` |
| 旧隐藏目录回退 | 分发包不含 | ✅ 无 `.handoff` 回退 |

### 2.3 安装器（fail-closed）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `--dry-run` | 打印命令、不改配置、不含 `--prompt` | ✅ |
| 首次 `--yes` | added，原有 `PreToolUse` 保留、新增 `Stop`、备份 | ✅ |
| 再次 `--yes` | replaced（不重复，仍 1 组 1 hook） | ✅ |
| 并发两次 `--yes` | 加锁串行，恰好 1 hook，无损坏 | ✅（added + replaced） |
| 无 TTY 默认 | 不写 offered、不自动安装 | ✅（仅打印手动片段） |
| 路径含空格 | shlex 转义、JSON 有效、单段 | ✅ |

### 2.4 信任门（P0-ε，负例）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| settings 在非粘滞 world-writable 目录 | 拒绝（2） | ✅ 2 |
| settings 自身 world-writable（666） | 拒绝（2） | ✅ 2 |
| world-writable 但带粘滞位（如 /tmp） | 放行 | ✅ 放行 |

### 2.5 运行时提醒（fail-open · 2026-10-11 v2.1.1 按双分支语义重写并重测 · 2026-10-12 v2.3.0 触发源回正+频控增测）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `l2_objective_hit=true`（streak≥3，tick+hook 端到端） | 催办行（指示直接打包，不出询问行） | ✅ 唯一催办行 |
| `packaging_advisory` 软信号（streak=2，端到端） | 询问行（§1.6 同稿，不出催办行） | ✅ 唯一询问行 |
| 自报失真（checks 缺字段，端到端） | 询问行，且不误触 L2 | ✅ |
| 无任何信号（streak=0 + 全 HEALTHY，端到端） | 静默 | ✅ 无输出 |
| **负例：自报 `output_scale=large` + 客观重复读取** | **不触发任何输出**（v2.1.1 删除 tick 的 large+重读子句后的关键负例——"单轮 large+重读"只归 AI 自检判 L2，hook 客观触发只剩 streak） | ✅ 函数级 `advisory=[]` 且端到端 hook 静默 |
| tick 超时（`BATON_TIMEOUT=0.001`）/ data 结构不符 / 无信号 | 静默、rc=0（fail-open） | ✅ 0 |
| `build_reminder` 单测（v2.1.0 起取代旧 `should_remind`，后者已删除） | None/异构/无信号→None；L2→催办行；失真→询问行 | ✅ |
| **无自报账（无 state.json）+ 客观 streak=2**（端到端，v2.3.0） | 询问行（`streak_source="objective"`） | ✅ 唯一询问行 |
| **无自报账 + 客观 streak=3**（端到端，v2.3.0） | 催办行（`l2_objective_hit=true`） | ✅ 唯一催办行 |
| **纯聊天会话**（无工具调用、无自报账，v2.3.0） | 静默 | ✅ 无输出（streak=0） |
| **二次提醒**（v2.3.0 任务3）：冷却未到→静默；streak 2→3 且回拨 ≥30min→换版出声并点明"已连续 3 个工作单元未落盘"；两次后→静默 | 见左（含 `count/exposure/ignore` 记账断言） | ✅ 三段全中 |
| **退出通道与埋点**（v2.3.0 任务4，补测）：行末附「（说「别提醒」本会话不再提醒）」；`--mute` 后静默、`--unmute` 恢复；`LATEST` 更新→ `handover_conversion+1` 且计数重置 | 见左 | ✅ |

> v2.1.1 重写说明：旧表引用的 `should_remind` 已在 v2.1.0 双分支改造中删除；
> 旧「tick 无矛盾 → 静默」断言在 v2.1.0 后不再成立（`packaging_advisory` 的询问行也属"有信号"）。
> 前 7 行于 2026-10-11 实跑通过（测试脚本构造 state.json 五场景）。
> **v2.3.0 五行于 2026-10-12 实跑通过**：夹具=独立 fixture workspace + 合成 workbuddy 会话 JSONL
> （`~/.workbuddy/projects/<encoded-ws>/`，跑完即删），`state.json` 按场景写入 `<ws>/handoff/`；
> 套件按分组 `baseline`(7) / `v230`(5) 组织，**全量 12 例、退出码 0、skipped=0**（套件为工作区产物，分发版省略路径）。
> ⚠️ 本次复跑解释器 = `/usr/bin/python3` **3.9.6**（详见 §1 复跑注），baton_tick.py 保持 3.9 兼容语法。

### 2.6 完整性自检（外部锚点）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| 与 manifest 一致（files map / flat） | 0 | ✅ 0 |
| 与 manifest 不一致 | 1 | ✅ 1 |
| manifest 缺 key | 2 | ✅ 2 |
| `BATON_EXPECTED_HASH` 匹配 / 不符 | 0 / 1 | ✅ 0 / 1 |
| 无外部锚点 | 不做安全声明，声明"非安全边界" | ✅（rc=0，见下注） |

> 注：无锚点时返回 rc=0 并明确打印"仅为完整性提示，非安全边界"。这是刻意选择——脚本本身
> 正常运行，只是"没有可比对的基准"；是否应视为失败可在 CI 中按团队口径自行决定。

### 2.6b 安装器发布校验（v4/S3 · 2026-10-14 实跑 9/9）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| A `files` map 五件全一致 | 0 + `✅ 校验通过（比对 5 件）` | ✅ 0 |
| B 扁平 selfcheck 形态两键（`reminder_sha256`/`tick_sha256`） | 0 + 报"另有 3 件未列出=未验证" | ✅ 0 |
| C 其中 1 件 hash 被改 | **3** + 逐件「期望/实得」 | ✅ 3（`期望=000000000000 实得=dad13ce5c0f3`） |
| E 清单不含任何发布面件 | 0 + 明说"**未验证**（不是校验通过）" | ✅ 0 |
| F 清单非对象（数组） | 3 + 拒绝接线 | ✅ 3 |
| G 无外部锚点 | 0 + "未验证（不是已验证通过）" + 打印实算值 | ✅ 0 |
| H 扁平清单端到端 `--yes` 装机 | 不拒装；真配置**未被改写**（幂等） | ✅ rc=0，`~/.workbuddy/settings.json` mtime 未变 |
| I 同一份 `files` 清单喂 selfcheck | 两消费方都认（0） | ✅ 0 |
| J 篡改清单端到端 | 3 + settings 字节 `before==after` | ✅ 3 / 字节一致 |

> ⚠️ **两个消费方的退出码刻意不同**：selfcheck 不符=1、安装器不符=3（安装器须让"校验失败"与"包本身坏"在 CI 里可分辨）。
> ⚠️ **缺键处理也刻意不同**：selfcheck 把"清单缺 `baton_reminder.py` 键"判 2（它只关心自家两件）；安装器把"清单未覆盖某件"降为**未验证登记**、⛔ 不拒装——否则发布方按 §2.6 扁平形态签的合法包会被安装器假红拒装（2026-10-14 实测撞到，已修，见 `FLAT_ALIASES` + 作用域规则 SKILL §7.5）。
> 落点提示：workbuddy provider 的 settings 是**用户级** `~/.workbuddy/settings.json`，不是 `<ws>/.workbuddy/settings.json`；用临时 ws 做探针时别把 md5 对比打错对象。

### 2.7 卸载

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `uninstall_reminder.py` | 移除 hook 标记、保留其他 hook、清当前 agent 状态 | ✅ |
| `uninstall_reminder.py --all` | 清整棵 `.baton-state` | ✅ |

### 2.8 WorkBuddy 适配实测（2026-10-11，A/B/C 改造后）

| 用例 | 期望 | 结果 |
| --- | --- | --- |
| `baton_tick.py --detect-provider <本 ws>` | 唯一命中 workbuddy，exit 0 | ✅ exit 0，`matches=["workbuddy"]`（改造前为 exit=4 假歧义） |
| `baton_tick.py --detect-provider <上一会话 ws>` | 同上 | ✅ exit 0，`matches=["workbuddy"]` |
| `install_reminder.py <ws> --dry-run` | 落点 `~/.workbuddy/settings.json`、事件 `UserPromptSubmit`、条目无 `timeout` | ✅ 三项全中 |
| `wiring_for('doubaowork' / 'qoder')` | `None` → 转手动（未实测不自动写） | ✅ 本机 `~/.claude` 不存在 → 均转手动（fail-closed） |

> 注：A/B/C 改造**未跑** `--yes` 实挂载回归——现有 `~/.workbuddy/settings.json` 里的
> baton 条目**不含幂等标记**（`marker_hit=False`），此时安装会 `added` 而非 `replaced`，
> 将产生两条重复 hook。故保持现状不动（另见 §3）。

## 3. 未验证 / 已知限制（诚实降级）

- **Windows / 其他平台**：仅做静态跨平台处理，**未在 Windows 上实测**。
  - Windows 深层 ACL 标准库无法读取，仅要求路径位于用户配置内；精确 ACL 校验需 `pywin32` / `icacls`。
  - Windows 路径转义（`list2cmdline`）未实测。
- **其他 8 个客观 provider**：本次未逐一在对应客户端下实测；`doubaowork` 为实测项。
- **豆包办公端**：无 hook 事件机制，安装器仅打印手动片段；核心交接流程不依赖 hook。
  - ⚠️ **内部矛盾未解决（2026-10-11 标注）**：本节称"豆包无 hook 事件机制"，而 §1 测试环境
    却把「实测宿主 = DoubaoWork、settings 形态 = `~/.claude/settings.json`」记为已测项 ——
    两者对"doubaowork 到底有没有 hook"给出相反口径，**未实证**。本机 `~/.claude` 不存在
    （`[ -d ~/.claude ]` = false），故 doubaowork 在本机一律 `wiring=None` → 手动片段。
    要定论须在真实豆包办公端跑一次 `--dry-run`；读文档无法解决。
- **WorkBuddy 项目级 `<ws>/.workbuddy/settings.json`**：本机 0 处实例，**未实测**是否被
  WorkBuddy 读取 → 安装器默认走用户级（`default_scope="user"`）；项目级仅当用户显式
  `--scope project` 时才写。
- **现有 hook 条目无幂等标记**：`~/.workbuddy/settings.json:316` 的 baton 命令不含
  `--hook-marker`，故 `install --yes` 会重复挂载（`added`）而非替换（`replaced`）。
  **实挂载回归未做**（属核心文件改动，需维护者确认后才动）。
- **wall_minutes（doubaowork）**：trajectory 无时间戳，用文件 mtime 兜底，时长不精确（已知限制）。
- **首次询问"每 workspace 一次"**：需呈现选择块的一方在选择后写入 `offered`；安装器默认"否"不写。

## 4. 复现方式

在临时 workspace 放 `.claude/settings.json`，依次运行 `install_reminder.py --dry-run / --yes`
（含二次、并发）、`baton_reminder.py --selfcheck [--manifest ...]`、`uninstall_reminder.py [--all]`；
负例在非粘滞可写目录或对 settings 做 666 后安装。
