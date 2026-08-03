#!/usr/bin/env bash
# guard.sh — 评估器版本管理（满足死规矩 1：评估器可升级须走版本管理）
#
# 用法：./scripts/guard.sh {snapshot|verify|check|diff|list}
#   snapshot  冻结当前评估器 sha256（评估器升级前必跑）
#   verify    校验评估器未越界（sha256 == 最新 snapshot）——防止被静默改
#   check     跑评估器 --self 自检（必过）
#   diff      对比当前评估器与最新 snapshot 的差异（用于版本回顾）
#   list      列出历史 snapshot 文件
#
# 死规矩 1（v1.1.1 落地）：
#   升级走版本管理：改前 guard.sh snapshot 冻结、改后 --self + 自举回归
#   不降分 + README 记版本号；不许顺手改（无版本记录的随意改动=静默事故）。
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL="${SCRIPT_DIR}/skill_eval.py"
SNAPSHOT_DIR="${SCRIPT_DIR}/.snapshots"
LATEST_LINK="${SNAPSHOT_DIR}/latest.sha256"
LATEST_FILE="${SNAPSHOT_DIR}/latest.py"

cmd=${1:-help}

sha256_of() { shasum -a 256 "$1" | awk '{print $1}'; }

case "$cmd" in
  snapshot)
    mkdir -p "$SNAPSHOT_DIR"
    ts=$(date +%Y%m%d-%H%M%S)
    sha=$(sha256_of "$EVAL")
    snap_file="${SNAPSHOT_DIR}/skill_eval_${ts}.py"
    cp -p "$EVAL" "$snap_file"
    echo "$sha  $(basename "$snap_file")" > "$LATEST_LINK"
    cp -p "$EVAL" "$LATEST_FILE"
    echo "✓ snapshot 冻结：sha256=${sha:0:12}...  文件=${snap_file}"
    echo "  之后改评估器会被 verify 检出"
    ;;
  verify)
    if [ ! -f "$LATEST_LINK" ]; then
      echo "✗ no snapshot, 先跑: guard.sh snapshot" >&2
      exit 1
    fi
    current=$(sha256_of "$EVAL")
    frozen=$(awk '{print $1}' "$LATEST_LINK")
    if [ "$current" = "$frozen" ]; then
      echo "✓ verify OK：评估器未动（sha256 一致）"
    else
      echo "✗ verify FAIL：评估器被改"
      echo "  frozen:  ${frozen:0:12}..."
      echo "  current: ${current:0:12}..."
      echo "  如确认是预期升级，跑 guard.sh snapshot 重置基线"
      exit 1
    fi
    ;;
  check)
    if ! python3 "$EVAL" --self >/dev/null 2>&1; then
      echo "✗ check FAIL：--self 没全过" >&2
      python3 "$EVAL" --self 2>&1 | tail -10 >&2
      exit 1
    fi
    if ! python3 "${SCRIPT_DIR}/run_goldens.py" >/dev/null 2>&1; then
      echo "✗ check FAIL：goldens 回归测试集没全过（评估器盲区/越改越瞎）" >&2
      python3 "${SCRIPT_DIR}/run_goldens.py" 2>&1 | tail -15 >&2
      exit 1
    fi
    echo "✓ check：--self + goldens 全过"
    ;;
  diff)
    if [ ! -f "$LATEST_FILE" ]; then
      echo "✗ no snapshot, 先跑: guard.sh snapshot" >&2
      exit 1
    fi
    diff -u "$LATEST_FILE" "$EVAL" || true
    ;;
  list)
    if [ ! -d "$SNAPSHOT_DIR" ] || [ -z "$(ls -A "$SNAPSHOT_DIR" 2>/dev/null)" ]; then
      echo "（无 snapshot）"
      exit 0
    fi
    ls -lt "$SNAPSHOT_DIR" | head -10
    ;;
  help|*)
    cat <<'EOF'
Usage: guard.sh {snapshot|verify|check|diff|list}
  snapshot  冻结当前评估器 sha256（评估器升级前必跑）
  verify    校验评估器未越界
  check     跑评估器 --self 自检
  diff      对比当前评估器与最新 snapshot
  list      列出历史 snapshot
EOF
    ;;
esac
