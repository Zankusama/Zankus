#!/bin/bash
# publish-check.sh — 发布脚本化（G-8 + 上传纪律固化，v3.0 W-28）
#
# 职责：把「connector 整目录上传」这条真实泄露路径收口成一条可重复的安全流程。
#   ① 备份本地填写版身份档案 config/local_profile.md（若当前是填写版）
#   ② 从 git HEAD 还原空模板（模板态——pre-publish-check 第 1 项要求的形态）
#   ③ 跑 pre-publish-check.sh，要求全 PASS 才放行
#   ④ 输出 connector 上传清单 + 永不更新远端 config/local_profile.md 提醒
#   ⑤ 无论通过与否，把填写版身份档案恢复回本地（本机继续可用）
#
# 用法：bash scripts/publish-check.sh [技能目录，默认脚本上级目录]
# 退出码：0 = pre-publish-check 全 PASS 且填写版已恢复；1 = 校验有红项或流程中断
#
# 与 pre-publish-check.sh 的关系：那是「能不能发」的静态判定（单次）；本脚本是
# 「要发了」的完整编排（备份→净化→判定→清单→恢复），判定逻辑复用前者，不重复实现。
set -u
S="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PPC="$S/scripts/pre-publish-check.sh"
CFG="$S/config/local_profile.md"

TPL_FROM_GIT=0
BACKUP=""
RC=1

echo "=== 发布编排：$S ==="

# 0) 前置：净化脚本必须在位
if [ ! -f "$PPC" ]; then
  echo "FAIL  pre-publish-check.sh 不存在（$PPC）——发布流程不可用"
  exit 1
fi

# 1) 判断当前身份档案形态；若是填写版先备份，并从 git HEAD 还原模板
filled=0
ph(){ grep -c "【待固化】" "$1" 2>/dev/null || true; }
if [ -f "$CFG" ]; then
  n=$(ph "$CFG"); n=${n:-0}
  [ "$n" -lt 6 ] && filled=1
fi

if [ "$filled" = "1" ]; then
  BACKUP=$(mktemp -d)
  cp "$CFG" "$BACKUP/local_profile.filled.md"
  echo "  · 发现填写版身份档案（占位<6），已备份到 $BACKUP"
  if git -C "$S" show HEAD:config/local_profile.md > "$CFG" 2>/dev/null; then
    TPL_FROM_GIT=1
    echo "  · 已从 git HEAD 还原空模板（占位=$(ph "$CFG")）"
  else
    echo "  · 无法从 git 还原模板（无 .git 或文件未跟踪）——将直接校验，填写版会拦下本次发布"
  fi
elif [ -f "$CFG" ]; then
  echo "  · 当前已是空模板（占位=$(ph "$CFG")），无需备份/还原"
else
  echo "  · config/local_profile.md 不存在——pre-publish-check 会拦截（发布前请确认模板在包内）"
fi

# 2) 运行净化判定
echo ""
if bash "$PPC" "$S"; then
  RC=0
  echo ""
  echo "=== 校验全 PASS，可发布 ==="
else
  RC=1
  echo ""
  echo "=== 校验存在红项——禁止发布（先修红项，重跑本脚本） ==="
fi

# 3) 输出 connector 上传清单与禁区提醒（无论 PASS/FAIL 都打印，供排障对齐）
echo ""
echo "=== connector 上传清单（整目录推送） ==="
if [ -d "$S/.git" ]; then
  git -C "$S" ls-files --cached 2>/dev/null | grep -v '^config/local_profile.md$' | sed "s#^#$S/#" || true
else
  ls -1 "$S"
fi
echo ""
echo ">>> 禁区：永不更新远端 config/local_profile.md（保持远端【待固化】模板版）"
echo ">>> 禁区：推送后抽查一次远端该文件，仍须是模板版（发布 gate 三重确认第 3 步）"

# 4) 恢复填写版（唯一含个人数据的版本，只留本机）
if [ -n "$BACKUP" ] && [ -s "$BACKUP/local_profile.filled.md" ]; then
  cp "$BACKUP/local_profile.filled.md" "$CFG"
  echo ""
  echo "✓ 已恢复本地填写版身份档案（占位=$(ph "$CFG")）"
fi

exit "$RC"