#!/usr/bin/env bash
# fixapply.sh — 沙箱应用 + 自动验证（修一验一脚本化）
#
# 用法：
#   ./scripts/fixapply.sh <skill名> <item名> <修复后SKILL.md路径>
#       # 默认模式：备份真实文件 → 复制修复版到沙箱 → 跑评估器验证该项 → 输出 变绿/未变
#       # 变绿后提示：确认应用真实文件请加 --apply
#   ./scripts/fixapply.sh <skill名> <item名> <修复后SKILL.md路径> --apply
#       # 应用模式：沙箱验证通过后，把修复版复制回真实文件（有备份可回滚）
#
# 死规矩：
#   1. 应用真实文件前必须停下来确认（默认模式只提示，--apply 才写真实文件）
#   2. 每项独立验证，不许攒多项一起验
#   3. 应用前 output/backups/ 必须有 cp -p 备份（默认模式第一步就做；备份落 AI 会话工作区 output/ 下，不藏 skill 目录）
#   4. 不许吞失败（无 || true）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "${SCRIPT_DIR}/.." && pwd)"          # skill-rehab 包根：定位 sandbox 与被修样本
OUTPUT_ROOT="${OUTPUT_ROOT:-$(pwd)}"                 # 产物输出根：默认 AI 调用时工作区，OUTPUT_ROOT 可覆盖

SKILL="${1:?用法: fixapply.sh <skill名> <item名> <修复后SKILL.md路径> [--apply]}"
ITEM="${2:?缺 item 名（如 key_constraint_repeated）}"
FIX_SRC="${3:?缺修复后 SKILL.md 路径}"
APPLY="${4:-}"

REAL_FILE="${WORKSPACE}/${SKILL}/SKILL.md"   # 真实目标（SKILL 可为工作区内 skill 目录路径，如 tests/golden/g15_anchor_repeat_fail）
SANDBOX_DIR="${WORKSPACE}/tests/fixsandbox/${SKILL}"
SANDBOX_FILE="${SANDBOX_DIR}/SKILL.md"
BACKUP_DIR="${OUTPUT_ROOT}/output/backups"

if [ ! -f "${FIX_SRC}" ]; then
  echo "❌ 修复源不存在: ${FIX_SRC}" >&2
  exit 1
fi
if [ ! -f "${REAL_FILE}" ]; then
  echo "❌ 真实 SKILL.md 不存在: ${REAL_FILE}（按 <工作区>/<skill>/SKILL.md 查找）" >&2
  exit 1
fi

# ── 第一步：备份真实文件（应用前后都必须有备份）──
mkdir -p "${BACKUP_DIR}"
BACKUP_TAG="$(echo "${SKILL}" | tr '/' '_')"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_TAG}_SKILL.md.bak.$(date +%Y%m%d_%H%M%S)"
cp -p "${REAL_FILE}" "${BACKUP_FILE}"
echo "✓ 已备份真实文件 → ${BACKUP_FILE}"

# ── 第二步：修复版复制到沙箱 ──
mkdir -p "${SANDBOX_DIR}"
cp -p "${FIX_SRC}" "${SANDBOX_FILE}"
echo "✓ 修复版已复制到沙箱 → ${SANDBOX_FILE}"

# ── 第三步：沙箱跑评估器，验证该项 ──
VERDICT=$(python3 -c "
import sys, os
sys.path.insert(0, '${SCRIPT_DIR}')
import skill_eval
item = '${ITEM}'
r = skill_eval.evaluate_skill('${SKILL}', '${SANDBOX_FILE}')
found = False
for pn, layer in r['layers'].items():
    for itn, it in layer.items():
        if itn == item:
            found = True
            print('PASS' if it['passed'] else 'FAIL')
            break
    if found:
        break
if not found:
    print('ITEM_NOT_FOUND')
")
echo "── 沙箱验证 ──"
echo "  该项（${ITEM}）在沙箱评估结果: ${VERDICT}"

if [ "${VERDICT}" != "PASS" ]; then
  echo "❌ 该项未变绿（${VERDICT}）——修复没生效，禁止应用真实文件。"
  echo "  沙箱副本保留: ${SANDBOX_FILE}（可手动查看差异）"
  exit 1
fi

# ── 第四步：变绿 → 提示确认（默认模式停在这）──
echo "✅ 该项已变绿（${ITEM}: FAIL → PASS）"
if [ "${APPLY}" == "--apply" ]; then
  cp -p "${FIX_SRC}" "${REAL_FILE}"
  echo "✅ 已应用修复到真实文件: ${REAL_FILE}"
  echo "  回滚: cp '${BACKUP_FILE}' '${REAL_FILE}'"
else
  echo "── 真实文件未动（默认模式）──"
  echo "确认应用真实文件请执行："
  echo "  ./scripts/fixapply.sh ${SKILL} ${ITEM} ${FIX_SRC} --apply"
fi
