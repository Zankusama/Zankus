#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""risk-check.py — 风险6维度覆盖检查器（行为准则②风险做提醒的机器可查子集）

输入输出文本，检查 6 风险维度（法规/市场/竞争/供应链/财务/组织）覆盖：
  已覆盖 → 列命中词；未覆盖 → 列入缺失。
全 6 维覆盖 → "PASS 6/6" 退出码 0；有缺失 → 列出缺失维度，退出码 1。
（维度完全无关时可写"X：未命中"显式声明——本脚本按文本证据判定，未命中即报缺失，
 由作者补"未命中"声明字样可豁免：声明行如「法规：未命中」。）

用法:
  python3 scripts/risk-check.py <文本文件>
  cat 输出.txt | python3 scripts/risk-check.py -
  python3 scripts/risk-check.py --self
"""
import sys, argparse

DIMS = {
    "法规": ["法规", "合规", "宣称", "备案", "监管", "标签", "法务"],
    "市场": ["市场", "需求", "趋势", "季节", "渗透"],
    "竞争": ["竞争", "竞品", "对手", "替代", "跟价", "价格战"],
    "供应链": ["供应链", "产能", "原料", "库存", "交期", "备货", "断货", "良率"],
    "财务": ["财务", "毛利", "成本", "回本", "现金流", "预算", "盈亏", "利润"],
    "组织": ["组织", "人力", "团队", "人员", "培训", "排产", "执行走形"],
}


def covered(text, kws):
    return [k for k in kws if k in text]


def check(text):
    covered_map, missing = {}, []
    for dim, kws in DIMS.items():
        hits = covered(text, kws)
        if hits:
            covered_map[dim] = hits
        elif ("%s：未命中" % dim) in text or ("%s:未命中" % dim) in text:
            # 未命中显式声明豁免（N7 死代码清理：原独立函数已内联，行为不变）
            covered_map[dim] = ["（作者显式声明未命中）"]
        else:
            missing.append(dim)
    return covered_map, missing


def self_test():
    good = "风险提醒：法规（宣称边界）市场（季节波动）竞争（竞品跟价）供应链（备货交期）财务（毛利）组织（培训）。"
    bad = "只提了成本和库存，别的没想。"
    cm, miss = check(good)
    ok = (len(miss) == 0)
    _, miss2 = check(bad)
    caught = len(miss2) >= 3
    print("self: 全覆盖样本 %s（6/6）；缺维样本拦截 %d 维（期望≥3）" % ("PASS✓" if ok else "FAIL✗", len(miss2)))
    return ok and caught


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 风险6维度覆盖检查器")
    ap.add_argument("input", nargs="?", help="文本文件，或 - 读 stdin")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if not a.input:
        ap.print_help()
        return 2
    try:
        text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    except OSError as e:
        print("读入失败: %s" % e)
        return 2
    cov, miss = check(text)
    for dim in DIMS:
        if dim in cov:
            print("已覆盖  %s（命中：%s）" % (dim, "/".join(cov[dim][:4])))
        else:
            print("缺失    %s（可补「%s：未命中」显式声明）" % (dim, dim))
    if miss:
        print("FAIL — 缺 %d/%d 维：%s" % (len(miss), len(DIMS), "/".join(miss)))
        print("覆盖边界：本次=输出文本的 6 风险维度关键词覆盖；未覆盖=风险判断的质量（命中≠判断对）。")
        return 1
    print("PASS %d/6" % len(DIMS))
    print("覆盖边界：本次=输出文本的 6 风险维度关键词覆盖；未覆盖=风险判断的质量（命中≠判断对）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
