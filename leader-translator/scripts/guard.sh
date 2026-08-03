#!/usr/bin/env bash
# guard.sh — 判卷冻结 + 基线不可退（把「防作弊」两条硬防线变成命令）
# 四个子命令：
#   guard.sh snapshot <基线文件> <路径...>            # 任务前：冻结判卷文件的 sha256
#   guard.sh verify   <基线文件>                      # 验收时：对比 hash，判卷被改即失败
#   guard.sh record   <基线文件> "key=value" [...]    # 任务前：记录数字基线（如 tests=42）
#   guard.sh check    <基线文件> "key=value" [...]    # 验收时：实际值 ≥ 基线才过
# 退出码: 0 = 过；1 = 不过
# 用法示例（写进任务书任务 0 与验收节）:
#   guard.sh snapshot .goal/hashes.txt tests/ ci.yml
#   guard.sh record   .goal/baseline.txt tests=42 coverage=80
#   guard.sh verify   .goal/hashes.txt
#   guard.sh check    .goal/baseline.txt tests=45 coverage=81

CMD="$1"; BASE="$2"; shift 2 2>/dev/null

# macOS 自带 shasum；Linux 通常用 sha256sum；缺则回退到 shasum（兼容 BSD）
if command -v sha256sum >/dev/null 2>&1; then
  hash_of() { sha256sum "$1" | cut -d' ' -f1; }
else
  hash_of() { shasum -a 256 "$1" | cut -d' ' -f1; }
fi

case "$CMD" in
  snapshot)
    [ -n "$BASE" ] || { echo "用法: guard.sh snapshot <基线文件> <路径...>"; exit 1; }
    : > "$BASE"
    for f in "$@"; do
      if [ -f "$f" ]; then echo "$(hash_of "$f")  $f" >> "$BASE"; else echo "⚠️ 路径不存在，跳过: $f"; fi
    done
    echo "✅ snapshot: $# 个文件 hash 已冻结 → $BASE"
    ;;
  verify)
    [ -f "$BASE" ] || { echo "❌ 找不到基线文件 $BASE（先跑 guard.sh snapshot）"; exit 1; }
    FAIL=0; CNT=0
    while read -r hash path; do
      [ -z "$hash" ] && continue
      CNT=$((CNT+1))
      if [ -f "$path" ]; then
        if [ "$(hash_of "$path")" = "$hash" ]; then echo "✅ 未变: $path"; else echo "❌ 已变: $path"; FAIL=1; fi
      else
        echo "❌ 文件消失: $path"; FAIL=1
      fi
    done < "$BASE"
    if [ "$FAIL" -eq 0 ] && [ "$CNT" -gt 0 ]; then echo "✅✅ 判卷文件全部冻结（${CNT} 个）"; exit 0
    elif [ "$CNT" -eq 0 ]; then echo "⚠️ 基线文件为空，没冻结任何文件"; exit 1
    else echo "❌ 判卷被改，验收失败"; exit 1; fi
    ;;
  record)
    [ -n "$BASE" ] || { echo "用法: guard.sh record <基线文件> \"key=value\" ..."; exit 1; }
    : > "$BASE"
    for kv in "$@"; do echo "$kv" >> "$BASE"; done
    echo "✅ 基线已记录（$# 项）→ $BASE"
    ;;
  check)
    [ -f "$BASE" ] || { echo "❌ 找不到基线文件 $BASE（先跑 guard.sh record）"; exit 1; }
    FAIL=0; CNT=0
    for kv in "$@"; do
      key="${kv%%=*}"; val="${kv##*=}"
      base=$(grep "^${key}=" "$BASE" | head -1 | cut -d= -f2)
      [ -z "$base" ] && { echo "⚠️ 基线无此键: $key（record 时没记？）"; continue; }
      CNT=$((CNT+1))
      if awk -v a="$val" -v b="$base" 'BEGIN{exit !(a>=b)}'; then
        echo "✅ $key: $val ≥ 基线 $base"
      else
        echo "❌ $key: $val < 基线 $base"; FAIL=1
      fi
    done
    if [ "$FAIL" -eq 0 ] && [ "$CNT" -gt 0 ]; then echo "✅✅ 基线全部守线（${CNT} 项）"; exit 0
    elif [ "$CNT" -eq 0 ]; then echo "⚠️ 没有可对比的键"; exit 1
    else echo "❌ 基线失守，验收失败"; exit 1; fi
    ;;
  *)
    echo "用法: guard.sh snapshot|verify|record|check <基线文件> [...]"
    exit 1;;
esac
