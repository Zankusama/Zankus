# adapters · 各 harness 怎么挂

⛔ **本目录不包含任何客户端专属 hook 实现。**

> 可选的**主动提醒** hook 统一在 `hooks/`（默认不挂，需显式安装），约定见 `SKILL.md` §7；
> 本节描述的是核心 skill 的挂载与各客户端客观能力，核心不依赖 hook。

这是一个**刻意的设计决定**，不是没写完：

- 本 skill 的触发完全靠「节拍 + prompt 自检 + 用户显式触发」，这三者**零宿主依赖**。
- 一旦为某个 harness 写 hook，就等于把「能跑」建立在那个 harness 的事件表上。业界有真实教训：**"有 hook 机制" ≠ "有你需要的那个事件"**——某个 harness 的 `hooks.json` 里确实出现了 `SessionStart` 字样，但它没有任何能在会话开始注入上下文的事件，那些字符串只是遥测。
- 所以：**hook 是可选加固，不是依赖。** 有则更准，无则照样工作。

---

## 通用挂载（三端都一样，先做这三步）

1. 把**本目录的父目录（skill 根）**放到你的 agent 能找到 skill 的位置（见下各端说明）。
   ⚠️ **skill 根 = 含 `SKILL.md` 的那一层**，即 `baton/`，**不是** `baton/v0.1/`、
   也不是任何子目录。`SKILL.md` 与 `LICENSE` **必须在 skill 根**。
2. 确保 `<skill 根>/SKILL.md` 可被读取（装完用 `ls <skill 根>/SKILL.md` 自检一次）。
3. 在**项目约定文件**里加一句提醒（见下 §5），让 agent 知道有这回事。

**然后就不需要做任何事。** L0 静默默认，无异常不出声。

---

**通用触发方式（所有端一致，自然语言，无需 hook）**：
说「交接」/「handoff」/「该交接了」 → 产出交接文档；说「resume」 → 认领上一份接着干。

---

## 1. 已接入客户端清单（客观 5 指标可用）

`scripts/baton_tick.py` 可从以下客户端本地会话文件提取 5 项客观指标（user_turns / tool_calls / output_bytes / read_dup / write_calls）：

| # | 客户端 | provider key | 会话文件位置 | 格式 | workspace 反查方式 |
|---|---|---|---|---|---|
| 1 | WorkBuddy | `workbuddy` | `~/.workbuddy/projects/<项目目录>/<session-uuid>.jsonl` | JSONL（Anthropic function_call 风格） | 目录名编码 workspace + 每条事件带 cwd 字段 |
| 2 | 豆包办公端 | `doubaowork` | `<workspace>/.sessions/<sid>/agents/<aid>/system/trajectory.jsonl` | JSONL（OpenAI 风格 trajectory） | 扫所有 trajectory.jsonl，取 mtime 最新（启发式） |
| 3 | Qoder | `qoder` | `~/.qoder/projects/<项目目录>/<session-uuid>.jsonl` | JSONL（Anthropic Messages 风格） | 目录名编码路径 + 首条 workspace-directories 事件 |
| 4 | Qoder Work CN | `qoder_cn` | `~/.qoderworkcn/projects/<项目目录>/<session-uuid>.jsonl` | JSONL（同 qoder） | 同 qoder |
| 5 | QwenWork CN | `qwenwork_cn` | `~/.qwenworkcn/projects/<项目目录>/<session-uuid>.jsonl` | JSONL（同 qoder） | workspace-directories 事件 + agents.db SQL 直查 |
| 6 | ZCode CLI | `zcode` | `~/.zcode/cli/db/db.sqlite` | SQLite（session / tool_usage 表） | `SELECT id FROM session WHERE directory = '<ws>'` |
| 7 | AutoClaw-official | `autoclaw_official` | `~/Library/Application Support/AutoClaw-official/accounts/*/runtime/runtime.sqlite` | SQLite（neutral_session_entries 表） | work_workspaces.root_path（沙箱路径，非用户 workspace） |
| 8 | GitHub Copilot Forge | `copilot` | `~/.copilot/session-store.db` | SQLite（sessions / turns / session_files 表） | `SELECT id FROM sessions WHERE cwd = '<ws>'` |
| 9 | AutoClaw Legacy | `autoclaw_legacy` | `~/.openclaw-autoclaw/agents/*/sessions/*.jsonl` | JSONL（OpenAI 风格） | 全扫 jsonl 首行 session 头找 cwd==ws |

路由顺序（`baton_tick.py` 自动探测）：workbuddy → doubaowork → qoder家族 → zcode / autoclaw / copilot → autoclaw_legacy。

---

## 2. 已挂载但客观侧不可用（仅软约束可用）

skill 本身已挂载、prompt 自检与用户显式触发正常工作，但 `baton_tick.py` 读不到客观会话数据：

| 客户端 | 挂载路径 | 不可用原因 | 软约束 |
|---|---|---|---|
| Trae CN | `~/.trae-cn/skills/baton` | `~/Library/Application Support/Trae CN/ModularData/ai-agent/database.db` 189MB 加密，标准 sqlite3 读不开 | ✅ 可用（§1.3 自观测 + 用户显式触发） |

---

## 3. 明确不接的客户端

本地无明文会话流，或会话在云端，客观侧不接：

| 客户端 | 路径 | 不接原因 |
|---|---|---|
| CodeBuddy CN | `~/Library/Application Support/CodeBuddy CN/` | genie-history 空目录 + vscdb 不透明 blob，消息体在云端 |
| CodeArts Agent | `~/Library/Application Support/CodeArts Agent/` | chat_sessions 空 + vscdb `agentSessions.state.cache=[]` |
| TeleAgent | `~/Library/Application Support/TeleAgent/` | 空目录，从未使用 |
| Doubao 客户端（非办公版） | `~/Library/Application Support/Doubao/` | 纯聊天应用，会话在云端 |
| .cline | `~/.cline/` | 仅 VSCode 扩展配置，真正历史在 VSCode workspaceStorage/vscdb blob |
| autoclaw（小写 App Support） | `~/Library/Application Support/autoclaw/` | Electron 缓存 + APM 遥测 db，无会话 |
| ZCode 桌面壳 | `~/Library/Application Support/ZCode/` | Electron 缓存，真正数据在 ~/.zcode CLI |
| Qoder CN CLI | `~/.qoder-cn/` | 仅配置目录 + external-commands 命令注册表，无 skills 加载机制，不硬挂 |

---

## 4. 挂载位置总览（软链）

维护者可在各端 skill 目录放置本包副本（或用软链指向同一份源），改一份即等于改所有端。

| 客户端 | skill 挂载路径 | 指向 | 状态 |
|---|---|---|---|
| 豆包办公端 | `~/.doubaowork/agent_mode/workspace/.user_skills/baton` | → SSOT | ✅ 已挂载 |
| WorkBuddy | `~/.workbuddy/skills/baton` | → SSOT | ✅ 已挂载 |
| Qoder | `~/.qoder/skills/baton` | → SSOT | ✅ 已挂载 |
| Qoder Work CN | `~/.qoderworkcn/skills/baton` | → SSOT | ✅ 已挂载 |
| QwenWork CN | `~/.qwenworkcn/skills/baton` | → SSOT | ✅ 已挂载 |
| ZCode CLI | `~/.zcode/skills/baton` | → SSOT | ✅ 已挂载 |
| Trae CN | `~/.trae-cn/skills/baton` | → SSOT | ✅ 已挂载 |
| AutoClaw Legacy | `~/.openclaw-autoclaw/skills/baton` | → SSOT | ✅ 已挂载 |
| Copilot Forge | `~/.copilot/skills/baton` | — | ❌ 未挂载 |

---

## 5. 建议加进项目约定文件的一句话

放到 `AGENTS.md` / `CLAUDE.md` / `README.md` 都行：

```markdown
## 交接约定
- 长会话中若察觉上下文漂移（重读已读文件、同错反复、我连续纠正、
  早期约束被忽略、连续多个工作单元没有落盘产物），
  按 `baton` skill 产出交接文档，默认静默。
- 我说「交接」/「handoff」/「该交接了」时，直接产出交接文档。
  我可能顺带说一句"下一棒要做什么"，请据此裁剪文档。
- **新会话里我说「resume」，你按 ./handoff/LATEST 认领最新那份交接文档，
  先把路径报给我确认，再开工。**
- 交接文档落在 `./handoff/`，不要把业务数字/日期/ID 摘要化；
  没有落盘路径的内容（我粘贴的原文、你只在回复里给的代码）要逐字留下并标 [无路径]。
```

### 5.1 ⚠️ 关于"放哪"：这是一个**待验证的候选办法**，不是"唯一可靠办法"

第一方文档指出：压缩会替换早期消息，**对话早期的具体指令可能不被保留**，
所以**持久规则应当放在"每次请求都重新注入"的位置**（而不是依赖压缩保留）。

但——**"某个 harness 是否真的对 `AGENTS.md` 做每请求重注入"这件事，本项目尚未验证。**

所以本条**降级为待验证候选**（v0 曾把它写成"唯一能绕过约束静默丢失的可靠办法"，那是未经证实的声称）。
本机上的立场：**先按候选使用，但不要把它写进任何"保证不丢"的论证里。**

**验证步骤（可执行，⛔ 别跳过）**：

1. 在本仓库的约定文件里放一条**唯一标记**的规则行，例如：
   `<!-- HANDOFF-PROBE-20260923：交接文档一律落 ./probe-handoff/ -->`
2. 起一个**足够长、会触发压缩**的会话（跨过压缩点）。
3. 压缩后开新会话，问它："刚才那条 `HANDOFF-PROBE-*` 规则说的落盘目录是哪个？"
4. 把结论（**是 / 否 / 未测**）写回本节，并写明 harness 与日期。
   - 答对 → 本候选在该 harness 上成立。
   - 答错或答不出 → 该 harness **不**做每请求重注入，本条对它无效；此时**只能靠用户显式说「交接」**。

**当前结论：未测（2026-09-23）。**

---

## 6. 跨端一致性检查表

换了 harness 之后，逐条确认：

- [ ] skill 能被加载（描述里的触发场景能被识别）
- [ ] `SKILL.md` **在 skill 根**（不是子目录），且能被读取
- [ ] 没有依赖本 harness 不存在的 hook
- [ ] `HANDOFF_DIR` 指向的位置在新 harness 里**可写且跨会话保留**
- [ ] 交接文档里的路径在新 harness / 新目录下**仍然有效**（文档 `META` 里写死了路径基准）
- [ ] `handoff.py` 在新环境可执行（只要有 `python3` ≥3.7 标准库即可；`--selftest` 可自证）
- [ ] `resume` 路径可用：`python3 scripts/handoff.py --latest` 能选出文档
- [ ] 若新 harness 会清临时目录，提示用户把文档复制到持久位置
