#!/bin/bash
# tests/test-scripts.sh — 8 脚本批量功能测试（exit 0=全绿，1=有红）
# 每脚本：--help 退出码0 + --self 退出码0 + 指定样例行为断言
set -u
S="$(cd "$(dirname "$0")/.." && pwd)"
SC="$S/scripts"
PASS=0; FAIL=0
ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

echo "== test-scripts.sh：8 脚本功能测试 =="

# ---------- 通用：help + self + def 数 ----------
for f in check_output.py scene-router.py stage-gate-check.py decision-record.py risk-check.py unknown-info-check.py priority-calc.py kano-classify.py; do
  if python3 "$SC/$f" --help >/dev/null 2>&1; then ok "$f --help 退出码0"; else bad "$f --help"; fi
  if python3 "$SC/$f" --self >/dev/null 2>&1; then ok "$f --self 通过"; else bad "$f --self"; fi
  n=$(grep -c "def " "$SC/$f")
  if [ "$n" -ge 2 ]; then ok "$f def数=$n (≥2)"; else bad "$f def数=$n (<2)"; fi
done

# ---------- 1 check_output.py ----------
cat > "$T/good.md" <<'EOF'
路径声明：验证轨 | 场景=S4 定价与盈利 | 可逆性=🔴不可逆 | 主查=ref-04定价与盈利.md
1. 选项：中价格带上沿 / 低价渗透 / 维持现价（含不做/维持现状）
2. 推荐倾向：中价格带上沿
3. 权衡分析：对毛利/销量/渠道接受度对账
4. 不做项说明：不做超低价（伤定位）
5. 风险：法规未命中；市场（季节波动）；竞争（跟价）；供应链（备货交期）；财务（毛利）；组织（培训）
6. 数据需求引导：补竞品成交价与支付意愿数据
# DR-20260831-p2-price
- 问题：[示例占位]A品上市定什么价
- 选项：中价格带上沿 / 低价渗透 / 维持现价
- 决定：推荐中价格带上沿
- 依据：ref-04 3C定价与价格带分析
- 反方意见：竞品若同步降价则渗透逻辑失效
- 风险：法规未命中；市场（季节）；竞争（跟价）；供应链（备货）；财务（毛利）；组织（培训）
- 假设清单：
⚠️ 假设·待验证：价格敏感度中等
- 复盘日期：2026-12-31
- 状态：草案
⚠️ 最终定价决策需跨部门确认（财务/销售/渠道/管理层）
EOF
cat > "$T/bad.md" <<'EOF'
# DR-20260831-x
- 问题：随便
- 决定：就这么干
- 状态：搞定
EOF
if python3 "$SC/check_output.py" "$T/good.md" >/dev/null 2>&1; then ok "check_output 好样本退出0"; else bad "check_output 好样本误报"; fi
if python3 "$SC/check_output.py" "$T/bad.md" >/dev/null 2>&1; then bad "check_output 坏样本漏检"; else ok "check_output 坏样本退出1并报缺失"; fi

# ---------- 2 scene-router.py ----------
declare -a QS=( "这个新品该不该立项？" "产品线太多先砍哪个" "这个品卖不动了怎么办" "要不要涨价" "新品怎么上市先铺哪些渠道" "帮我看看有什么风险" )
declare -a EXP=( "S1" "S2" "S3" "S4" "S5" "C类" )
for i in 0 1 2 3 4 5; do
  out=$(python3 "$SC/scene-router.py" "${QS[$i]}")
  if echo "$out" | grep -q "场景=${EXP[$i]}"; then ok "scene-router 「${QS[$i]}」→${EXP[$i]}"; else bad "scene-router 「${QS[$i]}」期望${EXP[$i]}，实得：$out"; fi
done
if python3 "$SC/scene-router.py" --json "要不要涨价" | python3 -c "import json,sys; json.load(sys.stdin)" >/dev/null 2>&1; then ok "scene-router --json 合法"; else bad "scene-router --json"; fi

# ---------- 3 stage-gate-check.py ----------
EMPTY=$(printf '' | python3 "$SC/stage-gate-check.py" - >/dev/null 2>&1; echo $?)
if [ "$EMPTY" = "1" ]; then ok "stage-gate 空上下文报缺失退出1"; else bad "stage-gate 空上下文退出码=$EMPTY"; fi
cat > "$T/full.txt" <<'EOF'
闸1齐：机会描述与来源、目标用户与使用场景界定、初步竞品扫描；渠道反馈、客服退货聚类已收集。
闸2齐：市场规模估算、毛利与成本区间测算、回本周期估算、风险清单与可逆性分级；财务口径复核、供应链产能确认。
闸3齐：产品概念陈述、差异化卖点定义、目标价格带与成本上限、概念测试与原型验证；研发确认、卖点测试。
闸4齐：试制品验证、成本达成核对、合规与质量风险确认、试销计划；批量生产可行性与产能排期、检测标准与法务结论。
闸5齐：复盘会AAR、销售与利润对照立项承诺、假设-结果对照、经验回填；动销库存复购反馈、交付良率与成本复盘。
EOF
if python3 "$SC/stage-gate-check.py" "$T/full.txt" >/dev/null 2>&1; then ok "stage-gate 全过样本退出0"; else bad "stage-gate 全过样本误报"; fi
if python3 "$SC/stage-gate-check.py" "$T/full.txt" | grep -q "通过"; then ok "stage-gate 关口建议含通过"; else bad "stage-gate 建议缺失"; fi

# ---------- 4 decision-record.py ----------
if python3 "$SC/decision-record.py" --template | grep -q "假设清单" && python3 "$SC/decision-record.py" --template | grep -q "复盘日期"; then ok "decision-record 模板含9字段"; else bad "decision-record 模板缺字段"; fi
printf '问题：A品要不要涨价\n' > "$T/miss.txt"
if python3 "$SC/decision-record.py" "$T/miss.txt" >/dev/null 2>&1; then bad "decision-record 缺必填未拦截"; else ok "decision-record 缺选项/决定 退出1"; fi
printf '问题：A品要不要涨价\n选项：涨/不涨（含维持现状）\n决定：推荐小步涨\n' > "$T/ok.txt"
if python3 "$SC/decision-record.py" "$T/ok.txt" >/dev/null 2>&1; then ok "decision-record 必填齐 退出0"; else bad "decision-record 合法样本误报"; fi

# ---------- 5 risk-check.py ----------
cat > "$T/risk_good.txt" <<'EOF'
风险提醒：法规（宣称合规）、市场（季节波动）、竞争（竞品跟价）、供应链（备货交期）、财务（毛利回本）、组织（培训排产）。
EOF
if python3 "$SC/risk-check.py" "$T/risk_good.txt" >/dev/null 2>&1; then ok "risk-check 6/6 退出0"; else bad "risk-check 全覆盖误报"; fi
if printf '只提了成本和库存。\n' | python3 "$SC/risk-check.py" - >/dev/null 2>&1; then bad "risk-check 缺维漏检"; else ok "risk-check 缺维退出1"; fi

# ---------- 6 unknown-info-check.py ----------
cat > "$T/ui_good.txt" <<'EOF'
先问：市场规模口径？目标人群画像？竞品对照谁？渠道适配哪条通路？成本结构能拆吗？
EOF
if python3 "$SC/unknown-info-check.py" --scene S1 "$T/ui_good.txt" >/dev/null 2>&1; then ok "unknown-info S1全引导 退出0"; else bad "unknown-info S1全引导误报"; fi
if printf '只问了人群。\n' | python3 "$SC/unknown-info-check.py" --scene S1 - >/dev/null 2>&1; then bad "unknown-info 漏问未拦截"; else ok "unknown-info S1漏问 退出1"; fi

# ---------- 7 priority-calc.py ----------
if python3 "$SC/priority-calc.py" --method rice --demo | head -5 | grep -q "SKU-A"; then ok "priority-calc RICE demo 第一=SKU-A"; else bad "priority-calc RICE 排序"; fi
if python3 "$SC/priority-calc.py" --method wsjf --demo | grep -q "项目丙"; then ok "priority-calc WSJF demo 含项目丙"; else bad "priority-calc WSJF"; fi
echo '不是json' > "$T/bad.json"
if python3 "$SC/priority-calc.py" --method rice --input "$T/bad.json" >/dev/null 2>&1; then bad "priority-calc 坏输入未拦截"; else ok "priority-calc 坏输入 退出2"; fi

# ---------- 8 kano-classify.py ----------
if python3 "$SC/kano-classify.py" --pos 喜欢 --neg 不喜欢 | grep -q "期望"; then ok "kano 喜欢×不喜欢=期望"; else bad "kano 期望样例"; fi
if python3 "$SC/kano-classify.py" --pos 理应如此 --neg 不喜欢 | grep -q "基本"; then ok "kano 理应如此×不喜欢=基本"; else bad "kano 基本样例"; fi
if python3 "$SC/kano-classify.py" --pos 理应如此 --neg 喜欢 | grep -q "反向"; then ok "kano 理应如此×喜欢=反向"; else bad "kano 反向样例"; fi

echo "═══════════════════════════"
echo "test-scripts 结果：$PASS 通过，$FAIL 失败"
[ "$FAIL" = 0 ] && echo "ALL GREEN ✅" || echo "HAS RED ❌"
exit "$FAIL"
