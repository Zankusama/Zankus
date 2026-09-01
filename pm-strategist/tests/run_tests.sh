#!/bin/bash
# pm-strategist tests runner v3 — 机器可跑验收（exit 0=全绿，1=有红）
# 断言对象 = 当前版本结构（frontmatter/触发词/核心机制/框架与引用文件/输出规范/通用化红线/脚本自检）
set -u
S="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
chk() { if [ "$2" -ge 1 ]; then ok "$1 ($2 处)"; else bad "$1 (0 处)"; fi; }

echo "== pm-strategist tests v3 =="
SMD="$S/SKILL.md"

echo "[1] SKILL.md frontmatter"
for f in "^name: pm-strategist" "^version:" "^description:"; do
  grep -qE "$f" "$SMD" && ok "frontmatter 含 $f" || bad "frontmatter 缺 $f"
done

echo "[2] 触发词（description 覆盖）"
words=(新品评估 产品决策 帮我决策 该不该做 怎么取舍 值不值得做 优先做哪个 定价 上市); for w in "${words[@]}"; do
  c=$(grep -c "$w" "$SMD"); chk "触发词「${w}」" "$c"
done

echo "[3] 核心机制关键词（假设显式化/收敛/止损/通用化）"
words=(可逆 先说判断 反方 假设 待验证 收敛 止损 通用化); for w in "${words[@]}"; do
  c=$(grep -c "$w" "$SMD"); chk "机制「${w}」" "$c"
done

echo "[4] frameworks/ 六文件 + 结构段"
names=(五闸 决策记录 优先级 复盘 生意思维 协同); for n in "${names[@]}"; do
  f=$(ls "$S/frameworks/" 2>/dev/null | grep "$n" | grep -v "\.bak" | head -1)
  if [ -z "$f" ]; then bad "缺 ${n} 框架文件"; continue; fi
  F="$S/frameworks/$f"; allok=1
  for sec in 适用时机 已知局限; do
    grep -q "$sec" "$F" || { allok=0; bad "$f 缺「${sec}」"; }
  done
  [ "$allok" = 1 ] && ok "$f 结构段齐"
done

echo "[5] 黑名单表述（应 0 处）"
BL=$(grep -rcE "最佳实践所以可信|所以建议可信|基于最佳实践" "$S" --include="*.md" --include="*.py" 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
if [ "$BL" = 0 ]; then ok "无黑名单表述"; else bad "黑名单表述 $BL 处"; fi

echo "[6] 根目录文档卫生（仅 SKILL.md / README.md，防僵尸文档回潮）"
RD=$(find "$S" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
if [ "$RD" = 2 ]; then ok "根目录 .md 计数=2"; else bad "根目录 .md 计数=$RD（期望仅 SKILL.md/README.md）"; fi

echo "[7] SKILL.md 5场景路由表 + 类别规则"
for s in "S1 新品立项与产品定义" "S2 产品线组合规划" "S3 产品生命周期与迭代" "S4 定价与盈利" "S5 上市GTM策略"; do
  c=$(grep -c "$s" "$SMD"); chk "路由含「${s}」" "$c"
done
chk "A类分析透" "$(grep -c '分析透' "$SMD")"
chk "B类跨部门标注（定价）" "$(grep -c '最终定价决策需跨部门确认' "$SMD")"
chk "B类跨部门标注（上市）" "$(grep -c '最终上市决策需跨部门确认' "$SMD")"
chk "C类只提醒不决策" "$(grep -c '只提醒不决策' "$SMD")"

echo "[8] SKILL.md 输出规范：建议6要素 + 决策记录9字段 + 收敛终端"
for w in "推荐倾向" "权衡分析" "不做项" "数据需求引导" "假设清单" "复盘日期"; do
  c=$(grep -c "$w" "$SMD"); chk "规范「${w}」" "$c"
done
chk "9字段清单行" "$(grep -c '问题/选项/决定/依据/反方意见/风险/假设清单/复盘日期/状态' "$SMD")"
chk "收敛终端" "$(grep -c '收敛终端' "$SMD")"

echo "[9] references/ 六文件三部分结构"
rc=$(ls "$S/references/" 2>/dev/null | grep -c "ref-0")
if [ "$rc" = 6 ]; then ok "references ref-0 计数=6"; else bad "references ref-0 计数=$rc (期望6)"; fi
for f in "$S"/references/ref-0*.md; do
  n=$(basename "$f")
  c1=$(grep -cE "检查单|检查项" "$f"); c2=$(grep -c "输出模板" "$f")
  if [ "$c1" -ge 1 ] && [ "$c2" -ge 1 ]; then ok "$n 三部分齐（检查单=${c1} 模板=${c2}）"; else bad "$n 结构缺（检查单=${c1} 模板=${c2}）"; fi
done
chk "ref-04 B类标注" "$(grep -c '需跨部门确认' "$S/references/ref-04定价与盈利.md" 2>/dev/null || echo 0)"
chk "ref-05 B类标注" "$(grep -c '需跨部门确认' "$S/references/ref-05上市GTM策略.md" 2>/dev/null || echo 0)"

echo "[10] 通用化硬断言（品牌/业务专属术语 0 处，示例标注除外；扫描含根目录，防根目录僵尸文档；如需检测自定义品牌词，追加到下方 grep -E 词表）"
GEN=$(grep -rnE "样品|设计稿|相关背书|大货生产|资料移交" "$S"/*.md "$S/references" "$S/frameworks" --include="*.md" 2>/dev/null | grep -vE "示例|举例" | wc -l | tr -d ' ')
if [ "$GEN" = 0 ]; then ok "通用化扫描 0 命中"; else bad "通用化命中 $GEN 处"; fi
OLD=$(grep -rnE "启动框架|落地框架" "$S"/*.md "$S/references" "$S/frameworks" --include="*.md" 2>/dev/null | wc -l | tr -d ' ')
if [ "$OLD" = 0 ]; then ok "根目录+refs+fm 无旧分类字样"; else bad "旧分类字样 $OLD 处"; fi

echo "[11] 测试用例计数（正≥5 负≥3 + 场景用例≥5 + 行为/格式/可逆/组件/B类用例在位）"
PC=$(grep -cE '^\| P[0-9]' "$S/tests/trigger-positive.md" || true)
NC=$(grep -cE '^\| N[0-9]' "$S/tests/trigger-negative.md" || true)
if [ "$PC" -ge 5 ]; then ok "正用例 $PC 条 (≥5)"; else bad "正用例 $PC 条 (<5)"; fi
if [ "$NC" -ge 3 ]; then ok "负用例 $NC 条 (≥3)"; else bad "负用例 $NC 条 (<3)"; fi
TC=$(grep -cE '^\| TS[0-9]' "$S/tests/trigger-scenes.md" 2>/dev/null || true)
if [ "$TC" -ge 5 ]; then ok "场景触发用例 $TC 条 (≥5)"; else bad "场景触发用例 $TC 条 (<5)"; fi
for t in behavior-principles-cases.md output-format-cases.md reversibility-grading-cases.md components-cases.md b-class-tag-cases.md trigger-negative-scenes.md; do
  [ -f "$S/tests/$t" ] && ok "tests/$t 在位" || bad "tests/$t 缺失"
done
TCNT=$(ls "$S/tests/" | grep -vc "\.bak$" || true)
if [ "$TCNT" -ge 10 ]; then ok "tests 文件数 $TCNT (≥10)"; else bad "tests 文件数 $TCNT (<10)"; fi

echo "[12] 可逆性判别对（最严重事故的回归防线）"
RC="$S/tests/reversibility-cases.md"
if [ -f "$RC" ]; then ok "reversibility-cases.md 存在"; else bad "reversibility-cases.md 缺失"; fi
RP=$(grep -cE '^\| R[0-9]' "$RC" 2>/dev/null || echo 0)
if [ "$RP" -ge 4 ]; then ok "判别对 $RP 条 (≥4)"; else bad "判别对 $RP 条 (<4)"; fi
if grep -q "砍掉整条产品线" "$S/SKILL.md" && grep -q "品牌重新定位" "$S/SKILL.md"; then ok "判别锚例已写入 SKILL.md"; else bad "SKILL.md 判别锚例缺失"; fi

echo "[13] check_output.py 自检（输出不变量校验器本体）"
if python3 "$S/scripts/check_output.py" --self >/dev/null 2>&1; then ok "check_output.py --self 通过"; else bad "check_output.py --self 失败"; fi

echo "[14] scripts/ 8件在位 + def≥2"
py=$(ls "$S/scripts/" 2>/dev/null | grep -c "\.py$")
if [ "$py" = 8 ]; then ok "scripts .py 计数=8"; else bad "scripts .py 计数=$py (期望8)"; fi
for f in "$S"/scripts/*.py; do
  n=$(basename "$f"); d=$(grep -c "def " "$f")
  [ "$d" -ge 2 ] && ok "$n def数=$d (≥2)" || bad "$n def数=$d (<2)"
done

echo "[15] config/local_profile.md 预置空模板"
CFG="$S/config/local_profile.md"
if [ -f "$CFG" ]; then
  n=$(grep -c "【待固化】" "$CFG")
  if [ "${n}" -ge 6 ]; then ok "身份层模板在位，占位字段 ${n} 个（≥6）"; else bad "身份层模板占位字段 ${n} 个 (<6)"; fi
else
  bad "config/local_profile.md 模板缺失"
fi

echo "═══════════════════════════"
echo "结果：$PASS 通过，$FAIL 失败"
[ "$FAIL" = 0 ] && echo "ALL GREEN ✅" || echo "HAS RED ❌"
exit "$FAIL"
