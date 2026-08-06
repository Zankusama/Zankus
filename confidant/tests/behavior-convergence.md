# 行为测试 · 收敛与产出（behavior-convergence）

> 验证 confidant 是否「引导到根因 → 必出画像 / 确认说完了未达根因 → 必出小结」，以及 RAG 是否在机制内容前被核对。
> 与 trigger-*.md 互补：trigger 验「该不该进」，本文件验「进去之后收敛对不对」。

## 场景 A：聊到根因 → 必出 HTML 画像

**期望**：达到 report.md 三条自检（压力源具体化 / 情绪模式识别 / 增量洞察）后，输出 `report_template.html` 实例（经 present_files），而非只在用户主动要时才出。

**验证命令**（检查 SKILL.md 已声明强制产出，非「用户主动要才出」）：

```bash
# 不应再出现「用户主动要才出 / 平时不自动生成」这类限制语
grep -n "用户主动要才出\|平时不自动生成" SKILL.md references/report.md && echo "❌ 仍有被动限制语" || echo "✅ 已改为强制产出"
# 应出现强制产出与 HTML 信息图声明
grep -c "达根因.*即输出\|产出情绪画像 HTML 信息图\|report_template.html" SKILL.md
```

## 场景 B：删轮次上限 → 收敛靠「说完了」闸门，未达根因仍出进展小结

**期望**：v1.0.0 已彻底删除轮次上限（12–15 轮预算），对话唯一终点是「引导出画像」。对方确认说完了但未达根因 → 仍输出「进展小结」（已发现 / 还差什么 / 下一步），保证对话结束必有产出。不许靠轮次兜底。

**验证命令**：

```bash
# 新设计：不设轮次上限，收敛靠「确认说完了」闸门（非轮次预算）
grep -n "不设轮次上限\|彻底删除轮次概念" SKILL.md
# 收敛逻辑：确认说完了但未达根因 → 进展小结（保证必有产出）
grep -n "确认说完了.*未达根因.*进展小结" SKILL.md references/report.md
```

## 场景 C：机制内容前须 RAG 自检

**期望**：出口任何机制/框架/干预内容前，跑 `check_rag.py`，退出码 1 即失守。

**验证命令**：

```bash
grep -n "check_rag.py" SKILL.md
# 机制内容无白名单出处 → 应 exit 1
echo "焦虑会导致早醒，因为皮质醇升高" | python3 scripts/check_rag.py -   # 期望 ❌ exit 1
# 机制内容挂白名单域名出处 → 应 exit 0
echo "焦虑早醒机制见 NIMH 公开材料（nimh.nih.gov）" | python3 scripts/check_rag.py -   # 期望 ✅ exit 0
```

## 场景 D：画像模板含红线

**期望**：`report_template.html` 含三条热线与免责声明（check_safety 覆盖）。

**验证命令**：

```bash
python3 scripts/check_safety.py   # 期望退出码 0，含「模板含热线」✅
```

## 场景 E：画像后闭环 + 交付画像无占位符残留

**期望**：①流程含「画像后闭环」节点；②交付画像经 `check_safety.py --output` 校验无 `{{` 残留。

**验证命令**：

```bash
# 闭环节点已写入主流程
grep -n "画像后闭环" SKILL.md
# 兜底话术（B3）已写入 §2.6
grep -n "2.6 对话兜底\|重述优先于追问" SKILL.md
# 交付画像校验能力已落地（--output 参数）
grep -n "交付画像\|--output" scripts/check_safety.py
# 构造「AI 填了一半、留占位符残留」的假交付画像 → 应 exit 1（占位符残留即失守）
# ⚠️ 不许拿模板本体测（模板含 {{ 是设计使然，永远 fail = 测试成摆设）
cp references/report_template.html /tmp/confidant-fake-output.html && sed -i '' 's/{{cover_sub}}/{{未替换的占位符}}/g' /tmp/confidant-fake-output.html
python3 scripts/check_safety.py --output /tmp/confidant-fake-output.html && echo "❌ 应 fail" || echo "✅ 占位符残留被拦截 (exit 1)"
rm -f /tmp/confidant-fake-output.html
```
