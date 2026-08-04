#!/usr/bin/env bash
# stage-gate.sh — 六道闸门（每步产出物校验，防跳步）｜编号 G1-G6，与流程步骤编号 1-7 区分（G=Gate 非步骤）
# 用法: stage-gate.sh <step> [file]
#   step=1  G1 定义   理清目标后：file=.goal/gate-1.txt（五层面答案，每行一层，共 5 行，缺=未清晰）
#   step=2  G2 调研完 调研后：    file=.goal/gate-2.txt（调研记录：查不到的必须标「假设，未验证」）
#   step=3  G3 补盲   盲点扫描后：file=.goal/gate-3.txt（补盲清单：必须含 ≥1 条 💡 主轴项）
#   step=4  G4 分类   提问后：    file=.goal/gate-4.txt（提问记录：必含「目前我听懂了的」小结 + 内部常识轮 + KANO 分类声明；⚠️ 项=0）
#   step=5  G5 写书前 写书前：    人类检查（不看文件）——脚本只输出核对清单，领导点头才算过
#   step=6  G6 写书后 写书后：    自动调 goal-lint + coverage-check + 回归目标；并输出「重点人工复核清单」
# 退出码: 0 = 过；1 = 不过
# 管理者每步跑一次，不过不许进下一步——防「定义跳过/问不全/写偏」全靠它挡。
# v1.6.0+ 防跳步预检：跑 G(N) 时自动检查 G(N-1) 产物存在——跳过本闸门 = 自动 fail（不靠 AI 自觉）

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

# === 防跳步预检（v1.6.0+）：G(N) 自动检查 G(N-1) 产物存在 ===
# G1 无前置跳过；G2-G4 检查 gate-(N-1).txt；G5/G6 是人工/自动检查不预检
if [ "$STEP" -ge 2 ] && [ "$STEP" -le 4 ]; then
  PREV=$((STEP - 1))
  PREV_FILE=".goal/gate-${PREV}.txt"
  if [ -f "$PREV_FILE" ]; then
    pass "防跳步预检：G${PREV} 产物 ${PREV_FILE} 存在"
  else
    fail "防跳步预检：缺 G${PREV} 产物 ${PREV_FILE}——回步骤 ${PREV} 跑 stage-gate.sh ${PREV} 生成后再来（G$STEP 不许在 G$PREV 没过的状态下跑）"
  fi
fi

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
    # ① 来源必带：调研产出必须带来源（URL/知识库/实测/文件路径），纯推理无来源=没调研
    if grep -qiE 'http|知识库|实测|路径|来源|source|查过|搜到|读到' "$FILE"; then
      pass "调研记录含来源标记（http/知识库/实测/路径）"
    else
      fail "调研记录没有任何来源（http/知识库/实测/路径）——纯内部推理不算调研，回步骤 2 真用工具查"
    fi
    # ② 三态判定：①有未知标注→过（查不到的标了）②明确全部查到→过 ③有未知迹象（估摸/大概/可能）但没标注→fail（漏标）
    if grep -qE '假设，未验证|未查到|未验证|查无' "$FILE"; then
      pass "调研记录含「假设，未验证/未查到」标注（查不到的标了）"
    elif grep -qE '全部查到|无未知|无需假设|无假设|全部核实|均查实' "$FILE"; then
      pass "调研记录明确全部查到（无未知项，无需标注）"
    elif grep -qE '估摸|大概|可能|不确定|估计' "$FILE"; then
      fail "调研记录有未知迹象（估摸/大概/可能）但没标「假设，未验证」——查不到必须标注，回步骤 2"
    else
      pass "调研记录无未知迹象（默认视为已查清；建议显式写「全部查到」更稳）"
    fi
    # ③ 🔍 可联网项应为 0（该联网的都查了）
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
    # 💡 必须带外部来源前缀（我的知识/联网查到/知识库）——内部常识凑数=fail
    SRC_CNT=$(grep -cE '💡.*(我的知识|联网查到|知识库|搜索|查到|实践)' "$FILE")
    [ "$SRC_CNT" -ge 1 ] || fail "💡 项都没有外部来源前缀（我的知识/联网查到/知识库）——拿内部常识凑数不算扫盲，回步骤 3 用外部知识真补盲"
    # 💡 必须带决策引导（怎么想/什么情况选什么）——盲区领导没想过，光列事实领导不知道怎么面对
    GUIDE_CNT=$(grep -cE '💡.*(判断|看|选|建议|考虑|维度|情况|条件|如果|则)' "$FILE")
    if [ "$GUIDE_CNT" -ge 1 ]; then
      pass "💡 项含决策引导（判断维度/选择路径）"
    else
      echo "⚠️ [闸门 G3] 💡 项缺决策引导——建议补「怎么想这事」或「什么情况选什么」（人工确认，不硬卡）"
    fi
    # 若有 ⚠️ 项但没给决策，允许（⚠️ 进步骤 4 提问解决，不在 3 卡）
    # 💡 联网查到必须带 URL（内容级校验——来源可验证，无 URL 应标 ⚠️ 未验证）
    NET_CNT=$(grep -cE '💡.*联网查到' "$FILE")
    if [ "$NET_CNT" -ge 1 ]; then
      NET_URL=$(grep -cE '💡.*联网查到.*(http|URL|链接|搜到|搜索|来源)' "$FILE")
      if [ "$NET_URL" -ge 1 ]; then
        pass "💡 联网查到 ${NET_CNT} 条带 URL/来源（可验证）"
      else
        echo "⚠️ [闸门 G3] 💡 联网查到 ${NET_CNT} 条无 URL——「联网查到」必须可验证，无 URL 应标 ⚠️ 未验证（人工确认，不硬卡）"
      fi
    fi
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
    # 内部常识轮必填（提问只问领导唯一知道的事——挖没挖干净）
    INT_CNT=$(grep -cE '内部常识|know-how|偏好|约束|历史背景|领导原话|领导唯一知道' "$FILE")
    [ "$INT_CNT" -ge 1 ] || fail "提问记录没有内部常识轮（know-how/偏好/约束/历史）——提问只问领导唯一知道的事，纯外部候选=没提问，回步骤 4 挖内部常识"
    pass "内部常识轮存在（× ${INT_CNT}）"
    # KANO 分类声明（清点 N 个未知：M 全处理/O 已默认/A 已归档/I 已扔/R 已禁——没问的被分类安置，不许静默消失）
    if grep -qE 'KANO|M 全处理|O 已默认|A 已归档|I 已扔|R 已禁|偏置' "$FILE"; then
      pass "KANO 分类声明存在（未知被分类安置：M/O/A/I/R）"
    else
      fail "提问记录缺 KANO 分类声明（清点 N 个未知：M 全处理/O 已默认/A 已归档/I 已扔/R 已禁）——没问的不许静默消失，回步骤 4 补声明"
    fi
    pass "提问分类清点通过（小结 + 内部常识 + KANO 分类声明 + ⚠️ 清零）"
    ;;
  5)
    echo "🟡 [闸门 G5 写书前] 人工检查——领导在对话里看图 + 文字骨架，逐项确认："
    echo "    呈现：用 scripts/pyramid-gen.py 生成 SVG，在对话里直接渲染给领导看（不许建 HTML 文件让领导自己打开）"
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
