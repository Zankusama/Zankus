# zankus · 个人 Skill 仓库

个人 AI Skill 集合，每个 skill 一个子目录，独立安装使用。

## 仓库结构

| 目录 | Skill | 说明 |
|------|-------|------|
| `leader-translator/` | 领导翻译官 | 围绕目标帮用户理清要做什么，并产出 AI 能直接执行的任务书（六道闸门防跳步、防作弊验收、5 行内人话报告） |

## 安装 Skill

把对应子目录（如 `leader-translator/`）放进你的 agent 客户端的 skills 目录：

- **用户级**（所有项目通用）：`~/.workbuddy/skills/<skill名>/`（或其他客户端的对应目录）
- **项目级**（仅当前项目）：`<项目根>/.workbuddy/skills/<skill名>/`

重启客户端即可使用。每个 skill 的详细安装与使用说明见其子目录内 README。

## 新增 Skill

1. 在仓库根目录新建子目录（英文名，如 `my-skill/`）
2. 放入 `SKILL.md`（必含 `name` / `description` / `version` frontmatter）+ 配套 references / scripts
3. 更新本文件的结构表
4. commit 后推送到 main

## 许可

各 skill 自带 LICENSE（默认 MIT，见子目录）。
