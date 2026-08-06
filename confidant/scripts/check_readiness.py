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

def main():
    if len(sys.argv) < 2:
        print("用法: check_readiness.py <dialogue_history.txt>"); sys.exit(2)
    lines = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    user, ai = [], []
    for ln in lines:
        if ln.startswith("USER:"): user.append(ln)
        elif ln.startswith("AI:"): ai.append(ln)

    # Gate1：用户确认说完了（必过，否则不出画像）
    if not any(any(d in u for d in DONE) for u in user):
        print("❌ Gate1 未过：用户未确认说完了 → 不出画像（可出进展小结）"); sys.exit(1)

    # Gate2：模式信号（客观，非 AI 自评）
    pattern = False
    for i in range(len(lines)-1):
        if lines[i].startswith("AI:") and lines[i+1].startswith("USER:") \
           and any(p in lines[i] for p in PAT_W) and any(a in lines[i+1] for a in AFFIRM):
            pattern = True
    if any(any(s in u for s in SELF) for u in user): pattern = True
    if sum(1 for a in ai if any(c in a for c in CROSS)) >= 2: pattern = True

    # Gate3：客观优先（脚本不读 AI 深度标记，天然降级到安全模板）
    tpl = "conceptual" if pattern else "narrative"
    print(f"✅ 就绪 → 模板: {tpl}"); sys.exit(0)

if __name__ == "__main__":
    main()
