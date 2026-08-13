#!/usr/bin/env python3
# check_readiness.py — 出画像前的就绪闸门（深度判定脚本写死，消除 AI 自由裁量）
# 用法: python3 scripts/check_readiness.py <dialogue_history.txt>
# 退出码:
#   0 = 就绪（输出选定模板 conceptual / narrative）
#   1 = 未达「说完了」闸门，不出画像（可出进展小结）
#   2 = 对话历史格式错误（首行非 USER:/AI: 前缀，或存在无前缀行）
# v1.2.0 修复（skill-rehab 盲审 F1/F2 实测复现）：
#   F1: CROSS 删单字「也/和」（中文高频虚词，≥2 条 AI 行含即误判 conceptual，叙事版模板几乎不可达）——保留短语级交叉信号
#   F2: DONE「可以了」与危机语境「可以了，不用管我了」重叠 → 危机语境误判就绪；加危机词负向排除（命中危机词则不算「说完了」）
import sys
from pathlib import Path

DONE   = ["说完了","差不多了","倒完了","可以了","先到这","帮我梳理",
          "给我画像","出个图","整理一下","想聊的都聊了"]
# F2: 危机语境负向词——「可以了，不用管我了」「别管我了」「撑不下去了」等含危机信号，
# 虽字面命中 DONE，但属于危机模式语境，不算「说完了」，不得出画像就绪（§4.5 坑点 6）
# v1.2.0 对抗复核收紧：删「放弃吧/算了吧/没意思了」（§2.6 明确「算了」是普通兜底场景，误伤正常收尾）
CRISIS = ["不用管我","别管我","撑不下去","撑不住了","不想活了","活不下去",
          "不想活","你们走","都别来"]
AFFIRM = ["对","是的","没错","确实","就是这样","说到点上了"]
PAT_W  = ["模式","机制","根因","核心","一直这样","每次都","本质上","底层"]
SELF   = ["我发现每次","我注意到自己","总是","一直都","说来奇怪","我好像"]
# F1: 交叉信号只用短语级（「也/和」单字为中文高频虚词，见 §1.5 双模板分层说明）
CROSS  = ["其实这两件事","本质上是一回事","这两件事是连着","是一体的"]

def _judge(lines):
    """核心判定（与 main 同逻辑），返回 (ready: bool, tpl: str|None)"""
    user, ai = [], []
    for ln in lines:
        if ln.startswith("USER:"): user.append(ln)
        elif ln.startswith("AI:"): ai.append(ln)

    # F2: 危机语境负向排除（v1.2.0 修复 + 对抗复核补强）——危机词检查扩展到整段 user 行集合，
    #   不只查含 DONE 的同一行：`USER:可以了` + `USER:不想活了` 跨行组合同样不得出画像（§4.5 坑点 6）
    any_crisis = any(any(c in u for c in CRISIS) for u in user)
    if any_crisis:
        return False, None

    if not any(any(d in u for d in DONE) for u in user):
        return False, None

    pattern = False
    for i in range(len(lines)-1):
        if lines[i].startswith("AI:") and lines[i+1].startswith("USER:") \
           and any(p in lines[i] for p in PAT_W) and any(a in lines[i+1] for a in AFFIRM):
            pattern = True
    if any(any(s in u for s in SELF) for u in user): pattern = True
    if sum(1 for a in ai if any(c in a for c in CROSS)) >= 2: pattern = True

    return True, ("conceptual" if pattern else "narrative")


def selftest():
    """脚本自检：5 用例（未说完拦 / 说完了选叙事 / 模式信号选概念 / F1 反例 / F2 反例）"""
    cases = [
        ("T1 未确认说完了 → 拦", ["USER: 最近压力挺大", "AI: 听起来挺熬人的", "USER: 嗯"], False, None),
        ("T2 说完了无模式信号 → 叙事模板", ["USER: 我最近失眠", "AI: 大概多久了", "USER: 说完了，先到这吧"], True, "narrative"),
        ("T3 说完了+模式确认 → 概念模板", ["USER: 我最近失眠", "AI: 你提到一直这样，是种模式吗", "USER: 对，一直都是", "USER: 说完了"], True, "conceptual"),
        # F1 反例（v1.2.0）：浅聊无模式确认，但 AI 行含单字「也/和」→ 应 narrative（修前误判 conceptual）
        ("T4 浅聊含也/和 → 应叙事（F1 反例）", ["USER: 最近工作有点烦", "AI: 听起来挺烦的，和你想的不太一样吧", "USER: 就是同事配合得不好，进度也慢", "AI: 那种白做了的感觉，也让人挺泄气的", "USER: 嗯，我说完了"], True, "narrative"),
        # F2 反例（v1.2.0）：危机语境「可以了，不用管我了」→ 应拦（修前误判就绪）
        ("T5 危机语境可以了 → 应拦（F2 反例）", ["USER: 最近真的撑不下去了", "AI: 听起来你很难熬，愿意多说一点吗", "USER: 你们不用管我了，可以了", "AI: 我在的，刚才那句话让我有点担心", "USER: 别管我了"], False, None),
    ]
    passed = 0
    for name, lines, exp_ready, exp_tpl in cases:
        ready, tpl = _judge(lines)
        ok = ready == exp_ready and (tpl == exp_tpl if exp_tpl else True)
        if ok:
            passed += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} → {'就绪'+str(tpl) if ready else '未就绪'}（期望 {'就绪'+str(exp_tpl) if exp_ready else '拦'}）")
    print(f"selftest: {passed}/{len(cases)} 过")
    sys.exit(0 if passed == len(cases) else 1)


def main():
    if len(sys.argv) < 2:
        print("用法: check_readiness.py <dialogue_history.txt>"); sys.exit(2)
    if sys.argv[1] == "--selftest":
        selftest()
        return
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    # v1.2.0 格式预检（P2-4）：首行非 USER:/AI: 前缀 → 明确报格式错误，而非静默当「未说完了」
    nonempty = [ln for ln in lines if ln.strip()]
    if nonempty and not any(nonempty[0].startswith(("USER:", "AI:")) for ln in [nonempty[0]]):
        print("❌ 对话历史格式错误：首行须为 `USER: 用户发言` 或 `AI: 助手发言`（前缀大写+英文冒号，见 SKILL.md §7.6）——当前首行: " + nonempty[0][:40])
        sys.exit(2)
    bad = [ln for ln in nonempty if not ln.startswith(("USER:", "AI:"))]
    if bad:
        print(f"❌ 对话历史格式错误：{len(bad)} 行无 `USER:`/`AI:` 前缀（前缀大写+英文冒号，见 SKILL.md §7.6）——示例: " + bad[0][:40])
        sys.exit(2)
    ready, tpl = _judge(lines)
    if not ready:
        print("❌ Gate1 未过：用户未确认说完了 → 不出画像（可出进展小结）"); sys.exit(1)
    print(f"✅ 就绪 → 模板: {tpl}"); sys.exit(0)

if __name__ == "__main__":
    main()
