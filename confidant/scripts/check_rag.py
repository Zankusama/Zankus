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


def main():
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    hits = [k for k in MECH_KEYWORDS if k in text]
    if not hits:
        print("✅ 未检出机制/循证内容，无需 RAG 核对（exit 0）")
        sys.exit(0)

    has_wl = any(w.lower() in text.lower() for w in WHITELIST)
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
