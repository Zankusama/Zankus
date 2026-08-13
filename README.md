# zankus · 个人 Skill 仓库

个人 AI Skill 集合，每个 skill 一个子目录，独立安装使用。

## 仓库结构

| 目录 | Skill | 版本 | 说明 |
|------|-------|------|------|
| `leader-translator/` | 领导翻译官 | v5.12.0 | 围绕目标帮用户理清要做什么，并产出 AI 能直接执行的任务书（六道闸门防跳步、防作弊验收、5 行内人话报告） |
| `confidant/` | 知心伙伴 | v1.2.0 | 情绪倾诉陪伴：温暖倾听 + 有出处的心理科普 + 可练的方法，产出情绪画像（HTML 信息图），内置危机识别与转介护栏 |
| `skill-rehab/` | Skill 康复师 | v1.9.0 | 已封装 skill 的系统化康复流程：诊断（三源+对抗式验证闸）→ 分级处方 → 治疗 → 复查（五闸门）→ 交付 |
| `oxhorse-polisher/` | 牛马精修 | v2.1.0 | instruction-mode 自主打磨：把外部任务书（goal）当唯一标准，后台执行→自查→找茬第二意见→修正，精细打磨初稿到达标，衔接 leader-translator 产物 |

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
