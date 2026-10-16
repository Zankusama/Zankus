# hooks/README.md — baton 主动提醒 hook 细节（维护者向）

> 本文件是 SKILL.md §7 的细节展开（挂载策略/判据/契约/安全约定的完整版）。
> SKILL.md 只留骨架；要改机制先读这里，再动脚本——两处不一致时以脚本实跑为准。
> 分发提示：单端用户（git clone 即用）只需要 `install_reminder.py`；多端软链部署才需要 `source_sync_guard.py`。

## 1. 组件详表

| 文件 | 角色 | 失败语义 |
| --- | --- | --- |
| `baton_reminder.py` | 运行时：挂在 **`UserPromptSubmit`**（v4/D5 纠偏：提醒必须在**模型作答之前**送达才可能被贴进本回合回复；`Stop` 时机在回复之后贴不进去，Stop 侧只做 D3 对账。此前 docstring 写"推荐 Stop"与 settings 实挂不一致）。读客观 + 自报账（**streak 取值回正**：自报优先、客观兜底，见 §2），**双分支**输出——**L2 级信号 → 催办一行**（指示直接打包，SKILL.md §1.1）；**sub-L2 软信号/自报失真 → 询问一行**（是否打包用户定，SKILL.md §1.6 同稿）；**1+1+静默频控 + 退出通道 + 埋点**（见 §5）。输出为 **v4/D1 两段式**：AI 专用指令行（⛔不进回复）+ 🎒 三行信封本体 | **fail-open**（异常/超时静默，不阻塞 agent） |
| `baton_delivery_guard.py` | **v4/D3 送达对账守卫**：挂 `Stop`，读载荷 `last_assistant_message` 等文本键，扫本轮回复是否含信封特征串。曝光未结清却查不到 → 台账 `delivery_miss`；查到 → `--settle` 同款记账 `delivered`。**只登记不拦截**，exit 恒 0；miss 时向 stderr **响亮告警**（驱动 AI 补贴信封） | **fail-open**（stdin 缺失/非法/异常一律静默；拿不到文本键时留痕 `delivery_no_text` 但⛔不判成漏贴，防假红） |
| `source_sync_guard.py` | **v4/S2 存活层源同步守卫**：设计挂 `SessionStart`（多端部署者才需要；单端用户天然空转）。扫各客户端 hooks 目录里「派生自技能中心但非软链」的 `.py` 实件，sha256 比对中心真源（中心默认 = 本 skill 包的父目录，`BATON_SKILL_CENTER` 可覆盖）；落后 → 输出 **D1 同款两段式**（AI 指令行 + `🧬 baton 源同步告警` 可见块）。⛔ 只报不修——修法有取向（源新→软链／副本新→回灌源→合并），判定权在人。去重键=**副本哈希**：同一份旧件只出声一次。另有 `--orphans` 只报「中心无真源的多端实体件」（不进告警块） | **fail-open**（中心不可读/目录缺失/任何异常 → 空表静默，exit 0） |
| `install_reminder.py` | 安装器：探测 provider、信任门、改 settings、幂等；**v4/S3 发布校验**：装/升级前把实件 sha256 与**外部**发布清单比对，不一致 → 拒写 settings；`--print-hashes` 产出待发签名。挂载策略：默认装 2 件（reminder@UserPromptSubmit + delivery_guard@Stop），`--full` 加装 source_sync_guard@SessionStart | **fail-closed**（任何失败保持原配置；**清单不一致 exit 3 → 一个字节都不写**） |
| `uninstall_reminder.py` | 卸载：按事件+脚本名移除 hook 条目（保留旧 HOOK_MARKER 标记兼容）、清状态；settings 不存在时零副作用，空移除不写台账 | **fail-closed** |
| `_baton_common.py` | 内部共享工具（路径/状态/信任门/跨平台/信封特征串单一事实源 `ENVELOPE_MARK`） | — |

## 2. 触发源（v2.3.0 回正）

- `streak` 取值 = `state.json` 自报**优先**，**缺失时用客观值**——`baton_tick.py` 由会话事件时间线切工作单元算出（时间间隔分段，纯聊天段不计），输出 `streak_source` ∈ `{"self_report", "objective"}`。⛔ v2.1.x 曾绑死自报账，无自报账的普通会话完全不触发（v2.1.0 设计-实现脱节的根因，v2.3.0 修复）。
- 双分支与 SKILL.md §1.1/§1.3 同一套阈值：streak ≥2 → 询问行；≥3 → 催办行（`l2_objective_hit`）；**失鲜轴 grounding ≥8 → 催办行**、>0 → 询问行报数（v4/T2）；体量轴（≥ **40** 真实人类轮，注入已过滤）**只进询问行**（v4/T3；跨度轴已删）。阈值全部自标**工程启发式**（依据：证据报告 2026-10-12 + 314 会话实测 2026-10-14，学术查无）。
- ⚠️ **方言限制**：失鲜轴需要逐次工具参数，仅 **JSONL 方言可测**；SQLite 型 provider 返回 `grounding_staleness=null` + `grounding_unavailable_reason`，⛔ 不冒充 0（宁可不判也不假绿）。
- ⛔ **压缩事件计数不接触发层**（v4/T4 待拍板）：核心目标=监控是否遵循目标，⛔ 非控制压缩次数（防古德哈特定律，2026-10-14 用户裁定）。技术前提：compaction 可测（workbuddy `.providerData.compactType` / qoder `.isCompactSummary` 均有命中）但未标定，接入属设计变更。

## 3. 送达对账（v4/D3）

- 判据链：`pending_exposure_epoch` 已置位 → 本轮 Stop 扫回复文本是否含 `🎒 baton 交接提醒`。含 → 记 `delivered`（幂等，一笔曝光只记一次）；不含 → 台账 `delivery_miss` 并响亮告警（AI 须补贴信封才算送达）；**载荷里没有文本键** → 只留痕 `delivery_no_text`，⛔ 不判漏贴（判例：同域某守卫因键表漏 `last_assistant_message` 而全程空转，故"拿不到文本"必须与"没贴"分开）。
- 防误伤：同一笔曝光只对账一次（`reconciled`）；超过 **30 分钟**新鲜窗的 pending 直接结清不判（多为同 workspace 别的会话留下的账）。
- 取数：`python3 hooks/baton_delivery_guard.py --stats <workspace>` 输出一行 JSON（`exposure / delivered / delivery_miss / delivery_ok / delivery_no_text`），供周报消费。特征串常量单一事实源在 `hooks/_baton_common.py:ENVELOPE_MARK`——构造方与对账方共用，⛔ 两处各写一份字面量就是又一个源↔副本漂移标本。

## 4. 存活层（v4/S1+S2 · 2026-10-14 实盘）

- **S1 已落地**：`~/.workbuddy/hooks` 实测 **40 软链 / 0 实体 py**——提醒与对账两个钩子都由 `settings.json` 直接指向技能配置源，跑的就是源本身，不存在"改源不同步"。判据：`ls -l ~/.workbuddy/hooks` + `find -maxdepth 1 -type l/-type f` 计数。
- **S2 判据的已知盲区（实测抓到，不是推测）**：`orphans` 扫出 `route_unknown_unknown.py` 在三端**各一份实体、哈希互异、技能中心无同名真源**。这类件"派生自彼此而非中心"，S2 主判据（有源可比）结构性抓不到 → 因此新增 `--orphans` 只登记不告警。**归属记忆系统而非 baton，未越界处置**。
- ⚠️ **mtime 不作同步判据**（实测 touch 未重拷仍更新 mtime）→ 一律 sha256。
- 自测：`python3 hooks/source_sync_guard.py --self-test` → **8/8**（含"同一旧副本只出声一次""源再前进而副本未变仍静默""副本对齐源即消音""目录缺失不抛"）。

## 5. 频控 1+1+静默（v2.3.0）· 退出通道与埋点

- 第 1 次出声后记账；**第 2 次**需同时满足「距上次 ≥ **30 分钟**」且「信号增强（streak 增加）」，**换版文案并点明具体信号**；**两次后本会话静默**。
- 检测到交接文档落盘（`HANDOFF_DIR/LATEST` 更新晚于上次提醒）→ **重置**计数，进入新循环。
- 频控状态：`<workspace>/.baton-state/<ws-hash>/<agent-id>/reminder_state.json`（权限 600）。
- 每条提醒行末尾附「（说「别提醒」本会话不再提醒）」；用户说了，**agent 执行** `python3 hooks/baton_reminder.py --mute <workspace>` 写 per-session 关闭 flag（`--unmute` 恢复）。⛔ hook 自身不读 prompt——措辞识别由 agent 完成，P0-γ 隐私边界不变。
- 状态文件记三个**纯计数**：`exposure` / `handover_conversion` / `ignore`；⛔ **只计数，不记 prompt**。
- **验收口径**：忽略率 = `ignore / (ignore + handover_conversion)`，**>70% 应收紧触发**（70% 为 Copilot 采纳率量级的工程推测，待埋点数据收敛）。

## 6. 状态根与隐私（SKILL.md §7.2 原详版）

- 状态根 = `<workspace>/.baton-state/<ws-hash>/<agent-id>/`，权限 `700`。
- ⛔ **不落 skill 包内**（只读 / 共享 / 版本控制目录不可写且会污染分发）；`.baton-state/` 进 `.gitignore`。
- 标记：`installed`（唯一安装判据）；`offered` 由呈现选择块的一方写入，安装器默认"否"时**不写**。
- 频控状态键全集：`count / last_at / last_streak / muted` + 三计数 + v4 送达两字段 `delivered` / `reconciled`。
  ⚠️ 新增键必须同步登记进 `baton_reminder.py:_fresh_state()`——`_load_state` 只回读模板里的键，漏登记 = 写入后被静默吞掉（v4 实测踩点）。
- 台账最小化：仅 `ws-hash / 事件 / 时间戳`；⛔ **不记 prompt 全文或摘要**。送达对账事件：`delivery_ok / delivery_miss / delivery_no_text keys=… / delivery_pending_expired`（`keys=` 只列载荷**键名**，⛔ 不列值）。

## 7. 安全约定（SKILL.md §7.3 原详版）

- **prompt 传输（P0-γ）**：命令串中不出现 `--prompt`；运行时 hook 不接收 prompt 内容（用位置参数 / stdin / JSON / 受控环境变量；明确转义、长度上限、脱敏）。
- **信任门（P0-ε）**：写 settings 前校验 skill / tick / 解释器 / settings 路径的 owner、权限、ACL；任一可被他人写入/替换 → 拒绝写入并退出非零。
- **完整性自检**：`baton_reminder.py --selfcheck` 的期望 hash 必须来自**外部签名 / 发布清单 / 只读信任源**（`--manifest` / `BATON_EXPECTED_HASH`）；无外部锚点时明确声明"仅完整性提示，非安全边界"，杜绝同目录 hash 自证。
- **执行面（P0-η）**：`BATON_SCRIPTS` 回退仅在显式、绝对、受信任时启用，否则取消。
- **超时（P1-7）**：hook 条目带 `timeout`；运行时设快速预算（`BATON_TIMEOUT`），不阻塞 agent。
  ⚠️ 例外（2026-10-11）：provider 的**实测**条目形态不含 `timeout` 时按实测写（如 WorkBuddy `UserPromptSubmit` 条目仅 `type/command`，见 references/TESTED.md §1）——快速预算由运行时 `BATON_TIMEOUT` 承担，⛔ 不为对齐本条而伪造条目键。

## 8. 生产-消费契约（P0-β）

状态/文档的写入方与读取方必须落在同一路径，否则自检静默失效（v0.1 曾因此恒空）：

| 写入方 | 产物 | 读取方 |
| --- | --- | --- |
| `handoff.py --log`（首选）/ 模型手写 | `HANDOFF_DIR/state.json`（默认 `./handoff/state.json`） | `baton_tick.py read_handoff_state`（同解析：`$HANDOFF_DIR` > `<ws>/handoff`） |
| 模型直写 / `handoff.py --write` | `HANDOFF_DIR/HANDOFF-*.md` | 下一棒 / `resume` |
| 落盘成功 | `HANDOFF_DIR/LATEST` | `resume` 解析、`handoff.py --latest` |
| `handoff.py --write` / `--redact-file` / `--pin` | `state.json` 的 `pinned_objective_path`（失鲜轴锚，v4/T2；落盘时自动写为本次交接文档路径） | `baton_tick.py grounding_staleness`（无此键时回退读 `LATEST`；两者都无 → `None`+原因，⛔ 不判） |

> ⛔ 分发包**删除**旧隐藏目录回退（三方一致），故 `grep '\.handoff' scripts/ README.md adapters/` 应为 0（CHANGELOG 中的历史描述除外）。
>
> ⚠️ **cwd==ws 约定（2026-10-11 补）**：读取方按**两套基准**定位 state——`baton_tick.py` 按**传入的 workspace 参数**（缺省 cwd）找 `<ws>/handoff/state.json`；`handoff.py --log` 按**当前 cwd** 解析 `./handoff/`。两者要对上，须约定**运行时 cwd == workspace**（或统一显式设 `HANDOFF_DIR`），否则自检静默失效（v0.1 曾因此恒空，同一教训）。

## 9. 首轮询问、卸载、升级与迁移

- 首轮必检（2026-10-12 v2.3.1）：skill 每次会话触发时先跑 `python3 hooks/install_reminder.py --dry-run`（只读预览·fail-closed）；未挂且 `offered` 不存在 → 每 workspace **提示一次**安装询问（per-ws key 双轨，保留"永不询问"路径）；已挂/已拒 → 静默。安装动作仍需用户确认（信任门 P0-ε 不变），本条只把"检查"从可忽略升级为必做。
- 升级：同标记的旧条目在**备份后替换**（幂等，不跳过）。
- 迁移：Python 解释器或 skill 路径迁移后，旧 hook 会变孤儿；重跑安装器或用 `uninstall_reminder.py` 清理后重装。
- **发布校验（v4/S3 · 2026-10-14 落地）**：安装器在写 settings **之前**把五件实件（`baton_reminder / baton_delivery_guard / source_sync_guard / _baton_common / scripts/baton_tick`）的 sha256 与清单比对，三态语义——
  ①覆盖到的件全对 → 绿灯继续；②有不符（含实件缺失、清单读不了、清单非对象）→ stderr 逐件列「期望=… 实得=…」并 **exit 3 拒绝写入**（fail-closed，实测 settings `before=after` 字节一致）；③**没有外部锚点** → 打印「未验证（**不是已验证通过**）」并照常安装，⛔ 静默冒充绿灯。清单存在但**一件发布面都没覆盖**时同样走"未验证"。
  **作用域规则**：清单**覆盖到**的件必须全对；未列出的件只登记不判（老包清单本就可能只列自家两件——缺键≠被篡改，据此拒装是假红，2026-10-14 实测抓到过并已修）。
  **与 selfcheck 共用一份清单**：两个消费方都认 `{"files": {"hooks/x.py": sha}}` 与扁平形态；扁平形态另认 selfcheck 的既有别名键 `reminder_sha256` / `tick_sha256`（`FLAT_ALIASES`）。⚠️ 退出码语义不同且刻意保留——selfcheck 不符=1、安装器不符=3；⛔ 不要把两套退出码混在一个脚本里判。
  ⚠️ **锚点必须在包外**：清单若与待验件同目录，副本一起被换掉就自证无效。软链跨机断链时本项为兜底（S2 只报漂移不修，S3 只拒装不修）。
  实测矩阵 **9/9**：A 全5件一致 rc0 / B 扁平2件 rc0（并列出"另有 3 件未验证"）/ C 篡改 rc3 / E 清单零覆盖=未验证 / F 非对象 rc3 / G 无锚点=未验证 / H 扁平清单端到端**不再拒装合法包**且真配置未被改写（幂等，mtime 未变）/ I 同一 `files` 清单 selfcheck 也认 / J 篡改端到端拒装且字节未变。
- 不支持 hook 的宿主（如豆包办公端）：安装器打印手动片段并记录"未挂载"，可忽略——核心不依赖 hook。
