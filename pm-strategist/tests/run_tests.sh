#!/bin/bash
# pm-strategist tests runner v4 — 机器可跑验收（exit 0=全绿，1=有红）
# 断言对象 = 当前版本结构（frontmatter/触发词/核心机制/框架与引用文件/台面四区契约/档案收敛闸/脚本自检）
set -u
S="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0; FAIL=0
ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }
chk() { if [ "$2" -ge 1 ]; then ok "$1 ($2 处)"; else bad "$1 (0 处)"; fi; }

echo "== pm-strategist tests v4 =="
SMD="$S/SKILL.md"

echo "[1] SKILL.md frontmatter"
for f in "^name: pm-strategist" "^version:" "^description:"; do
  grep -qE "$f" "$SMD" && ok "frontmatter 含 $f" || bad "frontmatter 缺 $f"
done

echo "[2] 触发词（description 覆盖）"
words=(新品评估 产品决策 帮我决策 该不该做 怎么取舍 值不值得做 优先做哪个 定价 上市 渠道 经销商 促销 大促 库存 清仓 临期 窜货 进场费 品牌重新定位 品牌架构); for w in "${words[@]}"; do
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
chk "fm-02 渲染三原则（M7 细则下沉）" "$(grep -c '渲染三原则' "$S/frameworks/fm-02决策记录.md" 2>/dev/null || echo 0)"
chk "fm-02 slug 命名规范（M12① 调用约定同步）" "$(grep -c 'DR-YYYYMMDD-<对象≤10字>-<动作≤6字>' "$S/frameworks/fm-02决策记录.md" 2>/dev/null || echo 0)"

echo "[5] 黑名单表述（应 0 处）"
BL=$(grep -rcE "最佳实践所以可信|所以建议可信|基于最佳实践" "$S" --include="*.md" --include="*.py" 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
if [ "$BL" = 0 ]; then ok "无黑名单表述"; else bad "黑名单表述 $BL 处"; fi

echo "[6] 根目录文档卫生（仅 SKILL.md / README.md，防僵尸文档回潮）"
RD=$(find -L "$S" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
if [ "$RD" = 2 ]; then ok "根目录 .md 计数=2"; else bad "根目录 .md 计数=${RD}（期望仅 SKILL.md/README.md）"; fi

echo "[7] SKILL.md 5场景路由表 + 类别规则"
for s in "S1 新品立项与产品定义" "S2 产品线组合规划" "S3 产品生命周期与迭代" "S4 定价与盈利" "S5 上市GTM策略"; do
  c=$(grep -c "$s" "$SMD"); chk "路由含「${s}」" "$c"
done
chk "A类分析透" "$(grep -c '分析透' "$SMD")"
chk "B类跨部门标注（定价）" "$(grep -c '最终定价决策需跨部门确认' "$SMD")"
chk "B类跨部门标注（上市）" "$(grep -c '最终上市决策需跨部门确认' "$SMD")"
chk "C类只提醒不决策" "$(grep -c '只提醒不决策' "$SMD")"

echo "[8] SKILL.md 台面输出契约：四区 + 形态谱系 + 首轮顺序协议 + 档案收敛"
for w in "【建议】" "【为什么】" "【为什么不选别的】" "【换挡条件】" "【最可能翻车的点】" "下一步（你）" "档案已存" "形态谱系" "首轮顺序协议" "无新意熔断" "自动降频" "探讨轨迹" "收敛终端" "决策相关性排序" "前 120 字" "不做/维持现状"; do
  c=$(grep -c "$w" "$SMD"); chk "契约「${w}」" "$c"
done
chk "9字段清单行" "$(grep -c '问题/选项/决定/依据/反方意见/风险/假设清单/复盘日期/状态' "$SMD")"
chk "M12① 调用约定：DR 文件名 slug 规范在 SKILL.md" "$(grep -c 'DR-YYYYMMDD-<对象≤10字>-<动作≤6字>' "$SMD")"
chk "旧口径「路径声明」0 残留" "$((1 - $(grep -c '路径声明' "$SMD")))"
chk "旧口径「建议6要素」0 残留" "$((1 - $(grep -c '建议6要素' "$SMD")))"

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
r5a=$(grep -l "【候选选项】" "$S"/references/ref-0[1-5]*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$r5a" = 5 ]; then ok "5 ref 台面模板补【候选选项】区（批次三五 ref 同步）"; else bad "ref 候选区补词 $r5a/5"; fi
r5b=$(grep -l "本轮跳过" "$S"/references/ref-0[1-5]*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$r5b" = 5 ]; then ok "5 ref 台面模板补进度行+自曝尾巴（T11 口径同步）"; else bad "ref 进度行补词 $r5b/5"; fi
chk "术语浮层表 补问格式模板（单问信息量，随 R-3 生效）" "$(grep -c '补问格式模板' "$S/references/术语浮层表.md" 2>/dev/null || echo 0)"

echo "[10] 通用化硬断言（品牌/业务专属术语 0 处，示例标注除外；扫描含根目录，防根目录僵尸文档；如需检测自定义品牌词，追加到下方 grep -E 词表）"
GEN=$(grep -rnE "样品|设计稿|相关背书|大货生产|资料移交" "$S"/*.md "$S/references" "$S/frameworks" --include="*.md" 2>/dev/null | grep -vE "示例|举例" | wc -l | tr -d ' ')
if [ "$GEN" = 0 ]; then ok "通用化扫描 0 命中"; else bad "通用化命中 $GEN 处"; fi
OLD=$(grep -rnE "启动框架|落地框架" "$S"/*.md "$S/references" "$S/frameworks" --include="*.md" 2>/dev/null | wc -l | tr -d ' ')
if [ "$OLD" = 0 ]; then ok "根目录+refs+fm 无旧分类字样"; else bad "旧分类字样 $OLD 处"; fi

echo "[11] 测试用例计数（正≥5 负≥3 + 场景用例≥5 + 行为/格式/可逆/组件/B类用例在位）"
PC=$(grep -cE '^[|] P[0-9]' "$S/tests/trigger-positive.md" || true)
NC=$(grep -cE '^[|] N[0-9]' "$S/tests/trigger-negative.md" || true)
if [ "$PC" -ge 5 ]; then ok "正用例 $PC 条 (≥5)"; else bad "正用例 $PC 条 (<5)"; fi
if [ "$NC" -ge 3 ]; then ok "负用例 $NC 条 (≥3)"; else bad "负用例 $NC 条 (<3)"; fi
TC=$(grep -cE '^[|] TS[0-9]' "$S/tests/trigger-scenes.md" 2>/dev/null || true)
if [ "$TC" -ge 5 ]; then ok "场景触发用例 $TC 条 (≥5)"; else bad "场景触发用例 $TC 条 (<5)"; fi
for t in behavior-principles-cases.md output-format-cases.md reversibility-grading-cases.md components-cases.md b-class-tag-cases.md trigger-negative-scenes.md; do
  [ -f "$S/tests/$t" ] && ok "tests/$t 在位" || bad "tests/$t 缺失"
done
TCNT=$(ls "$S/tests/" | grep -vc "\.bak$" || true)
if [ "$TCNT" -ge 10 ]; then ok "tests 文件数 $TCNT (≥10)"; else bad "tests 文件数 $TCNT (<10)"; fi

echo "[12] 可逆性判别对（最严重事故的回归防线）"
RC="$S/tests/reversibility-cases.md"
if [ -f "$RC" ]; then ok "reversibility-cases.md 存在"; else bad "reversibility-cases.md 缺失"; fi
RP=$(grep -cE '^[|] R[0-9]' "$RC" 2>/dev/null || echo 0)
if [ "$RP" -ge 4 ]; then ok "判别对 $RP 条 (≥4)"; else bad "判别对 $RP 条 (<4)"; fi
if grep -q "砍掉整条产品线" "$S/SKILL.md" && grep -q "品牌重新定位" "$S/SKILL.md"; then ok "判别锚例已写入 SKILL.md"; else bad "SKILL.md 判别锚例缺失"; fi

echo "[13] check_output.py 自检（台面四区校验器本体）"
if python3 "$S/scripts/check_output.py" --self >/dev/null 2>&1; then ok "check_output.py --self 通过"; else bad "check_output.py --self 失败"; fi

echo "[14] scripts/ 8件在位 + def≥2"
py=$(ls "$S/scripts/" 2>/dev/null | grep -c "\.py$")
if [ "$py" = 12 ]; then ok "scripts .py 计数=12（8 原有+calc-pricing+profile-check+info-gate+state-gate）"; else bad "scripts .py 计数=$py (期望12)"; fi
for f in "$S"/scripts/*.py; do
  n=$(basename "$f"); d=$(grep -c "def " "$f")
  [ "$d" -ge 2 ] && ok "$n def数=$d (≥2)" || bad "$n def数=$d (<2)"
done

echo "[15] config/local_profile.md 身份层在位（空模板=占位≥6；已固化=8键齐+固化日期——填了即本机身份层，两种都是合法状态）"
CFG="$S/config/local_profile.md"
if [ -f "$CFG" ]; then
  if grep -q -- "- 固化日期：" "$CFG" && [ "$(grep -c "【待固化】" "$CFG")" = "0" ]; then
    nk=0
    for k in 行业 品类 目标客群 公司规模 品牌阶段 渠道结构 拍板权 定位禁区; do
      grep -q -- "^- ${k}：" "$CFG" && nk=$((nk+1))
    done
    if [ "$nk" = 8 ]; then ok "身份层已固化（8 键齐 + 固化日期）"; else bad "身份层已固化但字段键缺（$nk/8）"; fi
  else
    n=$(grep -c "【待固化】" "$CFG")
    if [ "${n}" -ge 6 ]; then ok "身份层模板在位，占位字段 ${n} 个（≥6）"; else bad "身份层模板占位字段 ${n} 个 (<6)"; fi
  fi
else
  bad "config/local_profile.md 模板缺失"
fi

echo "[16] golden 三元组 G1-G5（场景/出口为主键，F3）"
g() { python3 "$S/scripts/scene-router.py" "$1" 2>/dev/null; }
if g "新品怎么上市？" | grep -q "场景=S5"; then ok "G1 新品怎么上市→S5"; else bad "G1 期望S5"; fi
if g "要不要给 A 出小规格？" | grep -q "场景=S4"; then ok "G2 出小规格→S4（F3 价格点动机）"; else bad "G2 期望S4"; fi
if g "A 品出个礼盒装怎么样？" | grep -q "场景=S2"; then ok "G3 礼盒装→S2（变体丰富动机）"; else bad "G3 期望S2"; fi
if g "品牌要不要重新定位" | grep -q "跨域"; then ok "G4 品牌重新定位→跨域拆解"; else bad "G4 期望跨域"; fi
G5O=$(g "砍掉 B 线，预算投 C 渠道")
if echo "$G5O" | grep -q "S2" && echo "$G5O" | grep -q "S5"; then ok "G5 砍线投渠道→复合S2+S5"; else bad "G5 期望复合S2+S5：$G5O"; fi

echo "[17] 路由用例集 ≥30 + 四态出口反例（R7/R9）"
RC=$(grep -cE '^[|] R[0-9]' "$S/tests/routing-cases.md" 2>/dev/null || true)
if [ "$RC" -ge 30 ]; then ok "routing-cases $RC 条 (≥30)"; else bad "routing-cases $RC 条 (<30)"; fi
if g "这个事儿帮我看看" | grep -q "澄清"; then ok "四态反例：原语缺失→澄清"; else bad "澄清出口缺失"; fi
if g "帮我看看有什么风险" | grep -q "C类"; then ok "四态反例：非决策→C类"; else bad "C类出口缺失"; fi
if python3 "$S/scripts/scene-router.py" --self >/dev/null 2>&1; then ok "scene-router --self（golden+四态+原语6例+仲裁6例=24例）"; else bad "scene-router --self"; fi
# v5.0#4 原语入参模式（AI 判·脚本校验）+ 双源仲裁（RC-3：冲突检出 100%，AI 自选率 0%）
if python3 "$S/scripts/scene-router.py" --action 判 --object 现有单品 | grep -q "场景=S3"; then ok "原语入参模式：判×现有单品→S3（跳过词法抽取，只做校验+查表）"; else bad "原语入参模式 --action/--object 路由错"; fi
if python3 "$S/scripts/scene-router.py" --action 大概 --object 现有单品 >/dev/null 2>&1; then bad "非法动作原语未被拦"; else ok "非法动作原语（大概）→ 澄清 exit 1"; fi
ARBJ=$(python3 "$S/scripts/scene-router.py" --action 判 --object 现有单品 --arbitrate "新品怎么上市？" --json 2>/dev/null)
if echo "$ARBJ" | grep -q '"divergence": true'; then ok "双源仲裁：AI=S3 vs 词法=S5 → divergence=true 透出（R2 事故复现）"; else bad "双源仲裁未透出 divergence：$ARBJ"; fi
if echo "$ARBJ" | grep -q "禁止 AI 自行选定"; then ok "仲裁输出含「禁止 AI 自选」指令"; else bad "仲裁输出缺禁止自选指令"; fi
if python3 "$S/scripts/scene-router.py" --action 判 --object 现有单品 --arbitrate "这个品卖不动了怎么办" --json 2>/dev/null | grep -q '"divergence": false'; then ok "双源仲裁：AI=S3 与词法一致 → divergence=false"; else bad "双源一致时误报 divergence"; fi
# B2 修复：纸面≠执行——黄金路由子集逐条真实断言场景（盯死"数行数不执行"盲区）
if python3 - "$S" >/dev/null 2>&1 <<'PY'
import sys, os, re, subprocess
S = sys.argv[1]
router = os.path.join(S, "scripts", "scene-router.py")
def scen(q):
    r = subprocess.run(["python3", router, q], capture_output=True, text=True)
    m = re.search(r"^场景=([^ |]+)", r.stdout, re.M)
    return m.group(1).strip() if m else "(无)"
cases = {
    "A品迭代还是退市？": "S3",
    "这个品卖不动了怎么办？": "S3",
    "成熟品怎么迭代焕新？": "S3",
    "要不要给A出小规格？": "S4",
    "要不要涨价？": "S4",
    "新品怎么上市？": "S5",
    "要不要撤了这个渠道？": "S5",
    "这个新品该不该立项？": "S1",
    "产品线太多先砍哪个？": "S2",
}
fails = [q for q, e in cases.items() if scen(q) != e]
for q in fails:
    print("FAIL:", q, "->", scen(q), "期望", cases[q])
sys.exit(1 if fails else 0)
PY
then ok "黄金路由子集 9/9 全中（纸面≠执行，B2修复）"; else bad "黄金路由子集有未命中"; fi

echo "[18] 口径唯一化（总案 Step 2：残留=0 + 三问统一 fm-05）"
KC=$(grep -rn "按显式假设继续" "$S" --include="*.md" --include="*.py" 2>/dev/null | grep -v "/\.git/" | wc -l | tr -d ' ')
if [ "$KC" = 0 ]; then ok "『按显式假设继续』残留=0"; else bad "『按显式假设继续』残留=$KC（应改写为口径唯一化条件式）"; fi
if grep -q "赚不赚钱" "$SMD" && ! grep -q "值得做吗/做得成吗/划得来吗" "$SMD"; then ok "生意思维三问=fm-05口径"; else bad "三问口径未统一fm-05"; fi

echo "[19] 双轨分流在位（F1：重写不得移除『先说判断』，删断言须留书面理由）"
chk "SKILL.md 含『先说判断』" "$(grep -c '先说判断' "$SMD")"
chk "SKILL.md 含『双轨』" "$(grep -c '双轨' "$SMD")"

echo "[20] 收敛闸+质量下限：零质量 DR 必 FAIL（修绿灯幻觉；DR 校验唯一入口=decision-record.py）"
TZ=$(mktemp -d)
# R-5 层3 fixture：草案落盘须 session_state.phase=S6_CONVERGED（PASS 用例配已收敛态）
printf '{"schema_version":"5.0.0","phase":"S6_CONVERGED"}' > "$TZ/state_ok.json"
export PM_STRATEGIST_STATE="$TZ/state_ok.json"
cat > "$TZ/zero.md" <<'EOT'
# DR-20260902-zero
- 问题：示例占位
- 选项：A方案
- 决定：就这么干
- 依据：感觉不错
- 反方意见：无
- 风险：法规：未命中；市场：未命中；竞争：未命中；供应链：未命中；财务：未命中；组织：未命中
- 假设清单：
无——输入已全部确认
- 复盘日期：2026-12-31
- 状态：已定
EOT
if python3 "$S/scripts/decision-record.py" "$TZ/zero.md" >/dev/null 2>&1; then bad "零质量 DR 未被拦（绿灯幻觉）"; else ok "零质量 DR → decision-record 必 FAIL"; fi
if python3 "$S/scripts/decision-record.py" --self >/dev/null 2>&1; then ok "decision-record --self（含收敛闸+质量下限）"; else bad "decision-record --self"; fi
cat > "$TZ/straw.md" <<'EOT'
# DR-20260902-straw
- 问题：示例占位
- 选项：A方案/维持现状
- 决定：推荐 A
- 依据：ref-02
- 反方意见：如果可能市场不好吧
- 风险：财务（毛利）
- 假设清单：
⚠️ 假设·待验证：动销达标
- 复盘日期：2026-12-31
- 状态：草案
- 探讨轨迹：初步版→用户反驳「再想想」→维持推荐
- 归位：择×现有单品 → S3 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🟢
EOT
STRAW_OUT=$(python3 "$S/scripts/decision-record.py" "$TZ/straw.md" 2>&1)
if echo "$STRAW_OUT" | grep -q "稻草人"; then ok "稻草人反方（只有连接词、无可反驳出口）→ 必拦"; else bad "稻草人反方漏拦：$STRAW_OUT"; fi
cat > "$TZ/skip.md" <<'EOT'
# DR-20260902-skip
- 问题：示例占位
- 选项：A方案/维持现状
- 决定：推荐 A
- 依据：ref-02
- 反方意见：若需求证伪则不成立；推翻条件=拿到试销数据
- 风险：财务（毛利）
- 假设清单：⚠️ 假设·待验证：动销达标
- 复盘日期：2026-12-31
- 状态：草案
- 探讨轨迹：用户跳过探讨
- 归位：择×现有单品 → S3 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🟢
EOT
SKIP_OUT=$(python3 "$S/scripts/decision-record.py" "$TZ/skip.md" 2>&1)
if echo "$SKIP_OUT" | grep -q "可观测证据"; then ok "跳过声明缺可观测证据 → 必拦（诚实闸）"; else bad "无证据跳过声明漏拦：$SKIP_OUT"; fi

# 误杀面回归（2026-09-03 独立复核发现：判定过严误杀 references 正常句式，校准后加保护）
# ①references 引导句式（无"若"用"则"） ②内置样本（具体条件+决定否定语义）→ 都必须 PASS，不得误杀
cat > "$TZ/ref4.md" <<'EOT'
# DR-20260902-ref4
- 问题：示例占位
- 选项：A方案/维持现状
- 决定：推荐 A
- 依据：ref-04
- 反方意见：竞品同步降价则渗透策略失效
- 风险：市场（竞品）
- 假设清单：
⚠️ 假设·待验证：竞品价格监测可用
- 复盘日期：2026-12-31
- 状态：草案
- 探讨轨迹：初步版→用户反驳「竞品会不会跟价」→写入换挡条件
- 归位：改×价格体系 → S4 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴
EOT
cat > "$TZ/ref2.md" <<'EOT'
# DR-20260902-ref2
- 问题：示例占位
- 选项：A方案/维持现状
- 决定：推荐 A
- 依据：ref-02
- 反方意见：若为渠道入场券则砍错
- 风险：渠道（进场资格）
- 假设清单：
⚠️ 假设·待验证：渠道合约条款可得
- 复盘日期：2026-12-31
- 状态：草案
- 探讨轨迹：初步版→用户反驳「渠道资格呢」→查合约条款后确认
- 归位：删×产品组合 → S2 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴
EOT
if python3 "$S/scripts/decision-record.py" "$TZ/ref4.md" --out "$TZ/refout" >/dev/null 2>&1; then ok "references 引导句式『竞品同步降价则渗透策略失效』→ PASS（不误杀）"; else bad "误杀 references 正常反方（判定过严）"; fi
if python3 "$S/scripts/decision-record.py" "$TZ/ref2.md" --out "$TZ/refout" >/dev/null 2>&1; then ok "内置样本『若为渠道入场券则砍错』→ PASS（不误杀）"; else bad "误杀内置样本（判定过严）"; fi
# R-5 层3 状态断言（v5.0#5：未收敛落盘 0 起）——无 state 拦、未收敛 phase 拦
if env -u PM_STRATEGIST_STATE python3 "$S/scripts/decision-record.py" "$TZ/ref4.md" >/dev/null 2>&1; then bad "R-5 层3 草案无 session_state 未被拦（fail-closed 失效）"; else ok "R-5 层3：草案无 session_state → FAIL（先 --init 逐门推进）"; fi
printf '{"schema_version":"5.0.0","phase":"S4_DRAFT"}' > "$TZ/state_s4.json"
if PM_STRATEGIST_STATE="$TZ/state_s4.json" python3 "$S/scripts/decision-record.py" "$TZ/ref4.md" >/dev/null 2>&1; then bad "R-5 层3 phase=S4_DRAFT 未收敛未被拦"; else ok "R-5 层3：phase=S4_DRAFT ≠ S6_CONVERGED → FAIL（未收敛不得落盘草案）"; fi
# R-5 层3 fail-closed 加严：闸外手写最小 JSON（无 schema / schema 不符）不算收敛证据
printf '{"phase":"S6_CONVERGED"}' > "$TZ/state_fake.json"
if PM_STRATEGIST_STATE="$TZ/state_fake.json" python3 "$S/scripts/decision-record.py" "$TZ/ref4.md" >/dev/null 2>&1; then bad "R-5 层3 无 schema_version 的伪 state 未被拦（闸外伪造）"; else ok "R-5 层3：缺 schema_version 的手写 state → FAIL（闸外伪造收敛无效）"; fi
printf '{"schema_version":"1.0","phase":"S6_CONVERGED"}' > "$TZ/state_old.json"
if PM_STRATEGIST_STATE="$TZ/state_old.json" python3 "$S/scripts/decision-record.py" "$TZ/ref4.md" >/dev/null 2>&1; then bad "R-5 层3 schema 版本落后未被拦"; else ok "R-5 层3：schema_version 落后 → FAIL（与 state-gate 同标 fail-closed）"; fi
# R-5 层1 文本断言：无原话叙述（白名单移除后）必须拦
sed 's/探讨轨迹：初步版→用户反驳「竞品会不会跟价」→写入换挡条件/探讨轨迹：初步版出过，用户反驳过，结论写入换挡条件/' "$TZ/ref4.md" > "$TZ/noquote.md"
if python3 "$S/scripts/decision-record.py" "$TZ/noquote.md" >/dev/null 2>&1; then bad "R-5 层1 无原话叙述未被拦（关键词白名单回潮）"; else ok "R-5 层1：『反驳过』无原话引用 → FAIL（原话是唯一硬证据）"; fi

echo "[21] DR=v0.7 自包含 HTML 决策档案 + 双主题 + 旧版回退（D10/D20）"
DRD="$TZ/drout"
printf '问题：示例占位 冒烟测试\n选项：做/不做（含维持现状）\n决定：推荐做\n依据：ref-02\n反方意见：若成本超两成则不成立\n风险：财务（毛利）；法规未命中（宣称无涉）\n假设清单：⚠️ 假设·待验证：动销达标\n复盘日期：2026-12-31\n状态：草案\n探讨轨迹：初步版建议做；用户反驳「预算紧」→ 改为分两期\n归位：增×新品 → S1 ｜ 归位成功 ｜ 冒烟测试 ｜ 可逆性=🔴\n' | python3 "$S/scripts/decision-record.py" - --out "$DRD" >/dev/null 2>&1
DRF=$(ls "$DRD"/*.html 2>/dev/null | head -1)
if [ -n "$DRF" ] && grep -q "<!DOCTYPE html>" "$DRF" && grep -q "</html>" "$DRF"; then ok "DR 渲染为自包含 HTML 单文件"; else bad "DR HTML 缺失/不自包含"; fi
if [ -n "$DRF" ] && grep -q -- "--bg:#0e1013" "$DRF"; then ok "v0.7 暗黑横版主题 token 在场"; else bad "v0.7 主题 token 缺失"; fi
if [ -n "$DRF" ] && grep -q "字段总账" "$DRF" && grep -q "探讨轨迹" "$DRF" && grep -q "归位" "$DRF" && grep -q "齐性自检" "$DRF"; then ok "档案信息守恒：探讨轨迹/归位/齐性自检/9字段总账在渲染内"; else bad "档案信息守恒缺件"; fi
if python3 - "$S" >/dev/null 2>&1 <<'PY'
import importlib.util, os, sys
S = sys.argv[1]
spec = importlib.util.spec_from_file_location("drmod", os.path.join(S, "scripts", "decision-record.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pts = {"问题": "示例占位 回退测试", "选项": "做/不做（含维持现状）", "决定": "推荐做", "依据": "ref-02",
       "反方意见": "若成本超两成则不成立", "风险": "财务（毛利）", "假设清单": "⚠️ 假设·待验证：动销达标",
       "复盘日期": "2026-12-31", "状态": "草案", "探讨轨迹": "初步版→用户反驳「预算紧」→分两期",
       "归位": "增×新品 → S1 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴", "置信度": "中高 · 测试"}
h = m.render_html(pts, {"dr_theme_legacy": True})
ok1 = "PM-STRATEGIST · DECISION RECORD" in h and "探讨轨迹" in h and "归位" in h
h2 = m.render_html(pts, {"dr_theme": "light"})
ok2 = 'data-theme="light"' in h2 and "--bg:#fcfcfa" in h2
fast = dict(pts); fast["状态"] = "草案·快轨"
fh = m.render_html(fast)
ok3 = fh.count("<svg") >= 3 and fh.count('class="lite"') >= 3  # M7 ③ 反转：轻量降级 ≥3 svg（原「无 SVG」废止）
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
PY
then ok "旧版回退开关+浅色主题+快轨紧凑档（M7 轻量降级 ≥3 svg）全过"; else bad "主题/回退/紧凑档断言失败"; fi

echo "[21b] 批次1 渲染断言：div-in-svg 清零 + DR 黑话清零 + html.parser 严解析（W-01/W-05/G-3/W-06）"
if python3 - "$S" >/dev/null 2>&1 <<'PY'
import importlib, importlib.util, os, re, sys
S = sys.argv[1]
spec = importlib.util.spec_from_file_location("drmod", os.path.join(S, "scripts", "decision-record.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
pts = {"问题": "示例占位 拍板引号测试", "选项": "做/不做（含维持现状）", "决定": "用户拍板：『先补数据再定』",
       "依据": "ref-02", "反方意见": "若成本超两成则不成立", "风险": "竞争（竞品Q4抢合约）；法规未命中（宣称无涉）；供应链（库存积压）",
       "假设清单": "⚠️ 假设·待验证：动销达标", "复盘日期": "2026-12-31", "状态": "草案",
       "探讨轨迹": "初步版建议做；用户反驳「预算紧」→ 改为分两期", "归位": "增×新品 → S1 ｜ 归位成功 ｜ 冒烟测试 ｜ 可逆性=🔴",
       "置信度": "中高 · 一句依据", "换挡条件": "月销连续两月下滑超过 10% 则终止扩量；若竞品降价超过 15% 则重估防线；若渠道回款恶化则压缩库存"}
h = m.render_html(pts)
fast = dict(pts); fast["状态"] = "草案·快轨"
fh = m.render_html(fast)
def svg_blocks(hh): return re.findall(r"<svg.*?</svg>", hh, re.S)
def div_in_svg(hh): return sum(b.count("<div") for b in svg_blocks(hh))
# W-01：任意 <svg>…</svg> 内无 <div（全档+紧凑档）
w01 = div_in_svg(h) == 0 and div_in_svg(fh) == 0 and h.count('class="item"') >= 1
# W-05：建议区实质决定无拍板引号残留
rm = re.search(r'class="rec">建议：<em>(.*?)</em>', h, re.S)
w05 = bool(rm) and "『" not in rm.group(1) and "「" not in rm.group(1)
# G-3：用户文案黑话清零
g3 = all(x not in h for x in ("归位（只读）", "四件套流程", "决策记录（DR）"))
# W-04：换挡条件多条件完整可见（HTML 列表），无截断省略号
w04 = "换挡条件 · 完整清单" in h and h.count("<li>") >= 2
# W-06：html.parser 严解析（标准库零依赖）
HP = importlib.import_module("html.parser")
class P(HP.HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self): super().__init__(); self.st=[]; self.err=[]
    def handle_starttag(self,t,a):
        if t not in self.VOID: self.st.append(t)
    def handle_endtag(self,t):
        if t in self.VOID: return
        if self.st and self.st[-1]==t: self.st.pop()
        elif t in self.st:
            while self.st and self.st[-1]!=t: self.err.append("@"+self.st[-1]); self.st.pop()
            if self.st: self.st.pop()
        else: self.err.append(t)
def strict(hh):
    p=P(); p.feed(hh); p.close(); return (not p.err) and (not p.st)
w06 = strict(h) and strict(fh)
sys.exit(0 if (w01 and w05 and g3 and w04 and w06) else 1)
PY
then ok "批次1：div-in-svg 清零 + 黑话清零 + W04 完整清单 + html.parser 严解析"; else bad "批次1 渲染断言失败"; fi

echo "[22] 闸口 H/C：calc-pricing 渠道扣减层 + profile-check 90天重验"
if python3 "$S/scripts/calc-pricing.py" --self >/dev/null 2>&1; then ok "calc-pricing --self（B5渠道扣减层+护栏3条）"; else bad "calc-pricing --self"; fi
if python3 "$S/scripts/calc-pricing.py" --price 59 >/dev/null 2>&1; then bad "calc-pricing 缺输入未拒算"; else ok "calc-pricing 缺输入拒算（护栏1）"; fi
if python3 "$S/scripts/profile-check.py" --self >/dev/null 2>&1; then ok "profile-check --self（闸口C）"; else bad "profile-check --self"; fi

echo "[23] ref-06 组件数演进防回归（头部声明=6 + 组件标题计数=6 + 术语并轨禁旧称）"
CN_RAW=$(grep -c "^## 组件" "$S/references/ref-06通用组件.md" || true)
CN_CHK=$(grep -c "^## 组件执行检查单" "$S/references/ref-06通用组件.md" || true)
CN6=$((CN_RAW - CN_CHK))
if [ "$CN6" -eq 6 ]; then ok "ref-06 组件标题计数=${CN6}（组件①-⑥在位）"; else bad "ref-06 组件标题计数=${CN6} ≠ 6（组件数演进后结构缺件）"; fi
if grep -q "六个组件" "$S/references/ref-06通用组件.md"; then ok "ref-06 头部声明含'六个组件'（数量声明与实际一致）"; else bad "ref-06 头部声明缺'六个组件'（组件数演进后头部漏改）"; fi
if grep -q "身份层" "$S/references/ref-06通用组件.md"; then ok "ref-06 术语'身份层'在位（并轨锚点）"; else bad "ref-06 术语'身份层'缺失"; fi
OLD=$(grep -cE "行业适配(层)?" "$S/references/ref-06通用组件.md" || true)
if [ "$OLD" -eq 0 ]; then ok "ref-06 旧术语'行业适配/行业适配层' 0 残留（禁旧称）"; else bad "ref-06 旧术语'行业适配' 残留 ${OLD} 处（术语第三次漂移）"; fi

echo "[24] 台面断言组：check_output 好/坏样本（full/light/黑话/裸百分比/🟡话术失实）"
TT="$TZ/taimian"; mkdir -p "$TT"
cat > "$TT/good_full.txt" <<'EOF'
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
进度：第 3 轮 · 砍线方案初步版待你怼 · 还差：渠道合约条码数门槛（未问）｜ 本轮跳过：无 ｜ 假设新增：0 项已挂账
EOF
cat > "$TT/good_light.txt" <<'EOF'
[轻]
这是详情页改字级的决定，随时可改，先试试。

【建议】按钮文案改成「马上抢」再观察一周（置信度：高 · 同类按钮 A/B 有成熟先例，首日数据 ⚠️ 待验证）
下一步（你）：今晚发布并设 7 天后回看转化

【候选选项】① 改「马上抢」（当前推荐）② 维持现状

【为什么】1. 按钮文案改动随时可回滚 → 所以按轻决策节奏走即可。

【为什么不选别的】维持现状：代价是转化优化窗口往后拖一周。

【换挡条件】若 7 天转化不升 → 换回原文案；复盘日 2026-09-12

【最可能翻车的点】若新文案让老客困惑、首日转化反降，本改动落空——不对就改回。不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-cta.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
进度：第 1 轮 · 文案已发布待回看 · 还差：7 天转化数据（已问待答）｜ 本轮跳过：无 ｜ 假设新增：1 项已挂账
EOF
if python3 "$S/scripts/check_output.py" "$TT/good_full.txt" >/dev/null 2>&1; then ok "完整态好样本退出0（T1-T11+零黑话）"; else bad "完整态好样本误报"; fi
if python3 "$S/scripts/check_output.py" "$TT/good_light.txt" >/dev/null 2>&1; then ok "压缩态好样本退出0（徽章路由 light）"; else bad "压缩态好样本误报"; fi
sed 's/｜ 本轮跳过：无 ｜ 假设新增：0 项已挂账//' "$TT/good_full.txt" > "$TT/good_notail.txt"
if python3 "$S/scripts/check_output.py" "$TT/good_notail.txt" >/dev/null 2>&1; then bad "T11 跳步自曝尾巴漏检（M9-3）"; else ok "T11 缺跳步自曝尾巴 → 必拦（M9-3 前移台面区）"; fi
sed '/^下一步（你）/d' "$TT/good_full.txt" > "$TT/nonext.txt"
if python3 "$S/scripts/check_output.py" "$TT/nonext.txt" >/dev/null 2>&1; then bad "缺「下一步（你）」漏拦"; else ok "缺「下一步（你）」→ 必拦"; fi
sed 's/先跟你确认两件事/主查=ref-02，路径声明：验证轨/' "$TT/good_full.txt" > "$TT/jargon.txt"
if python3 "$S/scripts/check_output.py" "$TT/jargon.txt" >/dev/null 2>&1; then bad "扩容黑话漏拦"; else ok "扩容黑话（主查/路径声明）→ 必拦"; fi
sed 's/置信度：中高/置信度：70%/' "$TT/good_full.txt" > "$TT/pct.txt"
if python3 "$S/scripts/check_output.py" "$TT/pct.txt" >/dev/null 2>&1; then bad "裸百分比漏拦"; else ok "台面裸百分比 → 必拦（T9）"; fi
sed 's/这事退不回/🟡这事退不回/' "$TT/good_full.txt" > "$TT/yellow.txt"
if python3 "$S/scripts/check_output.py" "$TT/yellow.txt" >/dev/null 2>&1; then bad "🟡话术失实漏拦"; else ok "🟡话术失实（直说退不回）→ 必拦（T6）"; fi

echo "[25] v4.4.1 盲审三缺口修复在位（B-2 9字段+自检实况 / B-3 --scene 契约 / B-4 快轨互证+🔴原话 / 噪点+轴标签）"
grep -q "S4/S5 场景必传" "$S/SKILL.md" && ok "B-3 SKILL.md 闸口D 写明 S4/S5 必传 --scene" || bad "B-3 SKILL.md 缺 --scene 输入契约"
grep -q "机器闸输入契约" "$S/SKILL.md" && ok "B-3 SKILL.md B类规则含 --scene 机器闸输入契约" || bad "B-3 SKILL.md B类规则缺契约"
grep -q "REQUIRED = list(FIELDS)" "$S/scripts/decision-record.py" && ok "B-2 REQUIRED=9字段全必填（名实相符）" || bad "B-2 REQUIRED 未扩容"
grep -q "def _tick" "$S/scripts/decision-record.py" && ok "B-2 齐性自检实况打勾（_tick 在场）" || bad "B-2 _tick 缺失"
grep -q 'class="noise"' "$S/scripts/decision-record.py" && ok "B-2顺手 v0.7 噪点 .03 在场" || bad "B-2顺手 噪点缺失"
grep -q 'font-size="10.5"' "$S/scripts/decision-record.py" && ! grep -q 'font-size="10"' "$S/scripts/decision-record.py" && ok "B-2顺手 SVG 轴标签字号 ≥10.5px" || bad "B-2顺手 轴标签字号未达标"
grep -q "盲审B-4" "$S/scripts/decision-record.py" && ok "B-4 快轨互证+🔴原话引用在闸" || bad "B-4 闸缺失"

echo "[26] v5.0 流程回归骨架：replay.py（D1-D5 可自动化断言，≥15 条；v5.0#7 RC-5）"
RL="$TZ/replay.log"
if python3 "$S/tests/replay.py" >"$RL" 2>&1; then
  rn=$(grep -c "^  ✅" "$RL")  # 只计断言行，剔除末行 "ALL GREEN ✅" 横幅——与 replay.py 摘要计数一致（P2-1 双路径对齐）
  if [ "$rn" -ge 15 ]; then ok "replay.py 全绿（流程断言 ${rn} 条 ≥15：D1 七门/D2 G闸/D3 收敛闸/D4 台账/D5 长会话）"
  else bad "replay.py 断言数 ${rn} <15"; fi
else bad "replay.py 有红项" "$(grep "❌" "$RL" | head -3)"; fi

echo "[27] 批次2 流程缺口（W-07~W-13：T8双态/临界口径/init落盘/EPERM耐挫/--to回写/双真源/搬运键）"
B2="$TZ/b2"; mkdir -p "$B2"
# W-08：critical 口径变更（月销趋势替换上市时长）在 info-gate 生效
if python3 "$S/scripts/info-gate.py" --critical-list --scene S3 2>/dev/null | grep -q "月销趋势"; then ok "W-08 S3 critical 含「月销趋势」"; else bad "W-08 S3 critical 缺月销趋势"; fi
if python3 "$S/scripts/info-gate.py" --critical-list --scene S3 2>/dev/null | grep -q "上市时长"; then bad "W-08 S3 critical 残留旧口径上市时长"; else ok "W-08 旧口径「上市时长」0 残留"; fi
# W-07：T8 双态 —— 格式合法但不存在的 DR 路径必拦（--dr-dir），初步版占位放行
mkdir -p "$B2/drdir"
sed 's|./决策记录/DR-20260905-bline.html|./决策记录/DR-20260905-ghost.html|' "$TT/good_full.txt" > "$B2/ghost.txt"
if python3 "$S/scripts/check_output.py" "$B2/ghost.txt" --dr-dir "$B2/drdir" >/dev/null 2>&1; then bad "W-07 真缺口（格式合法但 DR 不存在）未拦"; else ok "W-07 真缺口：格式合法但 DR 文件不存在 → 必拦"; fi
if python3 "$S/scripts/check_output.py" "$TT/good_full.txt" >/dev/null 2>&1; then ok "W-07 无 --dr-dir 只保格式（兼容合式引用，不误伤）"; else bad "W-07 无 --dr-dir 误报"; fi
sed 's|（档案已存：./决策记录/DR-20260905-bline.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）|（档案未落盘：初步版，收敛并落盘后补 DR 编号——探讨阶段不强制落档案）|' "$TT/good_full.txt" > "$B2/draft.txt"
if python3 "$S/scripts/check_output.py" "$B2/draft.txt" >/dev/null 2>&1; then ok "W-07 初步版占位「档案未落盘」→ 放行"; else bad "W-07 初步版占位误报"; fi
# W-09/W-10：--init 落盘（带 --state）；只读目录 EPERM → 可读指引无裸 traceback
if python3 "$S/scripts/state-gate.py" --init --scene S3 --state "$B2/s.json" >/dev/null 2>&1 && [ -f "$B2/s.json" ]; then ok "W-09 --init 落盘默认路径（--state 指定）"; else bad "W-09 --init 未落盘"; fi
mkdir -p "$B2/ro"; chmod 555 "$B2/ro"
EP_OUT=$(python3 "$S/scripts/state-gate.py" --init --scene S3 --state "$B2/ro/x.json" 2>&1)
if echo "$EP_OUT" | grep -q "Traceback"; then bad "W-10 config 只读 EPERM 仍裸 traceback"; else ok "W-10 只读目录 EPERM → 可读指引（无裸 traceback）"; fi
chmod 755 "$B2/ro"
# W-11：--to PASS 不只判定，还回写 phase+gate_log；--audit 复核 phase=目标态（幂等）
printf '{"schema_version":"5.0.0","scene":"S3","phase":"S0_IDLE","reversibility":"🟢","profile_ok":false,"draft_checked":false,"skip_declared":false,"converged_evidence":null,"dr_id":null,"info_ledger":{},"routing":{"ai_primitive":{"action":"判","object":"现有单品","scene":"S3"},"divergence":false,"confirmed_by_user":"对"},"gate_log":[]}' > "$B2/to.json"
python3 "$S/scripts/state-gate.py" --to S1_ROUTED --state "$B2/to.json" >/dev/null 2>&1
P=$(python3 -c "import json;print(json.load(open('$B2/to.json'))['phase'])" 2>/dev/null)
GL=$(python3 -c "import json;print(len(json.load(open('$B2/to.json'))['gate_log']))" 2>/dev/null)
if [ "$P" = "S1_ROUTED" ] && [ "$GL" -ge 1 ]; then ok "W-11 --to PASS 回写 phase=S1_ROUTED + gate_log"; else bad "W-11 --to 未回写（phase=$P gate_log=$GL）"; fi
if python3 "$S/scripts/state-gate.py" --audit --state "$B2/to.json" >/dev/null 2>&1; then ok "W-11 --to 后 --audit phase=目标态（审计一致）"; else bad "W-11 --to 后 --audit 不一致"; fi
if python3 "$S/scripts/state-gate.py" --to S1_ROUTED --state "$B2/to.json" >/dev/null 2>&1; then ok "W-11 --to 幂等：同态重复跑不回写出错"; else bad "W-11 --to 幂等破坏"; fi
# W-12：归位管道符双真源对齐（SKILL.md=decision-record.py 口径；旧括号式 0 残留）
GW_MACHINE=$(grep -o '动作×对象 → 场景号 ｜ 出口 ｜ 理由一句话 ｜ 可逆性=🔴/🟡/🟢' scripts/decision-record.py | head -1)
if [ -n "$GW_MACHINE" ] && grep -qF "$GW_MACHINE" "$SMD"; then ok "W-12 SKILL.md 归位管道符口径与机器一致（双真源对齐）"; else bad "W-12 SKILL.md 归位口径≠机器"; fi
if grep -q "动作×对象×场景×出口×理由" "$SMD"; then bad "W-12 SKILL.md 残留旧括号式归位口径"; else ok "W-12 旧括号式归位口径 0 残留"; fi
# W-13：DR 落盘输出「渲染键齐备度」，缺键明确列出（台面四区→DR 搬运）
printf '{"schema_version":"5.0.0","phase":"S6_CONVERGED"}' > "$B2/state_w13.json"
cat > "$B2/w13.md" <<'EOT'
# DR test
- 问题：示例占位
- 选项：做/不做（含维持现状）
- 决定：推荐做
- 依据：ref-02
- 反方意见：若成本超两成则不成立；推翻条件=拿到报价
- 风险：财务（毛利）
- 假设清单：⚠️ 假设·待验证：动销达标
- 复盘日期：2026-12-31
- 状态：草案
- 探讨轨迹：初步版→用户反驳「预算紧」→分两期
- 归位：增×新品 → S1 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴
- 置信度：中高 · 依据
EOT
W13_OUT=$(PM_STRATEGIST_STATE="$B2/state_w13.json" python3 "$S/scripts/decision-record.py" "$B2/w13.md" --out "$B2/drout13" --slug 新品-增 2>&1)
if echo "$W13_OUT" | grep -q "渲染键齐备度.*缺："; then ok "W-13 落盘输出「渲染键齐备度」且缺键明确列出（W13 验收）"; else bad "W-13 缺渲染键齐备度输出：$(echo "$W13_OUT" | tail -2)"; fi
if ls "$B2/drout13"/*.html 2>/dev/null | grep -q "新品-增.html"; then ok "W-13 --slug 显式传具体品名（文件名含品名）"; else bad "W-13 --slug 未生效"; fi

echo "[28] 批次3 资格提分+适配线（W-16 agent_created / W-24 澄清白话 / W-26 L223 指针 / W-27 README 兜底）"
# W-16：frontmatter 补 agent_created
if grep -q "^agent_created: true" "$SMD"; then ok "W-16 frontmatter 含 agent_created: true"; else bad "W-16 frontmatter 缺 agent_created"; fi
# W-24：澄清问句白话化——SKILL.md 问句走白话（含「几个方案里挑一个」），无裸「你要 增/删/改/择/判」机械序列
if grep -q "几个方案里挑一个" "$SMD" && grep -q "先评估现状再定" "$SMD"; then ok "W-24 SKILL.md 澄清问句白话化（择=几个方案里挑一个/判=先评估现状再定）"; else bad "W-24 SKILL.md 澄清问句未白话化"; fi
if grep -q "你要 增/删/改/择/判" "$SMD"; then bad "W-24 机械原语序列仍裸露在问句"; else ok "W-24 机械原语名不上问句（0 残留）"; fi
if grep -q "路由澄清白话问法" "$S/references/ref-06通用组件.md"; then ok "W-24 ref-06 白话脚手架同步路由澄清问法"; else bad "W-24 ref-06 缺路由澄清白话问法"; fi
if grep -q "动作原语" "$S/references/术语浮层表.md" && grep -q "几个方案里挑一个" "$S/references/术语浮层表.md"; then ok "W-24 术语浮层表加动作原语白话行"; else bad "W-24 术语浮层表缺动作原语行"; fi
# W-26：L106 逐条念与 L223 相关性排序对齐指针
if grep -q "L223 决策相关性排序" "$SMD"; then ok "W-26 L106 补「按 L223 相关性排序」指针（两处不再打架）"; else bad "W-26 L106 缺 L223 指针"; fi
# W-27（砍）：README 兜底承诺「不懂的术语会解释」
if grep -qE "不懂的术语会解释|术语都会解释|不懂.*会解释" "$S/README.md"; then ok "W-27（砍）：README 承诺术语兜底解释"; else bad "W-27 README 缺术语兜底承诺"; fi
# W-17：分层架构文档（参赛评审引用）
if [ -f "$S/references/分层架构.md" ] && grep -q "七态" "$S/references/分层架构.md" && grep -q "数据流" "$S/references/分层架构.md" && grep -q "脚本职责" "$S/references/分层架构.md"; then ok "W-17 references/分层架构.md 在位（七态+脚本职责+数据流）"; else bad "W-17 分层架构文档缺项"; fi
# W-18：脚本清单统一 14（12 py + 2 sh）+ 以机器输出为准（v3.0 W-28 新增 publish-check.sh）
N_PY=$(find "$S/scripts" -maxdepth 1 -name "*.py" 2>/dev/null | wc -l | tr -d ' ')
N_SH=$(find "$S/scripts" -maxdepth 1 -name "*.sh" 2>/dev/null | wc -l | tr -d ' ')
if [ "$N_PY" = "12" ] && [ "$N_SH" = "2" ] && grep -q "共 \*\*14\*\* 个" "$SMD" && grep -q "以机器输出为准" "$SMD" && grep -q "publish-check.sh" "$SMD"; then ok "W-18 脚本清单统一 14（机器=12 py+2 sh）且 SKILL.md 以机器输出为准"; else bad "W-18 脚本清单计数未统一（机器 py=${N_PY}/sh=${N_SH}）"; fi
# W-20：audit 本会话 DR 边界（历史 DR 不计、本会话仍告警）——由 state-gate --self 覆盖
if python3 "$S/scripts/state-gate.py" --self >/dev/null 2>&1; then ok "W-20 state-gate --self（含历史/本会话 DR 边界 W-20 用例）"; else bad "W-20 state-gate --self 失败"; fi
# W-25：会话分文件（--init 无显式路径 → session_state.<id>.json；两端并发 id 互异；注入沙箱不走真 config）
if python3 - "$S" >/dev/null 2>&1 <<'PY'
import argparse, importlib.util, json, os, tempfile, sys
S = sys.argv[1]
spec = importlib.util.spec_from_file_location("sg", os.path.join(S, "scripts", "state-gate.py"))
sg = importlib.util.module_from_spec(spec); spec.loader.exec_module(sg)
os.environ.pop("PM_STRATEGIST_STATE", None)
tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "config"))
sg.DEFAULT_STATE_DIR = tmp  # 沙箱注入，不污染真实 config
a1 = argparse.Namespace(); a1.state = None  # 供 state_path 判断显式 --state
st1 = sg.init_state("S2", "q1", "🟢"); p1 = os.path.join(sg.DEFAULT_STATE_DIR, "config", "session_state.%s.json" % st1["session_id"])
st2 = sg.init_state("S2", "q2", "🟢"); p2 = os.path.join(sg.DEFAULT_STATE_DIR, "config", "session_state.%s.json" % st2["session_id"])
sg.write_state(p1, st1); sg.write_state(p2, st2)
iso = (st1["session_id"] != st2["session_id"]) and (p1 != p2) and os.path.isfile(p1) and os.path.isfile(p2)
try:
    resolved = sg.state_path(a1)  # 无 legacy + 两个会话文件 → 取最新（不报错）
    resolvable = resolved in (p1, p2)
except Exception:
    resolvable = False
sys.exit(0 if (iso and resolvable) else 1)
PY
then ok "W-25 会话分文件：并发 --init id 互异 + 各写各的文件 + 读态解析不报错"; else bad "W-25 会话分文件未生效"; fi
# W-21：AI 侧 slug 优先（搬运清单）+ 脚本 fallback 保持
if grep -q "显式传具体品名" "$SMD" && grep -q "对象+动作原语对" "$SMD"; then ok "W-21 SKILL.md 写死 AI 侧 slug 优先 + 脚本 fallback"; else bad "W-21 slug 约定未文档化"; fi
# W-28：发布编排脚本在位（五步标记：备份/还原模板/全 PASS 放行/上传清单/恢复填写版）+ 闸口 E 挂上发布编排
if [ -f "$S/scripts/publish-check.sh" ] \
  && grep -qE "备份.*填写版|发现填写版" "$S/scripts/publish-check.sh" \
  && grep -qE "还原空模板|从 git HEAD 还原" "$S/scripts/publish-check.sh" \
  && grep -qE "connector 上传清单|上传清单" "$S/scripts/publish-check.sh" \
  && grep -qE "永不更新远端.*local_profile|禁区.*local_profile" "$S/scripts/publish-check.sh" \
  && grep -qE "恢复本地填写版|恢复.*填写版" "$S/scripts/publish-check.sh" \
  && grep -q "publish-check.sh" "$SMD"; then ok "W-28 publish-check.sh 发布编排在位（备份→还原模板→全 PASS→上传清单→恢复 五步标记）"; else bad "W-28 publish-check.sh 发布编排缺失"; fi
# W-23 README 用户版：开篇人话（无机制黑话）+ 5.1.0 预告 + 发布安全声明 + mini 结构
HEAD23=$(sed -n '1,42p' "$S/README.md")
if echo "$HEAD23" | grep -qE "决策原语|25 ?格矩阵|闸口"; then bad "W-23 README 开篇混入机制黑话"; else ok "W-23 README 开篇无机制黑话（决策原语/25格矩阵/闸口）"; fi
if echo "$HEAD23" | grep -q "一句话" && echo "$HEAD23" | grep -q "什么时候用"; then ok "W-23 README 首段含一句话+何时用/别用"; else bad "W-23 README 首段缺 mini 结构"; fi
if grep -q "5.1.0" "$S/README.md" && grep -q "发布与隐私" "$S/README.md"; then ok "W-23 README 5.1.0 预告 + 发布安全声明"; else bad "W-23 README 缺版本预告/隐私声明"; fi

echo "═══════════════════════════"
echo "结果：$PASS 通过，$FAIL 失败"
[ "$FAIL" = 0 ] && echo "ALL GREEN ✅" || echo "HAS RED ❌"
exit "$FAIL"
