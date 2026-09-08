#!/bin/bash
# tests/test-scripts.sh — 12 脚本批量功能测试（exit 0=全绿，1=有红）
# 每脚本：--help 退出码0 + --self 退出码0 + 指定样例行为断言
set -u
S="$(cd "$(dirname "$0")/.." && pwd)"
SC="$S/scripts"
PASS=0; FAIL=0
ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

echo "== test-scripts.sh：12 脚本功能测试 =="

# ---------- 通用：help + self + def 数 ----------
for f in check_output.py scene-router.py stage-gate-check.py decision-record.py risk-check.py unknown-info-check.py priority-calc.py kano-classify.py calc-pricing.py profile-check.py info-gate.py state-gate.py; do
  if python3 "$SC/$f" --help >/dev/null 2>&1; then ok "$f --help 退出码0"; else bad "$f --help"; fi
  if python3 "$SC/$f" --self >/dev/null 2>&1; then ok "$f --self 通过"; else bad "$f --self"; fi
  n=$(grep -c "def " "$SC/$f")
  if [ "$n" -ge 2 ]; then ok "$f def数=$n (≥2)"; else bad "$f def数=$n (<2)"; fi
done

# ---------- 1 check_output.py（台面四区校验） ----------
cat > "$T/good.md" <<'EOF'
[完整]
这是主力品调价级的决定，价格体系乱了收不回——先跟你确认两件事。

【建议】卡位中价格带上沿，不做超低价（置信度：中高 · 价格带空档+成本底线有据；弹性 ⚠️ 待验证）
下一步（你）：本周补竞品常态成交价与支付意愿测试

【候选选项】① 卡位中价格带上沿（当前推荐）② 低价渗透跟价 ③ 维持现价只调促销

【为什么】
1. 品类价格带在中高段有空档，且成本底线支持 → 所以卡位上沿可行。
2. 竞品常态成交价扫描到位 → 所以卡位有对照锚。

【为什么不选别的】
- 低价渗透：死于弹性无实测数据、跟价风险不可控。
- 维持现价只调促销：代价是价格带空档被竞品占位。

【换挡条件】若竞品同步降价 → 改判渗透方案；复盘日 2026-12-31

【最可能翻车的点】若竞品跟进降价则渗透逻辑失效——看竞品周跟踪。不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260831-p2-price.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）

⚠️ 最终定价决策需跨部门确认（财务/销售/渠道/管理层）
进度：第 2 轮 · 初步版已出待你怼 · 还差：弹性实测与支付意愿（未问）｜ 本轮跳过：无 ｜ 假设新增：2 项已挂账
EOF
cat > "$T/bad.md" <<'EOF'
# DR-20260831-x
- 问题：随便
- 决定：就这么干
- 状态：搞定
EOF
if python3 "$SC/check_output.py" "$T/good.md" >/dev/null 2>&1; then ok "check_output 台面好样本退出0"; else bad "check_output 台面好样本误报"; fi
if python3 "$SC/check_output.py" "$T/bad.md" >/dev/null 2>&1; then bad "check_output 坏样本漏检"; else ok "check_output 坏样本退出1并报缺失"; fi
sed '/^【候选选项】/d' "$T/good.md" > "$T/good_nocand.md"
if python3 "$SC/check_output.py" "$T/good_nocand.md" >/dev/null 2>&1; then bad "T10 缺候选区漏检"; else ok "T10 缺候选区被拦（四区增量：正选全集+当前推荐）"; fi
sed '/^进度：/d' "$T/good.md" > "$T/good_noprog.md"
if python3 "$SC/check_output.py" "$T/good_noprog.md" >/dev/null 2>&1; then bad "T11 缺进度行漏检"; else ok "T11 缺进度行被拦（M3 每轮发布末行）"; fi
sed 's/｜ 本轮跳过：无 ｜ 假设新增：2 项已挂账//' "$T/good.md" > "$T/good_notail.md"
if python3 "$SC/check_output.py" "$T/good_notail.md" >/dev/null 2>&1; then bad "T11 跳步自曝尾巴漏检"; else ok "T11 缺跳步自曝尾巴被拦（M9-3 前移台面区）"; fi

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
if python3 "$SC/decision-record.py" --template | grep -q "假设清单" && python3 "$SC/decision-record.py" --template | grep -q "探讨轨迹" && python3 "$SC/decision-record.py" --template | grep -q "归位"; then ok "decision-record 模板含9字段+探讨轨迹+归位"; else bad "decision-record 模板缺字段"; fi
# R-5 层3 fixture：草案落盘须 session_state.phase=S6_CONVERGED（PASS 用例配已收敛态；FAIL 用例不依赖 state）
printf '{"schema_version":"5.0.0","phase":"S6_CONVERGED"}' > "$T/state_ok.json"
export PM_STRATEGIST_STATE="$T/state_ok.json"
printf '问题：A品要不要涨价\n' > "$T/miss.txt"
# 防伪造闸回归：schema 落后（1.0）的 state 不得被当合法态读取（fail-closed）——用合法样本测（miss 缺字段本身就拦，测不出拒读）
printf '{"schema_version":"1.0","phase":"S6_CONVERGED"}' > "$T/state_old.json"
if python3 "$SC/decision-record.py" "$T/miss.txt" >/dev/null 2>&1; then bad "decision-record 缺必填未拦截"; else ok "decision-record 缺选项/决定/探讨轨迹/归位 退出1"; fi
printf '问题：A品要不要涨价\n选项：涨/不涨（含维持现状）\n决定：推荐小步涨\n依据：ref-04\n反方意见：若弹性不足则增收不增利，本提价决定失效；推翻条件=拿到试销弹性数据\n风险：财务（毛利）\n假设清单：⚠️ 假设·待验证：弹性中等\n复盘日期：2026-12-31\n状态：草案\n探讨轨迹：初步版建议涨一档；用户反驳「老客敏感」→ 改小步涨\n归位：改×价格体系 → S4 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🟡\n' > "$T/ok.txt"
if python3 "$SC/decision-record.py" "$T/ok.txt" --out "$T/drout" >/dev/null 2>&1; then ok "decision-record 合法样本（含两段）退出0"; else bad "decision-record 合法样本误报"; fi
if PM_STRATEGIST_STATE="$T/state_old.json" python3 "$SC/decision-record.py" "$T/ok.txt" >/dev/null 2>&1; then bad "R-5 旧 schema state 未拒读（伪造态可绕层3）"; else ok "R-5 旧 schema state 拒读（fail-closed）"; fi

# ---------- 4b decision-record.py v4.4.1 盲审B-2/B-4 回归（9字段/快轨互证/🔴原话/已定复盘） ----------
printf '问题：A品要不要砍（场景S2）\n选项：砍/不砍（含维持现状）\n决定：推荐砍\n反方意见：若为渠道入场券则砍错；推翻条件=拿到渠道合约条款\n探讨轨迹：初步版出过，用户反驳过，结论更新为砍\n归位：删×产品组合 → S2 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴\n' > "$T/min9.txt"
if python3 "$SC/decision-record.py" "$T/min9.txt" >/dev/null 2>&1; then bad "B-2 极简DR（缺5字段）未被拦"; else ok "B-2 9字段全必填：缺依据/风险/假设/复盘/状态 退出1"; fi
printf '问题：A品要不要砍（场景S2）\n选项：砍/不砍（含维持现状）\n决定：推荐砍＋60天缓冲\n依据：ref-02 单品贡献度框架\n反方意见：若为渠道入场券则砍错；推翻条件=拿到各SKU渠道合约条款\n风险：竞争（竞品Q4抢合约）\n假设清单：⚠️ 假设·待验证：渠道合约Q4到期\n复盘日期：2026-12-31\n状态：草案\n探讨轨迹：用户跳过探讨：原因=直接要结论（本会话为快轨）\n归位：删×产品组合 → S2 ｜ 归位成功 ｜ B线连续下滑 ｜ 可逆性=🔴\n' > "$T/fakefast.txt"
if python3 "$SC/decision-record.py" "$T/fakefast.txt" >/dev/null 2>&1; then bad "B-4 假快轨字样绕过未被拦"; else ok "B-4 快轨证据与状态互证：编造快轨（状态=草案）退出1"; fi
printf '问题：详情页改字（场景S1）\n选项：改/不改（含维持现状）\n决定：推荐改\n依据：ref-03 迭代框架\n反方意见：若点击率本就在波动区间，改了白改，本改动失效；推翻条件=拿到近30天点击率分布\n风险：市场（点击率统计功效不足，小流量结论弱）；法规未命中（宣称无涉）\n假设清单：⚠️ 假设·待验证：波动非季节因素\n复盘日期：2026-10-05\n状态：草案·快轨\n探讨轨迹：用户跳过探讨：原因=快轨\n归位：改×详情页文案 → S1 ｜ 归位成功 ｜ 单文案小流量 ｜ 可逆性=🟢\n' > "$T/legitfast.txt"
if python3 "$SC/decision-record.py" "$T/legitfast.txt" --out "$T/drout2" >/dev/null 2>&1; then ok "B-4 真快轨（状态·快轨+🟢+原因=快轨）合法退出0"; else bad "B-4 真快轨合法样本误拦"; fi
printf '问题：A品要不要砍（场景S2）\n选项：砍/不砍（含维持现状）\n决定：推荐砍\n依据：ref-02\n反方意见：若为渠道入场券则砍错，本决定失效；推翻条件=拿到渠道合约条款\n风险：竞争（竞品Q4抢合约）\n假设清单：⚠️ 假设·待验证：Q4到期\n复盘日期：2026-12-31\n状态：草案\n探讨轨迹：初步版出过，用户反驳过，结论更新为砍\n归位：删×产品组合 → S2 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴\n' > "$T/noquote.txt"
if python3 "$SC/decision-record.py" "$T/noquote.txt" >/dev/null 2>&1; then bad "B-4 🔴无用户原话未被拦"; else ok "B-4 🔴不可逆探讨轨迹须用户原话：零引用退出1"; fi
printf '问题：A品要不要涨价\n选项：涨/不涨（含维持现状）\n决定：推荐小步涨（用户拍板：先涨5%%试试）\n依据：ref-04\n反方意见：若弹性不足则增收不增利，本提价决定失效；推翻条件=拿到试销弹性数据\n风险：财务（毛利）\n假设清单：⚠️ 假设·待验证：弹性中等\n复盘日期：【待补充】YYYY-MM-DD\n状态：已定\n探讨轨迹：初步版建议涨一档；用户反驳「老客敏感」→ 改小步涨\n归位：改×价格体系 → S4 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🟡\n' > "$T/d6.txt"
if python3 "$SC/decision-record.py" "$T/d6.txt" >/dev/null 2>&1; then bad "B-2 已定+待补充复盘日期未被拦"; else ok "B-2 已定须有复盘日期（待补充占位也算缺）退出1"; fi
sed 's/置信度：中高 · 价格带空档+成本底线有据；弹性 ⚠️ 待验证/置信度：中高/' "$T/good.md" > "$T/hollow.md"
if python3 "$SC/check_output.py" "$T/hollow.md" >/dev/null 2>&1; then bad "B-2顺手 空壳置信度未被拦"; else ok "B-2顺手 T1 空壳置信度（三档词无依据）退出1"; fi

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

# ---------- 9 calc-pricing.py / profile-check.py（治理新增，总案 D' / 闸口C/H） ----------
if python3 "$SC/calc-pricing.py" --demo | grep -q "真实毛利"; then ok "calc-pricing demo 渠道扣减层输出"; else bad "calc-pricing demo"; fi
if python3 "$SC/calc-pricing.py" --price 59 >/dev/null 2>&1; then bad "calc-pricing 缺输入未拒算"; else ok "calc-pricing 缺输入拒算（退出2）"; fi
# profile-check 用临时样本（不依赖本机 profile 状态：空模板须拦、8键合法样本须过）
cat > "$T/placeholder.md" <<'EOF'
> schema 版本：v4.3.0
- 行业：【待固化】
- 品类：【待固化】
EOF
if python3 "$SC/profile-check.py" --profile "$T/placeholder.md" >/dev/null 2>&1; then bad "profile-check 占位模板未拦"; else ok "profile-check 占位模板拦截（退出1）"; fi
cat > "$T/valid.md" <<EOF
- 行业：示例占位
- 品类：示例占位
- 目标客群：【待固化】
- 公司规模：【待固化】
- 品牌阶段：【待固化】
- 渠道结构：【待固化】
- 拍板权：【待固化】
- 定位禁区：【待固化】
- 固化日期：$(date +%F)
> schema 版本：v4.3.0
EOF
if python3 "$SC/profile-check.py" --profile "$T/valid.md" >/dev/null 2>&1; then ok "profile-check 轻固化合法样本（L0两项+戳）退出0"; else bad "profile-check 合法轻固化误拦"; fi

# ---------- 10 v5.0 批次一：状态机 / G 闸 / 双源仲裁 / 发布校验（CLI 级） ----------
# 10a state-gate：--init 落盘（环境变量路径）+ 转移门 + fail-closed
ST="$T/state.json"
if PM_STRATEGIST_STATE="$ST" python3 "$SC/state-gate.py" --init --scene S3 --question "卖不动怎么办" >/dev/null 2>&1 \
   && python3 -c "import json,sys; d=json.load(open('$ST')); sys.exit(0 if d['phase']=='S0_IDLE' and len(d['info_ledger'])>=3 else 1)" 2>/dev/null; then
  ok "state-gate --init 经 PM_STRATEGIST_STATE 落盘 + 预置 critical 台账"
else bad "state-gate --init 环境变量落盘失败"; fi
if python3 "$SC/state-gate.py" --to S1_ROUTED --state "$ST" >/dev/null 2>&1; then bad "S0→S1 缺 ai_primitive 未拦"; else ok "state-gate 门①：缺 routing.ai_primitive → FAIL"; fi
python3 - "$ST" <<'PYEOF'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
d["routing"]["ai_primitive"] = {"action": "判", "object": "现有单品", "scene": "S3"}
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PYEOF
if python3 "$SC/state-gate.py" --to S1_ROUTED --state "$ST" >/dev/null 2>&1; then ok "state-gate 门①：原语齐 → 可转移 S1"; else bad "state-gate 门① 原语齐误拦"; fi
if python3 "$SC/state-gate.py" --to S4_DRAFT --state "$ST" >/dev/null 2>&1; then bad "S1→S4 跨态跳步未拦"; else ok "state-gate 跳步非法（S1→S4 拦）"; fi
if python3 "$SC/state-gate.py" --to S2_PROFILE_OK --state "$ST" >/dev/null 2>&1; then bad "S1→S2 缺 confirmed_by_user 未拦"; else ok "state-gate 门②：缺用户确认原话 → FAIL"; fi
printf '{}' > "$T/bad_state.json"
if python3 "$SC/state-gate.py" --to S1_ROUTED --state "$T/bad_state.json" >/dev/null 2>&1; then bad "state-gate 缺 schema_version 未拒读"; else ok "state-gate fail-closed：缺 schema_version → 拒读"; fi

# 10b info-gate：G 闸三态判定（CLI 退出码 0/1/2）
mk_gate_state() {
  python3 - "$1" "$2" <<'PYEOF'
import json, sys
path, rev = sys.argv[1], sys.argv[2]
led = {"渠道构成": {"critical": True, "status": "已确认", "value": "商超6成+线上4成", "src": "用户"},
       "复购": {"critical": True, "status": "已确认", "value": "18%", "src": "用户"},
       "月销趋势": {"critical": True, "status": "已确认", "value": "连续3个月~2000盒/月，增速平淡", "src": "用户"},
       "促销史": {"critical": False, "status": "未问", "value": None, "src": None},
       "陈列": {"critical": False, "status": "未问", "value": None, "src": None},
       "客诉": {"critical": False, "status": "未问", "value": None, "src": None}}
json.dump({"schema_version": "5.0.0", "phase": "S3_INFO_GATHERING", "scene": "S3",
           "reversibility": rev, "info_ledger": led},
          open(path, "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
}
mk_gate_state "$T/g0.json" "🟢"
python3 -c "import json; p='$T/g0.json'; d=json.load(open(p)); [d['info_ledger'][n].update(status='已确认') for n in d['info_ledger'] if not d['info_ledger'][n]['critical']]; json.dump(d, open(p,'w'), ensure_ascii=False)"
if python3 "$SC/info-gate.py" "$T/g0.json" >/dev/null 2>&1; then ok "info-gate critical 全确认 → exit 0"; else bad "info-gate 全确认误拦"; fi
mk_gate_state "$T/g1.json" "🟢"
python3 -c "import json; p='$T/g1.json'; d=json.load(open(p)); d['info_ledger']['复购']['status']='已问待答'; json.dump(d, open(p,'w'), ensure_ascii=False)"
if python3 "$SC/info-gate.py" "$T/g1.json" >/dev/null 2>&1; then bad "info-gate critical 已问待答未拦"; else ok "info-gate critical 缺口 → exit 1（问了没答=没问）"; fi
mk_gate_state "$T/g2.json" "🔴"
python3 -c "import json; p='$T/g2.json'; d=json.load(open(p)); d['info_ledger']['渠道构成']['status']='未问'; json.dump(d, open(p,'w'), ensure_ascii=False)"
if python3 "$SC/info-gate.py" "$T/g2.json" 2>&1 | grep -q "🔴红线闸" && ! python3 "$SC/info-gate.py" "$T/g2.json" >/dev/null 2>&1; then ok "info-gate 🔴红线闸：不可逆+critical缺口 → 红线消息+exit 1"; else bad "info-gate 🔴红线闸失效"; fi
python3 "$SC/info-gate.py" "$T/g3.json" >/dev/null 2>&1  # 缺文件 → 退出2（fail-closed）
if [ $? -eq 2 ]; then ok "info-gate 缺 state 文件 → exit 2"; else bad "info-gate 缺文件退出码异常"; fi
mk_gate_state "$T/g4.json" "🟢"
python3 - "$T/g4.json" <<'PYEOF'
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
for n in d["info_ledger"]:
    if not d["info_ledger"][n]["critical"]:
        d["info_ledger"][n]["status"] = "已确认"
d["info_ledger"]["非critical项甲"] = {"critical": False, "status": "未问", "value": None, "src": None}
d["info_ledger"]["非critical项乙"] = {"critical": False, "status": "未问", "value": None, "src": None}
d["info_ledger"]["非critical项丙"] = {"critical": False, "status": "未问", "value": None, "src": None}
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
ec=$(python3 "$SC/info-gate.py" "$T/g4.json" >/dev/null 2>&1; echo $?)
if [ "$ec" = "2" ]; then ok "info-gate 非 critical 缺 3 项 → exit 2（放行+置信度封顶）"; else bad "info-gate 非critical缺3项退出码=$ec（期望2）"; fi

# 10c scene-router v5.0：原语入参 + 双源仲裁
if python3 "$SC/scene-router.py" --action 判 --object 现有单品 "评估一下" | grep -q "场景=S3"; then ok "scene-router --action/--object 原语入参归位 S3"; else bad "scene-router 原语入参模式"; fi
if python3 "$SC/scene-router.py" --action 改 --object 品牌 "品牌重新定位" | grep -q "跨域拆解"; then ok "scene-router 对象=品牌 → 跨域拆解出口"; else bad "scene-router 品牌跨域出口"; fi
if python3 "$SC/scene-router.py" --action 买 --object 新品 "买不买" >/dev/null 2>&1; then bad "scene-router 非法原语未拦"; else ok "scene-router 非法动作原语 → 澄清 exit 1"; fi
if python3 "$SC/scene-router.py" --arbitrate "砍掉这条产品线把钱投新渠道" --action 删 --object 产品组合 | grep -q "归位成功"; then ok "scene-router --arbitrate 双源一致 → 归位成功"; else bad "scene-router --arbitrate 一致误判"; fi
if python3 "$SC/scene-router.py" --arbitrate "这个新品值不值得做" --action 判 --object 新品 | grep -q "divergence=true"; then ok "scene-router --arbitrate 双源分歧 → 仲裁出口（禁自选）"; else bad "scene-router --arbitrate 分歧漏检"; fi

# 10d check_output --publish（R-1 发布校验：信封豁免/台面污染/澄清轮）
cat > "$T/pub_good.md" <<'EOF'
【意图分类】产品决策·验证轨
归位透出（闸口A）：删×产品组合 → S2 产品线组合规划
身份层已核（确认戳 2026-09-01）

---

[完整]
这是砍产品线级的决定，这事退不回——先跟你确认两件事。

【建议】砍 B 线，设 60 天缓冲期再执行（置信度：中高 · 贡献度连续四季下滑；口径未扣返利 ⚠️ 待财务确认）
下一步（你）：本周内确认渠道合约有无条码数门槛

【候选选项】① 砍B线＋60天缓冲（当前推荐）② 收缩到A/C线主力渠道 ③ 维持现状

【为什么】
1. B 线贡献度连续四季下滑，长尾线占用仓储与陈列资源 → 所以机会成本在 A/C 线。
2. 渠道入场资格清单不含 B 线条码 → 所以砍线不丢渠道筹码，退出代价集中在库存处置。

【为什么不选别的】
- 轻量化改造：死于换线成本回收期超出预算窗。
- 维持现状：代价是每月倒贴仓储与陈列，下滑趋势未见底。

【换挡条件】若大促动销低于品类均值八成 → 维持砍线；复盘日 2026-11-05

【最可能翻车的点】若竞品在四季度抢签 B 线经销商合约条款，砍线等于把渠道阵地白送对手，本决定失效——不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-bline.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）｜ 本轮跳过：无 ｜ 假设新增：0 项已挂账

---
**机器闸口结果**：闸口C 身份层 PASS｜闸口D 台面 PASS（信封区豁免词：归位/闸口/身份层/验证轨）
EOF
if python3 "$SC/check_output.py" --publish "$T/pub_good.md" --scene S2 >/dev/null 2>&1; then ok "check_output --publish 信封区黑话豁免 → PASS"; else bad "check_output --publish 信封豁免误拦"; fi
sed 's/这是砍产品线级的决定/这事按归位到 S2 落格处理/' "$T/pub_good.md" > "$T/pub_bad.md"
if python3 "$SC/check_output.py" --publish "$T/pub_bad.md" --scene S2 >/dev/null 2>&1; then bad "--publish 台面区污染漏检（豁免≠盲区）"; else ok "check_output --publish 台面区「归位/落格」仍拦（R-2）"; fi
printf '这个问题我还原不出动作和对象，先补两个信息：你想砍的是整条线还是其中几个品？砍完资源投到哪？\n\n进度：归位中 · 澄清动作对象 · 还差：整线还是单品、资源去向\n\n---\n机器闸口：scene-router 出口=澄清（闸口A 未过）\n' > "$T/clar2.md"
if python3 "$SC/check_output.py" --publish "$T/clar2.md" >/dev/null 2>&1; then ok "check_output --publish 澄清轮两问+进度行+信封尾 → PASS"; else bad "check_output --publish 澄清轮两问误拦"; fi
printf '先补几个信息：上市多久了？月销多少？渠道构成是什么？复购高吗？竞品是谁？\n' > "$T/clar5.md"
if python3 "$SC/check_output.py" --publish "$T/clar5.md" >/dev/null 2>&1; then bad "--publish 五问倾泻漏检（R1 事故）"; else ok "check_output --publish 澄清轮五问 → FAIL（R-3）"; fi

echo "═══════════════════════════"
echo "test-scripts 结果：$PASS 通过，$FAIL 失败"
[ "$FAIL" = 0 ] && echo "ALL GREEN ✅" || echo "HAS RED ❌"
exit "$FAIL"
