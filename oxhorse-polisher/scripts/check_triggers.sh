#!/usr/bin/env bash
# usage: bash check_triggers.sh [SKILL.md 路径]
# 默认路径: 脚本同级的 ../SKILL.md（可移植，不写死本机绝对路径）
# 功能: 断言 oxhorse-polisher 触发词/定位关键词存在（修改后防回退）
# 退出码: 0=全过 / 1=有断言失败（可机器化验收用）
set -u

SKILL="${1:-$(cd "$(dirname "$0")/.." && pwd)/SKILL.md}"

if [ ! -f "$SKILL" ]; then
  echo "❌ SKILL.md 不存在: $SKILL"
  exit 1
fi

FAIL=0
check() {
  local kw="$1"
  local n
  n=$(grep -c "$kw" "$SKILL" 2>/dev/null || true)
  if [ "$n" -ge 1 ]; then
    echo "✅ $kw = $n"
  else
    echo "❌ $kw = 0（应 ≥1）"
    FAIL=1
  fi
}

check "牛马精修"
check "oxhorse-polisher"
check "循环精修"
check "loop polish"
check "instruction-mode"
check "不假扮终审闸门"

# 反向断言: 旧路径不得残留（改名/迁移防回退）
OLD=$(grep -c "references/task-standards.json" "$SKILL" 2>/dev/null || true)
if [ "$OLD" -eq 0 ]; then
  echo "✅ 旧路径 references/task-standards.json = 0"
else
  echo "❌ 旧路径 references/task-standards.json = $OLD（应 =0）"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "✅ 触发断言全过"
else
  echo "❌ 存在断言失败，请检查 SKILL.md"
fi
exit $FAIL
