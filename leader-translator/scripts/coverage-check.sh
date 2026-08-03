#!/usr/bin/env bash
# coverage-check.sh — 任务书完整性核验（防偷删：覆盖清单的每个要点必须命中）
# 用法: coverage-check.sh <覆盖清单> <任务书文件>
#       覆盖清单: .goal/coverage.txt，一行一个必须包含的信息点（子串匹配，支持正则）
#                 支持 # 注释行与空行；带 ^ 的行表示「必须以该字符串开头」
# 退出码: 0 = 全部命中；1 = 有遗漏（漏点=偷删嫌疑，不许发出）
# 管理者写书前先物化覆盖清单（列这本书必须有哪些信息点），写完跑本脚本核对。

set -u
COVERAGE="${1:-}"
TASKBOOK="${2:-}"

if [ -z "$COVERAGE" ] || [ -z "$TASKBOOK" ]; then
  echo "用法: coverage-check.sh <覆盖清单> <任务书文件>"
  exit 2
fi
if [ ! -f "$COVERAGE" ]; then
  echo "❌ 找不到覆盖清单: $COVERAGE（写书前先物化 .goal/coverage.txt）"
  exit 1
fi
if [ ! -f "$TASKBOOK" ]; then
  echo "❌ 找不到任务书: $TASKBOOK"
  exit 1
fi

TOTAL=0; HIT=0; MISS=0
echo "===== coverage-check 完整性核验 ====="
while IFS= read -r line; do
  # 跳过空行与注释
  [ -z "$line" ] && continue
  case "$line" in \#*) continue ;; esac
  TOTAL=$((TOTAL+1))
  if grep -qF -- "$line" "$TASKBOOK"; then
    HIT=$((HIT+1)); echo "✅ 命中: $line"
  else
    MISS=$((MISS+1)); echo "❌ 遗漏: $line"
  fi
done < "$COVERAGE"

echo "-----------------------------"
if [ "$TOTAL" -eq 0 ]; then
  echo "⚠️ 覆盖清单为空——没物化任何必含信息点，完整性无据可查（先写清单再核验）"
  exit 1
elif [ "$MISS" -eq 0 ]; then
  echo "✅✅ 覆盖清单 ${TOTAL}/${TOTAL} 全部命中，任务书完整性通过"
  exit 0
else
  echo "❌ 覆盖清单遗漏 ${MISS}/${TOTAL}——漏点=偷删嫌疑，不许发出"
  exit 1
fi
