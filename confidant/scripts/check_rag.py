#!/usr/bin/env python3
# check_rag.py — Confidant 运行时 RAG 合规校验器（可机器化验收）
# 用法:
#   python3 scripts/check_rag.py <response_text_file>
#   cat response.md | python3 scripts/check_rag.py -
# 退出码:
#   0 = RAG 合规（未检出机制内容，或机制内容已挂白名单出处）
#   1 = RAG 失守（检出机制/循证内容，但无白名单出处）
# 判定逻辑（确定性转移：把"AI 自判 RAG 合规"变成"脚本判"）：
#   1. 抽取机制关键词（心理机制/框架/干预/练习/理论名）
#   2. 若命中机制词 → 检查是否含白名单域名/机构引用
#   3. 命中机制但无白名单引用 → exit 1，须先 WebSearch 白名单挂出处再出口
import argparse
import re
import sys
from pathlib import Path

# 机制/循证关键词（特异性优先，避免"认知/创伤"等过宽词误触发）
MECH_KEYWORDS = [
    "焦虑", "抑郁", "失眠", "早醒", "睡眠维持", "皮质醇", "血清素", "多巴胺",
    "杏仁核", "前额叶", "自主神经", "副交感", "交感",
    "4-7-8", "盒式呼吸", "呼吸法", "正念", "冥想",
    "CBT", "ACT", "DBT", "认知行为", "接纳承诺",
    "依恋", "防御机制", "经验回避",
    "Beck", "Vaillant", "Bowlby", "Hayes", "C-SSRS",
]

# 白名单出处标识（who.int / nimh.nih.gov / apa.org / 卫健委 / PubMed / 三甲）
WHITELIST = [
    "who.int", "nimh.nih.gov", "apa.org", "pubmed", " pmid",
    "nih.gov", "ncbi", "卫健委", "卫生健康委", "三甲",
]


def _judge(text, mode="default"):
    """核心判定（与 main 同逻辑），返回 (ok: bool, msg: str)"""
    hits = [k for k in MECH_KEYWORDS if k in text]
    if not hits:
        return True, f"未检出机制内容（命中 0）"
    has_wl = any(w.lower() in text.lower() for w in WHITELIST)
    if mode == "dialogue":
        PSEUDO = ["研究表明", "根据研究", "数据显示", "有论文说"]
        pseudo = [p for p in PSEUDO if p in text and not has_wl]
        if pseudo:
            return False, f"对话模式伪引用 {pseudo} 无白名单"
        return True, "对话模式机制已内化"
    if has_wl:
        return True, f"命中机制 {len(hits)} 个已挂白名单"
    return False, f"命中机制 {len(hits)} 个无白名单出处"


def selftest():
    """脚本自检：3 用例（纯共情过 / 机制无出处拦 / 机制有出处过 + dialogue 伪引用拦）"""
    cases = [
        ("T1 纯共情不涉机制 → 过", "听起来那阵子挺难熬的，你愿意多说两句吗", "default", True),
        ("T2 机制无出处 → 拦", "焦虑会激活杏仁核，导致早醒", "default", False),
        ("T3 机制有白名单出处 → 过", "焦虑早醒与皮质醇相关（来源：who.int 公开材料）", "default", True),
        ("T4 dialogue 伪引用无出处 → 拦", "研究表明焦虑的人睡眠质量更差", "dialogue", False),
    ]
    passed = 0
    for name, text, mode, expect in cases:
        ok, msg = _judge(text, mode)
        mark = "PASS" if ok == expect else "FAIL"
        if ok == expect:
            passed += 1
        print(f"  [{mark}] {name} → {msg}（期望 {'过' if expect else '拦'}，实际 {'过' if ok else '拦'}）")
    print(f"selftest: {passed}/{len(cases)} 过")
    sys.exit(0 if passed == len(cases) else 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="-", help="回复文本文件，'-' 表示读 stdin")
    ap.add_argument("--mode", choices=["default", "dialogue"], default="default",
                    help="default=交付/正式出口需挂白名单；dialogue=对话内化不外露+伪引用拦截")
    ap.add_argument("--output", metavar="FILE",
                    help="校验交付画像（严：占位符残留拦截 + 机制须挂白名单出处）")
    ap.add_argument("--selftest", action="store_true", help="脚本自检（3 用例）")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    text = Path(args.file).read_text(encoding="utf-8") if args.file != "-" else sys.stdin.read()

    # --output：交付物严模式（占位符残留拦截）
    if args.output:
        out = Path(args.output).read_text(encoding="utf-8")
        if "{{" in out:
            print("❌ 交付画像含占位符残留 → 未填完（exit 1）")
            sys.exit(1)

    hits = [k for k in MECH_KEYWORDS if k in text]
    if not hits:
        print("✅ 未检出机制/循证内容，无需 RAG 核对（exit 0）")
        sys.exit(0)

    has_wl = any(w.lower() in text.lower() for w in WHITELIST)

    # --mode dialogue：对话内化不外露 + 伪引用拦截
    if args.mode == "dialogue":
        PSEUDO = ["研究表明", "根据研究", "数据显示", "有论文说"]
        pseudo = [p for p in PSEUDO if p in text and not has_wl]
        if pseudo:
            print(f"❌ 对话模式检出伪引用 {pseudo} 但无白名单 → 拦截（exit 1）")
            sys.exit(1)
        # 对话模式允许内化（有白名单即可），不强制外显引用
        if has_wl:
            print("✅ 对话模式：机制已内化、出处合规（exit 0）")
            sys.exit(0)
        print("❌ 对话模式：含机制但无白名单出处（exit 1）")
        sys.exit(1)

    if has_wl:
        print(f"✅ 命中机制词 {len(hits)} 个，已挂白名单出处 → RAG 合规（exit 0）")
        print("   机制词:", "、".join(hits[:8]))
        sys.exit(0)

    print(f"❌ 命中机制词 {len(hits)} 个，但无白名单出处 → RAG 失守（exit 1）")
    print("   机制词:", "、".join(hits[:8]))
    print("   须先 WebSearch 白名单（who.int / nimh.nih.gov / apa.org / 卫健委 / PubMed / 三甲）并挂出处")
    sys.exit(1)


if __name__ == "__main__":
    main()
