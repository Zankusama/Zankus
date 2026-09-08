#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unknown-info-check.py — 未知信息引导检查器（行为准则③的机器可查子集）

输入场景（S1-S5/C）+ 输出文本，检查该场景关键未知信息是否被引导提问：
  已问 → 列命中；漏问 → 列入缺失。
全问到 → 退出码 0；有漏问 → 退出码 1（--scene 缺省=C类）。

用法:
  python3 scripts/unknown-info-check.py --scene S1 <文本>
  cat 输出.txt | python3 scripts/unknown-info-check.py --scene S4 -
  python3 scripts/unknown-info-check.py --self
"""
import sys, argparse

SCENE_INFO = {
    "S1": {"市场规模口径": ["市场规模", "市场容量", "规模口径", "容量", "增速"],
           "目标人群画像": ["目标人群", "画像", "谁买", "人群"],
           "竞品对照": ["竞品", "竞争", "对照品", "对手"],
           "渠道适配": ["渠道", "铺货", "通路"],
           "成本结构": ["成本", "毛利", "料工费"]},
    "S2": {"单品贡献度": ["贡献", "占比", "销售额", "毛利额"],
           "增长趋势": ["增长", "增速", "趋势"],
           "产能约束": ["产能", "约束", "上限", "排产"],
           "战略定位": ["战略", "定位", "角色"]},
    "S3": {"销售增速口径": ["增速", "下滑", "增长", "同比"],
           "获客成本": ["获客", "拉新", "获客成本"],
           "渗透率": ["渗透"],
           "利润趋势": ["利润", "毛利趋势"],
           "复购": ["复购", "留存"]},
    "S4": {"价格带": ["价格带", "价位", "带位"],
           "成本与毛利目标": ["成本", "毛利目标", "毛利"],
           "竞品价格": ["竞品价格", "对手价格", "竞品卖多少", "竞品"],
           "需求弹性": ["弹性", "敏感", "支付意愿"]},
    "S5": {"渠道结构": ["渠道", "渠道结构", "首铺"],
           "上市节奏": ["节奏", "排期", "里程碑", "T-"],
           "资源预算": ["预算", "资源", "费用"],
           "物料准备": ["物料", "详情页", "话术", "陈列"]},
    "C": {"决策目标": ["目标", "解决什么", "为了什么"],
          "时间窗": ["时间", "期限", "deadline", "窗口"],
          "约束条件": ["约束", "限制", "不能超", "红线"]},
}


def check(scene, text):
    infos = SCENE_INFO.get(scene, SCENE_INFO["C"])
    asked, missed = [], []
    for info, kws in infos.items():
        (asked if any(k in text for k in kws) else missed).append(info)
    return asked, missed


def self_test():
    s1_text = "先问：市场规模口径是什么？目标人群画像有吗？竞品对照谁？渠道适配哪条通路？成本结构能拆吗？"
    asked, missed = check("S1", s1_text)
    ok = not missed
    _, missed2 = check("S1", "只问了人群画像。")
    caught = len(missed2) >= 3
    print("self: S1全引导样本 %s；只问1维样本漏问 %d 维（期望≥3）" % ("PASS✓" if ok else "FAIL✗", len(missed2)))
    return ok and caught


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 未知信息引导检查器")
    ap.add_argument("input", nargs="?", help="文本文件，或 - 读 stdin")
    ap.add_argument("--scene", default="C", help="S1/S2/S3/S4/S5/C（缺省C）")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.scene not in SCENE_INFO:
        print("未知场景 %s（可选：%s）" % (a.scene, "/".join(SCENE_INFO)))
        return 2
    if not a.input:
        ap.print_help()
        return 2
    try:
        text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    except OSError as e:
        print("读入失败: %s" % e)
        return 2
    asked, missed = check(a.scene, text)
    for x in asked:
        print("已问  %s" % x)
    for x in missed:
        print("漏问  %s" % x)
    if missed:
        print("FAIL — 漏问 %d/%d（行为准则③：影响决策但用户没说的信息应引导补充，或显式假设⚠️）" % (len(missed), len(asked) + len(missed)))
        print("覆盖边界：本次=引导清单关键词命中（v5.0 起结论性判定走 info-gate.py 三态台账，本脚本只做清单引导）。")
        return 1
    print("PASS — 该场景关键未知信息均已引导")
    print("覆盖边界：本次=引导清单关键词命中（v5.0 起结论性判定走 info-gate.py 三态台账，本脚本只做清单引导）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
