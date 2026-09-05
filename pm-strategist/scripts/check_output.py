#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_output.py — pm-strategist 台面输出校验（v4.0：纯台面 T1-T9 断言组）

对一份"给用户看的台面输出"做机器可查校验（决策对话形态，非审计档案形态）：
形态徽章路由 + 四区断言 T1-T9 + 不确定性标注 + B 类跨部门确认（--scene）。
DR9 字段/探讨轨迹/归位等档案结构校验不在本脚本——唯一入口 = decision-record.py（要点文件）。

用法:
  python3 scripts/check_output.py <台面输出文件> [--scene S4]
  cat 台面.txt | python3 scripts/check_output.py -
  python3 scripts/check_output.py --mode light <台面输出文件>   # 轻决策压缩态（T2≥1）
  python3 scripts/check_output.py --self
退出码: 0=PASS, 1=有缺项, 2=用法/读入错误
模式解析优先级：--mode 参数 > 首行徽章（[完整]→full / [轻]|[快轨]→light）> 默认 full
场景解析优先级：--scene 参数 > 文本内 场景=Sx 标记 > 未知（跳过 B 类断言）
⚠️ S4/S5 场景必须带场景来源（调用时传 --scene，或台面保留「场景=Sx」标记）——未知=断言不触发=漏检（SKILL.md 闸口 D）
C 类输出（只提醒不决策）不适用四区校验：自动检出 C 类时直接放行并提示。
本脚本只读文本，不写盘。
"""
import sys, re, argparse

# ── 形态徽章（首行 [完整]/[轻]/[快轨]；check_output 按标记路由断言集） ──
BADGE_RE = re.compile(r"\[(完整|轻|快轨)\]")
# ── T7 BANLIST：记忆层 10 词（v4.2.5）+ 台面扩容 12 词（v4.4.0，档案层与齐性自检豁免——
# 本脚本只吃台面文本，档案结构已不进台面，故全文生效） ──
BANLIST = ["决策情境", "披露分层", "回显确认", "升级通道", "记忆判据", "同词异层",
           "身份层", "待固化", "待补采", "确认戳",
           "路径声明", "归位", "主查", "闸口", "四态", "收敛终端",
           "反方意见", "双要素", "对照项", "D'-", "验证轨", "路由轨"]
# ── 反方双要素判定（最强反方/翻车点共用：具体条件 × 可反驳出口） ──
CON_RE = r"如果|若|一旦|假如|前提是|除非|当.{0,6}(时|成立|发生|出现)|在.{0,10}情况下"
TRIGGER_RE = r"则|就会|将会|导致|使得|造成|引发|即|一.{0,4}就"
FALSIFY_STRONG = (r"推翻|证伪|不成立|失效|站不住|需重估|需重做|重算|落空|白做|白费|前功尽弃|"
                  r"泡汤|打水漂|适得其反|得不偿失|弄巧成拙|反噬|不再成立|改变.{0,4}结论|"
                  r"推翻条件|什么数据|什么条件|什么信号")
FALSIFY_NEG = r"砍错|做错|误判|误杀|错杀|判断失误|决策失误|证明.{0,6}错|说明.{0,6}错|压根不该|不该砍|不该做"
# ── B 类跨部门确认句（S4/S5 台面必附） ──
B_TAGS = {"S4": "最终定价决策需跨部门确认", "S5": "最终上市决策需跨部门确认"}
# 三档置信词（台面禁裸百分比，百分比读数只在档案仪表）
GRADE_RE = re.compile(r"置信度[：:]*\s*(中高|高|中)(?![个点])")
REV_YELLOW_RE = re.compile(r"拿不准[，,]?\s*按退不回(对待|处理)|按退不回对待|拿不准.{0,8}按最坏打算")
REV_GREEN_RE = re.compile(r"随时可改|随时能改|先试试")
SIGNAL_RE = re.compile(r"若|一旦|信号|阈值|触发|低于|高于|超过|达到|≥|≤|＜|>")
PCT_RE = re.compile(r"\d+\s*[%％]")
# v4.4.2 T9 豁免：数据趋势对比（18%→9%）在全文已含不确定标注时视为"待核实线索"放行
TREND_PCT_RE = re.compile(r"\d+\s*[%％]\s*(?:→|➝|⟶|->|=>)\s*\d+\s*[%％]")


def sections(text):
    """【区名】→ 区内容（到下一个【区头或文末）。返回 [(区名, 内容)]。"""
    out = []
    matches = list(re.finditer(r"【([^】]{1,14})】", text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((m.group(1), text[start:end].strip()))
    return out


def get_section(text, name):
    for n, c in sections(text):
        if n == name:
            return c
    return None


def find_section(text, keyword):
    for n, c in sections(text):
        if keyword in n:
            return n, c
    return None, None


def resolve_mode(text, mode_arg):
    badge = BADGE_RE.search(text)
    if mode_arg:
        return mode_arg, (badge.group(1) if badge else None)
    if badge:
        return ("full" if badge.group(1) == "完整" else "light"), badge.group(1)
    return "full", None


def resolve_scene(text, scene_arg):
    if scene_arg:
        return scene_arg
    m = re.search(r"场景\s*[=:＝]\s*(S[1-5]|C类|待路由)", text)
    return m.group(1) if m else None


def check_full(text, mode="full"):
    """台面总校验（full=T2≥2 / light=T2≥1，其余断言两态同强度）。返回问题清单。"""
    problems = []
    # 0 形态徽章（首行标注 [完整]/[轻]/[快轨]，check_output 按标记路由断言集）
    badge = BADGE_RE.search(text)
    if not badge:
        problems.append("T0 缺形态徽章（首行应标 [完整]/[轻]/[快轨]——check_output 按标记路由断言集）")
    elif mode and ((mode == "full") != (badge.group(1) == "完整")):
        problems.append("T0 形态徽章[%s]与校验模式 --mode %s 不符（完整→full；轻/快轨→light）" % (badge.group(1), mode))
    # T1 建议区：推荐明确（禁推卸）+三档置信词+下一步（你）前 120 字内
    sug = get_section(text, "建议")
    if sug is None:
        problems.append("T1 缺【建议】区（四区模板首区）")
    else:
        if not sug.strip():
            problems.append("T1 【建议】区为空（应给明确推荐一句话）")
        if re.search(r"各有优劣.{0,6}自行判断|都可以.{0,4}你定|两者皆可", sug):
            problems.append("T1 推荐不明确（\"各有优劣请自行判断\"类推卸=违反；必须给明确推荐）")
        gseg = GRADE_RE.search(sug) or GRADE_RE.search(text[:200])
        if not gseg:
            problems.append("T1 缺三档置信词（置信度：高/中高/中 + 一句依据；台面禁裸百分比）")
        elif not re.search(r"[·・]\s*\S|依据", gseg.string[gseg.end():gseg.end() + 40]):
            problems.append("T1 置信度缺一句依据（三档词后须接「· 一句依据」——禁空壳置信度；判定词3）")
    nxt = text.find("下一步（你）")
    if nxt < 0:
        problems.append("T1 缺「下一步（你）：第一动作」（30 秒判定的行动锚）")
    elif nxt > 120:
        problems.append("T1 「下一步（你）」出现在第 %d 字（应位于输出前 120 字内——30 秒判定的操作化定义）" % nxt)
    # T2 为什么：论据数（full≥2/light≥1）且含 →/所以 因果连接
    why = get_section(text, "为什么")
    if why is None:
        problems.append("T2 缺【为什么】区（论据必须上台面，不许只在幕后）")
    else:
        items = [l for l in why.splitlines() if re.match(r"^\s*\d+\s*[\.、）)]", l)]
        if not items:
            items = [l for l in why.splitlines() if l.strip()]
        need = 2 if mode == "full" else 1
        if len(items) < need:
            problems.append("T2 【为什么】论据 %d 条（%s 态需 ≥%d；每条=可验证事实/数字 → 所以…）"
                            % (len(items), "完整" if mode == "full" else "压缩", need))
        if not re.search(r"→|所以", why):
            problems.append("T2 【为什么】缺因果连接（论据须写成 事实/数字 → 所以…，不许只摆框架）")
    # T3 为什么不选别的：死因 ≥1 且含 维持现状
    n3, dead = find_section(text, "不选")
    if dead is None:
        problems.append("T3 缺【为什么不选别的】区（落选项逐个死因）")
    else:
        if "维持现状" not in dead and "维持现价" not in dead:
            problems.append("T3 落选死因缺「维持现状」对照（不做是每个决策的真实备选）")
        if not re.search(r"死于|代价|损失|无法比较|缺.{0,12}(数据|数据无法)", dead):
            problems.append("T3 死因不具体（应写 死于<具体死因/代价>；证据不足写 缺<数据>无法比较）")
    # T4 换挡条件：信号+阈值，禁"再议/再看"，复盘日同源
    n4, shift = find_section(text, "换挡")
    if shift is None:
        problems.append("T4 缺【换挡条件】区（可证伪改判线，全强制含🟢轻决策）")
    else:
        if not SIGNAL_RE.search(shift):
            problems.append("T4 换挡缺可观察信号+阈值（若<信号+阈值> → 结论改为<选项>；禁\"再议/再看\"）")
        if re.search(r"再议|再看", shift):
            problems.append("T4 换挡条件不可证伪（含\"再议/再看\"——必须信号+阈值）")
        if "复盘日" not in shift:
            problems.append("T4 换挡缺复盘日（模板：复盘日 YYYY-MM-DD，与档案复盘字段同源）")
    # T5 最可能翻车的点：最强反方双要素（具体条件+可反驳出口）+邀请反驳
    n5, flip = find_section(text, "翻车")
    if flip is None:
        problems.append("T5 缺【最可能翻车的点】区（最强反方上台面，AI 主动抬杠）")
    else:
        has_cond = bool(re.search(CON_RE, flip)) or bool(re.search(TRIGGER_RE, flip))
        has_exit = bool(re.search(FALSIFY_STRONG, flip)) or bool(re.search(FALSIFY_NEG, flip))
        if not (has_cond and has_exit):
            miss = []
            if not has_cond:
                miss.append("①具体条件（若/一旦…什么事实成立）")
            if not has_exit:
                miss.append("②可反驳出口（本决定 失效/被推翻/砍错，或推翻条件=拿到<什么数据>）")
            problems.append("T5 翻车点是稻草人（缺 %s）——模板：若<事实成立>，本决定<失效/砍错>；推翻条件=拿到<数据>｜"
                            "例：若竞品四季度抢签合约条款，砍线等于把渠道阵地白送对手，本决定失效" % "、".join(miss))
        if not re.search(r"怼|反驳|不同意|欢迎", flip):
            problems.append("T5 翻车区缺邀请反驳（模板：——不同意就怼，我当场对）")
    # T6 可逆性人话 + 归位人话（透明度监督的人话版）
    if not re.search(r"级别?的决定", text):
        problems.append("T6 缺归位人话（开场应说\"这是<动作×对象>级的决定\"——用户看得见的监督锚）")
    has_r, has_y, has_g = "🔴" in text, "🟡" in text, "🟢" in text
    rev_hard = ("退不回" in text) or ("收不回" in text)
    if has_r and not rev_hard:
        problems.append("T6 🔴 不可逆但台面没说\"退不回/收不回\"（可逆性人话缺失）")
    if has_y and not REV_YELLOW_RE.search(text):
        problems.append("T6 🟡 话术失实——必须说\"拿不准，按退不回对待\"（保守侧但诚实），不得直说\"退不回\"")
    if has_g and not REV_GREEN_RE.search(text):
        problems.append("T6 🟢 可逆但台面没说\"随时可改/先试试\"（轻决策节奏应轻）")
    if not (has_r or has_y or has_g):
        if not (rev_hard or REV_GREEN_RE.search(text) or "拿不准" in text):
            problems.append("T6 缺可逆性人话（🔴=这事退不回/收不回；🟡=拿不准，按退不回对待；🟢=随时可改/先试试）")
    # T7 台面零 BANLIST（黑话不上台面；档案层与齐性自检豁免——本脚本只吃台面文本）
    hit = [w for w in BANLIST if w in text]
    if hit:
        problems.append("T7 台面出现流程黑话（须人话改写）：%s —— 例：说\"这是砍产品线级的决定\"而非\"归位\"；"
                        "说\"我先跟你确认\"而非\"路径声明/闸口\"" % "/".join(hit))
    # T8 档案提示行
    arch_line = None
    for line in text.splitlines():
        if "档案已存" in line:
            arch_line = line
            break
    if arch_line is None:
        problems.append("T8 缺档案提示行（收敛终版模板：档案已存：./决策记录/DR-YYYYMMDD-xxx.html——…齐全）")
    elif not ("决策记录" in arch_line or ".html" in arch_line):
        problems.append("T8 档案提示行缺落盘位置（应含 ./决策记录/…html 路径）")
    # T9 台面禁裸百分比（置信度/概率类伪精确；百分比读数只在档案仪表）
    # v4.4.2 松绑：数据趋势对比（18%→9%）且全文已含不确定标注（⚠️/待验证/不确定）时放行——
    # 视为"待核实的数据线索"供查证；置信度语境与单点百分比仍禁（防无来源精确断言）
    has_uncertain = ("不确定" in text) or ("待验证" in text) or ("⚠️" in text)
    residue = TREND_PCT_RE.sub("", text) if has_uncertain else text
    pct = PCT_RE.findall(residue)
    if pct:
        problems.append(
            "T9 台面出现裸百分比（{} 处）——置信度用三档词（高/中高/中）；"
            "数据对比写\"个点/成\"，或带 ⚠️/待验证 的趋势对比（18%→9%）可上桌，"
            "或沉档案仪表（伪精确制造过度自信）".format(len(pct)))
    # 行为准则⑤：不确定性标注痕迹
    if ("不确定" not in text) and ("待验证" not in text) and ("⚠️" not in text):
        problems.append("未见不确定性标注痕迹（应含 不确定/待验证 或 ⚠️ 假设·待验证）")
    return problems


def check_btag(text, scene):
    """B 类跨部门确认句（S4/S5 台面必附；场景由 --scene 或文本标记给出）。"""
    if scene in B_TAGS and B_TAGS[scene] not in text:
        return ["B类场景（%s）缺跨部门确认标注：%s…" % (scene, B_TAGS[scene])]
    return []


def self_test():
    GOOD_FULL = """[完整]
这是砍产品线级的决定，这事退不回——先跟你确认两件事。

【建议】砍 B 线，设 60 天缓冲期再执行（置信度：中高 · 贡献度连续四季下滑；口径未扣返利 ⚠️ 待财务确认）
下一步（你）：本周内确认渠道合约有无条码数门槛

【为什么】
1. B 线贡献度连续四季下滑，长尾线占用仓储与陈列资源 → 所以机会成本在 A/C 线。
2. 渠道入场资格清单不含 B 线条码 → 所以砍线不丢渠道筹码，退出代价集中在库存处置。

【为什么不选别的】
- 轻量化改造：死于换线成本回收期超出预算窗。
- 维持现状：代价是每月倒贴仓储与陈列，下滑趋势未见底。

【换挡条件】若大促动销低于品类均值八成 → 维持砍线；复盘日 2026-11-05

【最可能翻车的点】若竞品在四季度抢签 B 线经销商合约条款，砍线等于把渠道阵地白送对手，本决定失效——不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-bline.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
"""
    GOOD_LIGHT = """[轻]
这是详情页改字级的决定，随时可改，先试试。

【建议】按钮文案改成「马上抢」再观察一周（置信度：高 · 同类按钮 A/B 有成熟先例，首日数据 ⚠️ 待验证）
下一步（你）：今晚发布并设 7 天后回看转化

【为什么】1. 按钮文案改动随时可回滚 → 所以按轻决策节奏走即可。

【为什么不选别的】维持现状：代价是转化优化窗口往后拖一周。

【换挡条件】若 7 天转化不升 → 换回原文案；复盘日 2026-09-12

【最可能翻车的点】若新文案让老客困惑、首日转化反降，本改动落空——不对就改回。不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-cta.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
"""
    ok = True
    def chk(name, cond):
        nonlocal ok
        print("  %s %s" % ("✓" if cond else "✗ 未拦住/误报", name))
        if not cond:
            ok = False
    p_full = check_full(GOOD_FULL, "full")
    chk("完整态好样本 PASS（T0-T9 全过+零黑话+无裸百分比）", not p_full)
    if p_full:
        for x in p_full:
            print("     └ " + x)
    p_light = check_full(GOOD_LIGHT, "light")
    chk("压缩态好样本 --mode light PASS（T2≥1）", not p_light)
    p_light_as_full = check_full(GOOD_LIGHT, "full")
    chk("压缩态样本按 full 校验被拦（T2 论据 1<2）", any("T2" in x for x in p_light_as_full))
    # 徽章/模式不符
    p_mis = check_full(GOOD_LIGHT.replace("[轻]", "[完整]"), "full")
    chk("徽章[完整]但 T2 只有 1 条论据 → 被拦（按标记路由）", any("T2" in x for x in p_mis))
    # 缺件：删「下一步（你）」
    p1 = check_full(GOOD_FULL.replace("下一步（你）：本周内确认渠道合约有无条码数门槛\n", ""), "full")
    chk("缺「下一步（你）」被拦", any("T1" in x for x in p1))
    # 空壳置信度（三档词后无依据）
    p7h = check_full(GOOD_FULL.replace("（置信度：中高 · 贡献度连续四季下滑；口径未扣返利 ⚠️ 待财务确认）", "（置信度：中高）"), "full")
    chk("空壳置信度（三档词无依据）被拦（T1）", any("T1" in x for x in p7h))
    # 黑话（BANLIST 扩容词上台面）
    p2 = check_full(GOOD_FULL.replace("先跟你确认两件事", "主查=ref-02，路径声明：验证轨"), "full")
    chk("扩容黑话（主查/路径声明）上台面被拦", any("T7" in x for x in p2))
    # 裸百分比
    p3 = check_full(GOOD_FULL.replace("置信度：中高", "置信度：70%"), "full")
    chk("台面裸百分比被拦（T9）", any("T9" in x for x in p3))
    # v4.4.2 数据趋势对比豁免：带 ⚠️ 标注放行 / 无不确定标注仍拦
    p9a = check_full(GOOD_FULL.replace(
        "贡献度连续四季下滑；口径未扣返利 ⚠️ 待财务确认",
        "贡献度从 28%→9% ⚠️ 口径待财务确认"), "full")
    chk("数据趋势对比 28%→9%（全文含⚠️）放行（T9 豁免）", not any("T9" in x for x in p9a))
    if any("T9" in x for x in p9a):
        for x in p9a:
            if "T9" in x:
                print("     └ " + x)
    p9b = check_full(GOOD_FULL.replace(
        "贡献度连续四季下滑；口径未扣返利 ⚠️ 待财务确认",
        "贡献度从 28%→9%"), "full")
    chk("趋势对比但全文无不确定标注 → 仍拦（豁免前提）", any("T9" in x for x in p9b))
    # 🟡 话术失实（直说"退不回"）
    p4 = check_full(GOOD_FULL.replace("这事退不回", "🟡这事退不回"), "full")
    chk("🟡 话术失实被拦（须说「拿不准，按退不回对待」）", any("T6" in x for x in p4))
    # 换挡含"再议"
    p5 = check_full(GOOD_FULL.replace("若大促动销低于品类均值八成 → 维持砍线", "大促后效果不达预期 → 再议"), "full")
    chk("换挡条件含「再议」被拦（不可证伪）", any("T4" in x for x in p5))
    # 稻草人翻车点
    p6 = check_full(GOOD_FULL.replace(
        "若竞品在四季度抢签 B 线经销商合约条款，砍线等于把渠道阵地白送对手，本决定失效",
        "可能市场不好吧"), "full")
    chk("稻草人翻车点被拦（缺具体条件+可反驳出口）", any("T5" in x for x in p6))
    # B 类标注
    b4 = check_btag(GOOD_FULL, "S4")
    chk("S4 场景缺跨部门确认句被拦", len(b4) == 1)
    b4ok = not check_btag(GOOD_FULL + "\n⚠️ 最终定价决策需跨部门确认（财务/销售/渠道/管理层）", "S4")
    chk("S4 附跨部门确认句 → 放行", b4ok)
    # C 类放行
    chk("C 类输出不适用四区校验（说明性放行）", resolve_scene("场景=C类", None) == "C类")
    print("self: 台面校验器 v4.0（T0-T9 双模式+%d 禁词+双要素反方+B类标注） %s" %
          (len(BANLIST), "PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(
        description="pm-strategist 台面输出校验（四区 T1-T9 断言组；DR 档案校验唯一入口=decision-record.py）")
    ap.add_argument("input", nargs="?", help="台面输出文本文件路径，或 - 读 stdin")
    ap.add_argument("--mode", choices=["full", "light"], default=None,
                    help="full=完整态（T2≥2）；light=压缩/快轨态（T2≥1）。缺省按首行徽章路由，再缺省 full")
    ap.add_argument("--scene", choices=["S1", "S2", "S3", "S4", "S5", "C类"], default=None,
                    help="场景号（S4/S5 必传——B 类跨部门断言的输入来源；缺省=断言不触发=漏检）")
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
    scene = resolve_scene(text, a.scene)
    if scene == "C类":
        print("PASS — C 类输出（只提醒不决策）不适用四区台面校验")
        return 0
    mode, badge = resolve_mode(text, a.mode)
    problems = check_full(text, mode) + check_btag(text, scene)
    if problems:
        print("FAIL — 台面校验缺 %d 项（模式=%s%s）：" % (len(problems), mode,
              "，徽章=[%s]" % badge if badge else "，未标徽章"))
        for x in problems:
            print("  ❌ " + x)
        return 1
    print("PASS — 台面四区齐全（%s态：T1-T9 过，零黑话，无裸百分比）%s" %
          ("完整" if mode == "full" else "压缩", "，B类标注在场" if scene in B_TAGS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
