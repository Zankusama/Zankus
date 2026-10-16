# baton · 工作交接（v2.4.4）

## ⭐ 你只需要记住两个词

| 说这个 | 会发生什么 |
| --- | --- |
| **`交接`** | 我产出一份交接文档，并把新会话怎么接告诉你 |
| **`resume`** | 新会话里说这个，我认领上一份交接文档接着干 |

其余都是别名（`handoff` / `接着干` / `该交接了`），不用记。
⚠️ `该压缩了` 也认，但它与宿主内置的 compact 同名、语义可能与"交接"错开 —— 想表达"该交接了"就直说「该交接了」。

## 安装与客户端适配

- **提醒 hook（可选增强）**：`python3 hooks/install_reminder.py --dry-run` 预览 → 加 `--yes` 安装；不装核心功能不打折。skill 首次触发时会自动做一次安装检查并询问（每 workspace 至多一次，可说"永不询问"）。
- **客户端适配**：tick 自动探测 9 种客户端（WorkBuddy/豆包/Qoder 系/ZCode/AutoClaw/Copilot 等），首跑即适配；不在清单内时 JSON 返回 `objective_unavailable_reason`（fail-open，交接核心不受影响）。扩新客户端见 `adapters/README.md`。
- **已知边界**：运行 cwd ≠ workspace 时提醒会失明（详见文末 FU-4 声明）。

> 会话即将被压缩、或已经出现上下文漂移时，把当前对话压成一份**结构化交接文档**，让新会话 / 新 agent **不失关键信息**地接手。

---

## 这个 skill 解决什么

长会话会退化。有实测的行为代价（来源：langwatch.ai/blog/context-tax-when-to-compact，2026-08-02，单一实践者 162 天 873 次压缩实录；下列数字与引语均 2026-10-11 一手回源）：**压缩后 5 步内纠错率 41.9% vs 基线 17.7%（2.37×）**，升高**至少持续 30 步、120 步时尚未完全消退**。而一次中位压缩把 **574,875 tokens 的窗口压到只剩 4,382 tokens 的摘要（不足原文 1% 存活）**。

> ⚠️ **这个数字是观测性的，原作者明确不声称因果。** 作者原话（逐字）：
> *"sometimes I compact because things are already going badly, which by itself would inflate the post-compaction spike"*——
> 运维者可能**因为会话已经变糟才去压缩**，这本身就会抬高压缩后纠错率；
> *"The correction measurement is observational, not an experiment"*。
> 来源是**单一实践者、162 天、873 次压缩**（等级 C）。**本 skill 不主张"压缩必然有害"**——它只主张"交接时要少丢东西"。

其中最容易静默消失的是**精确信息**：压缩后**只有约 17% 的会话约束存活**（等级 B·preprint，17% 是平均值、随压缩器/长度/措辞/注入位置剧烈变化，arXiv:2608.11242）；受控保留基准上**逐字锚定抽取 recall 97.5%（摘要法 19.0%）、exact match 93.0%**（等级 B/E，单一作者的合成对照，召回对象是植入事实条目，⛔ 不要外推到数字/日期/ID，arXiv:2601.00821 v1）。往上下文里补"保留摘要"对冲丢失是反方向——输入越长性能越不可靠，定向只给相关信息显著更优（research.trychroma.com/context-rot）。

**所以本 skill 的第一优先级不是"压得更小"，而是"别丢关键信息"。**

---

## 它与其他做法的区别

| | `/compact` | `handoff`（参考实现） | **baton** |
| --- | --- | --- | --- |
| 触发 | 宿主自动 | 人显式打 `/handoff` | **静默默认** + 节拍 + 用户显式 |
| 漂移自检 | 无 | 无 | **有（5 类，折叠进同一次 pass）** |
| 逐字保留契约 | 无 | 无（只管"不重复已有产物"） | **有（字段级规则 + 回归样本）** |
| 面向下一任务裁剪 | 无 | **有**（核心机制） | **有（自然语言输入，不绑客户端字段）** |
| 无路径产物 | 丢 | 丢 | **标 `[无路径]` 逐字内联** |
| 落盘位置 | — | OS 临时目录 | **`./handoff/`（仓库内，可分发）+ `LATEST` 指针** |
| 跨 harness | 各端不同 | 纯 prompt，可移植 | **纯 prompt + 可选 stdlib 脚本** |
| 依赖 hook | 是 | 否 | **否（有 hook 只作可选加固）** |

---

## 安装（4 步）

```bash
# 1. 把 skill 根目录放进你的 agent 能读到 skill 的目录
#    WorkBuddy : ~/.workbuddy/skills/baton/
#    Claude Code: ~/.claude/skills/baton/
#    Codex     : 按 Codex 的 skill 目录约定
git clone <repo-url> <skill-root>/baton      # <skill-root> 替换为本端 skill 父目录
#    多 skill 仓库（baton 是其中一格）：clone 后指子目录，别把仓克隆进 baton 里
#      git clone <repo-url> /tmp/skills && ln -s /tmp/skills/baton <skill-root>/baton

# 2. 自检：确认 SKILL.md 在 skill 根（harness 登记的路径），而不是在子目录里
ls <skill-root>/baton/SKILL.md

# 3. （可选）验证脚本可用
python3 <skill-root>/scripts/handoff.py --help      # <skill-root> 替换为本端 skill 安装路径
python3 <skill-root>/scripts/handoff.py --selftest

# 4. 在项目约定文件里加一句（AGENTS.md / CLAUDE.md 均可）
#    见 adapters/README.md §5
```

**完成。** 不需要装任何 hook，不需要配置任何东西。

> ⚠️ `handoff.py` 是**便利设施，不是前置依赖**。装不了 python3 的环境，agent 按 `SKILL.md` §3 直接手写交接文档即可，功能不打折。
> ⚠️ **Python 最低版本 3.7**（`from __future__ import annotations` 需 3.7+；用 `open(..., newline="\n")`，不用 `write_text(newline=)`——后者需要 3.10+）。
> 实测环境以 `references/TESTED.md` 为**唯一口径**（当前：Python 3.9.6 / macOS 26.4.1）。⛔ 无任何 pip 依赖。

---

## 目录说明

```
baton/                    ← 这就是 skill 根
├── SKILL.md                     # ★ 技能正文：触发/自检/schema/步骤/反模式/可选hook（★ 必须在根）
├── LICENSE                      # MIT
├── CHANGELOG.md                 # 版本变更（1.x 从未发布）
├── references/TESTED.md         # 实测矩阵（诚实降级，未验证项显式列出）
├── README.md                    # ← 你在这里
├── scripts/
│   ├── handoff.py               # 落盘 / 脱敏 / 自检记账（纯 stdlib，无硬编码路径）
│   └── baton_tick.py            # 客观体量代理（多客户端自动路由；不可用时降级为自报）
├── hooks/                       # 可选：主动提醒（默认不挂，需显式安装）
│   ├── baton_reminder.py        # 运行时（UserPromptSubmit·fail-open）
│   ├── baton_delivery_guard.py  # 送达对账守卫（Stop·fail-open）
│   ├── source_sync_guard.py     # 源同步守卫（SessionStart·fail-open·仅 --full 装）
│   ├── install_reminder.py      # 安装器（fail-closed；默认装前两件，--full 加源同步）
│   ├── uninstall_reminder.py    # 卸载器（按事件+脚本名清）
│   ├── README.md                # hook 机制细节（维护者向）
│   └── _baton_common.py         # 内部共享工具
├── references/
│   ├── schema-完整模板.md       # 15 字段填写样例 + [无路径] 豁免规则
│   ├── resume-接手流程.md       # 新会话 resume 解析顺序 + 接手方契约
│   ├── 脱敏规则表.md            # 三级替换判定 + PII 规则
│   ├── 验收清单.md              # 交接后自检
│   └── 许可与出处.md            # 许可、出处与已知局限
└── adapters/
    └── README.md                # 各端挂载与客户端清单（核心不含任何客户端专属 hook 实现）
```

**产物落盘位置**：默认 `./handoff/HANDOFF-<YYYYMMDD-HHMMSS>.md`（**相对当前工作目录**）。
可用环境变量覆盖：`HANDOFF_DIR=/path/to/dir`。置 `HANDOFF_DISABLE=1` 可整体静默关闭
（`--help` 与 `--selftest` 仍然放行）。
每次落盘会同时写 `./handoff/LATEST`（一行文本，指向最新那份），并在指路时打印**绝对路径**。

**`.gitignore` 两种写法**（团队自己选）：

```gitignore
# 公共：hook 状态与临时产物（不进版本控制）
.baton-state/
baton_reminder_*

# 写法 A：整个忽略 —— 交接文档是本机工作态，不进版本控制
handoff/

# 写法 B：只忽略记账文件，保留文档留痕（团队想复盘交接历史时用）
handoff/state.json
handoff/LATEST
```

---

## 怎么用

默认**什么都不用做**——它在后台按节拍内联自检，无异常不出声。

需要交接时，任选一种：

| 你说 | 会发生什么 |
| --- | --- |
| （什么都不说，自动） | 自检判定达 L2（漂移/空转等硬信号）时**直接打包**交接文档并指路——无需说"交接"（v2.1.0 起，打包是主动义务） |
| 「交接」/「handoff」/「该交接了」 | 产出交接文档，告诉你新会话怎么接 |
| 「交接，下一棒只用来改文案」 | 同上，但**按"下一棒用途"裁剪**，无关字段写 `none` |
| 「resume」 | 新会话按 `LATEST` 指针认领上一份文档，**先报路径请你确认**再开工 |
| 「检查上下文健康」 | 跑一次 5 类自检并报告 |

**想知道它有没有在盯**（静默默认下唯一的事后凭据）：

```bash
python3 scripts/handoff.py --state-show     # 看 ./handoff/state.json（最近 20 条自检记录）
python3 scripts/handoff.py --latest         # 看 resume 会认领哪一份文档
```

---

## 跨端说明

- **零客户端专属 hook。** 触发靠节拍 + prompt 自检 + 用户显式，三者都是纯自然语言。
- **零客户端专属字段。** "下一棒要做什么"用**自然语言**给，不依赖 `argument-hint` 之类的键。
- **零硬编码绝对路径。** 默认相对目录，环境变量可覆盖（指路时打印的是运行时 `resolve()` 出来的绝对路径）。
- **零 pip 依赖。** 只用 python3 标准库（≥3.6）。
- **脱敏的唯一实现点是"落盘后扫描并就地替换"**（`--scan` → `--redact-file`）。
  这样"模型直写文件"与"脚本落盘"两条路径**收敛到同一行为**——不会出现 A 路径有脱敏、B 路径没有。
  ⛔ **脱敏只动凭据，绝不动业务数字、金额、日期、ID、commit sha、包名@版本、路径。**
  PII（邮箱 / 手机号 / 身份证）**默认关闭**，只在强上下文命中，需显式 `--pii` 开启。
- **诚实边界。** 本 skill **不能执行压缩**，也**不测量 token**；监控是建议性的，不能强制中断执行。详见 `SKILL.md` §0。

---

## 可选：主动提醒 hook

默认**不需要装**。宿主支持 hook 事件时，可让脚本在会话节点客观对撞、必要时主动提醒：

```bash
# 预览（不改任何配置）
python3 hooks/install_reminder.py --dry-run

# 安装（标准 settings 位置；其余 provider 会打印手动片段）
python3 hooks/install_reminder.py

# 卸载（移除 hook 标记并清状态）
python3 hooks/uninstall_reminder.py
```

- 状态在 `<workspace>/.baton-state/`（已在 `.gitignore`），不落 skill 包；命令不传输 prompt。
- 写 settings 前有信任门（路径不可信则拒绝）；运行时 hook fail-open、安装器 fail-closed。
- **提醒分两档**（双分支）：**L2 级信号**（连续 ≥3 个工作单元零落盘产物等硬触发）→ **催办行**，指示直接打包；**sub-L2 软信号**（连续 2 个工作单元零落盘、自报失真、体量轴 ≥40 轮（60 分钟跨度轴已删：实测 30.3% 命中=噪声））→ **询问行**，"是否打包"由你定。
- **触发源（v2.3.0 回正）**：`streak` 自报（`handoff/state.json`）优先，**没有自报账的普通会话改用客观值**（由会话事件时间线切工作单元算出，输出 `streak_source` 标注来源）——v2.1.x 曾绑死自报账导致主场景完全不提醒。
- **频控 1+1+静默**：每会话最多 2 次；第 2 次需距上次 ≥30 分钟且信号增强，换版点明"已连续 N 个工作单元未落盘"；两次后静默，交接文档落盘（`LATEST` 更新）自动重置。
- **退出通道**：提醒行末尾附「（说「别提醒」本会话不再提醒）」——说了之后执行 `python3 hooks/baton_reminder.py --mute <ws>` 关闭（`--unmute` 恢复）。
- **埋点与验收**：状态文件记 `exposure / handover_conversion / ignore` 三个纯计数（⛔ 不记 prompt）；**忽略率 = ignore/(ignore+handover_conversion)，>70% 应收紧触发**（70% 为工程推测，待数据收敛）。
- 升级 / Python 路径迁移后若 hook 变孤儿，重跑安装器或先卸载再装。
- 宿主不支持 hook（如豆包办公端）时忽略即可，核心交接不依赖它。
- **已知边界（FU-4，未修）**：tick 与 hook 按**传入的 workspace（缺省 cwd）**定位会话与状态；当运行 cwd ≠ workspace 时 hook 会失明——宿主行为不可控，本包不修，只在此声明。

---

## 许可

MIT，见 `LICENSE`。

- 漂移自检清单（`<DRIFT_SCAN>` / `<SCAN_RESULT>`）的**全部条目文本、类别命名、字段名与判档规则均为本项目自撰**，
  未复制任何 GPL-3.0 来源的 prompt 文本、标签或字段名。其分类维度（"把漂移拆成 5 类"这一想法）
  参考了公开实践中已有的做法，**来源数 n=1**（相关设计意图见 SKILL.md §1.3 漂移自检清单）。
  （v0 曾把这份清单写成 CEK（GPL-3.0）的 1:1 翻译却声称"自撰"，v0.1 已重写并改正表述。）
- 「每 10 轮」这个节拍**不是行业共识**，它同样来自**同一份单一来源（n=1）**，本文只当兜底采样节拍。

---

## ✅ 已拍板（2026-09-23）

- 命名：`baton` /「工作交接」
- 安装：本包即为源码；各端工作副本放在该客户端的 skill 目录（如 `.user_skills/baton/`），可用软链指向同一份源
