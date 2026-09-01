#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scene-router.py — pm-strategist 场景路由器（关键词+规则，零外部模型）

输入用户问题，输出：场景（S1-S5/C类）+ 类别（A/B/C）+ 需加载references + 置信度。
无命中→「未识别」+ 低置信度 + 建议 C类（正常输出，退出码0）。

用法:
  python3 scripts/scene-router.py "这个新品该不该立项？"
  echo "产品线怎么取舍" | python3 scripts/scene-router.py -
  python3 scripts/scene-router.py --json "定多少价合适"
  python3 scripts/scene-router.py --self
"""
import sys, json, argparse

ROUTES = {
    "S1": {"name": "S1 新品立项与产品定义", "cat": "A", "refs": "ref-01新品立项与产品定义.md+fm-01五闸开发流程.md",
           "kw": ["新品", "立项", "机会", "值得投", "要不要做这个", "新品牌", "上新"]},
    "S2": {"name": "S2 产品线组合规划", "cat": "A", "refs": "ref-02产品线组合规划.md+fm-03优先级排序.md",
           "kw": ["产品线", "SKU", "组合", "取舍", "砍掉", "倾斜", "留哪个", "排产优先"]},
    "S3": {"name": "S3 产品生命周期与迭代", "cat": "A", "refs": "ref-03产品生命周期与迭代.md+fm-04复盘框架.md",
           "kw": ["生命周期", "迭代", "卖不动", "成熟", "衰退", "焕新", "换代", "复购下滑"]},
    "S4": {"name": "S4 定价与盈利", "cat": "B", "refs": "ref-04定价与盈利.md",
           "kw": ["定价", "价格", "涨价", "降价", "促销价", "毛利不够", "盈亏平衡", "卖多少钱", "定多少价", "什么价", "定什么价", "定价多少"]},
    "S5": {"name": "S5 上市GTM策略", "cat": "B", "refs": "ref-05上市GTM策略.md",
           "kw": ["上市", "GTM", "铺货", "铺哪些渠道", "上市节奏", "首发", "渠道铺开"]},
}
C_KW = ["风险", "复盘", "值不值", "生意", "壁垒", "划不划算", "帮我看", "信息收集", "提醒"]


def route(question):
    """返回 (scene_id, conf, hits)；规则：场景词命中≥1取最高分；
    同分并列→MIX「待路由」（不偏袒先定义场景，守 B 类跨部门防线）；
    0 场景命中看 C 类词；含「复盘」提升 mid（设计内组件⑤，非未识别）。"""
    q = question
    hits = {}
    for sid, cfg in ROUTES.items():
        n = sum(1 for k in cfg["kw"] if k in q)
        if n:
            hits[sid] = n
    if hits:
        best = max(hits.values())
        top = [sid for sid, n in hits.items() if n == best]
        if len(top) > 1:
            return "MIX", "mid", hits
        sid = top[0]
        conf = "high" if hits[sid] >= 2 else "mid"
        return sid, conf, hits
    cn = sum(1 for k in C_KW if k in q)
    if cn:
        conf = "mid" if (cn >= 2 or "复盘" in q) else "low"
        return "C", conf, {}
    return "C", "low", {}


def render(sid, conf):
    if sid == "MIX":
        return {"scene": "待路由（多场景并列命中）", "category": "?", "refs": ["ref-06通用组件.md"], "confidence": conf,
                "note": "并列命中：先向用户澄清主意图再路由，不擅自偏袒（尤其含 B 类场景时守住跨部门防线）"}
    if sid == "C":
        return {"scene": "C类（组件级提醒，不决策）", "category": "C", "refs": ["ref-06通用组件.md"], "confidence": conf}
    cfg = ROUTES[sid]
    return {"scene": cfg["name"], "category": cfg["cat"], "refs": cfg["refs"].split("+"), "confidence": conf}


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 场景路由器（关键词+规则）")
    ap.add_argument("question", nargs="?", help="用户问题文本，或 - 读 stdin")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        cases = [("这个新品该不该立项？", "S1"), ("产品线太多先砍哪个", "S2"),
                 ("这个品卖不动了怎么办", "S3"), ("要不要涨价", "S4"),
                 ("新品怎么上市先铺哪些渠道", "S5"), ("帮我看看有什么风险", "C"),
                 ("这个品定多少价合适", "S4"), ("新品上市定多少价", "MIX"),
                 ("上次决策复盘一下", "C"), ("新品上市定什么价", "S4")]
        ok = all(route(q)[0] == exp for q, exp in cases)
        print("self: 10样例路由 %s（期望 S1/S2/S3/S4/S5/C×2/S4/MIX/S4 全中）" % ("PASS✓" if ok else "FAIL✗"))
        return 0 if ok else 1
    if not a.question:
        ap.print_help()
        return 2
    q = sys.stdin.read() if a.question == "-" else a.question
    sid, conf, hits = route(q)
    r = render(sid, conf)
    if a.json:
        print(json.dumps({"input": q.strip(), "scene_id": ("C" if sid == "C" else sid), **r}, ensure_ascii=False))
    else:
        if sid == "C":
            note = "（未识别具体场景，建议走C类组件）" if conf == "low" else ""
            print("场景=%s | 类别=C | 主查=%s | 置信度=%s%s" % (r["scene"], r["refs"][0], conf, note))
        else:
            print("场景=%s | 类别=%s | 主查=%s | 置信度=%s" % (r["scene"], r["category"], "+".join(r["refs"]), conf))
    return 0


if __name__ == "__main__":
    sys.exit(main())
