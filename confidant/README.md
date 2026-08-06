# Confidant（知心伙伴）

给情绪已经影响到生活、又不愿意走进心理门诊的人，一个像朋友一样的倾听出口——温暖陪伴、有出处的科普与可练的方法、产出情绪画像（HTML 信息图），并内置危机识别与转介护栏。

## 安装

把本目录放到 WorkBuddy skills 目录（如 `~/.workbuddy/skills/confidant/`），或按 WorkBuddy 文档的 skill 安装流程导入。

## 使用

对话中直接说（任一触发词即可）：
- 「最近心里堵得慌，想找人说说话」
- 「帮我做个心理咨询」/「我想要心理支持」/「情绪低落想倾诉」
- 「给我做一份情绪画像」

skill 会自动进入陪伴模式；命中危机信号时切换危机模式，按 `references/crisis.md` 分级转介。

## 能力边界

| 能做 | 不能做 |
|:---|:---|
| 倾听、共情、情绪命名 | 医学诊断（不给病名/不下结论） |
| 有出处的科普（RAG 权威白名单） | 开药/用药建议 |
| 循证锚点解释（CBT/ACT/依恋等） | 承诺治愈/疗效保证 |
| 呼吸/正念练习引导 | 替代面诊/专业治疗 |
| 情绪画像（确认说完了 → AI 主动提议出，HTML 信息图） | 隐瞒 AI 身份 |
| 危机识别与转介（12356 等热线） | 危机时只共情不转介 |

## 对话与画像逻辑（v1.0.0）

- **两条正交轴**：安全轴（轻/中/重 = 风险等级，只决转介，每 4–6 轮内部重评）与对话轴（阶段 A 倾诉接住 → B 深度挖掘 → C 凝结画像）解耦，互不绑架——风险等级不决定出不出画像。
- **对话唯一终点 = 引导出画像**：全程不设轮次上限。AI 在阶段 B 主动把该说的都引导出来；当对方确认「说完了」且达根因（report.md 三条自检全过），AI 主动提议出情绪画像（对方可拒）。对方一直浅聊，AI 须持续引导而非等轮次；说完了仍未达根因则出「进展小结」。
- **双模板自动分层**：`scripts/check_readiness.py` 按对话深度选模板——聊出模式/根因 → 概念化专业版（`report_template.html`）；偏叙事回望 → 叙事性回望版（`report_narrative_template.html`）。
- **首屏状态条动态生成**：依个案维度抽 3–4 个关键维度（如 grief 案例→悲伤/功能/关系/意义），不再写死焦虑/睡眠/工作/希望。
- **RAG 分流**：对话过程内化不外露、保持朋友腔；画像交付物严挂白名单出处（who.int / apa.org / nimh.nih.gov / 卫健委 / PubMed / 三甲）。

## 文件清单

| 文件 | 作用 |
|:---|:---|
| `SKILL.md` | 主流程（双轴 / 阶段角色 / 分级 / RAG / 禁区 / 重评 / 变更记录） |
| `references/crisis.md` | 危机分级追问、热线与转介清单 |
| `references/anchors.md` | 循证锚点与出处 |
| `references/practices.md` | 可操作练习（4-7-8 / 盒式呼吸） |
| `references/report.md` | 情绪画像触发自检与 HTML 模板使用规范 |
| `references/report_template.html` | 情绪画像 HTML 信息图模板·概念化专业版（自包含 + 内联 SVG） |
| `references/report_narrative_template.html` | 情绪画像 HTML 信息图模板·叙事性回望版（同视觉风格） |
| `scripts/check_safety.py` | 安全红线自检脚本（退出码 0=过；`--output <画像>` 校验交付画像无占位符残留 + 禁区词话术区零使用） |
| `scripts/check_rag.py` | 运行时 RAG 合规校验器（`--mode dialogue` 对话内化 / 默认模式校验机制词出处；退出码 0=合规） |
| `scripts/check_readiness.py` | 出画像前就绪闸门（三道脚本写死判定：说完了 / 模式信号 / 客观优先；自动选模板） |
| `tests/trigger-positive.md` `tests/trigger-negative.md` | 触发正 / 负向用例 |
| `tests/behavior-convergence.md` | 行为收敛测试（5 场景：强制产出 / 收敛 / check_rag / 模板红线 / 画像后闭环） |

## 当前版本（v1.0.0）

- 脱离实验期首个稳定版（0.x → 1.x）；对话轴 / 安全轴正交互设计
- 对话唯一终点 = 引导出画像；删轮次上限，收敛靠「说完了」闸门 + AI 主动提议（可拒）
- 双模板（概念化版 + 叙事性回望版）按对话深度自动分层，由 `check_readiness.py` 三闸门脚本写死判定
- 首屏状态条动态生成 3–4 维度，不再写死焦虑/睡眠/工作/希望；症状谱系去 GAD-7 专用化
- 四条发问前自检 + 深度层纪律（表层 → 模式层 → 根层不可跳）
- RAG 分流：对话内化不外露、画像严挂白名单出处（`check_rag.py --mode dialogue`）
- 画像后闭环补「先接住知道根因的冲击」前置
- 三脚本机器校验兜底（safety / rag / readiness）

## 贡献与维护

- 修改红线内容（热线号码 / 禁区 / 危机话术）后必须重跑 `python3 scripts/check_safety.py`，退出码 0 才允许交付
- 出口任何心理机制 / 框架 / 干预内容前，跑 `python3 scripts/check_rag.py <回复文本>`（或 `--mode dialogue`），退出码 1 须先补白名单检索再出口
- 出画像前跑 `python3 scripts/check_readiness.py <对话历史>`，确认闸门通过、模板选择正确
- 版本变更记录在 `SKILL.md` §7.7
- 电话热线号码会变：建议每季度核验一次 `references/crisis.md` 中的号码
