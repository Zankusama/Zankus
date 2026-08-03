#!/usr/bin/env bash
# goal-lint.sh — 任务书发出前自检（把「发出前自检」清单可机器化的部分变成命令）
# 用法: goal-lint.sh <任务书文件>   或   cat 任务书.txt | goal-lint.sh
#       goal-lint.sh --self <SKILL.md路径>   体检 skill 本体（脚本/引用文件/章节/版本齐全性）
# 退出码: 0 = 全过可发出；1 = 有项不过，修完再发
# 管理者写书后、发出前必跑；执行者收到书后也可先跑一遍确认没被改坏。

# ---- --self 模式：体检 skill 本体（脚本/引用文件/章节/版本齐全性） ----
if [ "$1" = "--self" ]; then
  SKILL_FILE="${2:-}"
  if [ -z "$SKILL_FILE" ] || [ ! -f "$SKILL_FILE" ]; then
    echo "❌ --self 需要 SKILL.md 路径: goal-lint.sh --self <SKILL.md>"
    exit 1
  fi
  SKILL_DIR=$(cd "$(dirname "$SKILL_FILE")" && pwd)
  FAIL=0
  pass() { echo "✅ $1"; }
  fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }
  echo "===== goal-lint --self skill 本体体检 ====="
  for f in "$SKILL_DIR/scripts/goal-lint.sh" "$SKILL_DIR/scripts/guard.sh" "$SKILL_DIR/scripts/coverage-check.sh" "$SKILL_DIR/scripts/stage-gate.sh" "$SKILL_DIR/scripts/pyramid-gen.py"; do
    if [ -f "$f" ]; then pass "存在: ${f#$SKILL_DIR/}"; else fail "缺失: ${f#$SKILL_DIR/}"; fi
  done
  for f in "$SKILL_DIR/references/anatomy.md" "$SKILL_DIR/references/glossary.md" "$SKILL_DIR/references/style.md"; do
    if [ -f "$f" ]; then pass "存在: ${f#$SKILL_DIR/}"; else fail "缺失: ${f#$SKILL_DIR/}"; fi
  done
  for sec in "## 流程" "## 写书规则" "## 发出前自检"; do
    if grep -qF "$sec" "$SKILL_FILE"; then pass "含节: $sec"; else fail "缺节: $sec"; fi
  done
  if grep -qE "^version: [0-9]+\.[0-9]+\.[0-9]+" "$SKILL_FILE"; then pass "version 数字三段式"; else fail "version 非数字三段式"; fi
  echo "-----------------------------"
  if [ "$FAIL" -eq 0 ]; then
    echo "✅✅ --self 全过，skill 本体完整"
    exit 0
  else
    echo "❌ --self 有 ${FAIL} 项不过"
    exit 1
  fi
fi

INPUT="${1:-/dev/stdin}"
if [ -f "$INPUT" ]; then
  CONTENT=$(cat "$INPUT")
elif [ -p /dev/stdin ] || [ -t 0 ]; then
  CONTENT=$(cat)
else
  echo "❌ 找不到文件: $INPUT（用法: goal-lint.sh <任务书文件> 或 cat 任务书 | goal-lint.sh）"
  exit 1
fi

FAIL=0
pass() { echo "✅ $1"; }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "===== goal-lint 任务书自检 ====="

# 1. 字符数 ≤4000（/goal 硬上限）；超限必须拆书，不许压缩偷删
#    wc -m 依赖 locale（LANG=C 下中文按字节计会虚高），强制 UTF-8 再统计
UTF8_LOCALE=$(locale -a 2>/dev/null | grep -iE 'utf-?8' | head -1)
[ -z "$UTF8_LOCALE" ] && UTF8_LOCALE="C"
LEN=$(printf '%s' "$CONTENT" | LC_ALL="$UTF8_LOCALE" wc -m | tr -d ' ')
if [ "$LEN" -le 4000 ]; then pass "字符数 ${LEN}/4000"; else fail "字符数 ${LEN} 超 4000 硬上限"; fi
# 1b. 超 3500（接近上限）：必须有「拆书方案」+ 给 N 本数量 + 给接缝关键词
#   ——三个条件都满足才认「拆书方案」是真方案，不是有"拆"字就过
if [ "$LEN" -gt 3500 ]; then
  HAS_SPLIT=$(printf '%s' "$CONTENT" | grep -cE "拆书方案|拆成|分次")
  HAS_COUNT=$(printf '%s' "$CONTENT" | grep -cE "第一本|第二本|第一部分|第二部分|本[1-9]|共 ?[0-9]+ 本|拆成 ?[0-9]+ 本|分 ?[0-9]+ 本|拆 ?[0-9]+ 本|分 ?[0-9]+ 份")
  HAS_SEAM=$(printf '%s' "$CONTENT" | grep -cE "接缝|衔接|交接|边界|交点")
  if [ "$HAS_SPLIT" -ge 1 ] && [ "$HAS_COUNT" -ge 1 ] && [ "$HAS_SEAM" -ge 1 ]; then
    pass "字数 ${LEN}>3500 拆书方案完整（N 本+接缝）"
  elif [ "$HAS_SPLIT" -ge 1 ]; then
    fail "字数 ${LEN}>3500 拆书方案缺要素：需 N 本数量+接缝关键词（如「接缝」「衔接」）"
  else
    fail "字数 ${LEN}>3500 无拆书方案——超限任务书必须拆书分次发出，不许压缩偷删保 4000"
  fi
else
  pass "字数 ${LEN}≤3500，未触发拆书检查"
fi

# 2. 必含节（开头声明 + 六节标题：含「工作产物放哪」）
if printf '%s' "$CONTENT" | grep -q "你是执行者"; then pass "开头声明「你是执行者」"; else fail "缺开头声明「你是执行者」"; fi
for t in "我替领导拍的板" "界限" "工作产物放哪" "现状与任务 0" "完成条件"; do
  if printf '%s' "$CONTENT" | grep -q "$t"; then pass "含节: $t"; else fail "缺节: $t"; fi
done
if printf '%s' "$CONTENT" | grep -qE "【任务 ?[0-9]"; then pass "含任务节"; else fail "缺任务节（【任务 N】）"; fi

# 3. 黑名单词（内部术语/违禁词不许进书）
for w in "暗卷" "探索型" "执行型" "来找我"; do
  if printf '%s' "$CONTENT" | grep -qF "$w"; then fail "黑名单词出现: $w"; else pass "无黑名单词: $w"; fi
done

# 4. 产物路径检查（三条禁令 + 修复原「无产物引用直接 pass」漏检）
#    触发：任务书有【界限】/【工作产物放哪】/【现状与任务 0】/【完成条件】任一节→应有 .goal/ 声明
PROD_LINES=$(printf '%s\n' "$CONTENT" | grep -E "PROGRESS\.md|BLOCKED\.md|\.bak|\.goal")
if [ -z "$PROD_LINES" ]; then
  # 检查是否含可能产生产物的节
  if printf '%s' "$CONTENT" | grep -qE "【工作产物放哪】|【界限】|【现状与任务 0】"; then
    fail "应有产物声明但全文无 .goal/ 引用（【工作产物放哪】/【界限】/【现状与任务 0】三节要求声明产物路径）"
  else
    pass "无产物引用（本任务书不产生工作产物）"
  fi
else
  # 4a. 禁裸名：产物行不含 "/"（如 "PROGRESS.md"）= 违规
  if printf '%s\n' "$PROD_LINES" | grep -v "/" | grep -qE "PROGRESS\.md|BLOCKED\.md|\.bak"; then
    fail "产物裸文件名（缺路径前缀）——产物一律写 .goal/xxx 或绝对路径，禁止裸名 PROGRESS.md/BLOCKED.md"
  else
    pass "产物均带路径前缀（.goal/ 或绝对路径）"
  fi
  # 4b. 禁指 skill 本体目录
  if printf '%s\n' "$PROD_LINES" | grep -qE "skills/|技能配置|AI记忆库"; then
    fail "产物路径指向 skill 本体目录（含 skills/ 或 技能配置）"
  else
    pass "产物未指向 skill 本体目录"
  fi
  # 4c. 禁预埋用户绝对路径（/Users/、/home/、C:\ 等）
  if printf '%s\n' "$PROD_LINES" | grep -qE "/Users/[a-zA-Z]|/home/[a-zA-Z]|C:\\\\\\\\[Uu]sers"; then
    fail "产物路径预埋使用者绝对路径（/Users/xxx /home/xxx C:\\Users\\xxx）——违反「不预埋任何使用者机器路径」原则，应改用 .goal/ 相对路径或 <工作区>/.goal/ 占位"
  else
    pass "产物路径未预埋使用者绝对路径"
  fi
fi

# 5. 完成条件段含可执行判定（命令或机器可判断言）
if printf '%s' "$CONTENT" | awk '/【完成条件】/,0' | grep -qE "grep|diff|test|python|node|npm|git|curl|sha|hash|check|verify|==|->|→"; then
  pass "完成条件含可执行判定"
else
  fail "完成条件无可执行判定（硬指标要能机器判）"
fi

# 6. 违禁行为（一个目标一次粘贴，不许存文件、不许发明命令）
for w in "存文件" "第二个 /goal"; do
  if printf '%s' "$CONTENT" | grep -qF "$w"; then fail "违禁行为: $w"; else pass "无违禁行为: $w"; fi
done

echo "-----------------------------"
if [ "$FAIL" -eq 0 ]; then
  echo "✅✅ goal-lint 全过，任务书可以发出"
  exit 0
else
  echo "❌ goal-lint 有 ${FAIL} 项不过，修完再发"
  exit 1
fi
