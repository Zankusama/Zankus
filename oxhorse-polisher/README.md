# oxhorse-polisher（牛马精修）

instruction-mode 自主打磨 skill：把"你一句我一句"的交互切换成"你给 goal，AI 在后台打磨到标准"。衔接 leader-translator 产物（外部任务书 ingest），也可自产标准（三问/七问）。

- **版本**：v2.1.0（2026-08-13）｜**定位**：instruction-mode 自主打磨，不假扮终审闸门（交付标"未经你终审"）
- **兼容**：workbuddy / trae / qoder 等（子Agent 不可用自动降级 NoAgent 模式）

## 安装

1. 将本目录放到平台的 skills 目录（或软链接到权威源 `AI记忆库/技能配置/oxhorse-polisher`）。
2. 依赖：零外部依赖（Python 标准库 + bash grep），无需安装任何包。

## 使用

触发词（开头即可，不强制空格）：

| 触发词 | 说明 |
|:---|:---|
| `牛马精修 …` / `oxhorse-polisher …` | 主触发 |
| `循环精修 …` / `loop polish …` | 别名 |

流程：阶段0 前置判定 → 阶段1 标准层（任务书 ingest 或三问/七问）→ 阶段2 打磨循环（执行→自查→找茬第二意见→修正，封顶4轮）→ 阶段3 交付（+执行履历，标注"未经你终审"）→ 阶段4 后续（标准持久化/经验回流）。

## 文件清单

| 文件 | 作用 |
|:---|:---|
| `SKILL.md` | 主文件：铁律/四层契约/阶段0-4/三接口/评估集/可机器化验收声明 |
| `references/progress-template.md` | progress.md 格式模板（细节外置） |
| `scripts/check_triggers.sh` | 触发词/定位断言（修改后防回退） |
| `scripts/check_standards.py` | standards.json schema 校验（v2.1） |
| `scripts/check_progress.py` | progress.md 结构校验 |
| `tests/trigger-assertions.md` | 触发测试（三场景：明显/改写/不相关） |

运行时数据（不随 skill 分发）：`~/.workbuddy/oxhorse-polisher/standards.json`（标准复用）+ `lessons/`（经验回流）。

## 维护

- 修改 SKILL.md/standards.json 后：跑 `bash scripts/check_triggers.sh` + `python3 scripts/check_standards.py` 回归。
- 真实使用发现误触发/漏步骤/产物偏差 → 补进评估集 + tests/，先回归再继续。
