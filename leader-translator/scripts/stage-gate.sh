#!/usr/bin/env bash
# stage-gate.sh — 六道闸门（每步产出物校验，防跳步）｜编号 G1-G6，与流程步骤编号 1-7 区分（G=Gate 非步骤）
# 用法: stage-gate.sh <step> [file]
#   step=1  G1 定义   理清目标后：file=.goal/gate-1.txt（五层面答案，每行一层，共 5 行，缺=未清晰）
#   step=2  G2 调研完 调研后：    file=.goal/gate-2.txt（调研记录：查不到的必须标「假设，未验证」）
#   step=3  G3 补盲   盲点扫描后：file=.goal/gate-3.txt（补盲清单：必须含 ≥1 条 💡 主轴项）
#   step=4  G4 穷尽   提问后：    file=.goal/gate-4.txt（提问记录：必含「目前我听懂了的」小结；⚠️ 项=0）
#   step=5  G5 写书前 写书前：    人类检查（不看文件）——脚本只输出核对清单，领导点头才算过
#   step=6  G6 写书后 写书后：    自动调 goal-lint + coverage-check + 回归目标；并输出「重点人工复核清单」
# 退出码: 0 = 过；1 = 不过
# 管理者每步跑一次，不过不许进下一步——防「定义跳过/问不全/写偏」全靠它挡。

STEP="${1:-}"
FILE="${2:-}"

if [ -z "$STEP" ]; then
  echo "用法: stage-gate.sh <step 1-6> [file]"
  echo "  G1-G4（step 1-4）需要该步产出物文件（.goal/gate-N.txt）"
  echo "  G5（step 5）人工检查，不需要文件"
  echo "  G6（step 6）写书后自动检查，不需要额外文件（自动调 goal-lint/coverage）"
  exit 2
fi

fail() { echo "❌ [闸门 G$STEP] $1"; exit 1; }
pass() { echo "✅ [闸门 G$STEP] $1"; }

case "$STEP" in
  1)
    [ -f "$FILE" ] || fail "缺 .goal/gate-1.txt（五层面答案，每行一层：给谁用/解决什么/形态/画面/禁区）"
    # 非空行数 ≥5（每层一行）
    LINES=$(grep -cE '.+' "$FILE")
    [ "$LINES" -ge 5 ] || fail "五层面只有 ${LINES}/5 层有答案——缺层=目标未清晰，回步骤 1"
    # 空答案过滤：只拦「不知道/待定/空白/TBD」（整行或行尾，兼容「解决什么：不知道」带前缀写法）；「无」放行（如「禁区=无」是实质答案）
    EMPTY=$(grep -cE '(不知道|待定|空白|TBD)$' "$FILE")
    [ "$EMPTY" -eq 0 ] || fail "五层面有 ${EMPTY} 层是空答案（不知道/待定/空白）——不许进步骤 2"
    pass "目标清晰度通过（五层面 ${LINES} 层均有实质答案）"
    ;;
  2)
    [ -f "$FILE" ] || fail "缺 .goal/gate-2.txt（调研记录）"
    # 三态判定：①有未知标注→过（查不到的标了）②明确全部查到→过 ③有未知迹象（估摸/大概/可能）但没标注→fail（漏标）
    if grep -qE '假设，未验证|未查到|未验证|查无' "$FILE"; then
      pass "调研记录含「假设，未验证/未查到」标注（查不到的标了）"
    elif grep -qE '全部查到|无未知|无需假设|无假设|全部核实|均查实' "$FILE"; then
      pass "调研记录明确全部查到（无未知项，无需标注）"
    elif grep -qE '估摸|大概|可能|不确定|估计' "$FILE"; then
      fail "调研记录有未知迹象（估摸/大概/可能）但没标「假设，未验证」——查不到必须标注，回步骤 2"
    else
      pass "调研记录无未知迹象（默认视为已查清；建议显式写「全部查到」更稳）"
    fi
    # 🔍 可联网项应为 0（该联网的都查了）
    if grep -qE '🔍' "$FILE"; then
      fail "调研记录仍有 🔍（可联网搜）项未清——能联网查的还没查完，回步骤 2"
    else
      pass "🔍 项已清零（能联网查的都查了）"
    fi
    ;;
  3)
    [ -f "$FILE" ] || fail "缺 .goal/gate-3.txt（补盲清单）"
    CNT=$(grep -cE '💡' "$FILE")
    [ "$CNT" -ge 1 ] || fail "补盲清单没有 💡 主轴项（AI 主动补盲是扫盲的核心，≥1 条才合格）"
    pass "补盲清单含 💡 × ${CNT}（AI 主动补盲到位）"
    # 若有 ⚠️ 项但没给决策，允许（⚠️ 进步骤 4 提问解决，不在 3 卡）
    ;;
  4)
    [ -f "$FILE" ] || fail "缺 .goal/gate-4.txt（提问记录）"
    grep -qE '目前我听懂了的|我理解到' "$FILE" || fail "提问记录没有「目前我听懂了的」小结——逐轮确认缺失，回步骤 4"
    # ⚠️ 项必须清零（被提问解决或被默认值覆盖）
    if grep -qE '⚠️' "$FILE"; then
      fail "提问记录仍有 ⚠️（需领导决策）项未清零——没问完或不许带未决项进写书，回步骤 4"
    else
      pass "⚠️ 项已清零（需领导决策的都定了或走了默认值）"
    fi
    pass "提问穷尽性通过（小结存在 + ⚠️ 清零）"
    ;;
  5)
    echo "🟡 [闸门 G5 写书前] 人工检查——领导看图 + 文字骨架，逐项确认："
    echo "    ① 塔尖「这活为什么干」是你要的吗？"
    echo "    ② 柱子（任务/界限/验收）齐不齐？有没有漏的？"
    echo "    ③ 顺序对不对（依赖在前的先做）？"
    echo "    领导全部点头 = 过；任一摇头 = 改到点头再写正文"
    exit 0   # G5 不判，人工定夺
    ;;
  6)
    SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    BOOK="${FILE:-}"
    if [ -z "$BOOK" ] || [ ! -f "$BOOK" ]; then
      echo "❌ [闸门 G6 写书后] 缺任务书文件: stage-gate.sh 6 <任务书.md>"
      exit 1
    fi
    echo "===== [闸门 G6] 写书后检查 ====="
    # 6a. goal-lint 全过
    "$SKILL_DIR/scripts/goal-lint.sh" "$BOOK" > /dev/null 2>&1 \
      && pass "goal-lint 全过" \
      || fail "goal-lint 有项不过——修完再进 6b"
    # 6b. 回归目标：任务书必须含「这活为什么干」+ 开头声明，且开头声明必须出现（塔尖在书里）
    grep -qE '这活为什么干' "$BOOK" || fail "任务书缺「这活为什么干」（塔尖）——没有意图的任务书不许发出"
    # 6c. 输出重点人工复核清单（猜的决策/假设/拆书方案/硬指标）
    echo "🟡 [闸门 G6] 重点人工复核清单（领导过目）："
    grep -nE '猜的|假设|拆书|硬指标' "$BOOK" | head -8 || echo "  （无猜的决策/假设/拆书项——如确认无，可跳过）"
    echo "    领导确认以上决策/假设可以接受 = 过；有异议 = 改书"
    exit 0
    ;;
  *)
    echo "❌ [闸门 G$STEP] 未知步骤（1-6）"
    exit 1
    ;;
esac
