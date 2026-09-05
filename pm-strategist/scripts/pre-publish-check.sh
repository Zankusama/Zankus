#!/bin/bash
# pre-publish-check.sh — 分享 / 上传 GitHub 前自检（v3.2 起：通用污染检测 + 个人词表外置）
#
# 检查两类问题：
#   A. 通用污染（随包分发，对任何使用者都生效）：外部技能点名 / 记忆系统依赖 /
#      开发过程与旧版残留 / 本机绝对路径 / 版本号不一致 / config 被填 / 运行时产物 / .git
#   B. 个人敏感词（真名、品牌）——词表不随包分发，按下列顺序在“包外”查找，找不到则 SKIP（不判失败）：
#        1) 环境变量 PM_PUBLISH_BLOCKLIST 指向的文件
#        2) 本技能包上级目录的 .pm-publish-blocklist.txt
#        3) 本技能包内 .blocklist.local（已被 .gitignore，仅供本机临时使用）
#
# 用法：bash scripts/pre-publish-check.sh [技能目录，默认脚本上级目录]
# 退出码：0 = 全部 PASS（个人词表缺失只 SKIP）；1 = 存在 FAIL
# 说明：统一 grep -E，不依赖 GNU BRE 的 \|，兼容 BSD/GNU/toybox/busybox
set -u
S="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
SELF="pre-publish-check.sh"
FAIL=0; PASS=0; SKIP=0

ok(){ echo "PASS  $1"; PASS=$((PASS+1)); }
no(){ echo "FAIL  $1"; printf '%s\n' "${2:-}" | sed 's/^/        /'; FAIL=$((FAIL+1)); }
sk(){ echo "SKIP  $1"; SKIP=$((SKIP+1)); }

# 通用文本扫描：$1=标题  $2=ERE 模式（检测器自身永远排除，避免规则词表自我命中）
scan(){
  local title="$1" pat="$2" hit
  hit=$(grep -rnE "$pat" "$S" \
          --include="*.md" --include="*.py" --include="*.sh" \
          --exclude="$SELF" --exclude=".blocklist.local" 2>/dev/null | grep -v "/\.git/")
  if [ -z "$hit" ]; then ok "${title}"; else no "${title}，命中：" "$hit"; fi
}

echo "=== 分享前自检：$S ==="

# 1) config/local_profile.md 必须仍是空模板（【待固化】≥6）——v4.3.0：身份层唯一文件，填写版含个人数据
CFG="$S/config/local_profile.md"
if [ -f "$CFG" ]; then
  n=$(grep -c "【待固化】" "$CFG")
  if [ "$n" -ge 6 ]; then ok "config 仍为空模板（占位字段 ${n} 个）"
  else no "config/local_profile.md 已被固化个人信息（占位仅 ${n} 个）——身份层填写版含个人数据，分享前须还原空模板或排除"; fi
else no "缺少 config/local_profile.md（应预置空模板）"; fi

# 1b) config/pm_settings.json（DR 落盘偏好，运行时生成）不得随包分享
if [ -f "$S/config/pm_settings.json" ]; then no "config/pm_settings.json 存在（本机 DR 偏好）——分享前删除"; else ok "无 config/pm_settings.json"; fi

# 2) 运行时产物 / 系统垃圾
LEAK=$(find "$S" \( -name "DR-*.md" -o -name "*.log" -o -name "__pycache__" \
                   -o -name "*.pyc" -o -name ".snapshots" -o -name ".DS_Store" -o -name "决策记录" \) 2>/dev/null | grep -v "/\.git/")
if [ -z "$LEAK" ]; then ok "无运行时产物（DR/日志/pycache/系统垃圾）"
else no "存在运行时产物，删除或排除后再分享：" "$LEAK"; fi

# 2b) scripts .py 计数（治理后应为 10：8 原有 + calc-pricing + profile-check）
PYC=$(find "$S/scripts" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$PYC" = "10" ]; then ok "scripts .py 计数=10"
else no "scripts .py 计数=$PYC（治理后期望 10）"; fi

# 3) .git 目录
if [ -d "$S/.git" ]; then ok ".git 存在（本地 git 开发模式：Step0a 版本管理目录，不入分发包；导出/上传前经 grep -v '/.git/' 排除，绝不含 .git）"
else ok "无 .git 目录"; fi

# 4) 外部技能点名（彻底不点名：能力边界一律用通用语表述）
scan "无外部技能点名（三明智/leader-translator/skill-rehab 等）" \
     "三明智|triwich|leader-translator|leader_translator|skill-rehab|skill_rehab"

# 5) 记忆系统依赖（他人未必装有记忆系统，身份层只靠 config 或当次提问）
scan "无记忆系统/记忆导入依赖" "agent 记忆导入|记忆系统"

# 6) 开发过程与旧版残留
scan "无开发过程/旧版残留（死规矩/旧口令/五类框架/版本演进/任务书编号/治疗记录等）" \
     "死规矩|旧口令|五类框架|与旧版|v1\.0\.|v2\.0\.|149/149|评估器|三方审查|任务书[0-9]|restore-my-skills|骨架废除|全项治疗"

# 7) 本机绝对路径（放行 ~/.xxx 这类通用 home 简写，只抓真实绝对路径与个人目录名）
scan "无本机绝对路径（/Users、/home、个人目录名）" "/Users/|/home/|AI记忆库"

# 8) 版本号一致性：以 SKILL.md frontmatter 的 version 为准，全包三段版本号不得有异
#    （README「版本记录」表 = 显式变更史，含历史版本属正常，放行表格行；只扫正文引用；
#      schema 版本行豁免：身份层字段口径版本≠包版本，仅字段集/口径变化时才 bump，不随包版本联动——BLOCKED B-1 解法 C）
CUR=$(grep -E '^version:' "$S/SKILL.md" | head -1 | sed -E 's/[^0-9]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/')
if [ -z "$CUR" ]; then no "SKILL.md frontmatter 读不到 version"; else
  DIFF=$(find "$S" -name "*.md" -not -path "*/.git/*" -print 2>/dev/null \
        | while IFS= read -r f; do \
            if [ "$(basename "$f")" = "README.md" ]; then \
              sed -E '/^\|[[:space:]]*[vV]?[0-9]+\.[0-9]+\.[0-9]+/d' "$f"; \
            else cat "$f"; fi; \
          done \
        | grep -vE 'schema[[:space:]]*版本' \
        | grep -oE "[vV]?[0-9]+\.[0-9]+\.[0-9]+" \
        | sed -E 's/^[vV]//' | grep -vE "^${CUR//./\\.}$" | sort -u)
  if [ -z "$DIFF" ]; then ok "版本号一致（全包均为 ${CUR}；README 变更史表放行）"
  else no "存在与 frontmatter(${CUR}) 不一致的版本号：" "$DIFF"; fi
fi

# 9) 个人敏感词（词表在包外；缺失则 SKIP，外部使用者没有你的词表属正常，不判失败）
BL=""
if [ -n "${PM_PUBLISH_BLOCKLIST:-}" ] && [ -f "$PM_PUBLISH_BLOCKLIST" ]; then BL="$PM_PUBLISH_BLOCKLIST"; fi
[ -z "$BL" ] && [ -f "$S/../.pm-publish-blocklist.txt" ] && BL="$S/../.pm-publish-blocklist.txt"
[ -z "$BL" ] && [ -f "$S/.blocklist.local" ] && BL="$S/.blocklist.local"
if [ -z "$BL" ]; then
  sk "未找到个人敏感词表（包外 .pm-publish-blocklist.txt 或环境变量 PM_PUBLISH_BLOCKLIST）——跳过个人名检测"
else
  PAT=$(grep -vE '^[[:space:]]*(#|$)' "$BL" | sed 's/[[:space:]]*$//' | paste -sd'|' - 2>/dev/null)
  if [ -z "${PAT:-}" ]; then sk "个人词表为空：${BL}"
  else
    HIT=$(grep -rnE "$PAT" "$S" --include="*.md" --include="*.py" --include="*.sh" \
            --exclude="$SELF" --exclude=".blocklist.local" 2>/dev/null | grep -v "/\.git/")
    if [ -z "$HIT" ]; then ok "无个人敏感词（词表：${BL}）"
    else no "命中个人敏感词，分享前必须清除：" "$HIT"; fi
  fi
fi

echo "=== 结果：PASS $PASS ｜ SKIP $SKIP ｜ FAIL $FAIL ==="
[ "$FAIL" -eq 0 ]
