#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scene-router.py — pm-strategist 决策原语路由器（教练模式，总案 v2.1 §2.2/§2.3）

判定依据从「用户怎么说（词）」改为「决策是什么（结构）」：任何 PM 决策 = 动作原语 × 对象原语。

设计权衡（C4，显式承认）：语义抽取回到 AI；本脚本做**确定性校验**——
动作×对象原语合法性 + 25 格矩阵查表 + 四态出口分流 + 复合决策分解建议。
脚本不假装做语义判断：它把归位拦在合法格子里，并透出归位理由供闸口 A 确认。

动作原语消歧（AI 抽取规则，与 SKILL.md 同源）：
  增=引入此前不存在的东西（新立项/新 SKU/新规格/新渠道/新价格点）
  删=移除已存在的东西（砍品/退市/撤价/撤渠道）
  改=原地变更已存在的东西（SKU 数不变）
  择=已摆上桌的选项间做 A 还是 B 型取舍；"要不要X"不默认归择：
     X 是具体动作物→按 X 的动作原语；抽象机会型"值不值得投"才归择
  判=对现状出评估结论，不改变任何东西
对象判定：取"决策直接改动的东西"，不取"被影响的维度"（"降价伤不伤品牌"对象=价格体系）。
规格/包装消歧（F3）：价格点动机（小规格/入门价/量贩装）→价格体系；
  变体丰富动机（礼盒/限定/季节款）→现有单品；动机不明→双候选，闸口 A 透出让用户定。

四态出口：归位成功 / 澄清（原语缺失，附定向补问） / 跨域拆解（对象枚举外，如品牌级） / C类（非决策）

v5.0 新增两种调用形态（RC-3 双判定源治理）：
  --action/--object（AI 判定模式）：传入 AI 抽取的原语 → 跳过全部词法抽取，只做
    合法性校验 + 矩阵查表 + 返回格子定义。真正落实「AI 判、脚本校验」。
  --arbitrate（仲裁模式）：AI 判定 + 用户问题 → 跑词法候选，双源对照。
    一致 → 直接归位；不一致 → divergence=true，输出结构化差异对照 + 各自判据，
    由 AI 用人话呈现给用户选，禁止 AI 自行选定后只提一句。

用法:
  python3 scripts/scene-router.py "新品怎么上市？"
  echo "问题" | python3 scripts/scene-router.py -
  python3 scripts/scene-router.py --json "品牌要不要重新定位"
  python3 scripts/scene-router.py --action 判 --object 现有单品            # AI 判定模式
  python3 scripts/scene-router.py --action 判 --object 现有单品 --arbitrate "这个品卖不动怎么办" --json
  python3 scripts/scene-router.py --self
退出码: 0=产出定义路由（归位成功/跨域拆解/C类/仲裁完成含 divergence）; 1=需澄清（原语缺失或非法）; 2=用法错误
"""
import sys, json, argparse, re

SCENES = {
    "S1": {"name": "S1 新品立项与产品定义", "cat": "A", "refs": "ref-01新品立项与产品定义.md+fm-01五闸开发流程.md"},
    "S2": {"name": "S2 产品线组合规划", "cat": "A", "refs": "ref-02产品线组合规划.md+fm-03优先级排序.md"},
    "S3": {"name": "S3 产品生命周期与迭代", "cat": "A", "refs": "ref-03产品生命周期与迭代.md+fm-04复盘框架.md"},
    "S4": {"name": "S4 定价与盈利", "cat": "B", "refs": "ref-04定价与盈利.md"},
    "S5": {"name": "S5 上市GTM策略", "cat": "B", "refs": "ref-05上市GTM策略.md"},
}

# 25 格矩阵（总案 §2.2 逐格，无空格）：(动作, 对象) -> (场景id, 格子说明)
MATRIX = {
    ("增", "新品"): ("S1", "立项"),
    ("增", "产品组合"): ("S2", "补SKU"),
    ("增", "现有单品"): ("S2", "衍生规格引入★"),
    ("增", "价格体系"): ("S4", "规格价格架构★"),
    ("增", "渠道/上市"): ("S5", "上市方案设计★"),
    ("删", "新品"): ("S1", "砍项目†（上市前=Gate-Kill→S1；上市后砍新品项=组合修剪→S2）"),
    ("删", "产品组合"): ("S2", "砍品"),
    ("删", "现有单品"): ("S3", "退市清退"),
    ("删", "价格体系"): ("S4", "撤价项"),
    ("删", "渠道/上市"): ("S5", "撤渠道"),
    ("改", "新品"): ("S1", "产品定义"),
    ("改", "产品组合"): ("S2", "组合调优"),
    ("改", "现有单品"): ("S3", "迭代焕新"),
    ("改", "价格体系"): ("S4", "调价"),
    ("改", "渠道/上市"): ("S5", "渠道适配"),
    ("择", "新品"): ("S1", "值不值得做"),
    ("择", "产品组合"): ("S2", "资源倾斜"),
    ("择", "现有单品"): ("S3", "迭代还是退市"),
    ("择", "价格体系"): ("S4", "定价方案"),
    ("择", "渠道/上市"): ("S5", "先铺哪"),
    ("判", "新品"): ("S1", "机会评估"),
    ("判", "产品组合"): ("S2", "结构诊断"),
    ("判", "现有单品"): ("S3", "卖不动诊断"),
    ("判", "价格体系"): ("S4", "算账验毛利"),
    ("判", "渠道/上市"): ("S5", "渠道现状"),
}
OBJECTS = ["新品", "产品组合", "现有单品", "价格体系", "渠道/上市"]

# 词法层（确定性校验用，AI 语义抽取不受此限）
LAUNCH_KW = ["上市", "首发", "铺货", "铺哪", "上线", "GTM", "渠道铺开", "铺开"]
BRAND_KW = ["品牌重新定位", "重新定位", "品牌架构", "品牌定位"]
SPEC_PRICE_KW = ["小规格", "入门价", "入门装", "量贩", "三连包"]
SPEC_VARIANT_KW = ["礼盒", "限定", "季节款", "新包装", "包装换新"]
KILL_KW = ["砍掉", "砍", "退市", "清退", "淘汰", "撤掉", "撤", "停掉", "下架", "裁掉"]
PRICE_KW = ["定价", "涨价", "降价", "调价", "定多少价", "什么价", "价格", "价盘"]
COMBO_KW = ["产品线", "产品组合", "组合", "SKU", "sku", "品类结构", "产品结构"]
SINGLE_KW = ["单品", "这个品", "现有产品", "老品", "成熟品", "这个产品"]
_X_PIN = re.compile(r"([0-9A-Za-z\u4e00-\u9fa5])品")


def _is_single(q):
    """判定 q 是否锁定"现有单品"对象：显式单品词 / 单字+品（A品/B品/老品），排除 产品/新品/单品/商品/样品/礼品 等组合词。"""
    if _hit(SINGLE_KW, q):
        return True
    m = _X_PIN.search(q)
    return bool(m) and m.group(1) not in "产新商单样礼"
NEW_KW = ["新品", "新产品", "新品牌", "新项目", "立项", "机会"]
INCREASE_KW = ["推出", "出个", "出小", "出礼", "增加", "延伸", "开发", "引入", "预算投", "投"]
ADJUST_KW = ["调整", "优化", "升级", "迭代", "焕新", "改款", "变更"]
PICK_KW = ["选哪个", "先哪个", "优先做哪个", "取舍", "二选一", "还是", "倾斜", "先做哪个", "留哪个", "先砍哪个"]
JUDGE_KW = ["值不值", "该不该", "要不要", "能不能", "怎么办", "诊断", "评估", "怎么样", "如何"]
SELLBAD_KW = ["卖不动", "动销差", "卖不好"]
RISK_REVIEW_KW = ["风险", "复盘", "生意三问", "三问", "帮我看", "帮我想", "提醒我"]
DECISION_MARKERS = ["要不要", "该不该", "怎么", "值不值", "哪个", "多少", "怎么办", "帮我看", "帮我想",
                    "决策", "建议", "如何", "评估", "定什么", "定多少", "怎么样"]


def _hit(kws, q):
    return [k for k in kws if k in q]


def _extract_segment(q):
    """对一段（无标点）问题做规则级联抽取，返回 [(动作, 对象, 理由)]。"""
    pairs = []
    actions, objects = set(), set()
    notes = []
    # R1 品牌级（对象枚举外 → 跨域拆解出口）
    if _hit(BRAND_KW, q):
        return [("改" if ("重新定位" in q or "品牌定位" in q or "品牌架构" in q) else "改",
                 "品牌", "对象枚举外：决策直接改动的对象是品牌本身（战略本体）→ 跨域拆解出口")]
    # R2 上市/渠道（新品为主语时对象=渠道/上市，符合对象判定规则：取直接改动的东西）
    if _hit(LAUNCH_KW, q):
        act = "删" if _hit(KILL_KW, q) and ("撤" in q) else "增"
        if "先铺哪" in q or "铺哪些" in q:
            act = "择"
        objects.add("渠道/上市"); actions.add(act)
        notes.append("上市/铺货语境 → 对象=渠道/上市（新品为主语，对象取直接改动的上市方案）")
    # R3 规格/包装消歧（F3）
    sp, sv = _hit(SPEC_PRICE_KW, q), _hit(SPEC_VARIANT_KW, q)
    if sp and sv:
        return [("?", "?", "规格动机不明：价格点动机（S4）与变体丰富动机（S2）双候选 → 闸口 A 透出，请用户定")]
    if sp:
        objects.add("价格体系"); notes.append("价格点管理动机（小规格/入门价/量贩）→ 对象=价格体系")
    if sv:
        objects.add("现有单品"); notes.append("变体丰富动机（礼盒/限定/季节款）→ 对象=现有单品（line extension）")
    # R4 价格
    if _hit(PRICE_KW, q):
        objects.add("价格体系")
        if _hit(["涨价", "降价", "调价"], q):
            actions.add("改")
        elif "定多少价" in q or "什么价" in q or "定价" in q:
            actions.add("择")
    # R5 砍/退市
    if _hit(KILL_KW, q):
        actions.add("删")
        if _hit(COMBO_KW, q):
            objects.add("产品组合")
        elif _is_single(q):
            objects.add("现有单品")
        elif "项目" in q:
            objects.add("新品")
        elif "价格" in q or "价" in q:
            objects.add("价格体系")
        elif "渠道" in q:
            objects.add("渠道/上市")
        elif not objects:
            objects.add("产品组合"); notes.append("砍/退市未指明层级 → 默认按产品组合（组合修剪），闸口 A 确认")
    # R6 组合取舍
    if _hit(PICK_KW, q) and _hit(COMBO_KW, q):
        actions.add("择"); objects.add("产品组合")
    # R7 现有单品（迭代/卖不动）
    if _hit(SELLBAD_KW, q):
        actions.add("判")
        if not objects:
            objects.add("现有单品")
        notes.append("卖不动诊断 → 判×现有单品（S3）")
    if _hit(ADJUST_KW, q):
        actions.add("改")
        if not objects:
            objects.add("现有单品")
    if _is_single(q) and not (sp or sv):
        objects.add("现有单品")
    # R7b 现有单品二选一（F3 择兜底：迭代还是退市 → 择×现有单品 S3；仅已锁定现有单品且为"还是/二选一"取舍）
    if ("还是" in q or "二选一" in q) and objects == {"现有单品"}:
        actions = {"择"}
    # R8 新品/机会
    if _hit(NEW_KW, q) and "渠道/上市" not in objects:
        objects.add("新品")
        if "立项" in q or "值不值" in q or "该不该" in q:
            actions.add("择" if "该不该" in q or "值不值" in q else "增")
    # R8b 渠道显式提及（对象补齐；动作只认 投/进/铺/开拓 的明确语境，不强塞默认动作）
    if "渠道" in q and "渠道/上市" not in objects:
        objects.add("渠道/上市")
        if _hit(["投", "铺", "开拓", "进"], q) and not ({"增", "删", "改", "择", "判"} & actions):
            actions.add("增")
    # R9 动作兜底
    if _hit(INCREASE_KW, q) and not ({"增", "删", "改", "择", "判"} & actions):
        actions.add("增")
    if _hit(JUDGE_KW, q) and not ({"增", "删", "改", "择", "判"} & actions):
        # "要不要X"消歧：X 是具体动作物→按 X 的原语（前面规则已抓）；否则抽象机会型归择
        if objects and objects <= {"新品"}:
            actions.add("择")
        elif objects:
            actions.add("判")
        else:
            actions.add("择")
    # 组装格子
    for a in actions:
        for o in objects:
            if (a, o) in MATRIX:
                pairs.append((a, o, "；".join(notes) if notes else "词法命中 %s×%s" % (a, o)))
    return pairs


def extract_pairs(q):
    """分句抽取（复合决策识别：一句话含 ≥2 个动作×对象对）。"""
    segs = [s for s in re.split(r"[，,。；;？?！!\n]", q) if s.strip()]
    pairs = []
    if segs:
        for s in segs:
            pairs.extend(_extract_segment(s))
    if not pairs:
        pairs = _extract_segment(q)
    # 去重：同 (动作,对象) 合并；同对象同场景不同动作 → 合并为一个落点（F3：落点等价不重复计）
    seen, out = set(), []
    for a, o, r in pairs:
        key = (a, o)
        if key in seen:
            continue
        seen.add(key); out.append((a, o, r))
    return out


def route(q):
    """返回结构化路由结果。"""
    pairs = extract_pairs(q)
    if not pairs:
        if _hit(["风险", "复盘", "三问"], q):
            return {"exit": "C类", "pairs": [], "composite": False,
                    "advice": "非完整决策问题 → C类真组件（风险提醒/复盘/生意思维三问），职责回归纯粹",
                    "refs": ["ref-06通用组件.md"]}
        if _hit(DECISION_MARKERS, q):
            return {"exit": "澄清", "pairs": [], "composite": False,
                    "advice": "原语缺失：说不清动作或对象 → 定向补问（判据：答后能构成 动作×对象 才澄清，否则 C类）",
                    "refs": ["ref-06通用组件.md"]}
        return {"exit": "C类", "pairs": [], "composite": False,
                "advice": "无决策信号 → C类（非决策）",
                "refs": ["ref-06通用组件.md"]}
    # 跨域拆解判定：对象枚举外（品牌）
    if any(o == "品牌" for _, o, _ in pairs):
        return {"exit": "跨域拆解", "pairs": [
            {"动作": a, "对象": o, "场景": "跨域拆解（层3）", "场景id": "X", "格子": "战略本体",
             "理由": r + "；拆解优先：拆出产品域可执行部分逐个归位拿弹药；战略本体走纪律服务（显式假设+反方+风险六维+DR9）；品牌重新定位=🔴不可逆；转介锚点：Aaker 谱系（ref-06）"}
            for a, o, r in pairs if o == "品牌"],
            "composite": False,
            "advice": "对象枚举外（品牌级）→ 拆解优先，不硬塞矩阵；显式声明「品牌战略本体超出场景弹药」",
            "refs": ["ref-06通用组件.md"]}
    # 归位
    resolved, scenes = [], []
    for a, o, r in pairs:
        if (a, o) in MATRIX:
            sid, label = MATRIX[(a, o)]
            resolved.append({"动作": a, "对象": o, "场景": SCENES[sid]["name"], "场景id": sid,
                             "格子": label, "理由": r})
            scenes.append(sid)
        elif a == "?":
            return {"exit": "澄清", "pairs": [], "composite": False, "advice": r,
                    "refs": ["ref-06通用组件.md"]}
    distinct = sorted(set(scenes))
    composite = len(distinct) >= 2
    advice = "复合决策：拆为独立决策点逐个归位（100%规则：不重叠不遗漏）；主意图优先服务；互为前提→问「哪个先定？」；DR 各记一条，决策链字段互引" if composite else "单决策点归位 → 闸口 A 透出确认（动作×对象×场景×理由）"
    refs = []
    for sid in distinct:
        refs.extend(SCENES[sid]["refs"].split("+"))
    return {"exit": "归位成功", "pairs": resolved, "composite": composite, "advice": advice,
            "refs": refs or ["ref-06通用组件.md"]}


ACTIONS = ["增", "删", "改", "择", "判"]


def route_primitives(action, obj):
    """AI 判定模式（RC-3）：AI 抽取的原语入参，脚本只做确定性校验 + 矩阵查表。"""
    if action not in ACTIONS:
        return {"exit": "澄清", "pairs": [], "composite": False,
                "advice": "动作原语非法（%r）：合法值=增/删/改/择/判 → AI 抽取失败，出口=澄清，做定向补问" % action,
                "refs": ["ref-06通用组件.md"]}
    if obj == "品牌":
        return {"exit": "跨域拆解", "pairs": [
            {"动作": action, "对象": "品牌", "场景": "跨域拆解（层3）", "场景id": "X", "格子": "战略本体",
             "理由": "AI 判定对象=品牌（枚举外）：拆解优先，产品域可执行部分逐个归位；品牌重新定位=🔴不可逆"}],
            "composite": False,
            "advice": "对象枚举外（品牌级）→ 拆解优先，不硬塞矩阵；显式声明「品牌战略本体超出场景弹药」",
            "refs": ["ref-06通用组件.md"]}
    if obj not in OBJECTS:
        return {"exit": "澄清", "pairs": [], "composite": False,
                "advice": "对象原语非法（%r）：合法值=%s → AI 抽取失败，出口=澄清，做定向补问" % (obj, "/".join(OBJECTS)),
                "refs": ["ref-06通用组件.md"]}
    sid, label = MATRIX[(action, obj)]
    pair = {"动作": action, "对象": obj, "场景": SCENES[sid]["name"], "场景id": sid, "格子": label,
            "理由": "AI 判定（原语入参模式）：跳过词法抽取，脚本仅校验合法性并查表"}
    return {"exit": "归位成功", "pairs": [pair], "composite": False,
            "advice": "单决策点归位 → 闸口 A 透出确认（动作×对象×场景×理由）",
            "refs": SCENES[sid]["refs"].split("+")}


def route_arbitrate(q, action, obj):
    """仲裁模式（RC-3）：AI 判定 vs 词法候选 双源对照。

    一致（词法候选含 AI 的 动作×对象 对）→ divergence=false，直接归位；
    不一致 → divergence=true，输出结构化差异对照，须呈现给用户选，禁止 AI 自选。
    输出结构对齐 session_state.routing（ai_primitive/script_candidates/divergence/confirmed_by_user）。"""
    ai = route_primitives(action, obj)
    lex = route(q)
    cands = [{"action": p["动作"], "object": p["对象"], "scene": p["场景id"]} for p in lex.get("pairs", [])]
    if ai["exit"] == "归位成功":
        ai_prim = {"action": action, "object": obj, "scene": ai["pairs"][0]["场景id"]}
        agree = lex["exit"] == "归位成功" and any(
            c["action"] == action and c["object"] == obj for c in cands)
    elif ai["exit"] == "跨域拆解":
        ai_prim = {"action": action, "object": obj, "scene": "X"}
        agree = lex["exit"] == "跨域拆解"
    else:
        return {"exit": "澄清", "pairs": [], "composite": False, "advice": ai["advice"],
                "refs": ai["refs"]}
    exit_name = "跨域拆解" if ai["exit"] == "跨域拆解" and agree else ("归位成功" if agree else "仲裁")
    return {"exit": exit_name, "pairs": ai["pairs"], "composite": False,
            "routing": {"ai_primitive": ai_prim, "script_candidates": cands,
                        "divergence": not agree, "confirmed_by_user": None},
            "advice": ("双源一致（AI 判定 ∈ 词法候选）→ 归位成功，仍须闸口 A 向用户透出确认"
                       if agree else
                       "双源不一致（divergence=true）→ 必须把两个候选对照呈现给用户选，禁止 AI 自行选定后只提一句；"
                       "用户确认原话写入 session_state.routing.confirmed_by_user"),
            "refs": ai["refs"], "lexical_exit": lex["exit"], "lexical_advice": lex["advice"]}


def render_text(q, r):
    lines = []
    if r["exit"] == "归位成功":
        for p in r["pairs"]:
            lines.append("归位透出：动作=%s | 对象=%s | 场景=%s | 出口=归位成功" % (
                p["动作"], p["对象"], p["场景"]))
            lines.append("  格子=%s" % p["格子"])
        if r["composite"]:
            lines.append("场景=%s（复合决策，%d 个落点）" % ("/".join(sorted(set(p["场景id"] for p in r["pairs"]))), len(r["pairs"])))
        else:
            lines.append("场景=%s" % r["pairs"][0]["场景"])
    elif r["exit"] == "仲裁":
        rt = r["routing"]
        p = r["pairs"][0]
        lines.append("归位仲裁：AI 判定与词法候选不一致（divergence=true）")
        lines.append("  AI 判定：  %s × %s → %s（判据：AI 语义抽取——决策直接改动的是什么）" % (
            rt["ai_primitive"]["action"], rt["ai_primitive"]["object"], rt["ai_primitive"]["scene"]))
        if rt["script_candidates"]:
            for c in rt["script_candidates"]:
                lines.append("  词法候选：%s × %s → %s（判据：词法规则命中；词法出口=%s）" % (
                    c["action"], c["object"], c["scene"], r.get("lexical_exit", "—")))
        else:
            lines.append("  词法候选：无（词法出口=%s，无法佐证 AI 判定）" % r.get("lexical_exit", "—"))
        lines.append("  格子=%s" % p["格子"])
        lines.append("  → 两源不一致必须把对照呈现给用户选，禁止 AI 自行选定后只提一句；确认原话写入 confirmed_by_user")
    elif r["exit"] == "跨域拆解":
        lines.append("场景=跨域拆解 | 出口=跨域拆解（对象枚举外：品牌级）")
    elif r["exit"] == "澄清":
        lines.append("场景=待澄清 | 出口=澄清（原语缺失）")
        lines.append("建议补问：你要「增/删/改/择/判」哪类动作？决策直接改动的是 新品/产品组合/现有单品/价格体系/渠道 中的哪个？")
    else:
        lines.append("场景=C类 | 出口=C类（非决策/组件级）")
    lines.append("路由建议：%s" % r["advice"])
    lines.append("主查=%s" % "+".join(r["refs"]))
    return "\n".join(lines)


def self_test():
    cases = [
        ("新品怎么上市？", ["S5"], "归位成功"),
        ("要不要给 A 出小规格？", ["S4"], "归位成功"),
        ("A 品出个礼盒装怎么样？", ["S2"], "归位成功"),
        ("砍掉 B 线，预算投 C 渠道", ["S2", "S5"], "归位成功"),
        ("品牌要不要重新定位", ["跨域"], "跨域拆解"),
        ("帮我看看有什么风险", ["C类"], "C类"),
        ("这个事儿帮我看看", ["澄清"], "澄清"),
        ("今天渠道开会聊了库存", ["C类"], "C类"),
        ("这个品卖不动了怎么办", ["S3"], "归位成功"),
        ("要不要涨价", ["S4"], "归位成功"),
        ("产品线要不要砍", ["S2"], "归位成功"),
        ("这个新品该不该立项", ["S1"], "归位成功"),
    ]
    bad = []
    for q, exp_ids, exp_exit in cases:
        r = route(q)
        if r["exit"] != exp_exit:
            bad.append("%s → 出口=%s（期望%s）" % (q, r["exit"], exp_exit)); continue
        got = set()
        for p in r["pairs"]:
            got.add(p["场景id"])
        if exp_exit == "跨域拆解":
            if "跨域" not in " ".join(got) and "跨域" not in r["exit"]:
                got.add("跨域")
        if exp_exit == "澄清" or exp_exit == "C类":
            continue
        for e in exp_ids:
            if e == "跨域":
                continue
            if e not in got:
                bad.append("%s → %s（期望含%s）" % (q, sorted(got), e))
    if bad:
        print("self: FAIL✗ %d 项不符" % len(bad))
        for b in bad:
            print("  ❌ " + b)
        return False
    # v5.0 原语入参模式 + 仲裁模式（RC-3：冲突检出率 100%，AI 自选率 0%）
    prim_cases = [
        # (action, object, 期望出口, 期望场景id)
        ("判", "现有单品", "归位成功", "S3"),
        ("增", "新品", "归位成功", "S1"),
        ("择", "价格体系", "归位成功", "S4"),
        ("改", "品牌", "跨域拆解", "X"),
        ("大概", "现有单品", "澄清", None),
        ("判", "市场", "澄清", None),
    ]
    for act, obj, exp_exit, exp_sid in prim_cases:
        r = route_primitives(act, obj)
        if r["exit"] != exp_exit:
            bad.append("原语模式 %s×%s → 出口=%s（期望%s）" % (act, obj, r["exit"], exp_exit)); continue
        if exp_sid and r["pairs"] and r["pairs"][0]["场景id"] != exp_sid:
            bad.append("原语模式 %s×%s → 场景=%s（期望%s）" % (act, obj, r["pairs"][0]["场景id"], exp_sid))
    arb_cases = [
        # (问题, action, object, 期望 divergence)
        ("这个品卖不动了怎么办", "判", "现有单品", False),   # 双源一致
        ("新品怎么上市？", "判", "现有单品", True),          # R2 实测事故：AI=S3 vs 词法=S5
        ("要不要给 A 出小规格？", "判", "价格体系", True),   # 同场景不同动作
        ("A 品出个礼盒装怎么样？", "择", "现有单品", True),  # 动作与对象双异
        ("帮我看看有什么风险", "判", "渠道/上市", True),     # 词法 C类 无法佐证
        ("品牌要不要重新定位", "判", "现有单品", True),      # AI 判 S3 vs 词法跨域
    ]
    for q, act, obj, exp_div in arb_cases:
        r = route_arbitrate(q, act, obj)
        div = r.get("routing", {}).get("divergence")
        if div != exp_div:
            bad.append("仲裁 %s×%s「%s」→ divergence=%s（期望%s；词法出口=%s）"
                       % (act, obj, q, div, exp_div, r.get("lexical_exit")))
        elif div is True and "禁止 AI 自行选定" not in r["advice"]:
            bad.append("仲裁 %s×%s「%s」→ divergence 输出缺「禁止自选」指令" % (act, obj, q))
    if bad:
        print("self: FAIL✗ %d 项不符" % len(bad))
        for b in bad:
            print("  ❌ " + b)
        return False
    print("self: golden G1-G5 + 四态反例 + 原语模式 6 例 + 仲裁 6 例（含 5 组双源冲突）共%d例全中 PASS✓"
          % (len(cases) + len(prim_cases) + len(arb_cases)))
    return True


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 决策原语路由器（教练模式：原语校验+25格矩阵+四态出口）")
    ap.add_argument("question", nargs="?", help="用户问题文本，或 - 读 stdin（--action/--arbitrate 模式下为词法/仲裁输入）")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    ap.add_argument("--action", default=None, help="AI 判定模式：AI 抽取的动作原语（增/删/改/择/判）")
    ap.add_argument("--object", dest="obj_arg", default=None, help="AI 判定模式：AI 抽取的对象原语（5 对象或品牌）")
    ap.add_argument("--arbitrate", action="store_true", help="仲裁模式：AI 判定 + 问题词法候选双源对照（须同时给 --action/--object 和问题）")
    ap.add_argument("--self", action="store_true", help="内置样例自检（golden G1-G5+四态反例+原语/仲裁模式）")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.action or a.obj_arg or a.arbitrate:
        if not a.arbitrate:
            if not (a.action and a.obj_arg):
                ap.error("--action 与 --object 必须成对使用")
            r = route_primitives(a.action, a.obj_arg)
            q = a.question or ("%s × %s" % (a.action, a.obj_arg))
        else:
            if not (a.action and a.obj_arg):
                ap.error("--arbitrate 需要 --action/--object（AI 判定）+ 问题文本（词法候选）")
            if not a.question:
                ap.error("--arbitrate 需要问题文本作为位置参数")
            q = sys.stdin.read().strip() if a.question == "-" else a.question
            r = route_arbitrate(q, a.action, a.obj_arg)
        if a.json:
            out = {"input": q, "出口": r["exit"], "复合决策": r["composite"],
                   "pairs": r["pairs"], "建议": r["advice"], "主查": r["refs"]}
            if "routing" in r:
                out["routing"] = r["routing"]
            print(json.dumps(out, ensure_ascii=False))
        else:
            print(render_text(q, r))
        return 1 if r["exit"] == "澄清" else 0
    if not a.question:
        ap.print_help()
        return 2
    q = sys.stdin.read().strip() if a.question == "-" else a.question
    r = route(q)
    if a.json:
        print(json.dumps({"input": q, "出口": r["exit"], "复合决策": r["composite"],
                          "pairs": r["pairs"], "建议": r["advice"], "主查": r["refs"]}, ensure_ascii=False))
    else:
        print(render_text(q, r))
    return 1 if r["exit"] == "澄清" else 0


if __name__ == "__main__":
    sys.exit(main())
