#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage-gate-check.py — 五闸过闸检查器（与 fm-01五闸开发流程.md 逐字对齐）

输入决策上下文文本（评审记录/进展纪要），逐条检查五闸核心项+协作项，
输出每闸 过/未过 + 缺失项 + 关口建议（通过/否决/搁置/重做）。
空上下文 → 全部缺失项列出，退出码 1。

关口建议规则（fm-01 默认规则的可计算子集）：
  文本含否决信号（证伪/战略不符/终止）→ 否决候选
  核心项全过+协作项齐 → 通过
  核心项缺 1-2 → 搁置（写明补齐条件）
  核心项缺 ≥3 → 重做（退回本闸重新准备）
  核心项全过+协作项缺 → 通过（附协作项提醒）

用法:
  python3 scripts/stage-gate-check.py <上下文文件>
  cat 纪要.txt | python3 scripts/stage-gate-check.py -
  python3 scripts/stage-gate-check.py --self
退出码: 0=五闸全过, 1=有未过/缺失, 2=读入错误
"""
import sys, argparse

GATES = {
    "闸1机会输入": {
        "core": {"机会描述与来源": ["机会描述", "谁在什么场景", "机会来源"],
                 "目标用户与使用场景界定": ["目标用户", "使用场景", "目标人群"],
                 "初步竞品扫描": ["竞品扫描", "竞品盘点", "现有解法"]},
        "collab": {"销售与渠道一线反馈": ["渠道反馈", "一线反馈", "电商评论"],
                   "客服与退货问题聚类": ["客服", "退货", "问题聚类"]}},
    "闸2商业论证": {
        "core": {"市场规模估算": ["市场规模", "市场容量", "规模估算"],
                 "目标毛利与成本区间测算": ["毛利测算", "成本区间", "毛利与成本"],
                 "投入产出与回本周期估算": ["回本周期", "投入产出", "ROI"],
                 "主要风险清单与可逆性分级": ["风险清单", "可逆性"]},
        "collab": {"财务口径复核": ["财务复核", "财务口径", "财务确认"],
                   "供应链产能与原料成本区间": ["产能", "原料成本", "供应链确认"]}},
    "闸3概念定义": {
        "core": {"产品概念陈述": ["产品概念", "概念陈述", "价值主张"],
                 "差异化卖点定义": ["差异化", "卖点定义", "凭什么赢"],
                 "目标价格带与成本上限": ["价格带", "成本上限"],
                 "概念测试与原型验证": ["概念测试", "原型验证", "原型测试"]},
        "collab": {"研发可行性结论": ["研发确认", "可行性结论", "研发结论"],
                   "卖点测试结果": ["卖点测试", "文案测试", "市场部测试"]}},
    "闸4开发验证": {
        "core": {"试制品验证结果": ["试制品验证", "试制验证", "原型验证结果"],
                 "成本达成核对": ["成本达成", "实测成本", "成本核对"],
                 "合规与质量风险确认": ["合规", "质量风险", "检测"],
                 "试销或小范围验证计划": ["试销", "小范围验证", "判停线"]},
        "collab": {"批量生产可行性与产能排期": ["批量生产", "量产可行", "产能排期"],
                   "检测标准与合规结论": ["检测标准", "品控", "法务结论"]}},
    "闸5上市复盘": {
        "core": {"上市后复盘会（AAR四问）": ["复盘会", "AAR", "复盘"],
                 "销售与利润对照立项承诺": ["对照立项承诺", "销售与利润对照", "缺口归因"],
                 "假设-结果对照": ["假设-结果对照", "假设对照", "假设清单"],
                 "经验回填": ["经验回填", "回填检查单", "修正项落盘"]},
        "collab": {"动销库存复购反馈": ["动销", "库存反馈", "复购反馈"],
                   "交付良率与成本复盘数据": ["良率", "交付复盘", "成本复盘"]}},
}
VETO_SIGNALS = ["证伪", "战略不符", "终止", "否决"]


def gate_state(text):
    """返回 {gate: {"core_miss":[], "collab_miss":[], "core_n":x, "core_total":y}}"""
    out = {}
    for g, cfg in GATES.items():
        core_miss = [item for item, kws in cfg["core"].items() if not any(k in text for k in kws)]
        collab_miss = [item for item, kws in cfg["collab"].items() if not any(k in text for k in kws)]
        out[g] = {"core_miss": core_miss, "collab_miss": collab_miss,
                  "core_n": len(cfg["core"]) - len(core_miss), "core_total": len(cfg["core"])}
    return out


def suggest(state, text):
    veto = [s for s in VETO_SIGNALS if s in text]
    if veto:
        return "否决候选（信号：%s）" % "/".join(veto)
    n_miss = len(state["core_miss"])
    if n_miss == 0:
        if state["collab_miss"]:
            return "通过（附协作项提醒：%s）" % "/".join(state["collab_miss"])
        return "通过"
    if n_miss <= 2:
        return "搁置（补齐后再议）"
    return "重做（退回本闸重新准备）"


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 五闸过闸检查器（fm-01 对齐）")
    ap.add_argument("input", nargs="?", help="决策上下文文本文件，或 - 读 stdin；空上下文报全部缺失")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        full = ("闸1：机会描述与来源、目标用户与使用场景界定、初步竞品扫描齐；渠道反馈、客服退货聚类已收集。"
                "闸2：市场规模估算、毛利与成本区间测算、回本周期估算、风险清单与可逆性分级齐；财务口径复核、供应链产能确认齐。"
                "闸3：产品概念陈述、差异化卖点定义、目标价格带与成本上限、概念测试与原型验证齐；研发确认、卖点测试齐。"
                "闸4：试制品验证、成本达成核对、合规与质量风险确认、试销计划齐；批量生产可行性与产能排期、检测标准与法务结论齐。"
                "闸5：复盘会AAR、销售与利润对照立项承诺、假设-结果对照、经验回填齐；动销库存复购反馈、交付良率与成本复盘齐。")
        st = gate_state(full)
        empty = gate_state("")
        ok = all(not st[g]["core_miss"] for g in st) and all(len(empty[g]["core_miss"]) == len(GATES[g]["core"]) for g in GATES)
        print("self: 全过样本 %s；空上下文全缺失 %s" % ("PASS✓" if ok else "FAIL✗", "PASS✓" if ok else "FAIL✗"))
        return 0 if ok else 1
    if not a.input:
        ap.print_help()
        return 2
    try:
        text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    except OSError as e:
        print("读入失败: %s" % e)
        return 2
    states = gate_state(text)
    all_pass = True
    lines = []
    for g, st in states.items():
        passed = not st["core_miss"]
        all_pass = all_pass and passed
        sug = suggest(st, text)
        lines.append("%s：核心项 %d/%d%s%s → 关口建议=%s" % (
            g, st["core_n"], st["core_total"],
            "（未过，缺：%s）" % "/".join(st["core_miss"]) if st["core_miss"] else "（过）",
            "；协作项缺：%s" % "/".join(st["collab_miss"]) if st["collab_miss"] else "",
            sug))
    if a.json:
        import json
        print(json.dumps(states, ensure_ascii=False, indent=2))
    else:
        for l in lines:
            print(l)
        if not all_pass:
            print("结论：FAIL — 存在未过闸口（核心项缺失不得通过，最多搁置；见 fm-01 默认规则）")
        else:
            print("结论：PASS — 五闸核心项齐全")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
