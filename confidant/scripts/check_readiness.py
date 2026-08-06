#!/usr/bin/env python3
# check_readiness.py — 出画像前的就绪闸门（深度判定脚本写死，消除 AI 自由裁量）
# 用法: python3 scripts/check_readiness.py <dialogue_history.txt>
# 退出码:
#   0 = 就绪（输出选定模板 conceptual / narrative）
#   1 = 未达「说完了」闸门，不出画像（可出进展小结）
import sys
from pathlib import Path

DONE   = ["说完了","差不多了","倒完了","可以了","先到这","帮我梳理",
          "给我画像","出个图","整理一下","想聊的都聊了"]
AFFIRM = ["对","是的","没错","确实","就是这样","说到点上了"]
PAT_W  = ["模式","机制","根因","核心","一直这样","每次都","本质上","底层"]
SELF   = ["我发现每次","我注意到自己","总是","一直都","说来奇怪","我好像"]
CROSS  = ["也","同样","和","其实这两件事","本质上是一回事"]

def _judge(lines):
    """核心判定（与 main 同逻辑），返回 (ready: bool, tpl: str|None)"""
    user, ai = [], []
    for ln in lines:
        if ln.startswith("USER:"): user.append(ln)
        elif ln.startswith("AI:"): ai.append(ln)

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
    """脚本自检：3 用例（未说完拦 / 说完了选叙事 / 模式信号选概念）"""
    cases = [
        ("T1 未确认说完了 → 拦", ["USER: 最近压力挺大", "AI: 听起来挺熬人的", "USER: 嗯"], False, None),
        ("T2 说完了无模式信号 → 叙事模板", ["USER: 我最近失眠", "AI: 大概多久了", "USER: 说完了，先到这吧"], True, "narrative"),
        ("T3 说完了+模式确认 → 概念模板", ["USER: 我最近失眠", "AI: 你提到一直这样，是种模式吗", "USER: 对，一直都是", "USER: 说完了"], True, "conceptual"),
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
    ready, tpl = _judge(lines)
    if not ready:
        print("❌ Gate1 未过：用户未确认说完了 → 不出画像（可出进展小结）"); sys.exit(1)
    print(f"✅ 就绪 → 模板: {tpl}"); sys.exit(0)

if __name__ == "__main__":
    main()
