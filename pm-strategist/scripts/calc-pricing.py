#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""calc-pricing.py — pm-strategist 算账器（总案 v2.1 §2.7 闸口 H + B5）

涉盈亏/毛利/弹性/促销费效的决策点**必须调用**（闸口 H 全强制）。
含渠道费用与返利扣减层（B5）：净价 = 牌价 − 渠道费用 − 返利，
对照"未扣渠道层"的毛利，显式给出虚高幅度（防毛利系统性高估 15-25%）。

伪精度护栏 3 条：
  1. 缺输入拒算：必需输入（--price/--unit-cost/--fixed-cost）缺失 → 列出缺口，退出码 2，不给任何数字
  2. 敏感性标注：所有结果为区间估计，附敏感性区间说明，不是精确预测
  3. 取整：金额取整到元，比率保留 1 位小数

用法:
  python3 scripts/calc-pricing.py --price 59 --unit-cost 18 --fixed-cost 300000 \\
      --channel-fee-rate 0.25 --rebate-rate 0.08 --volume 20000 [--elasticity -1.5]
  python3 scripts/calc-pricing.py --demo      # 示例占位数据演示
  python3 scripts/calc-pricing.py --self
退出码: 0=算完; 1=输入非法; 2=缺必需输入（拒算）
"""
import sys, json, argparse, math

REQUIRED = ["price", "unit_cost", "fixed_cost"]


def parse_rate(v):
    """25 / 0.25 都收；越界报错。"""
    x = float(v)
    if x > 1:
        x = x / 100.0
    if not (0.0 <= x <= 1.0):
        raise ValueError("费率应在 0-1（或 0-100 百分数）之间，当前 %s" % v)
    return x


def money(x):
    return "{:,}".format(int(round(x)))


def pct(x):
    return "%.1f%%" % (x * 100)


def check_missing(args):
    return [k for k in REQUIRED if getattr(args, k) is None]


def compute(price, unit_cost, fixed_cost, fee_rate=0.0, rebate_rate=0.0,
            volume=None, elasticity=None, scen_pct=0.2, price_pct=0.1):
    channel_fee = price * fee_rate
    rebate = price * rebate_rate
    net = price - channel_fee - rebate
    gross_naive = price - unit_cost
    unit_margin = net - unit_cost
    inflated = gross_naive - unit_margin
    inflation_pct = (inflated / gross_naive) if gross_naive > 0 else 0.0
    margin_rate = (unit_margin / net) if net > 0 else 0.0
    out = {
        "① 净价拆解（B5 渠道扣减层）": "",
        "牌价/件": money(price),
        "渠道费用/件（费率%s）" % pct(fee_rate): "−" + money(channel_fee),
        "返利/件（费率%s）" % pct(rebate_rate): "−" + money(rebate),
        "净价/件": money(net) + "（渠道扣减合计占比 %s）" % pct(fee_rate + rebate_rate),
        "② 毛利结构": "",
        "未扣渠道层的毛利/件": money(gross_naive) + "（虚高口径）",
        "真实毛利/件（按净价）": money(unit_margin),
        "毛利虚高幅度": pct(inflation_pct) + "——只看牌价算毛利会高估这么多（B5 防高估）",
        "毛利率（按净价）": pct(margin_rate),
        "③ 盈亏平衡": "",
    }
    if unit_margin > 0:
        out["盈亏平衡量"] = "{:,} 件（固定成本 {:,} 元 ÷ 单件毛利 {} 元）".format(
            int(math.ceil(fixed_cost / unit_margin)), int(fixed_cost), money(unit_margin))
    else:
        out["盈亏平衡量"] = "算不出：净价不覆盖单位成本（卖一件亏一件）——先修结构再谈量"
    if volume:
        base = volume * unit_margin - fixed_cost
        out["④ 三情景（销量 ±%s）" % pct(scen_pct)] = ""
        out["月利润（基准 %s 件）" % "{:,}".format(int(volume))] = money(base) + " 元"
        for name, k in (("乐观", 1 + scen_pct), ("悲观", 1 - scen_pct)):
            v = volume * k
            out["  %s（%s 件）" % (name, "{:,}".format(int(v)))] = "月利润 " + money(v * unit_margin - fixed_cost) + " 元"
        if elasticity is not None:
            out["⑤ 弹性敏感（价格 ±%s，弹性 %.1f）" % (pct(price_pct), elasticity)] = ""
            for dp in (price_pct, -price_pct):
                new_price = price * (1 + dp)
                new_net = new_price * (1 - fee_rate - rebate_rate)
                new_margin = new_net - unit_cost
                new_vol = volume * (1 + elasticity * dp)
                out["  价格 %+d%%：净价/件 %s，毛利/件 %s，销量反推 %s 件，月利润 %s 元" % (
                    round(dp * 100), money(new_net), money(new_margin),
                    "{:,}".format(int(new_vol)), money(new_vol * new_margin - fixed_cost))] = ""
        else:
            out["⑤ 弹性敏感"] = "未提供 --elasticity：价格弹性反推缺输入，按护栏1不编数（可只看④销量情景）"
    out["敏感性标注（护栏2）"] = "以上全部为区间估计：价格±%s / 销量±%s 内结论稳健才可入 DR；非精确预测" % (pct(price_pct), pct(scen_pct))
    return out


def render(out):
    lines = []
    for k, v in out.items():
        if v == "":
            lines.append(k)
        else:
            lines.append("  %s：%s" % (k, v)) if k.startswith("  ") else lines.append("%s：%s" % (k, v))
    return "\n".join(lines)


def self_test():
    out = compute(59, 18, 300000, 0.25, 0.08, volume=20000, elasticity=-1.5)
    ok = True
    def chk(name, cond):
        nonlocal ok
        if not cond:
            ok = False
            print("  ❌ " + name)
    net = 59 * (1 - 0.25 - 0.08)
    chk("净价含渠道扣减（59→%.2f）" % net, net < 59)
    chk("真实毛利 < 未扣渠道层毛利（B5）", (net - 18) < (59 - 18))
    chk("毛利虚高幅度>0", ((59 - 18) - (net - 18)) / (59 - 18) > 0)
    chk("盈亏平衡量为正整数", int(out["盈亏平衡量"].split(" 件")[0].replace(",", "")) > 0)
    chk("取整护栏（money(59.4)=59）", money(59.4) == "59")
    chk("三情景有数字", "月利润" in "".join(out.keys()) or any("月利润" in k for k in out))
    # 护栏1：缺输入拒算
    class A: pass
    a = A(); a.price = None; a.unit_cost = 18; a.fixed_cost = None
    miss = check_missing(a)
    chk("缺输入拒算（缺 %s）" % "/".join(miss), set(miss) == {"price", "fixed_cost"})
    print("self: calc-pricing 渠道扣减层/护栏/取整 %s" % ("PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 算账器（闸口H：盈亏平衡/毛利含渠道费用返利层/三情景/弹性/伪精度护栏3条）")
    ap.add_argument("--price", type=float, help="牌价/件（必需）")
    ap.add_argument("--unit-cost", dest="unit_cost", type=float, help="单位成本/件（必需）")
    ap.add_argument("--fixed-cost", dest="fixed_cost", type=float, help="固定成本（必需，如月度）")
    ap.add_argument("--channel-fee-rate", dest="channel_fee_rate", default="0", help="渠道费用率（0-1 或百分数，默认0）")
    ap.add_argument("--rebate-rate", dest="rebate_rate", default="0", help="返利率（0-1 或百分数，默认0）")
    ap.add_argument("--volume", type=float, help="月销量（给三情景/月利润）")
    ap.add_argument("--elasticity", type=float, help="价格弹性（负值，如 -1.5；不给则跳过弹性反推）")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    ap.add_argument("--demo", action="store_true", help="示例占位数据演示")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.demo:
        a.price, a.unit_cost, a.fixed_cost = 59, 18, 300000
        a.channel_fee_rate, a.rebate_rate, a.volume, a.elasticity = "0.25", "0.08", 20000, -1.5
        print("（以下为示例占位数据演示，非任何真实业务数字）")
    miss = check_missing(a)
    if miss:
        print("拒算（护栏1 缺输入拒算）——缺必需输入：%s" % "、".join(
            {"price": "--price 牌价", "unit_cost": "--unit-cost 单位成本", "fixed_cost": "--fixed-cost 固定成本"}[k] for k in miss))
        print("补齐后再算；不给任何编造数字。")
        return 2
    try:
        fee = parse_rate(a.channel_fee_rate)
        reb = parse_rate(a.rebate_rate)
        if a.price <= 0 or a.unit_cost <= 0 or a.fixed_cost <= 0:
            raise ValueError("价格/成本/固定成本必须为正数")
    except ValueError as e:
        print("输入非法：%s" % e)
        return 1
    out = compute(a.price, a.unit_cost, a.fixed_cost, fee, reb,
                  volume=a.volume, elasticity=a.elasticity)
    if a.json:
        out2 = {k: v for k, v in out.items() if v != ""}
        print(json.dumps(out2, ensure_ascii=False, indent=1))
    else:
        print(render(out))
        print("（取整护栏3：金额取整到元、比率 1 位小数；结果入 DR 时请连同敏感性标注一起写）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
