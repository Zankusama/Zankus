# skill-rehab — Skill 康复师

> 给「已经写好的 AI skill」做体检、出修复方案、复查验收的专用工具。
> 装完你能立刻干三件事：**诊断**任意 skill 的质量（打分 + 列出未过项）→ 按症状查**修复方案**（分级清单，不硬套格式）→ 复查通过后沉淀成**可复用案例**，越修越聪明。

它不是从 0 写新 skill 的脚手架，而是修「已封装 skill」的康复流程：**诊断 → 处方 → 治疗 → 复查 → 交付**。任意风格、任意人写的 skill，都能被系统化修好，而不是哪疼贴哪。

---

## 一、安装

### 方式一：三平台软链接同步（推荐，一条命令装完 WorkBuddy / Trae / Qoder）

本包随「技能配置」目录一起分发，目录内自带同步脚本 `restore-my-skills.sh`：

```bash
# 1. 把技能配置目录放到你喜欢的位置（例如：主目录/技能配置/）
# 2. 进目录跑脚本（默认：权威源=脚本所在目录）
cd 技能配置目录
./restore-my-skills.sh
```

脚本自动扫描目录下所有含 `SKILL.md` 的子目录（含本包 skill-rehab），按目录名建立软链接到三平台：

| 平台 | 软链接位置 |
|:---|:---|
| WorkBuddy | `~/.workbuddy/skills/` |
| Trae | `~/.trae-cn/skills/` |
| Qoder | `~/.qoder/skills/` |

软链接指向权威源目录——**以后改 skill 只改权威源一份，三平台天然同步**。自定义路径用参数：`-a` 权威源 / `-w` WorkBuddy / `-t` Trae / `-q` Qoder（`./restore-my-skills.sh -a /path/to/技能配置`）。

### 方式二：单包手动放置

只想装到单个平台时，把本包整个目录放进该平台的 skills 目录（目录名保持 `skill-rehab`），或建目录软链接指向你的副本：

```bash
ln -s /你的路径/skill-rehab ~/.workbuddy/skills/skill-rehab   # 以 WorkBuddy 为例
```

装完在 AI 对话里触发「修skill / 康复师 / skill体检 / 诊断skill / 打磨skill」即可接诊。

### 运行依赖

- **python3**（仅标准库 os/re/json/sys/argparse/datetime，无第三方包）
- 外部命令：无（评估器自包含）

---

## 二、使用

### 1. 诊断一条命令跑通

```bash
python3 scripts/skill_eval.py --base <技能目录> --skills <skill名> --output <报告目录>
```

> `<技能目录>` / `<skill名>` / `<报告目录>` 是**需要你替换的参数**，别照抄尖括号。示例：
> `python3 scripts/skill_eval.py --base ~/我的skills --skills skill-rehab --output ~/report`

输出：总分（0–100，等级 S/A/B/C）+ 十个原理逐项得分 + 未过项清单 + 边界声明。

### 2. 怎么读报告（双源，缺一不可）

诊断结论来自**两个独立来源**，只看一个会漏判：

- **① 必要条件闸门——内置评估器**（`scripts/skill_eval.py`，v4.2.0 · 7 层架构 · P0/P1/P2 分级打分 · ~134 分）：做「有无类」判定——该有的有没有、结构健不健壮。**评估器满分 ≠ skill 全好**：它只证明「必要条件齐了」，证明不了「这一类 skill 该有的都想到了」（案例 01 实证：机器 100 分仍被完整性自查挖出 3 处纪律性盲区）。7 层：定位/触发/骨架/质量/安全/工程/生命周期（生命周期不进评估器，靠 completeness.md 引导）。
- **② 充分性审查——类别完整性清单**（`references/completeness.md`）：按 skill 类别穷尽「这类该有的」，逐项核对——评估器没点名的项，这里也不许跳过。

两源都过才算「诊断合格」；处方（`references/mechanism.md`）把两源缺口合并后按 Kano 五类分级（基本型必改 / 期望型建议 / 兴奋型备选 / 无差异跳过 / 反向红线），按机制给修法，不按格式给——不同风格 skill 不会被修成同一模子。

### 3. 五步流程速览

| 步骤 | 做什么 | 关键产出 |
|:---|:---|:---|
| ① 诊断 | 跑评估器（闸门）+ 完整性清单（充分性） | 总分 + 未过项 + 缺口 |
| ② 处方 | 未过项查 `references/mechanism.md`，按 Kano 五类分级 | 分级修复清单 |
| ③ 治疗 | 只修基本型（防镀金，死规矩 9），修一验一 | 每项 diff |
| ④ 复查 | 全量重跑评估器（分 ≥ 修复前）+ 完整性清单缺口清零 | 双源复查结论 |
| ⑤ 交付 | 修复 diff + 修复履历（为什么修 → 对应机制） | 可交付报告 |

---

## 三、贡献

- **提 issue / 反馈问题**：去项目仓库（`Zankusama/Zankus`，目录 `skill-rehab/`）开 issue，附上：skill 名称 + 诊断报告关键输出 + 你期望的行为。评估器误判（假阳性/假阴性）请同时贴 `scripts/skill_eval.py` 版本（`__version__`）与 `tests/golden/` 样本名。
- **案例入库**：康复治疗复查通过后，按 `references/cases/README.md` 的入库规则（复查通过 / 有真实改动 / 格式自包含 / 分级清楚 / 日期+评估器版本）新增 `{skill名}-case-{序号}.md`，并报备（哪个 case / 符合哪几条规则 / 格式是否合规）。评估器自身 bug 修复**不入案例库**——走版本管理归档到 `references/eval-notes/`。
- **修评估器**：见下方「评估器版本管理流程」——先 `guard.sh snapshot` 冻结基线，改完 `guard.sh check` + `verify` + 自举回归，最后重新 snapshot，不许裸改。

---

## 四、附录（维护者向）

### 内置评估器

- 版本：`scripts/skill_eval.py`（`__version__ = "4.2.0"`）；7 层架构 · P0 基本型 5 分/P1 期望型 3 分/P2 兴奋型 1 分 · 总分 134（机器 114 + 评审 20）
- 自检：`python3 scripts/skill_eval.py --self` 全过（层 weight = item 之和 / P0 项 14 个）
- goldens 回归集：`python3 scripts/run_goldens.py`（tests/golden/ 56 样本）——评估器升级必过，防「越改越瞎」
- 判卷完整性：`./scripts/guard.sh verify`（评估器 sha256 冻结核对）+ `./scripts/guard.sh check`（--self + goldens 全过）

### 评估器版本管理流程（v3 起）

1. **改前**：`./scripts/guard.sh snapshot` 冻结当前 sha256
2. **改中**：自由改 `scripts/skill_eval.py`
3. **改后**：`./scripts/guard.sh check` + `./scripts/guard.sh verify`（应 fail = 改了 = 预期）+ 自举回归 ≥90
4. **正式发布**：`./scripts/guard.sh snapshot` 重置基线
5. **禁止**：不 snapshot 改评估器 = 静默事故（死规矩 1）

### 边界

- **NOT for 从 0 设计新 skill**（只修已封装 skill）
- **NOT for 文案/合规审核类任务**（各有专职流程）
- 包内零绝对路径（以主目录开头的路径命中 = 0），脚本一律相对路径，可整包分享

---

## 变更记录

- **v1.6.0（2026-08-05）**：流程缺陷修复（交接包 D1-D5 全落地，Kano 分级+稳定优先）：修 fixapply.sh KeyError + fixgen.py 正则失配；口径统一（总分 125→134，等级阈值对齐代码）；验收锚点升级（判定词+脚本存在双条件）；行为层 3 新检查项（产出载体/收敛终端/运行时行为校验）；诊断报告增「运行时行为合规」章节；行为测试规范（tests/behavior-*.md + 真实演练可选人工复核）；goldens 56→62 断言；评估器 v4.1.0→v4.2.0。
- **v1.5.0（2026-08-05）**：路径可移植性（本次踩坑根因）：评估器③骨架层加 l3_path_portability（P1/3分，判裸相对脚本调用须显式声明路径策略）+ run_runtime_tests.py 加 R5 异地执行探测（真跑非文本判，退出码≠127/2）+ checklist 运行时实测 4→5 项 + 新增 golden 样本 g55_path_fail（锁死回归）+ 评估器 v4.0.0→v4.1.0（总分 122→125）。
- **v1.2.0（2026-08-03）**：双源流程成文（必要条件闸门 + 完整性清单充分性审查）+ goldens 回归集落地 + scriptized 收紧；README 重构为陌生人向四段（首屏/安装/使用/贡献）。
- **v1.1.1（2026-08-03）**：分享泛化——NOT for 去掉私有 skill 指向（可分享给任何人）；清理内部称呼噪音；checklist 加 S10 分享泛化检查。
- **v1.1.0（2026-08-03）**：自举康复——死规矩 9 只做基本型（防镀金）；评估器升级走版本管理；修法来源三级声明（设计推断/案例验证/行业实践）。
- **v1.0.2（2026-08-03）**：分级升级 Kano 五类——兴奋/无差异/反向三类处理策略 + Kano 迁移定律。
- **v1.0.1（2026-08-03）**：自修复——命令占位符加替换说明；死规矩 8 未验证标注；版本变更记录机制。
- **v1.0.0（2026-08-03）**：初版——五步流程 + 防五死法 + 内置评估器。
