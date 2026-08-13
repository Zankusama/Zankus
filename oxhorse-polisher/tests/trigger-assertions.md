# oxhorse-polisher 触发词断言测试

> 每次修改 SKILL.md 后跑一遍，验证触发词/定位未回退。
> 更完整的机器化入口：`bash scripts/check_triggers.sh [SKILL.md 路径]`（本文件为人工可读版断言清单）。
> 运行方式：在 skill 根目录（含 SKILL.md 的目录）执行，不依赖本机绝对路径。

## 断言清单（三场景覆盖：明显触发 / 改写触发 / 不相关不触发）

### A. 明显触发场景（触发词原样出现）
- [ ] `grep -c "牛马精修" SKILL.md ≥ 1` — 主触发词存在
- [ ] `grep -c "oxhorse-polisher" SKILL.md ≥ 1` — 英文名存在
- [ ] `grep -c "循环精修" SKILL.md ≥ 1` — 中文别名存在
- [ ] `grep -c "loop polish" SKILL.md ≥ 1` — 英文别名存在

### B. 改写触发场景（无空格/不同句式仍触发）
- [ ] `grep -c "牛马精修一下" SKILL.md ≥ 0` 且触发条件节含"不强制空格" — 触发词无空格变体有规则
- [ ] `grep -c "触发词开头即可" SKILL.md ≥ 1` — 放宽匹配规则已声明
- [ ] 评估集不应触发表含"循环/loop 单前缀"负例 — 与 clock-loop 边界已测试（`grep -c "clock-loop 的触发域" SKILL.md ≥ 1`）

### C. 不相关不触发场景（否定/前缀排除）
- [ ] `grep -c "否定前缀排除" SKILL.md ≥ 1` — 否定前缀（"不用精修了"）不触发
- [ ] `grep -c "不用"循环/loop"单前缀" SKILL.md ≥ 1` — 单前缀不触发（clock-loop 区分）

### D. 定位/防回退断言
- [ ] `grep -c "instruction-mode" SKILL.md ≥ 1` — instruction-mode 定位存在
- [ ] `grep -c "不假扮终审闸门" SKILL.md ≥ 1` — 不假扮终审闸门定位存在
- [ ] `grep -c "references/task-standards.json" SKILL.md = 0` — 旧路径已删（反向验证项）

## 运行方式

```bash
# 站在 skill 根目录运行（无需绝对路径）
SKILL=SKILL.md
for kw in 牛马精修 oxhorse-polisher 循环精修 "loop polish" instruction-mode 不假扮终审闸门; do
  echo "$kw: $(grep -c "$kw" "$SKILL")"
done
echo "旧路径: $(grep -c 'references/task-standards.json' "$SKILL")"
# 机器化入口（推荐）
bash scripts/check_triggers.sh "$SKILL"
```
