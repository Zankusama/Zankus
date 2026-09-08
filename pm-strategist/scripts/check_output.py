#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_output.py — pm-strategist 台面输出校验（v5.0：T1-T11 + 发布校验/信封边界/澄清轮断言）

对一份"给用户看的台面输出"做机器可查校验（决策对话形态，非审计档案形态）：
形态徽章路由 + 四区断言 T1-T9 + T10 候选区/T11 进度行（v5.0 批次二四区增量；M9-3 跳步自曝尾巴并入 T11）+ 不确定性标注 + B 类跨部门确认（--scene）。
DR9 字段/探讨轨迹/归位等档案结构校验不在本脚本——唯一入口 = decision-record.py（要点文件）。

v5.0 新增（批次一根因修复线）：
  R-1 --publish 发布校验模式：校验对象=最终发布组合文本（信封+台面）——修复
     "校验-发布脱钩"（v4.4.4 R2 事故：草稿过闸但发布文本 FAIL 项照样上台）。
  R-2 信封-台面边界仲裁（--publish 下）：会话信封区（徽章行前 + 机器闸口/系统日志尾）
     豁免 T7 黑话断言——守闸口 A（归位透出）不再必违 T7；台面区锚点=首行徽章起算。
  R-3 澄清轮轻断言：非四区形态输出（澄清/冷启动轮）补问 ≤2（疑问句计数，嵌套子项
     按子项数计）+ 零 BANLIST 词——R1 五问倾泻从此可拦。
  #16 --scene 必传：S4/S5 不传=B 类跨部门断言静默跳过=漏检，改为 exit 2 强制。

用法:
  python3 scripts/check_output.py <台面输出文件> --scene S4
  cat 台面.txt | python3 scripts/check_output.py - --scene S2
  python3 scripts/check_output.py --publish <发布组合文本> --scene S3   # R-1 发布前校验（三步硬序列第 2 步）
  python3 scripts/check_output.py --mode light <台面输出文件> --scene S3 # 轻决策压缩态（T2≥1）
  python3 scripts/check_output.py --self
退出码: 0=PASS, 1=有缺项, 2=用法/读入错误（含 --scene 缺传）
模式解析优先级：--mode 参数 > 首行徽章（[完整]→full / [轻]|[快轨]→light）> 默认 full
场景解析优先级：--scene 参数（必传）> 文本内 场景=Sx 标记
C 类输出（只提醒不决策）不适用四区校验：--scene C类 时直接放行并提示。
本脚本只读文本，不写盘。
"""
import sys, re, os, argparse

# ── 形态徽章（首行 [完整]/[轻]/[快轨]；check_output 按标记路由断言集） ──
BADGE_RE = re.compile(r"\[(完整|轻|快轨)\]")
# ── T7 BANLIST：记忆层 10 词（v4.2.5）+ 台面扩容 12 词（v4.4.0）+ 「落格」（v5.0 R-2
# 补词通道：本 session 实测上台而词表缺；--publish 模式下信封区豁免，台面区全文生效） ──
BANLIST = ["决策情境", "披露分层", "回显确认", "升级通道", "记忆判据", "同词异层",
           "身份层", "待固化", "待补采", "确认戳",
           "路径声明", "归位", "主查", "闸口", "四态", "收敛终端",
           "反方意见", "双要素", "对照项", "D'-", "验证轨", "路由轨", "落格"]
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
# v5.0 T11 进度行（M3）：末行固定「进度：第 X 轮/归位中 · <步骤人话> · 还差：<台账未确认项/可收敛>」
# 轮=一次用户输入+一次AI回复；澄清轮不计入轮次（标注归位中）
PROGRESS_RE = re.compile(r"^进度：(?:第\s*\d+\s*轮|归位中)\s*·\s*[^·]+?\s*·\s*还差[:：]\s*\S")
# v5.0 M9-3 跳步自曝（前移台面区，透明化信号非兜底）：四区进度行尾巴固定
# 「｜ 本轮跳过：<无/跳了什么+一句人话原因> ｜ 假设新增：<N> 项已挂账」——无跳过也须写「无」（写出来才算声明）
DISCLOSE_RE = re.compile(r"｜\s*本轮跳过[:：]\s*\S[^｜]*｜\s*假设新增[:：]\s*\d+\s*项")
# ── W-07 T8 双态：初步版占位「档案未落盘」/ 终版「档案已存」须匹配 DR 文件名（--dr-dir 给出时还须真实存在）──
ARCH_DRAFT_RE = re.compile(r"档案未落盘")
ARCH_DONE_RE = re.compile(r"档案已存")
DR_RE = re.compile(r"DR-\d{8}-[A-Za-z0-9_\-]+\.html")


def last_nonempty_line(text):
    for ln in reversed(text.splitlines()):
        if ln.strip():
            return ln.strip()
    return ""


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


# ── R-2 信封-台面边界（--publish 模式）──
# 尾部信封锚行：机器闸口段 / 系统日志块 / 纯分隔线（--- 与 markdown 表格分隔 |---| 区分）
ENVELOPE_TAIL_RE = re.compile(r"^(?:\**机器闸口|📝|系统日志|-{3,}|={3,}|━{3,}|─{3,})")


def split_publish(text):
    """发布组合文本 → (台面区, 信封区)。
    台面区 = 首个徽章行起 → 徽章后第一个尾部信封锚行（不含）或文末；
    信封区 = 徽章行前的头部（意图分类/归位透出）+ 尾部锚行起的机器内容（闸口结果/系统日志）。
    无徽章 → 全文按台面处理（T0 拦缺徽章；不静默豁免）。"""
    lines = text.splitlines(keepends=True)
    badge_idx = None
    for i, ln in enumerate(lines):
        if BADGE_RE.search(ln):
            badge_idx = i
            break
    if badge_idx is None:
        return text, ""
    tail_idx = len(lines)
    for i in range(badge_idx + 1, len(lines)):
        if ENVELOPE_TAIL_RE.match(lines[i].strip()):
            tail_idx = i
            break
    table = "".join(lines[badge_idx:tail_idx])
    envelope = "".join(lines[:badge_idx]) + "".join(lines[tail_idx:])
    return table, envelope


# ── R-3 澄清轮轻断言（非四区形态：澄清/冷启动轮）──
SUBITEM_RE = re.compile(r"[（(][a-eA-E][)）]|[①②③④⑤⑥⑦⑧⑨⑩]|(?<![\w.])(?<![①②③④⑤⑥⑦⑧⑨⑩])[1-9][.、）)]")


def count_questions(text):
    """有效补问计数：每个疑问句 1 问；某问行内/紧邻行带 ≥2 个子项标记（a) ① 1.）时按子项数计
    （R1 事故：一问内嵌 9 子项的"单问"不是单问）。"""
    lines = text.splitlines()
    total = 0
    for i, ln in enumerate(lines):
        nq = ln.count("？") + ln.count("?")
        if not nq:
            continue
        sub = 0
        for seg in (ln, lines[i + 1] if i + 1 < len(lines) else ""):
            sub += len(SUBITEM_RE.findall(seg))
        total += max(nq, sub) if sub >= 2 else nq
    return total


def check_clarify(text):
    """澄清/冷启动轮（非四区形态且含疑问句）轻断言。返回 problems；None=非澄清轮形态（不适用）。
    四区文本（有【建议】或【换挡条件】）不走本断言——探讨邀请不是补问。"""
    if get_section(text, "建议") is not None or find_section(text, "换挡")[1] is not None:
        return None
    if "？" not in text and "?" not in text:
        return None
    problems = []
    qn = count_questions(text)
    if qn > 2:
        problems.append("R3 澄清轮补问 %d 问（须 ≤2：一轮只补最关键两问，其余下轮；"
                        "嵌套子项按子项数计——一问带 9 子项=9 问）" % qn)
    # 进度行=机器格式行（M3 规定澄清轮标「归位中」），黑话扫描豁免该行本身（同 R-2 信封豁免逻辑）
    scan = "\n".join(l for l in text.splitlines() if not PROGRESS_RE.match(l.strip()))
    hit = [w for w in BANLIST if w in scan]
    if hit:
        problems.append("R3 澄清轮台面出现流程黑话（须人话改写）：%s" % "/".join(hit))
    if not PROGRESS_RE.match(last_nonempty_line(text)):
        problems.append("R3 澄清轮缺进度行（末行固定「进度：归位中（澄清轮不计轮次）或 第 X 轮 · "
                        "<步骤人话> · 还差：<台账未确认项>」——M3 每轮发布文本末行）")
    return problems


def check_full(text, mode="full", dr_dir=None):
    """台面总校验（full=T2≥2 / light=T2≥1，其余断言两态同强度）。返回问题清单。
    dr_dir=DR 落盘目录（W-07：给出时终版 T8 还校验 DR 文件真实存在；None 只保格式）。"""
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
    # T8 档案提示行（W-07 双态：初步版占位「档案未落盘」/ 终版「档案已存」须匹配 DR 文件名且真实存在）
    arch_line = None
    for line in text.splitlines():
        if ARCH_DRAFT_RE.search(line) or ARCH_DONE_RE.search(line):
            arch_line = line
            break
    if arch_line is None:
        problems.append("T8 缺档案提示行（初步版占位：档案未落盘（初步版）…；终版模板：档案已存：./决策记录/DR-YYYYMMDD-xxx.html——…齐全）")
    elif ARCH_DRAFT_RE.search(arch_line):
        # 初步版占位：明确「未落盘」，不应冒充已落盘（不许带具体 DR 文件名）
        md = DR_RE.search(arch_line)
        if md:
            problems.append("T8 初步版占位既写「档案未落盘」又带 DR 文件名（%s）——占位应明确未落盘" % md.group(0))
    else:
        # 终版：须有合法 DR 文件名；给了 --dr-dir 还须真实存在（W-07 真缺口样本=格式合法但不存在的 DR 路径）
        md = DR_RE.search(arch_line)
        if not md:
            problems.append("T8 档案提示行缺合法 DR 文件名（终版应含 DR-YYYYMMDD-事件.html，如 ./决策记录/DR-20260905-bline.html）")
        elif dr_dir and not os.path.isfile(os.path.join(dr_dir, md.group(0))):
            problems.append("T8 档案提示行指向的 DR 文件不存在（%s，目录：%s）——引用了格式合法但未落盘的档案"
                            % (md.group(0), dr_dir))
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
    # T10 候选选项区（v5.0 四区增量：正选全集+当前推荐——T3 只有落选死因，正选全集是 R4 实测缺口）
    n_c, cand = find_section(text, "候选")
    if cand is None:
        problems.append("T10 缺【候选选项】区（正选全集 ≥2 项含「维持现状」+ 标注「当前推荐」——"
                        "用户须看到完整选项集，不只看到推荐；放【建议】之后，落选死因见 T3）")
    else:
        circled = set(re.findall(r"[①②③④⑤⑥⑦⑧⑨⑩]", cand))
        cand_lines = [l.strip() for l in cand.splitlines() if l.strip()]
        bullets = [l for l in cand_lines if re.match(r"^[-*·•]\s*\S+", l)]
        items_n = max(len(circled), len(bullets), len(cand_lines))
        if items_n < 2:
            problems.append("T10 【候选选项】不足 2 项（正选全集 ≥2：当前推荐 + 维持现状对照；"
                            "单行用 ①②… 分隔或多行列表）")
        if "维持现状" not in cand and "维持现价" not in cand:
            problems.append("T10 候选区缺「维持现状/现价」对照项（不做是每个决策的真实备选）")
        if "推荐" not in cand:
            problems.append("T10 候选区缺「当前推荐」标注（标明哪项是本轮推荐，与【建议】呼应）")
    # T11 进度行（M3：每轮发布文本末行固定——轮=一次用户输入+一次AI回复；澄清轮=归位中）
    # + M9-3 跳步自曝尾巴（前移台面区的透明化信号非兜底：跳了什么/新增几条假设挂账——写「无/0 项」也是声明）
    t11_last = last_nonempty_line(text)
    if not PROGRESS_RE.match(t11_last):
        problems.append("T11 缺进度行（末行固定「进度：第 X 轮（或归位中）· <步骤人话> · 还差："
                    "<台账未确认项/可收敛> ｜ 本轮跳过：… ｜ 假设新增：N 项已挂账」——每轮发布文本末行；还差引用台账，不自造黑话）")
    elif not DISCLOSE_RE.search(t11_last):
        problems.append("T11 进度行缺跳步自曝尾巴（M9-3 前移台面区）：末行补「｜ 本轮跳过：<无/跳了什么+一句人话原因> ｜ "
                        "假设新增：<N> 项已挂账」——跳过与挂账数取自 session_state（gate_log/台账），无跳过写「无」、"
                        "零新增写「0 项」；透明化信号不兜底，但不写=未声明")
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

【候选选项】① 砍B线＋60天缓冲（当前推荐）② 收缩到A/C线主力渠道 ③ 维持现状

【为什么】
1. B 线贡献度连续四季下滑，长尾线占用仓储与陈列资源 → 所以机会成本在 A/C 线。
2. 渠道入场资格清单不含 B 线条码 → 所以砍线不丢渠道筹码，退出代价集中在库存处置。

【为什么不选别的】
- 轻量化改造：死于换线成本回收期超出预算窗。
- 维持现状：代价是每月倒贴仓储与陈列，下滑趋势未见底。

【换挡条件】若大促动销低于品类均值八成 → 维持砍线；复盘日 2026-11-05

【最可能翻车的点】若竞品在四季度抢签 B 线经销商合约条款，砍线等于把渠道阵地白送对手，本决定失效——不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-bline.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）｜ 本轮跳过：无 ｜ 假设新增：1 项已挂账
"""
    GOOD_LIGHT = """[轻]
这是详情页改字级的决定，随时可改，先试试。

【建议】按钮文案改成「马上抢」再观察一周（置信度：高 · 同类按钮 A/B 有成熟先例，首日数据 ⚠️ 待验证）
下一步（你）：今晚发布并设 7 天后回看转化

【候选选项】① 改「马上抢」（当前推荐）② 维持现状

【为什么】1. 按钮文案改动随时可回滚 → 所以按轻决策节奏走即可。

【为什么不选别的】维持现状：代价是转化优化窗口往后拖一周。

【换挡条件】若 7 天转化不升 → 换回原文案；复盘日 2026-09-12

【最可能翻车的点】若新文案让老客困惑、首日转化反降，本改动落空——不对就改回。不同意就怼，我当场对。

（档案已存：./决策记录/DR-20260905-cta.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）
进度：第 1 轮 · 快轨直接收敛 · 还差：可收敛｜ 本轮跳过：探讨轮（用户要快） ｜ 假设新增：0 项已挂账
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
    # v5.0 R-2 信封-台面边界：组合文本=头部信封（含黑话）+ 台面（干净）+ 尾部机器段（含黑话）
    COMBO = ("【意图分类】产品决策·验证轨\n归位透出（闸口A）：判×现有单品 → S3\n身份层已核\n---\n"
             + GOOD_FULL +
             "\n---\n**机器闸口结果**：闸口C 身份层 PASS｜闸口D 台面 PASS（信封区豁免词：归位/闸口/身份层/验证轨）\n")
    table, envelope = split_publish(COMBO)
    chk("R-2 边界切分：台面区不含信封头尾（信封含「归位」，台面不含）",
        "归位" in envelope and "归位" not in table)
    p_combo = check_full(table, "full")
    chk("R-2 发布文本（信封区黑话豁免）台面区 T7 全过", not any("T7" in x for x in p_combo))
    # 台面区被污染 → 仍拦（豁免≠盲区）
    COMBO_BAD = COMBO.replace("先跟你确认两件事", "这事按归位到 S3 落格处理")
    table_bad, _ = split_publish(COMBO_BAD)
    p_bad = check_full(table_bad, "full")
    chk("R-2 台面区出现「归位/落格」仍被拦（豁免只在信封区）", any("T7" in x for x in p_bad))
    # 表格分隔线 |---| 不误判为信封锚（含表格的死因区完整保留在台面区）
    COMBO_TBL = COMBO.replace("- 轻量化改造：死于换线成本回收期超出预算窗。\n", "")
    COMBO_TBL = COMBO_TBL.replace("【为什么不选别的】\n", "【为什么不选别的】\n| 选项 | 死于 |\n|---|---|\n| 改造 | 死于预算 |\n")
    table_tbl, _ = split_publish(COMBO_TBL)
    chk("R-2 markdown 表格分隔行不误判信封锚（死因表格留在台面区）", "| 改造 | 死于预算 |" in table_tbl)
    # v5.0 T10/T11（四区增量：候选区+进度行——先红后绿）
    p_t10a = check_full(GOOD_FULL.replace("【候选选项】① 砍B线＋60天缓冲（当前推荐）② 收缩到A/C线主力渠道 ③ 维持现状\n\n", ""), "full")
    chk("T10 缺候选区被拦", any("T10" in x for x in p_t10a))
    p_t10b = check_full(GOOD_FULL.replace(
        "【候选选项】① 砍B线＋60天缓冲（当前推荐）② 收缩到A/C线主力渠道 ③ 维持现状",
        "【候选选项】① 砍B线＋60天缓冲"), "full")
    chk("T10 候选区仅 1 项且缺维持现状被拦", any("T10" in x for x in p_t10b))
    p_t11a = check_full(GOOD_FULL.replace(
        "进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）｜ 本轮跳过：无 ｜ 假设新增：1 项已挂账\n",
        ""), "full")
    chk("T11 缺进度行被拦", any("T11" in x for x in p_t11a))
    p_t11b = check_full(GOOD_FULL.replace(
        "进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）｜ 本轮跳过：无 ｜ 假设新增：1 项已挂账",
        "进度：第 3 轮 · 还差：渠道合约条码门槛"), "full")
    chk("T11 进度行缺步骤段被拦（格式=轮次 · 步骤 · 还差）", any("T11" in x for x in p_t11b))
    p_t11c = check_full(GOOD_FULL + "（此行在进度行之后）", "full")
    chk("T11 进度行不在末行被拦（末行固定）", any("T11" in x for x in p_t11c))
    p_t11d = check_full(GOOD_FULL.replace(
        "进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）｜ 本轮跳过：无 ｜ 假设新增：1 项已挂账",
        "进度：第 3 轮 · 初步版已出待你怼 · 还差：渠道合约条码门槛（已问待答）"), "full")
    chk("T11 缺跳步自曝尾巴被拦（M9-3 前移台面区：跳过/假设挂账写了才算声明）", any("自曝" in x for x in p_t11d))
    # v5.0 R-3 澄清轮断言
    five_q = ("这是卖不动诊断的准备轮。先补几个信息：上市多久了？月销多少？渠道构成是什么？复购高吗？竞品是谁？\n"
              "进度：归位中 · 信息收集 · 还差：五个关键输入")
    c5 = check_clarify(five_q)
    chk("R-3 五问倾泻被拦（R1 事故复现）", c5 is not None and any("R3" in x for x in c5))
    two_q = "先确认两件事：上市多久了？月销大概多少？\n进度：归位中 · 澄清动作对象 · 还差：上市时长与月销"
    c2 = check_clarify(two_q)
    chk("R-3 两问+进度行合规放行", c2 == [])
    nested = ("请把动销数据给我：①近30天销量 ②各渠道占比 ③自然动销 ④复购 ⑤退货 ⑥毛利 ⑦库存 ⑧投产比 ⑨客单价？\n"
              "进度：归位中 · 信息收集 · 还差：动销九项")
    cn = check_clarify(nested)
    chk("R-3 一问内嵌 9 子项按 9 问计被拦（单问信息量缝隙）", cn is not None and any("R3" in x for x in cn))
    chk("R-3 四区文本不触发澄清轮断言（探讨邀请不是补问）", check_clarify(GOOD_FULL) is None)
    c_jargon = check_clarify("这个品归位是 S3 吗？月销多少？\n进度：归位中 · 澄清场景号 · 还差：场景确认")
    chk("R-3 澄清轮黑话被拦", c_jargon is not None and any("T7" not in x and "黑话" in x for x in c_jargon))
    c_noprog = check_clarify("先确认两件事：上市多久了？月销大概多少？")
    chk("R-3 澄清轮缺进度行被拦（M3 每轮末行）", c_noprog is not None and any("进度行" in x for x in c_noprog))
    # ── W-07 T8 双态：初步版占位 / 终版 DR 文件存在性 ──
    # 终版好样本：格式合法+目录里真实存在 → PASS（先造真实 DR 文件）
    import tempfile
    _wd = tempfile.mkdtemp(prefix="co_t8_")
    open(os.path.join(_wd, "DR-20260905-bline.html"), "w", encoding="utf-8").write("x")
    p_arch = check_full(GOOD_FULL, "full", _wd)   # GOOD_FULL 的档案行指向 bline.html
    chk("W-07 终版 DR 文件真实存在（--dr-dir）→ PASS T8", not any("T8" in x for x in p_arch))
    # 初步版占位：明确「档案未落盘」+ 无 DR 文件名 → PASS
    DRAFT = GOOD_FULL.replace(
        "（档案已存：./决策记录/DR-20260905-bline.html——9 字段/风险六维/假设/反方/探讨轨迹齐全）",
        "（档案未落盘：初步版，收敛并落盘后补 DR 编号与结论——探讨阶段不强制落档案）")
    p_draft = check_full(DRAFT, "full", _wd)
    chk("W-07 初步版占位「档案未落盘」（无 DR 文件名）→ PASS T8", not any("T8" in x for x in p_draft))
    # 初步版占位却带 DR 文件名 → 拦
    p_draft_fake = check_full(DRAFT.replace("档案未落盘：初步版",
                                            "档案未落盘：初步版 DR-20260905-bline.html"), "full", _wd)
    chk("W-07 初步版占位冒带 DR 文件名 → 拦（占位应明确未落盘）", any("T8" in x for x in p_draft_fake))
    # 真缺口样本：格式合法但不存在的 DR 路径（W-07 验收核心）→ 拦
    GHOST = GOOD_FULL.replace("DR-20260905-bline.html", "DR-20260905-ghost.html")
    p_ghost = check_full(GHOST, "full", _wd)
    chk("W-07 真缺口：格式合法但文件不存在的 DR 路径 → 拦", any("T8" in x and "不存在" in x for x in p_ghost))
    # 不传 --dr-dir：只保格式，不验存在（good 全量断言不受影响）
    chk("W-07 无 --dr-dir 只保格式（兼容合式引用）", not any("T8" in x for x in check_full(GHOST, "full", None)))
    print("self: 台面校验器 v5.0（T0-T11 双模式+%d 禁词+双要素反方+B类标注+信封边界+澄清轮+候选区+进度行+跳步自曝+T8双态） %s" %
          (len(BANLIST), "PASS✓" if ok else "FAIL✗"))
    return ok


def strip_envelope_tail(text):
    """非四区文本的信封尾剥离：首个机器锚行（机器闸口/系统日志/---）起视为信封，返回 (台面体, 信封尾)。"""
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if ENVELOPE_TAIL_RE.match(ln.strip()):
            return "".join(lines[:i]), "".join(lines[i:])
    return text, ""


def check_publish(text, scene, mode_arg, dr_dir=None):
    """R-1 发布校验：校验对象=最终发布组合文本。有徽章 → R-2 边界切分后台面区全文断言；
    无徽章 → R-3 澄清轮轻断言（信封尾豁免）。返回 exit code（0=PASS / 1=FAIL）。"""
    table, envelope = split_publish(text)
    if BADGE_RE.search(table):
        if scene == "C类":
            print("PASS — C 类输出（只提醒不决策）不适用四区台面校验（发布模式）")
            print("覆盖边界：本次=C 类形态判定（不决策不四区）；未覆盖=提醒内容本身的准确性（无断言）。")
            return 0
        mode, badge = resolve_mode(table, mode_arg)
        problems = check_full(table, mode, dr_dir) + check_btag(table, scene)
        if problems:
            print("FAIL — 发布文本台面区缺 %d 项（模式=%s%s；信封区 %d 字已豁免）：" %
                  (len(problems), mode, "，徽章=[%s]" % badge if badge else "，未标徽章", len(envelope)))
            for x in problems:
                print("  ❌ " + x)
            print("覆盖边界：本次=发布组合文本的台面区 T1-T11（信封区黑话豁免边界已划）；未覆盖=DR 档案结构（走 decision-record.py）。")
            return 1
        print("PASS — 发布文本校验过（%s态：台面区 T1-T11 全过；信封区 %d 字豁免黑话断言）%s" %
              ("完整" if mode == "full" else "压缩", len(envelope),
               "，B类标注在场" if scene in B_TAGS else ""))
        print("覆盖边界：本次=发布组合文本的台面区 T1-T11（信封区黑话豁免边界已划）；未覆盖=DR 档案结构（走 decision-record.py）。")
        return 0
    body, env_tail = strip_envelope_tail(text)
    cl = check_clarify(body)
    if cl is None:
        print("PASS — 非四区形态且无补问（确认/透出轮）：R-3 不适用，放行")
        print("覆盖边界：本次=确认/透出轮零补问形态；未覆盖=四区断言（出四区时须再走全量校验）。")
        return 0
    if cl:
        print("FAIL — R-3 澄清轮断言 %d 项（信封尾 %d 字已豁免）：" % (len(cl), len(env_tail)))
        for x in cl:
            print("  ❌ " + x)
        print("覆盖边界：本次=澄清轮 R-3（补问 ≤2 按疑问句+子项计数、零黑话）；未覆盖=四区断言（本轮非四区形态）。")
        return 1
    print("PASS — 澄清轮断言过（补问 ≤2 + 零黑话；信封尾 %d 字豁免）" % len(env_tail))
    print("覆盖边界：本次=澄清轮 R-3（补问 ≤2 按疑问句+子项计数、零黑话）；未覆盖=四区断言（本轮非四区形态）。")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="pm-strategist 台面输出校验（四区 T1-T9 断言组；DR 档案校验唯一入口=decision-record.py）")
    ap.add_argument("input", nargs="?", help="台面输出文本文件路径，或 - 读 stdin")
    ap.add_argument("--mode", choices=["full", "light"], default=None,
                    help="full=完整态（T2≥2）；light=压缩/快轨态（T2≥1）。缺省按首行徽章路由，再缺省 full")
    ap.add_argument("--scene", choices=["S1", "S2", "S3", "S4", "S5", "C类"], default=None,
                    help="场景号（S4/S5 必传——B 类跨部门断言的输入来源；缺省=断言不触发=漏检）")
    ap.add_argument("--publish", action="store_true",
                    help="R-1 发布校验模式：校验对象=最终发布组合文本（信封+台面）——R-2 信封区黑话豁免/台面区全文生效；无徽章=澄清轮走 R-3 轻断言")
    ap.add_argument("--dr-dir", dest="dr_dir", default=None,
                    help="W-07 T8：DR 落盘目录（给定时终版档案提示行还校验 DR 文件真实存在；缺省只保格式校验）")
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
    if a.publish:
        return check_publish(text, scene, a.mode, a.dr_dir)
    if scene == "C类":
        print("PASS — C 类输出（只提醒不决策）不适用四区台面校验")
        print("覆盖边界：本次=C 类形态判定（不决策不四区）；未覆盖=提醒内容本身的准确性（无断言）。")
        return 0
    mode, badge = resolve_mode(text, a.mode)
    problems = check_full(text, mode, a.dr_dir) + check_btag(text, scene)
    if problems:
        print("FAIL — 台面校验缺 %d 项（模式=%s%s）：" % (len(problems), mode,
              "，徽章=[%s]" % badge if badge else "，未标徽章"))
        for x in problems:
            print("  ❌ " + x)
        print("覆盖边界：本次=台面草稿 T1-T11（四区形态%s）——未覆盖=会话信封与最终发布组合文本"
              "（发布前须走 --publish 三步硬序列）。" % ("，B类断言已触发" if scene in B_TAGS else ""))
        return 1
    print("PASS — 台面四区齐全（%s态：T1-T11 过，零黑话，无裸百分比）%s" %
          ("完整" if mode == "full" else "压缩", "，B类标注在场" if scene in B_TAGS else ""))
    print("覆盖边界：本次=台面草稿 T1-T11（四区形态%s）——未覆盖=会话信封与最终发布组合文本"
          "（发布前须走 --publish 三步硬序列）。" % ("，B类断言已触发" if scene in B_TAGS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
