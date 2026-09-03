#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_output.py — pm-strategist 输出质量总校验（v3.0）

对一份 skill 完整输出文本做机器可查项校验：
5场景路由+通用组件+行为准则5条痕迹+建议6要素+决策记录9字段+可逆性分级+收敛终端；
缺项报具体缺什么，任一缺项退出码 1。

用法:
  python3 scripts/check_output.py <输出文本文件>
  cat 输出.txt | python3 scripts/check_output.py -
  python3 scripts/check_output.py --mode dr <输出文本文件>   # 仅校验 DR 结构不变量
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
# ① B 类记忆层术语机器断言（术语浮层表 B 类：对用户输出禁甩流程黑话，须白话改写）
# 术语表 A 类行业词（动销率/费比/毛利等）不禁——科普解释是术语表合法职能；
# 禁的是"记忆/流程内部词"裸用于对用户输出（决策情境/披露分层/回显确认/升级通道/
# 记忆判据/同词异层/身份层 = 包内机制名；待固化/待补采/确认戳 = 记忆层技术词）。
BANLIST = ["决策情境", "披露分层", "回显确认", "升级通道", "记忆判据", "同词异层",
           "身份层", "待固化", "待补采", "确认戳"]
# D'-③ 反方意见双要素：①具体条件（什么事实成立）②可反驳出口（推翻/失效/推翻条件=…）
# 只写连接词（"如果可能市场不好吧"）＝稻草人，等于没有反方——两要素缺一即拦。
CON_RE = r"如果|若|一旦|假如|前提是|除非|当.{0,6}(时|成立|发生|出现)|在.{0,10}情况下"
# ①条件句式无"若/如果"但用"则/将/导致"连接（如"竞品同步降价则渗透策略失效"）
TRIGGER_RE = r"则|就会|将会|导致|使得|造成|引发|即|一.{0,4}就"
# ②出口·强失效语义（本决定/方案失效）
FALSIFY_STRONG = (r"推翻|证伪|不成立|失效|站不住|需重估|需重做|重算|落空|白做|白费|前功尽弃|"
                  r"泡汤|打水漂|适得其反|得不偿失|弄巧成拙|反噬|不再成立|改变.{0,4}结论|"
                  r"推翻条件|什么数据|什么条件|什么信号")
# ②出口·决定否定语义（"砍错/做错"= 本决定被证伪的自然表达）
FALSIFY_NEG = r"砍错|做错|误判|误杀|错杀|判断失误|决策失误|证明.{0,6}错|说明.{0,6}错|压根不该|不该砍|不该做"
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
    # ---- D' 质量下限 4+2 断言（总案 §2.7/P1-B：修"绿灯幻觉"，保质量下限非判断力） ----
    opt = field_value(text, "选项：") or ""
    if opt and ("不做" not in opt and "维持现状" not in opt):
        problems.append("D'-① 选项未含「不做/维持现状」对照项（不做是每个决策的真实备选）")
    dec = field_value(text, "决定：") or ""
    if "已定" in (field_value(text, "状态：") or "") and "用户拍板：" not in dec:
        problems.append("D'-② 状态已定但决定字段无「用户拍板：」原文（闸口 B：无拍板原文不得写已定）")
    con = (field_value(text, "反方意见：") or "").strip()
    if not con or con.startswith("无"):
        problems.append("D'-③ 反方意见为空/「无」——反方非空且必须具体到可反驳")
    else:
        # 三通道判定：条件句式/因果句式 × 出口（强失效或决定否定），任一组合满足即非稻草人
        out_ok = bool(re.search(FALSIFY_STRONG, con)) or bool(re.search(FALSIFY_NEG, con))
        ok_cond = bool(re.search(CON_RE, con)) and out_ok
        ok_trigger = bool(re.search(TRIGGER_RE, con)) and out_ok
        if not (ok_cond or ok_trigger):
            miss = []
            if not (bool(re.search(CON_RE, con)) or bool(re.search(TRIGGER_RE, con))):
                miss.append("①具体条件（若/一旦/竞品降价则…，什么事实成立）")
            if not out_ok:
                miss.append("②可反驳出口（本决定 失效/被推翻/砍错/做错，或推翻条件=拿到<什么数据>）")
            problems.append("D'-③ 反方意见是稻草人（缺 " + "、".join(miss) + "）——"
                            "模板：若<什么事实成立>，则本决定<失效/需重估/砍错>；推翻条件=拿到<什么数据>｜"
                            "例：若渠道合约含条码数门槛，砍SKU将导致进场筹码下降；推翻条件=拿到各SKU条码贡献的渠道合约条款｜"
                            "可过写法：①若…则砍错 ②竞品降价则渗透失效 ③推翻条件=拿到…数据")
    riskv = (field_value(text, "风险：") or "").strip()
    if riskv:
        segs = [x for x in re.split(r"[；;\n]", riskv) if x.strip()]
        if segs and all("未命中" in x for x in segs):
            problems.append("D'-④ 风险全部「未命中」——至少 1 个真实风险点，或诚实论证为何全未命中")
    basis = (field_value(text, "依据：") or "").strip()
    if basis and not re.search(r"ref-0[1-6]|fm-0[1-6]", basis):
        problems.append("D'-⑤ 依据缺 ref/fm 引用格式（应标注 ref-0X/fm-0X 哪条）")
    return problems


def check_full(text):
    """完整输出总校验：路径声明+场景+可逆性+建议6要素+风险6维+DR9+收敛终端+B类标注。"""
    problems = []
    # 0 B 类记忆层术语机器断言：输出文本裸用流程黑话 → 拦（对用户须白话改写）
    hit_ban = [w for w in BANLIST if w in text]
    if hit_ban:
        problems.append("B 类记忆层术语裸用于对用户输出（须白话改写，禁甩流程黑话）：%s —— "
                        "例：说\"这次退不退得回/该问多细\"而非\"披露分层\"；说\"记进长期档案前我会念给你确认\"而非\"回显确认\""
                        % "/".join(hit_ban))
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
    zeroq = """# DR-20260902-zero
- 问题：示例占位
- 选项：A方案
- 决定：就这么干
- 依据：感觉不错
- 反方意见：无
- 风险：法规：未命中；市场：未命中；竞争：未命中；供应链：未命中；财务：未命中；组织：未命中
- 假设清单：
无——输入已全部确认
- 复盘日期：2026-12-31
- 状态：已定
"""
    zero_problems = check_dr(zeroq)
    zero_ok = len(zero_problems) >= 4
    # 稻草人反方必拦（"如果…吧"只有连接词、无可反驳出口）
    straw = good.replace("- 反方意见：竞品若同步降价则渗透逻辑失效——看竞品周跟踪",
                         "- 反方意见：如果可能市场不好吧")
    straw_caught = any("D'-③" in p for p in check_dr(straw))
    # B 类记忆层术语裸用于对用户输出必拦
    jargon = good.replace("权衡分析：对毛利/销量/渠道接受度对账",
                          "权衡分析：对毛利/销量/渠道接受度对账（含披露分层判定）")
    jargon_caught = any("B 类记忆层术语" in p for p in check_full(jargon))
    no_false = not any("B 类记忆层术语" in p for p in check_full(good))
    print("self: 完整好样本 %s（期望PASS）；坏样本拦截 %d 处（期望≥3）；DR结构 %s；零质量DR拦截 %d 项（期望≥4）%s；稻草人反方拦截 %s；禁词拦截 %s（好样本无误报 %s）" % (
        "PASS✓" if ok else "FAIL✗", len(check_full(bad)), "PASS✓" if dr_ok else "FAIL✗",
        len(zero_problems), "✓" if zero_ok else "✗",
        "✓" if straw_caught else "✗ 未拦住（判定失效）",
        "✓" if jargon_caught else "✗ 未拦住",
        "✓" if no_false else "✗ 误报"))
    return ok and caught and dr_ok and zero_ok and straw_caught and jargon_caught and no_false


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
    print("PASS — 5场景/可逆性/建议6要素/风险6维度/DR9字段/D'质量下限(4+2)/收敛终端 齐全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
