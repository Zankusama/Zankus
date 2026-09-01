#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_output.py — pm-strategist 输出质量总校验（v3.0）

对一份 skill 完整输出文本做机器可查项校验：
5场景路由+通用组件+行为准则5条痕迹+建议6要素+决策记录9字段+可逆性分级+收敛终端；
缺项报具体缺什么，任一缺项退出码 1。

用法:
  python3 scripts/check_output.py <输出文本文件>
  cat 输出.txt | python3 scripts/check_output.py -
  python3 scripts/check_output.py --mode dr <DR文本>   # 仅校验 DR 结构不变量
  python3 scripts/check_output.py --self
退出码: 0=PASS, 1=有缺项, 2=用法/读入错误
本脚本只读文本，不写盘。
"""
import sys, re, argparse

SCENES = ["S1", "S2", "S3", "S4", "S5", "C类"]
DR_FIELDS = ["问题：", "选项：", "决定：", "依据：", "反方意见：", "风险：", "假设清单：", "复盘日期：", "状态："]
DR_STATUS = ["草案", "已定", "复盘", "关闭"]
RISK_DIMS = {
    "法规": ["法规", "合规", "宣称", "备案", "监管", "标签", "法务"],
    "市场": ["市场", "需求", "趋势", "季节", "渗透"],
    "竞争": ["竞争", "竞品", "对手", "替代", "跟价"],
    "供应链": ["供应链", "产能", "原料", "库存", "交期", "备货", "断货"],
    "财务": ["财务", "毛利", "成本", "回本", "现金流", "预算", "盈亏"],
    "组织": ["组织", "人力", "团队", "人员", "排产", "培训"],
}
B_TAGS = {"S4": "最终定价决策需跨部门确认", "S5": "最终上市决策需跨部门确认"}
ADVICE6 = {
    "选项(含不做/维持现状)": r"选项|方案",
    "推荐倾向": r"推荐|倾向",
    "权衡分析": r"权衡|对账|得失|利弊",
    "不做项说明": r"不做|放弃|不做什么",
    "风险": r"风险",
    "数据需求引导": r"数据需求|补.{0,4}数据|需要.{0,4}数据|取数",
}


def field_value(text, field):
    i = text.find("- " + field)
    if i < 0:
        return None
    seg = text[i + len("- " + field):]
    j = seg.find("\n- ")
    return seg[:j].strip() if j >= 0 else seg.strip()


def check_dr(text):
    """DR9结构不变量校验，返回缺项清单。"""
    problems = []
    if not re.search(r"#\s*DR-\d{8}", text):
        problems.append("缺 DR 标题（# DR-YYYYMMDD-<slug>）")
    for f in DR_FIELDS:
        if ("- " + f) not in text:
            problems.append("缺字段 - " + f)
    if problems:
        return problems
    if not field_value(text, "选项："):
        problems.append("选项为空（应≥2个，含不做/维持现状）")
    if not field_value(text, "决定："):
        problems.append("决定为空（拍板原文或推荐倾向）")
    st = field_value(text, "状态：") or ""
    if not any(x in st for x in DR_STATUS):
        problems.append("状态非法（应为 草案/已定/复盘/关闭 之一，当前: %s）" % st[:20])
    d = field_value(text, "复盘日期：") or ""
    if d and not re.search(r"\d{4}-\d{2}-\d{2}", d):
        problems.append("复盘日期格式应为 YYYY-MM-DD（当前: %s）" % d[:20])
    i = text.find("- 假设清单：")
    seg = text[i + len("- 假设清单："):]
    k = seg.find("- 复盘日期：")
    if k >= 0:
        seg = seg[:k]
    core = seg.strip()
    if not core or core.startswith("无"):
        pass  # 显式"无"合法
    else:
        lines = [l for l in core.splitlines() if l.strip()]
        bad = [l for l in lines if not l.strip().startswith("⚠️")]
        if bad:
            problems.append("假设清单 %d 条未带 ⚠️ 前缀（首条: %s）" % (len(bad), bad[0].strip()[:30]))
    return problems


def check_full(text):
    """完整输出总校验：路径声明+场景+可逆性+建议6要素+风险6维+DR9+收敛终端+B类标注。"""
    problems = []
    # 1 路径声明（CRITICAL 首条回复声明路径）
    if "路径声明" not in text:
        problems.append("缺路径声明（第一条回复应含「路径声明：验证轨|路由轨 | 场景=… | 可逆性=… | 主查=…」）")
    # 2 场景路由痕迹
    scene = None
    m = re.search(r"场景\s*[=:＝]\s*(S[1-5]|C类|待路由)", text)
    if m:
        scene = m.group(1)
    else:
        hit = [s for s in SCENES if s in text]
        scene = hit[0] if hit else None
    if not scene:
        problems.append("缺场景标记（应含 场景=S1..S5|C类|待路由）")
    # 3 可逆性分级
    rev = re.search(r"[🟢🔴🟡]", text)
    if not rev:
        problems.append("缺可逆性分级（应含 🟢可逆/🔴不可逆/🟡拿不准 之一）")
    # 4 建议6要素
    for name, pat in ADVICE6.items():
        if not re.search(pat, text):
            problems.append("建议6要素缺项：%s" % name)
    # 5 风险6维度覆盖（未命中需显式声明"未命中"）
    missing_dims = []
    for dim, kws in RISK_DIMS.items():
        if not any(k in text for k in kws):
            missing_dims.append(dim)
    if missing_dims:
        problems.append("风险6维度未覆盖且未见「未命中」声明：%s" % "/".join(missing_dims))
    # 6 行为准则⑤不确定标注痕迹
    if ("不确定" not in text) and ("待验证" not in text) and ("假设·待验证" not in text) and ("⚠️" not in text):
        problems.append("未见不确定性标注痕迹（应含 不确定/待验证 或 ⚠️ 假设·待验证）")
    # 7 DR9 + 收敛终端
    problems.extend(check_dr(text))
    if "- 状态：" in text:
        tail = text[text.rfind("- 状态："):]
        rest = tail[tail.find("\n"):] if "\n" in tail else ""
        # B类跨部门确认标注允许跟在 DR 之后
        rest_lines = [l for l in rest.splitlines() if l.strip() and "需跨部门确认" not in l]
        if rest_lines:
            problems.append("收敛终端：DR 之后仍有未归入记录的正文（每次输出应以决策记录9字段收尾）")
    # 8 B类标注
    if scene in B_TAGS and B_TAGS[scene] not in text:
        problems.append("B类场景（%s）缺跨部门确认标注：%s…" % (scene, B_TAGS[scene]))
    return problems


def self_test():
    good = """路径声明：验证轨 | 场景=S4 定价与盈利 | 可逆性=🔴不可逆 | 主查=ref-04定价与盈利.md
1. 选项：中价格带上沿 / 低价渗透 / 维持现价（含不做/维持现状）
2. 推荐倾向：中价格带上沿
3. 权衡分析：对毛利/销量/渠道接受度对账
4. 不做项说明：不做超低价（伤定位）
5. 风险：法规未命中；市场（季节波动）；竞争（跟价）；供应链（备货交期）；财务（毛利）；组织（培训）
6. 数据需求引导：补竞品成交价与支付意愿数据
# DR-20260831-p2-price
- 问题：[示例占位]A品上市定什么价
- 选项：中价格带上沿 / 低价渗透 / 维持现价（含不做/维持现状）
- 决定：推荐中价格带上沿
- 依据：ref-04 3C定价与价格带分析
- 反方意见：竞品若同步降价则渗透逻辑失效——看竞品周跟踪
- 风险：法规未命中；市场（季节波动）；竞争（跟价）；供应链（备货交期）；财务（毛利）；组织（培训）
- 假设清单：
⚠️ 假设·待验证：目标人群价格敏感度中等
- 复盘日期：2026-12-31
- 状态：草案
⚠️ 最终定价决策需跨部门确认（财务/销售/渠道/管理层）"""
    bad = good.replace("- 状态：草案", "- 状态：搞定").replace("推荐倾向", "偏好").replace("🟢", "").replace("🔴", "").replace("🟡", "")
    bad = bad.replace("3. 权衡分析：对毛利/销量/渠道接受度对账", "3. 主观感觉：应该不错").replace("6. 数据需求引导：补竞品成交价与支付意愿数据", "6. 后续：再看")
    ok = not check_full(good)
    caught = len(check_full(bad)) >= 3
    dr_ok = not check_dr(good)
    print("self: 完整好样本 %s（期望PASS）；坏样本拦截 %d 处（期望≥3）；DR结构 %s" % (
        "PASS✓" if ok else "FAIL✗", len(check_full(bad)), "PASS✓" if dr_ok else "FAIL✗"))
    return ok and caught and dr_ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 输出质量总校验（缺项报具体，退出码1）")
    ap.add_argument("input", nargs="?", help="输出文本文件路径，或 - 读 stdin")
    ap.add_argument("--mode", choices=["full", "dr"], default="full", help="full=完整输出总校验；dr=仅DR结构")
    ap.add_argument("--self", action="store_true", help="内置样本自检")
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
    problems = check_dr(text) if a.mode == "dr" else check_full(text)
    if problems:
        print("FAIL — 缺 %d 项：" % len(problems))
        for x in problems:
            print("  ❌ " + x)
        return 1
    print("PASS — 5场景/可逆性/建议6要素/风险6维度/DR9字段/收敛终端 齐全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
