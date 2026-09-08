#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decision-record.py — 决策档案（DR）：收敛闸 + 9字段校验 + v0.7 HTML 落盘（DR 校验唯一入口）

架构定界（v4.4.0，终稿 §3.6/§7）：check_output.py 只管台面四区；本脚本是 DR 校验**唯一入口**——
要点文件校验 = 9 字段 + 两段（探讨轨迹[收敛闸必填] + 归位[只读]）+ 质量下限（选项含不做/已定须拍板
原文/反方双要素/风险不全绿/依据有出处），校验通过渲染自包含 HTML 决策档案。

档案模板（v0.7）：暗黑横版（屏幕）+ 浅色（打印 @media print 自动切换；dr_theme:"light" 可选浅色屏幕）；
双主题 = 同模板两套 CSS 变量。信息守恒：9 字段/反方/六维（含未命中理由）/假设/探讨轨迹/归位一项不少；
关键内容点 self_test 7/7 grep 断言。密度分档：🔴/实质=8 组件全量；快轨/🟢轻决策=紧凑档案。
旧模板回退开关：config/pm_settings.json `dr_theme_legacy: true`。
渲染可选键（不填组件降级，不伪造）：置信度（中高 · 依据句）/下一步/落选死因（含"评分=NN"才画横条）/
换挡条件/可逆性。

用法（脚本不在用户工程目录，须带 skill 目录前缀——先 `SKILL_DIR=<skill 安装路径>` 再 `python3 "$SKILL_DIR/scripts/decision-record.py" …`）:
  python3 "$SKILL_DIR/scripts/decision-record.py" --template              # 打印文本模板（聊天内引导用）
  python3 "$SKILL_DIR/scripts/decision-record.py" <要点文件>               # 收敛闸+校验+渲染+落盘 HTML
  cat 要点.txt | python3 "$SKILL_DIR/scripts/decision-record.py" - --out /tmp/x
  python3 "$SKILL_DIR/scripts/decision-record.py" <要点文件> --stdout      # 只打印 HTML 不落盘
  python3 "$SKILL_DIR/scripts/decision-record.py" --self
退出码: 0=渲染成功; 1=缺必填/收敛闸/校验失败; 2=读入错误
"""
import sys, os, re, json, argparse, datetime, tempfile, importlib

DR_DATE = datetime.date.today().strftime("%Y%m%d")
FIELDS = ["问题", "选项", "决定", "依据", "反方意见", "风险", "假设清单", "复盘日期", "状态"]
REQUIRED = list(FIELDS)  # v4.4.1 盲审B-2：9字段全必填（名实相符，对齐 fm-02 自查点"9字段一个不缺"）
SECTION_FIELDS = ["探讨轨迹", "归位"]  # v4.4.0：探讨轨迹=收敛闸必填；归位=只读审计段
OPTIONAL = ["决策链", "置信度", "下一步", "落选死因", "换挡条件", "可逆性"]  # 决策链=复合决策；其余渲染增强
# ── W-13 渲染键齐备度：台面四区→DR 的手工搬运键（缺键静默=漏进档案，须上台提示） ──
RENDER_KEYS = [("置信度", "四区【建议】置信二极管·依据"), ("下一步", "四区【建议】下一步（你）"),
               ("落选死因", "四区【为什么不选别的】"), ("换挡条件", "四区【换挡条件】"),
               ("可逆性", "归位段内可逆性")]
STATUS = ["草案", "已定", "复盘", "关闭"]
HINTS = {
    "问题": "一句决策问题（含场景号与决策者/截止时间）",
    "选项": "≥2个，必须含不做/维持现状",
    "决定": "用户拍板原文（以「用户拍板：」开头）；未拍板写推荐倾向",
    "依据": "引用哪个 ref/fm 的哪条（标注文件与条目）",
    "反方意见": "最强反方+什么数据/条件会推翻本决定",
    "风险": "6维度命中的风险点+验证方式（不替用户做风险结论）",
    "假设清单": "每条 ⚠️ 前缀「假设·待验证」；确无假设写「无——输入已全部确认」",
    "复盘日期": "YYYY-MM-DD",
    "状态": "草案/已定/复盘/关闭（快轨决策在状态后加「·快轨」= 橙色徽章）",
    "探讨轨迹": "【收敛闸必填·R-5 层1】必须含用户原话引用「…」。①初步版→用户反驳（引原话「…」）→结论如何更新（验证轨：用户判断→军师校准/反对→用户再驳→是否改判）②用户跳过探讨：原因=直接要结论/快轨/连续降频 ＋ 用户原话引用「…」（引「快轨」须与状态字段·快轨后缀一致）。无原话引用的叙述（「反驳过/更新过」）不算收敛证据",
    "归位": "【必填·只读】动作×对象 → 场景号 ｜ 出口 ｜ 理由一句话 ｜ 可逆性=🔴/🟡/🟢（落盘后不许事后改写）",
}
OPTIONAL_HINTS = {
    "决策链": "（可选，仅复合决策填；引用关联 DR id，如 DR-20260902-001、DR-20260902-002）",
    "置信度": "（渲染可选：三档词+可选依据，格式「中高 · 一句依据」→ 结论卡仪表）",
    "下一步": "（渲染可选：第一动作一句话 → 结论卡「下一步（你）」框）",
    "落选死因": "（渲染可选：选项名＝死于…；分号分隔；含「评分=NN」才画对比横条，无评分不伪造分值）",
    "换挡条件": "（渲染可选：信号+阈值 → 改判方向一句话 → 换挡时间线）",
    "可逆性": "（渲染可选：🔴/🟡/🟢，也可写在归位段内 → 刊头胶囊；🟢或「·快轨」=紧凑档案）",
}
TEMPLATE = "# DR-%s-<slug>（日期已自动填入；slug 默认=对象+动作（归位原语对），可 --slug 覆盖）\n" % DR_DATE + \
    "".join("- %s：%s\n" % (f, ("【待补充】" + HINTS[f])) for f in FIELDS) + \
    "".join("- %s：%s\n" % (f, ("【待补充】" + HINTS[f])) for f in SECTION_FIELDS) + \
    "".join("- %s：%s\n" % (k, v) for k, v in OPTIONAL_HINTS.items())

# ── 反方双要素判定（与台面 T5 同标准：具体条件 × 可反驳出口） ──
CON_RE = r"如果|若|一旦|假如|前提是|除非|当.{0,6}(时|成立|发生|出现)|在.{0,10}情况下"
TRIGGER_RE = r"则|就会|将会|导致|使得|造成|引发|即|一.{0,4}就"
FALSIFY_STRONG = (r"推翻|证伪|不成立|失效|站不住|需重估|需重做|重算|落空|白做|白费|前功尽弃|"
                  r"泡汤|打水漂|适得其反|得不偿失|弄巧成拙|反噬|不再成立|改变.{0,4}结论|"
                  r"推翻条件|什么数据|什么条件|什么信号")
FALSIFY_NEG = r"砍错|做错|误判|误杀|错杀|判断失误|决策失误|证明.{0,6}错|说明.{0,6}错|压根不该|不该砍|不该做"
RISK_DIMS = [("法规", "#4cc9f5"), ("市场", "#a78bfa"), ("竞争", "#ff6b8a"),
             ("供应链", "#ffb454"), ("财务", "#3fd0b6"), ("组织", "#6b7cff")]
DIM_KWS = {
    "法规": ["法规", "合规", "宣称", "备案", "监管", "标签", "法务"],
    "市场": ["市场", "需求", "趋势", "季节", "渗透"],
    "竞争": ["竞争", "竞品", "对手", "替代", "跟价"],
    "供应链": ["供应链", "产能", "原料", "库存", "交期", "备货", "断货"],
    "财务": ["财务", "毛利", "成本", "回本", "现金流", "预算", "盈亏"],
    "组织": ["组织", "人力", "团队", "人员", "排产", "培训"],
}
B_TAGS = {"S4": "最终定价决策需跨部门确认（财务/销售/渠道/管理层）",
          "S5": "最终上市决策需跨部门确认（销售/市场/供应链/管理层）"}


def parse_points(text):
    """key: value / key：value 逐行解析（全半角冒号兼容）；JSON 对象也认；
    无冒号后续行并入上一字段值（探讨轨迹多步/假设多行）。"""
    pts = {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {k: str(v) for k, v in obj.items()}
    except (ValueError, TypeError):
        pass
    known = FIELDS + SECTION_FIELDS + OPTIONAL
    last = None
    for line in text.splitlines():
        raw = line.strip().lstrip("-• ")
        if not raw or raw.startswith("#"):
            continue
        matched = False
        for sep in ("：", ":"):
            if sep in raw:
                k, v = raw.split(sep, 1)
                k = k.strip()
                if k in known:
                    pts[k] = (pts.get(k, "") + "\n" + v.strip()).strip() if k in pts and pts.get(k) else v.strip()
                    last = k
                    matched = True
                break
        if not matched and last and raw:
            pts[last] = (pts.get(last, "") + "\n" + raw).strip()
    return pts


def render_key_status(pts):
    """台面四区→DR 手工搬运键的齐备度（W-13）：返回 (齐全键[], 缺失键+来源[])。
    缺键静默=漏进档案，落盘输出须明确列出。"""
    present, missing = [], []
    for k, src in RENDER_KEYS:
        v = (pts.get(k) or "").strip()
        if v and "【待补充】" not in v:
            present.append(k)
        else:
            missing.append("%s（来源=%s）" % (k, src))
    return present, missing


def _load_session_state(path=None):
    """读 session_state（R-5 层3：状态断言）。返回 (state, err)；路径解析与 state-gate.py 同序：
    --state 参数 > PM_STRATEGIST_STATE 环境变量 > <skill根>/config/session_state.json。
    fail-closed 与 state-gate 同标：缺 schema_version / 版本不符 → 拒读——闸外手写最小 JSON
    （如 {"phase":"S6_CONVERGED"}）不算收敛证据。"""
    p = path or os.environ.get("PM_STRATEGIST_STATE") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "session_state.json")
    if not os.path.isfile(p):
        return None, "session_state 不存在（%s）" % p
    try:
        st = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, "session_state 损坏（%s）" % e
    if not isinstance(st, dict):
        return None, "session_state 不是 JSON 对象"
    v = st.get("schema_version")
    if not v:
        return None, "session_state 缺 schema_version（闸外伪造嫌疑）——须 state-gate.py --init 生成后逐门推进"
    import importlib.util
    sys.dont_write_bytecode = True  # 动态加载不落 __pycache__（保持包目录零运行时产物）
    spec = importlib.util.spec_from_file_location(
        "state_gate_mod", os.path.join(os.path.dirname(os.path.abspath(__file__)), "state-gate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if v != mod.SCHEMA_VERSION:
        return None, "session_state schema_version=%s ≠ %s（版本落后或伪造）——须 --init 重建" % (v, mod.SCHEMA_VERSION)
    return st, None


def validate(pts, state=None, state_err=None):
    """收敛闸（R-5 三层断言）+ 9 字段 + 质量下限。返回 (missing, problems)。

    三层断言（v5.0#5，未收敛落盘 0 起）：
      层1 文本：探讨轨迹必须含用户原话引用「…」（反驳记录与跳过声明同标准；
        「初步版出过、用户反驳过」这类无原话叙述不算收敛证据——关键词白名单已移除）
      层2 证据：跳过声明须 原因=X ＋ 原话引用（或快轨与状态字段互证）
      层3 状态：状态=草案 时 session_state.phase 必须 = S6_CONVERGED（fail-closed）"""
    def _blank(v):
        v = (v or "").strip()
        return (not v) or v.startswith("【待补充】")
    missing = [f for f in REQUIRED + SECTION_FIELDS if _blank(pts.get(f))]
    problems = []
    if "探讨轨迹" not in missing:
        tt = pts.get("探讨轨迹", "").strip()
        quoted = bool(re.search(r"「[^」]{2,}」|“[^”]{2,}”|\"[^\"]{2,}\"", tt))
        if "跳过探讨" in tt or ("跳过" in tt and "原因" in tt):
            has_reason = bool(re.search(r"原因\s*[=:＝]\s*\S+", tt))
            # v4.4.1 盲审B-4：引「快轨」作证据须与状态字段「·快轨」后缀互证（防字面编造绕过）
            fast_ok = "快轨" in tt and "快轨" in pts.get("状态", "")
            if not (has_reason and (quoted or fast_ok)):
                problems.append("探讨轨迹跳过声明缺可观测证据（须含 原因=X ＋ 用户原话引用「…」；引「快轨」作证据须与状态字段·快轨后缀互证）——诚实闸：自报口径、复盘可审计")
        elif not quoted:
            # R-5 层1：移除关键词白名单（「反驳|初步|更新」字面命中≠收敛证据），原话引用是唯一硬证据
            problems.append("探讨轨迹无用户原话引用「…」（R-5 层1：初步版→用户反驳→结论更新必须引用用户原话；"
                            "「初步版出过、用户反驳过」这类无原话叙述不算收敛证据）")
        # v4.4.1 盲审B-4：不可逆决策不允许无原话记录收敛
        if _rev_of(pts) == "🔴" and not quoted:
            problems.append("可逆性=🔴（不可逆决策）的探讨轨迹须至少一处用户原话引用「…」——不可逆决定不允许无记录收敛")
    if "归位" not in missing:
        gy = pts.get("归位", "")
        if not (re.search(r"[×x]", gy) and re.search(r"S[1-5]|C类|跨域", gy)):
            problems.append("归位段格式不对（应为：动作×对象 → 场景号 ｜ 出口 ｜ 理由一句话 ｜ 可逆性=🔴/🟡/🟢）")
    st = pts.get("状态", "")
    st_base = st.split("·")[0].strip()
    if st_base and st_base not in STATUS:
        problems.append("状态非法（应为 草案/已定/复盘/关闭，可加「·快轨」后缀；当前: %s）" % st[:20])
    # ── R-5 层3：状态断言——草案落盘须状态机已收敛（已定/复盘/关闭=终态或历史档案重渲，不查）──
    if st_base == "草案":
        if state_err:
            problems.append("R-5 层3 状态断言：状态=草案但 session_state 不可读（%s）——"
                            "草案落盘须状态机在 S6_CONVERGED；先 state-gate.py --init 逐门推进（fail-closed，不静默豁免）" % state_err)
        elif state is None:
            problems.append("R-5 层3 状态断言：状态=草案但未提供 session_state——"
                            "草案落盘须状态机在 S6_CONVERGED（快轨走 S4→S6 跳过声明门，同样到 S6）")
        elif state.get("phase") != "S6_CONVERGED":
            problems.append("R-5 层3 状态断言：session_state.phase=%s ≠ S6_CONVERGED——"
                            "未收敛不得落盘草案（先 state-gate.py --to S6_CONVERGED 过门；critical 补齐后强制回 S4 重出）"
                            % state.get("phase"))
    d = pts.get("复盘日期", "")
    if d and "待补充" not in d:
        if not re.search(r"\d{4}-\d{2}-\d{2}", d):
            problems.append("复盘日期格式应为 YYYY-MM-DD（当前: %s）" % d[:20])
    chain = pts.get("决策链", "")
    if chain and "可选" not in chain and "待补充" not in chain:
        ids = re.findall(r"DR-\d{8}[\w\-]*", chain)
        if not ids:
            problems.append("决策链字段应引用关联 DR id（如 DR-20260902-001，多个用顿号分隔）；当前: %s" % chain[:30])
    # ── 质量下限（自 check_output.py check_dr 移入：DR 校验唯一入口承接，防绿灯幻觉回潮） ──
    opt = pts.get("选项", "")
    if opt and ("不做" not in opt and "维持现状" not in opt):
        problems.append("选项未含「不做/维持现状」（不做是每个决策的真实备选）")
    dec = pts.get("决定", "")
    if re.search(r"选\s*项\s*[0-9①②③④⑤⑥⑦⑧⑨⑩]|选\s*[0-9]{1,2}\s*[、号）)]|其余同上", dec):
        problems.append("M7-1 决定字段禁编号指代（「选项2/选3/其余同上」读档案的人无上文可查；"
                        "必须完整句写明选了什么）")
    if "已定" in st and "用户拍板：" not in dec:
        problems.append("状态已定但决定字段无「用户拍板：」原文（无拍板原文不得写已定）")
    rev = (pts.get("复盘日期", "") or "").strip()
    if "已定" in st and (not rev or "待补充" in rev):
        problems.append("状态已定但缺复盘日期（fm-02：没有复盘日期的 DR 不许标已定）")
    con = (pts.get("反方意见", "") or "").strip()
    if not con or con.startswith("无"):
        problems.append("反方意见为空/「无」——反方非空且必须具体到可反驳")
    else:
        out_ok = bool(re.search(FALSIFY_STRONG, con)) or bool(re.search(FALSIFY_NEG, con))
        ok_cond = bool(re.search(CON_RE, con)) and out_ok
        ok_trigger = bool(re.search(TRIGGER_RE, con)) and out_ok
        if not (ok_cond or ok_trigger):
            miss = []
            if not (bool(re.search(CON_RE, con)) or bool(re.search(TRIGGER_RE, con))):
                miss.append("①具体条件（若/一旦/竞品降价则…，什么事实成立）")
            if not out_ok:
                miss.append("②可反驳出口（本决定 失效/被推翻/砍错/做错，或推翻条件=拿到<什么数据>）")
            problems.append("反方意见是稻草人（缺 %s）——模板：若<什么事实成立>，则本决定<失效/需重估/砍错>；"
                            "推翻条件=拿到<什么数据>" % "、".join(miss))
    riskv = (pts.get("风险", "") or "").strip()
    if riskv:
        segs = [x for x in re.split(r"[；;\n]", riskv) if x.strip()]
        if segs and all("未命中" in x for x in segs):
            problems.append("风险全部「未命中」——至少 1 个真实风险点，或诚实论证为何全未命中")
    basis = (pts.get("依据", "") or "").strip()
    if basis and not re.search(r"ref-0[1-6]|fm-0[1-6]", basis):
        problems.append("依据缺 ref/fm 引用格式（应标注 ref-0X/fm-0X 哪条）")
    return missing, problems


def render_text(pts):
    lines = ["# DR-%s-<slug>（日期由脚本自动填入；slug 默认=对象+动作（归位原语对），--slug 可覆盖）" % DR_DATE]
    for f in FIELDS + SECTION_FIELDS:
        v = pts.get(f, "").strip() or "【待补充】%s" % HINTS[f]
        lines.append("- %s：%s" % (f, v))
    for k in OPTIONAL:
        if pts.get(k, "").strip():
            lines.append("- %s：%s" % (k, pts[k].strip()))
    return "\n".join(lines)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def _tick(v):
    """齐性自检逐字段实况打勾（v4.4.1 盲审B-2：禁止无条件绿勾）。"""
    v = (v or "").strip()
    return "✓" if (v and not v.startswith("【待补充】")) else "✗缺"


def _rev_of(pts):
    """可逆性：显式键 > 归位段内。返回 🔴/🟡/🟢 或 None。"""
    v = pts.get("可逆性", "") or ""
    if not v:
        m = re.search(r"可逆性\s*[=:＝]\s*([🔴🟡🟢])", pts.get("归位", ""))
        v = m.group(1) if m else ""
    return v if v in ("🔴", "🟡", "🟢") else None


def _is_compact(pts):
    if "快轨" in pts.get("状态", ""):
        return True
    return _rev_of(pts) == "🟢"


def _force_full(pts):
    """M7 ②：判类（S3）与「结论是下游不可逆前提」强制全量档——可逆≠轻量（诊断本身可逆，
    但下游动作拿它当前提时，档案信息密度不许降）。"""
    if _scene(pts) == "S3":
        return True
    blob = pts.get("问题", "") + pts.get("归位", "") + pts.get("换挡条件", "")
    return ("下游不可逆" in blob) or ("不可逆前提" in blob)


def _default_slug(pts):
    """M12 脚本默认值层：无 --slug 时 slug=对象+动作（归位字段原语对，
    命名规范 DR-YYYYMMDD-<对象≤10字>-<动作≤6字>）；归位无原语对 → 退问题字段清洗截 12
    （文件名 ≤30 字硬约束——R2 实测旧默认截 24 字产出 40+ 字文件名）。"""
    m = re.search(r"([增删改择判])\s*[×xX]\s*([\u4e00-\u9fff]{1,10})", pts.get("归位", "") or "")
    if m:
        return "%s-%s" % (m.group(2)[:10], m.group(1)[:6])
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", pts.get("问题", ""))[:12] or "dr"


def _scene(pts):
    blob = pts.get("问题", "") + pts.get("归位", "")
    m = re.search(r"S([1-5])", blob)
    return ("S" + m.group(1)) if m else None


def _gauge(conf):
    """结论卡 SVG 仪表：三档词直显（高/中高/中档）。口径变更(W-03)：取消档位→百分比换算——
    旧设计允许档案显百分比读数，机械换算(中=50%/中高=70%/高=90%)属伪造精度，改为大字显档位词；
    弧线弧长仅作定性视觉，不标读数。非 bug 修复。"""
    m = re.search(r"(中高|高|中)", conf or "")
    if not m:
        return ""
    frac = {"高": 0.9, "中高": 0.7, "中": 0.5}[m.group(1)]
    ang = (180 - 180 * frac) * 3.141592653589793 / 180.0
    x, y = round(110 + 76 * __import__("math").cos(ang), 1), round(108 - 76 * __import__("math").sin(ang), 1)
    basis = ""
    parts = re.split(r"[·；;]", conf, maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        basis = '<div class="basis">置信度依据：%s</div>' % esc(parts[1].strip())
    label = m.group(1) + ("档" if m.group(1) != "高" else "")
    return ('<svg width="190" height="112" viewBox="0 0 220 130" role="img" aria-label="置信度">'
            '<defs><linearGradient id="gg" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#6b7cff"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>'
            '<path d="M34,108 A76,76 0 0 1 186,108" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="6" stroke-linecap="round"/>'
            '<path d="M34,108 A76,76 0 0 1 %s,%s" fill="none" stroke="url(#gg)" stroke-width="6" stroke-linecap="round"/>'
            '<text x="62" y="26" font-size="10.5" fill="#8b93a1" text-anchor="middle">中</text>'
            '<text x="158" y="26" font-size="10.5" fill="#8b93a1" text-anchor="middle">中高</text>'
            '<text x="196" y="96" font-size="10.5" fill="#8b93a1" text-anchor="middle">高</text>'
            '<text x="110" y="85" font-size="27" fill="#e9ebf2" text-anchor="middle" class="num" font-weight="700">%s</text>'
            '<text x="110" y="106" font-size="10.5" fill="#8b93a1" text-anchor="middle">置信度 · 三档词</text></svg>' % (x, y, label)), basis


def _radar_and_hits(riskv):
    segs = [x.strip() for x in re.split(r"[；;\n]", riskv or "") if x.strip()]
    info = {dim: {"hit": False, "lv": 0, "note": ""} for dim, _ in RISK_DIMS}
    for seg in segs:
        for dim, _ in RISK_DIMS:
            hit_dim = seg.startswith(dim) or any(k in seg[:14] for k in DIM_KWS[dim])
            if hit_dim and not info[dim]["hit"]:
                info[dim]["hit"] = True
                info[dim]["note"] = seg
                if "未命中" not in seg:
                    mlv = re.search(r"(高|中|低)", seg.replace("高风险", ""))
                    info[dim]["lv"] = {"高": 3, "中": 2, "低": 1}.get(mlv.group(1), 2) if mlv else 2
                break
    cx, cy, R = 160.0, 125.0, 98.0
    import math
    pts, svg_texts, html_items, misses = [], [], [], []
    for i, (dim, color) in enumerate(RISK_DIMS):
        a = math.radians(90 - 60 * i)
        vx, vy = cx + R * math.cos(a), cy - R * math.sin(a)
        d = info[dim]
        f = {0: 0.0, 1: 0.33, 2: 0.66, 3: 1.0}[d["lv"]]
        pts.append("%.1f,%.1f" % (cx + f * (vx - cx), cy + f * (vy - cy)))
        ax, ay = (cx + (R + 22) * math.cos(a), cy - (R + 22) * math.sin(a))
        anchor = "middle" if abs(ax - cx) < 30 else ("start" if ax > cx else "end")
        strong = ' font-weight="700"' if d["lv"] else ""
        fill = color if d["lv"] else "#5b6270"
        label = dim + (" · %s" % {1: "低", 2: "中", 3: "高"}[d["lv"]] if d["lv"] else " · 未命中")
        rows = '<text x="%.1f" y="%.1f" font-size="11.5" fill="%s" text-anchor="%s"%s>%s</text>'
        svg_texts.append(rows % (ax, ay, fill, anchor, strong, esc(label)))
        note = re.sub(r"^(%s)\s*[：:（(]?" % dim, "", d["note"] or "")
        note = note.replace("未命中", "", 1).strip(" ：:，,。（）—") if "未命中" in (d["note"] or "") else note
        if d["lv"]:
            html_items.append('<div class="item"><span class="dot" style="--c:%s"></span><b>%s</b><span class="lv">命中 · %s</span><p>%s</p></div>'
                        % (color, dim, {1: "低", 2: "中", 3: "高"}[d["lv"]], esc(note or "——")))
        else:
            reason = note or "风险字段未提及——复盘补一句理由"
            misses.append('<div class="m"><span class="dot" style="--c:%s"></span><b>%s · 未命中</b>——%s</div>'
                          % (color, dim, esc(reason)))
    polygon = '<polygon points="%s" fill="#6b7cff" opacity="0.14" stroke="#6b7cff" stroke-width="1.5"/>' % " ".join(pts)
    grid = ('<polygon points="160,27 244.9,76 244.9,174 160,223 75.1,174 75.1,76" fill="none" stroke="rgba(255,255,255,.10)" stroke-width="1"/>'
            '<polygon points="160,59.7 216.6,92.4 216.6,157.6 160,190.3 103.4,157.6 103.4,92.4" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="1"/>'
            '<polygon points="160,92.4 188.3,108.7 188.3,141.3 160,157.6 131.7,141.3 131.7,108.7" fill="none" stroke="rgba(255,255,255,.05)" stroke-width="1"/>'
            '<line x1="160" y1="125" x2="160" y2="27" stroke="rgba(255,255,255,.07)"/><line x1="160" y1="125" x2="244.9" y2="76" stroke="rgba(255,255,255,.07)"/>'
            '<line x1="160" y1="125" x2="244.9" y2="174" stroke="rgba(255,255,255,.07)"/><line x1="160" y1="125" x2="160" y2="223" stroke="rgba(255,255,255,.07)"/>'
            '<line x1="160" y1="125" x2="75.1" y2="174" stroke="rgba(255,255,255,.07)"/><line x1="160" y1="125" x2="75.1" y2="76" stroke="rgba(255,255,255,.07)"/>')
    svg = ('<svg viewBox="0 0 320 262" role="img" aria-label="风险雷达">%s%s%s</svg>' % (grid, polygon, "".join(svg_texts)))
    hitlist = '<div class="hitlist">%s<div class="miss">%s</div></div>' % (
        "".join(html_items), "".join(misses))
    return svg, hitlist


def _shift_conds(shift):
    parts = [x.strip() for x in re.split(r"[；;\n]", shift or "") if x.strip()]
    if len(parts) <= 1 and "\n" in (shift or ""):
        parts = [x.strip() for x in shift.splitlines() if x.strip()]
    return parts


def _shift_full(shift):
    """换挡条件完整 HTML 列表（W-04：SVG 只留短标签，完整条件拆 HTML——不挤压不截断）。"""
    conds = _shift_conds(shift)
    if not conds:
        return ""
    if len(conds) == 1:
        return '<div class="shiftfull"><b>换挡条件：</b>%s</div>' % esc(conds[0])
    lis = "".join('<li>%s</li>' % esc(c) for c in conds)
    return '<div class="shiftfull"><b>换挡条件 · 完整清单：</b><ol>%s</ol></div>' % lis


def _shift_svg(pts):
    shift = (pts.get("换挡条件", "") or "").strip()
    review = pts.get("复盘日期", "") or "待填"
    if not shift:
        return ('<div class="capnote">复盘日 %s——对照「当时前提 vs 实际结果」（fm-04）。</div>' % esc(review))
    return ('<svg width="100%%" viewBox="0 0 720 106" role="img" aria-label="换挡时间线">'
            '<line x1="30" y1="54" x2="700" y2="54" stroke="rgba(255,255,255,.14)" stroke-width="1.5"/>'
            '<circle cx="70" cy="54" r="5" fill="#e9ebf2"/>'
            '<text x="70" y="78" font-size="11.5" fill="#c0c6d2" text-anchor="middle" font-weight="600">%s 决定生效</text>'
            '<rect x="294" y="48" width="12" height="12" rx="2.5" transform="rotate(45 300 54)" fill="#6b7cff"/>'
            '<text x="300" y="36" font-size="11.5" fill="#c0c6d2" text-anchor="middle" font-weight="600">监测</text>'
            '<text x="300" y="15" font-size="11" fill="#8b9bff" text-anchor="middle" font-weight="600">触发条件见下方清单</text>'
            '<text x="300" y="97" font-size="11" fill="#e9ebf2" text-anchor="middle" font-weight="600">触发 → 按换挡条件改判</text>'
            '<circle cx="560" cy="54" r="7" fill="none" stroke="#6b7cff" stroke-width="2.2"/>'
            '<text x="560" y="36" font-size="11.5" fill="#8b9bff" text-anchor="middle" font-weight="700">复盘 %s</text>'
            '<text x="560" y="78" font-size="10.5" fill="#8b93a1" text-anchor="middle">前提 vs 实际结果</text></svg>'
            '<div class="capnote">信号可证伪：口径变化＝提前复盘。</div>'
            '%s'
            % (esc(datetime.date.today().strftime("%m-%d")), esc(review), _shift_full(shift)))


def _bars(dead, allow_bars=True):
    rows = []
    for seg in [x.strip() for x in re.split(r"[；;\n]", dead or "") if x.strip()]:
        m = re.search(r"评分\s*[=:＝]\s*(\d{1,3})", seg)
        name = re.split(r"[＝=：:]", seg, maxsplit=1)[0].strip()
        desc = seg[len(re.split(r"[＝=：:]", seg, maxsplit=1)[0]):].lstrip("＝=：: ").strip()
        if m and allow_bars:
            w = min(int(m.group(1)), 100)
            rows.append('<div class="dbar"><div class="dname">%s</div><div class="dtrack"><div class="dfill" style="width:%d%%"></div></div><div class="dscore num">%d</div><div class="ddesc">%s</div></div>'
                        % (esc(name), w, w, esc(desc)))
        else:
            rows.append('<div class="drow"><b>%s</b>：%s</div>' % (esc(name), esc(desc)))
    return "".join(rows)


def _gauge_lite(conf):
    """紧凑档轻量置信度条（M7 ③ 降级不全删：width 150<190 + 置信度文本 + 轻量标记 class="lite"）。
    W-03 口径变更：取消百分比读数，条长仅作定性视觉，不标数字。"""
    m = re.search(r"(中高|高|中)", conf or "")
    if not m:
        return ""
    frac = {"高": 0.9, "中高": 0.7, "中": 0.5}[m.group(1)]
    w = int(146 * frac)
    return ('<svg class="lite" width="150" height="36" viewBox="0 0 150 36" role="img" aria-label="置信度（轻量）">'
            '<rect x="0" y="6" width="150" height="10" rx="5" fill="var(--track)"/>'
            '<rect x="0" y="6" width="%d" height="10" rx="5" fill="var(--indigo)"/>'
            '<text x="0" y="32" font-size="10.5" fill="var(--muted)">置信度 · %s档</text></svg>'
            % (w, m.group(1)))


def _radar_lite(riskv):
    """紧凑档轻量风险雷达（M7 ③：小尺寸网格多边形+命中色块，零动画属性）。"""
    segs = [x.strip() for x in re.split(r"[；;\n]", riskv or "") if x.strip()]
    info = {dim: 0 for dim, _ in RISK_DIMS}
    for seg in segs:
        for dim, _ in RISK_DIMS:
            if (seg.startswith(dim) or any(k in seg[:14] for k in DIM_KWS[dim])) and not info[dim]:
                if "未命中" not in seg:
                    mlv = re.search(r"(高|中|低)", seg.replace("高风险", ""))
                    info[dim] = {"高": 3, "中": 2, "低": 1}.get(mlv.group(1), 2) if mlv else 2
                break
    import math
    cx, cy, R = 66.0, 62.0, 46.0
    poly_pts = []
    for i, (dim, _c) in enumerate(RISK_DIMS):
        a = math.radians(90 - 60 * i)
        vx, vy = cx + R * math.cos(a), cy - R * math.sin(a)
        f = {0: 0.0, 1: 0.33, 2: 0.66, 3: 1.0}[info[dim]]
        poly_pts.append("%.1f,%.1f" % (cx + f * (vx - cx), cy + f * (vy - cy)))
    grid = ('<polygon points="66,16 105.8,39 105.8,85 66,108 26.2,85 26.2,39" fill="none" stroke="var(--grid)" stroke-width="1"/>'
            '<polygon points="66,39 85.9,50.5 85.9,73.5 66,85 46.1,73.5 46.1,50.5" fill="none" stroke="var(--grid)" stroke-width="1"/>')
    poly = '<polygon points="%s" fill="var(--indigo)" opacity="0.16" stroke="var(--indigo)" stroke-width="1.2"/>' % " ".join(poly_pts)
    hits = []
    for i, (dim, color) in enumerate(RISK_DIMS):
        if info[dim]:
            a = math.radians(90 - 60 * i)
            hx, hy = cx + (R + 13) * math.cos(a), cy - (R + 13) * math.sin(a)
            hits.append('<rect x="%.1f" y="%.1f" width="7" height="7" rx="1.5" fill="%s"/>'
                        '<text x="%.1f" y="%.1f" font-size="10.5" fill="var(--body)" text-anchor="middle">%s</text>'
                        % (hx - 3.5, hy - 3.5, color, hx, hy + 18, dim))
    return ('<svg class="lite" width="132" height="124" viewBox="0 0 132 124" role="img" aria-label="风险雷达（轻量）">%s%s%s</svg>'
            % (grid, poly, "".join(hits)))


def _shift_svg_lite(pts):
    """紧凑档单行换挡时间线（M7 ③：viewBox 高度 48 ≤ 原版 106 的 50%，含复盘日节点）。
    W-04 同拆：SVG 只留短标签，完整条件拆 HTML 列表。"""
    shift = (pts.get("换挡条件", "") or "").strip()
    review = pts.get("复盘日期", "") or "待填"
    return ('<svg class="lite" width="100%%" viewBox="0 0 720 48" role="img" aria-label="换挡时间线（单行）">'
            '<line x1="20" y1="26" x2="700" y2="26" stroke="var(--line)" stroke-width="1.5"/>'
            '<circle cx="56" cy="26" r="4" fill="var(--ink)"/>'
            '<text x="56" y="13" font-size="10.5" fill="var(--body)" text-anchor="middle">决定生效</text>'
            '<rect x="356" y="22" width="8" height="8" rx="2" transform="rotate(45 360 26)" fill="var(--indigo)"/>'
            '<text x="360" y="13" font-size="10.5" fill="var(--indigo2)" text-anchor="middle">监测 · 条件见下方清单</text>'
            '<circle cx="648" cy="26" r="5" fill="none" stroke="var(--indigo)" stroke-width="2"/>'
            '<text x="648" y="13" font-size="10.5" fill="var(--indigo2)" text-anchor="middle" font-weight="700">复盘日 %s</text></svg>'
            '<div class="capnote">信号可证伪：口径变化＝提前复盘（紧凑单行版）。</div>'
            '%s'
            % (esc(review), _shift_full(shift)))


def _steps(v):
    parts = [x.strip() for x in re.split(r"[；;]", v or "") if x.strip()]
    if len(parts) <= 1 and "\n" in (v or ""):
        parts = [x.strip() for x in v.splitlines() if x.strip()]
    lis = []
    for i, p in enumerate(parts, 1):
        lis.append('<li><span class="n">%d</span>%s</li>' % (i, esc(p)))
    return '<ul class="trace">%s</ul>' % "".join(lis)


_HTML_V07 = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="__THEME__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Decision Brief · __DRID__</title>
<style>
  :root{
    --bg:#0e1013; --card:#15181e; --ink:#e9ebf2; --body:#c0c6d2; --muted:#8b93a1; --faint:#5b6270;
    --line:rgba(255,255,255,.08); --hair:rgba(255,255,255,.05); --track:rgba(255,255,255,.07);
    --indigo:#6b7cff; --indigo2:#8b9bff; --violet:#a78bfa; --teal:#3fd0b6;
    --amber:#ffb454; --rose:#ff6b8a; --cyan:#4cc9f5; --grid:rgba(255,255,255,.07);
    --num:"Didot","Bodoni 72","Playfair Display",Georgia,"Times New Roman",serif;
  }
  html[data-theme="light"]{
    --bg:#fcfcfa; --card:#ffffff; --ink:#15171c; --body:#33373f; --muted:#82878f; --faint:#aab0b8;
    --line:#e6e8ec; --hair:#f0f1f4; --track:#eef0f3; --grid:#eef0f3;
    --indigo:#2742c8; --indigo2:#2742c8; --violet:#2742c8; --amber:#b7791f; --rose:#b3455e;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth}
  body{
    background:
      radial-gradient(1100px 560px at 12% -8%, rgba(107,124,255,.10), transparent 62%),
      radial-gradient(900px 520px at 108% 108%, rgba(167,139,250,.08), transparent 60%),
      var(--bg);
    color:var(--body);
    font:13.5px/1.75 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    padding:0 20px 26px;-webkit-font-smoothing:antialiased}
  html[data-theme="light"] body{background:var(--bg)}
  .wrap{max-width:1160px;margin:0 auto}
  .nav{position:sticky;top:0;z-index:30;margin:0 -20px 18px;padding:9px 20px;
    display:flex;gap:16px;justify-content:center;flex-wrap:wrap;
    background:rgba(14,16,19,.78);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
  html[data-theme="light"] .nav{background:rgba(252,252,250,.85)}
  .nav a{font-size:11.5px;color:var(--muted);text-decoration:none;letter-spacing:.03em}
  .nav a:hover{color:var(--indigo2)}
  .nav .b{color:var(--faint)}
  .masthead{padding-top:10px}
  .kicker{font-size:10.5px;letter-spacing:.24em;color:var(--muted);font-weight:600}
  .kicker .no{font-family:var(--num);letter-spacing:.08em}
  h1{font-size:25px;font-weight:800;line-height:1.4;margin:10px 0 8px;color:var(--ink)}
  .meta{font-size:12px;color:var(--muted);padding-bottom:14px}
  .meta .ir{display:inline-block;background:linear-gradient(90deg,#6b7cff,#a78bfa);color:#fff;
    border-radius:999px;padding:1.5px 10px;font-size:11px;font-weight:600;margin-right:6px;
    box-shadow:0 0 14px rgba(107,124,255,.35)}
  html[data-theme="light"] .meta .ir{background:var(--ink);box-shadow:none}
  .meta i{font-style:normal;color:var(--faint);padding:0 8px}
  .gradline{height:2px;border-radius:2px;margin-top:2px;
    background:linear-gradient(90deg,#6b7cff,#a78bfa 34%,#3fd0b6 66%,rgba(63,208,182,0) 96%)}

  .grid{display:grid;grid-template-columns:1fr 1fr;gap:22px 26px;margin-top:20px}
  .full{grid-column:1/-1}
  @media (max-width:900px){.grid{grid-template-columns:1fr}}

  .h{display:flex;align-items:baseline;gap:10px;margin-bottom:12px}
  .h .no{font-family:var(--num);font-size:14px;color:var(--indigo2)}
  .h .t{font-size:13.5px;font-weight:700;letter-spacing:.04em;color:var(--ink)}
  .h .rule{flex:1;height:1px;background:var(--line)}

  .hero{background:linear-gradient(180deg,#171b22,#13161c);border:1px solid var(--line);
    border-left:3px solid var(--indigo);border-radius:14px;padding:20px 24px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 20px 50px rgba(0,0,0,.45)}
  html[data-theme="light"] .hero{background:var(--card);box-shadow:0 1px 2px rgba(21,23,28,.04),0 10px 28px rgba(21,23,28,.05)}
  .verdict{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
  .verdict .right{flex:1;min-width:280px}
  .rec{font-size:18.5px;font-weight:700;line-height:1.65;color:var(--ink)}
  .rec em{font-style:normal;font-weight:700;
    background:linear-gradient(90deg,#8b9bff,#c4b5fd);
    -webkit-background-clip:text;background-clip:text;color:transparent}
  html[data-theme="light"] .rec em{color:var(--indigo);background:none}
  .basis{font-size:12.5px;color:var(--muted);margin-top:6px}
  .next{margin-top:12px;background:rgba(107,124,255,.10);border:1px solid rgba(107,124,255,.25);
    border-radius:10px;padding:10px 14px;font-size:12.5px;color:var(--body)}
  .next b{color:var(--indigo2)}

  .why{display:flex;gap:14px;padding:10px 0;border-bottom:1px solid var(--hair)}
  .why:last-child{border-bottom:none}
  .why .no{font-family:var(--num);font-size:21px;color:var(--faint);line-height:1.3;min-width:26px}
  .why .so{color:var(--ink);font-weight:600}
  .why .arrow{color:var(--faint);padding:0 5px}

  .drow{padding:9px 0;border-bottom:1px solid var(--hair);font-size:13px;line-height:1.8}
  .drow b{color:var(--ink)}
  .dbar{margin:12px 0}
  .dname{font-size:13px;color:var(--ink);font-weight:600;display:inline-block;min-width:120px}
  .dtrack{display:inline-block;width:52%;height:9px;border-radius:4.5px;background:var(--track);vertical-align:middle}
  .dfill{height:9px;border-radius:4.5px;background:linear-gradient(90deg,#6b7cff,#a78bfa)}
  .dscore{display:inline-block;font-size:17px;color:var(--ink);font-weight:700;margin-left:10px;
    font-variant-numeric:tabular-nums}
  .ddesc{font-size:11.5px;color:var(--muted);margin-top:4px}

  .flip{border-left:3px solid var(--rose);background:rgba(255,107,138,.06);border-radius:0 12px 12px 0;
    padding:13px 16px;font-size:13.5px;line-height:1.85;color:var(--ink)}
  .flip .q{color:var(--rose);font-weight:700}
  .capnote{font-size:11.5px;color:var(--muted);margin-top:8px}
  .basisline{font-size:12px;color:var(--muted);margin-top:8px}

  .riskrow{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
  .riskrow svg{flex:none;width:295px;max-width:100%}
  .hitlist{flex:1;min-width:230px}
  .hitlist .item{display:flex;gap:9px;align-items:baseline;padding:7px 0;border-bottom:1px solid var(--hair)}
  .hitlist .dot{width:7px;height:7px;border-radius:50%;background:var(--c);flex:none;
    box-shadow:0 0 9px var(--c);transform:translateY(-1px)}
  .hitlist b{font-size:12.5px;color:var(--ink);font-weight:650;white-space:nowrap}
  .hitlist .lv{font-size:11px;color:var(--amber);font-weight:600;white-space:nowrap}
  .hitlist p{font-size:12px;color:var(--muted);flex:1}
  .hitlist .miss{margin-top:9px;border-top:1px dashed var(--hair);padding-top:7px}
  .hitlist .m{display:flex;gap:8px;align-items:baseline;font-size:11.5px;color:var(--muted);padding:2.5px 0}
  .hitlist .m .dot{width:6px;height:6px;border-radius:50%;background:transparent;
    border:1.5px solid var(--c);box-shadow:none;transform:translateY(0)}
  .hitlist .m b{color:var(--body);font-weight:600}

  .btag{margin-top:22px;border:1px dashed var(--amber);background:rgba(255,180,84,.07);
    border-radius:10px;padding:10px 14px;font-size:12.5px;color:var(--amber);font-weight:600}

  .arch{margin-top:24px;border-top:1px solid var(--line)}
  .arch summary{cursor:pointer;list-style:none;font-size:12.5px;color:var(--muted);
    letter-spacing:.06em;padding:13px 0;user-select:none}
  .arch summary::-webkit-details-marker{display:none}
  .arch summary:after{content:"▴";float:right;color:var(--faint)}
  .arch:not([open]) summary:after{content:"▾"}
  .arch .inner{display:grid;grid-template-columns:1fr 1fr;gap:18px 30px;padding-bottom:6px;margin-top:4px}
  .arch .inner .full{grid-column:1/-1}
  @media (max-width:900px){.arch .inner{grid-template-columns:1fr}}

  .trace{list-style:none}
  .trace li{position:relative;padding:0 0 13px 34px;font-size:12.5px;line-height:1.75}
  .trace .n{position:absolute;left:0;top:-1px;font-family:var(--num);font-weight:700;
    font-size:14px;color:var(--violet)}
  .trace li:not(:last-child):before{content:"";position:absolute;left:4px;top:20px;bottom:3px;
    width:1px;background:var(--hair)}
  .assump{font-size:12.5px;color:#f5c069;background:rgba(255,180,84,.07);border-radius:10px;
    padding:8px 12px;margin:4px 0}
  html[data-theme="light"] .assump{color:var(--amber);background:#faf4e8}
  .audit{font-size:11px;color:var(--muted);line-height:2}
  .audit b{color:var(--body);font-weight:600}
  .ledger{margin-top:10px;font-size:11px;color:var(--muted);line-height:1.9;border-top:1px dashed var(--hair);padding-top:8px}
  .ledger b{color:var(--body);display:block;margin-bottom:3px;letter-spacing:.05em}

  footer{margin-top:26px;border-top:1px solid var(--line);padding-top:12px;text-align:center;
    font-size:11px;color:var(--faint);letter-spacing:.04em}
  .noise{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.03;
    background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}
  html[data-theme="light"] .noise{display:none}
  svg text{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
  svg .num{font-family:var(--num)}
  @media print{
    body{background:#fff !important;color:#222;padding:10mm}
    .nav{display:none}
    .noise{display:none}
    .hero{background:#fff;box-shadow:none}
  }
</style>
</head>
<body>
<div class="noise" aria-hidden="true"></div>
<div class="wrap">

  <nav class="nav">
    <a href="#s01">01 结论</a><a href="#s02">02 为什么</a><a href="#s03">03 对比</a><a href="#s04">04 换挡</a><a href="#s05">05 风险</a><a href="#s06">06 翻车点</a><a href="#s07">07 轨迹</a><a href="#s08">08 假设</a><span class="b">｜</span><span style="font-size:11.5px;color:var(--faint)">__DRID__ · 决策档案</span>
  </nav>

  <header class="masthead">
    <div class="kicker">DECISION BRIEF · <span class="no">__DRID__</span></div>
    <h1>__TITLE__</h1>
    <div class="meta"><span class="ir">__PILL__</span>__OBJ__<i>·</i>状态：__STATUS__<i>·</i>复盘日 __REVIEW__</div>
    <div class="gradline"></div>
  </header>

  <div class="grid">
    <div class="hero full" id="s01">
      <div class="h"><span class="no">01</span><span class="t">结论</span><span class="rule"></span></div>
      <div class="verdict">
        __GAUGE__
        <div class="right">
          <div class="rec">建议：<em>__REC__</em></div>
          __BASIS__
          __NEXT__
        </div>
      </div>
    </div>

    <section id="s02">
      <div class="h"><span class="no">02</span><span class="t">为什么</span><span class="rule"></span></div>
      __WHY__
    </section>

    <section id="s03">
      <div class="h"><span class="no">03</span><span class="t">为什么不选别的</span><span class="rule"></span></div>
      __DEAD__
    </section>

    <section class="full" id="s04">
      <div class="h"><span class="no">04</span><span class="t">换挡条件 · 什么情况改主意</span><span class="rule"></span></div>
      __SHIFT__
    </section>

    <section id="s05">
      <div class="h"><span class="no">05</span><span class="t">风险六维 · 命中与应对</span><span class="rule"></span></div>
      <div class="riskrow">__RISK__</div>
      <div class="capnote">六维＝固定板块（行为准则②，机器校验逐维）；命中与未命中均须一句理由（不允许无论证的全绿）。</div>
    </section>

    <section id="s06">
      <div class="h"><span class="no">06</span><span class="t">最可能翻车的点 · 欢迎怼</span><span class="rule"></span></div>
      <div class="flip"><span class="q">__FLIP__</span><b>不同意就怼，复盘时对答案。</b></div>
    </section>
  </div>

  __BTAG__

  <details class="arch" open>
    <summary id="s07">存档区 · 探讨轨迹 / 归位 / 假设与依据（复盘用，可点收起）</summary>
    <div class="inner">
      <section id="s07x">
        <div class="h"><span class="no">07</span><span class="t">探讨轨迹 · 这个结论怎么长出来的</span><span class="rule"></span></div>
        __TRACE__
      </section>
      <section id="s08">
        <div class="h"><span class="no">08</span><span class="t">归位 / 假设与依据</span><span class="rule"></span></div>
        <div class="assump">本次判断的类型：__GUIWEI__</div>
        __ASSUMP__
        <div class="basisline">依据（档案层）：__FMREF__ ｜ 决策链：__CHAIN__</div>
        <div class="audit" style="margin-top:16px"><b>齐性自检</b> —— __AUDIT__</div>
        <div class="ledger"><b>9 字段总账（原始留痕，复盘不改动）</b>__LEDGER__</div>
      </section>
    </div>
  </details>

  <footer>决策简报 · 由产品军师（pm-strategist）生成 · 自包含单文件 · 零外部依赖 · 打印自动转浅色</footer>
</div>
</body></html>
"""

_HTML_LEGACY = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 决策记录</title>
<style>
  :root{--ink:#1b1b1b;--muted:#807a70;--line:#e9e4da;--accent:#8a6d3b;--bg:#fbfaf7}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.8 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
  .wrap{max-width:840px;margin:0 auto;padding:56px 28px 80px}
  .kicker{color:var(--muted);font-size:12px;letter-spacing:.35em}
  h1{font-size:25px;font-weight:600;margin:10px 0 4px;letter-spacing:.02em;line-height:1.4}
  .meta{color:var(--muted);font-size:13px;margin-bottom:10px}
  .badges{margin:6px 0 26px}
  .badge{display:inline-block;font-size:12px;padding:3px 12px;border-radius:999px;border:1px solid var(--line);margin-right:8px;background:#fff}
  .badge.ok{background:#eef7ee;border-color:#bcd9bc}
  .badge.info{background:#eef2f8;border-color:#b9c9e0}
  .badge.draft{background:#f4f1ea}
  .badge.off{background:#f0f0f0;color:var(--muted)}
  .badge.fast{background:#fdf1df;border-color:#e5a13c;color:#92600a}
  table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line)}
  th,td{text-align:left;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--line)}
  tr:last-child th,tr:last-child td{border-bottom:none}
  th{width:96px;color:var(--muted);font-weight:500;white-space:nowrap}
  .review{margin-top:36px;border:1px dashed var(--line);background:#fff;padding:20px 22px}
  .review h2{font-size:14px;margin:0 0 8px;color:var(--accent);letter-spacing:.1em}
  .review p{color:var(--muted);font-size:13px;margin:4px 0}
  .foot{margin-top:30px;color:var(--muted);font-size:12px}
  @media print{body{background:#fff}.wrap{padding:12px}}
</style>
</head>
<body><div class="wrap">
<div class="kicker">PM-STRATEGIST · DECISION RECORD</div>
<h1>__TITLE__</h1>
<div class="meta">生成日期 __DATEFULL__ ｜ decision-record.py 渲染（旧版回退模板 dr_theme_legacy）</div>
<div class="badges">__BADGES__</div>
<table>
__ROWS__
</table>
<div class="review">
<h2>复盘区（复盘日期到时填）</h2>
<p>对照「当时前提 vs 实际结果」：证伪的假设回填检查单；前提过时 → 触发重验/更新前提库。方法见 fm-04复盘框架.md。</p>
<p>复盘结论追加于此区，不改动上方原始记录。</p>
</div>
<div class="foot">本文件为自包含 HTML 单文件，可直接归档/回看；来源标注遵循 SKILL.md 弹药引用纪律。</div>
</div></body></html>
"""


def settings_file():
    d = os.environ.get("PM_STRATEGIST_PROFILE_DIR") or os.environ.get("PM_STRATEGIST_PROFILE")
    if d and os.path.isfile(d):
        d = os.path.dirname(d)
    # 默认落 skill 目录 config/（相对解析，不写死平台目录；零平台绑定）
    d = d or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
    return os.path.join(d, "pm_settings.json")


def load_settings():
    try:
        return json.load(open(settings_file(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(s):
    try:
        os.makedirs(os.path.dirname(settings_file()), exist_ok=True)
        json.dump(s, open(settings_file(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def resolve_out_dir(ask=True):
    """落盘目录解析（可配置默认；首次问一次存配置文件）。"""
    env = os.environ.get("PM_STRATEGIST_DR_DIR")
    if env:
        return env, "环境变量 PM_STRATEGIST_DR_DIR"
    s = load_settings()
    if s.get("dr_dir"):
        return s["dr_dir"], "配置文件偏好（首次落盘时的选择，%s）" % settings_file()
    d = "./决策记录"
    if ask and sys.stdin.isatty():
        try:
            ans = input("DR 默认落盘到 %s/ ？（回车确认 / 输入其他目录）" % d).strip()
        except EOFError:
            ans = ""
        if ans:
            d = ans
        s["dr_dir"] = d
        save_settings(s)
        return d, "本次确认（已存配置文件偏好，下次不再问）"
    return d, "默认值（非交互环境未询问；可用 --out 或 PM_STRATEGIST_DR_DIR 覆盖）"


def render_html(pts, settings=None):
    s = settings if settings is not None else load_settings()
    if s.get("dr_theme_legacy"):
        return _render_legacy(pts)
    theme = s.get("dr_theme", "dark")
    st = pts.get("状态", "").strip() or "草案"
    st_base = st.split("·")[0].strip() or "草案"
    rev = _rev_of(pts)
    pill = {("🔴"): "不可逆 · 退不回", "🟡": "拿不准 · 按退不回对待", "🟢": "可逆 · 随时可改"}.get(rev, "决策档案")
    conf = pts.get("置信度", "") or ""
    compact = _is_compact(pts) and not _force_full(pts)
    if compact:
        # M7 ③：紧凑档可视化轻量降级（原全删=自废最值钱的设计；可逆≠轻量见 _force_full）
        gauge = _gauge_lite(conf) or '<div class="basis">置信度未标注（台面三档词：高/中高/中）</div>'
        basis = ""
    else:
        gauge, basis = (("", "") if not conf else _gauge(conf))
        if not gauge:
            gauge = '<div class="basis">置信度未标注（台面三档词：高/中高/中）</div>'
    rec = pts.get("决定", "") or "【待补充】"
    rec = re.sub(r"^(?:用户)?拍板\s*[：:]\s*", "", rec)
    rec = rec.strip("『』「」“‘”’\"'<>（）() \t")
    rec = re.sub(r"^拍板[。，,；;：: ]*", "", rec)
    next_raw = (pts.get("下一步", "") or "").strip()
    next_box = ('<div class="next"><b>下一步（你）：</b>%s</div>' % esc(next_raw)) if next_raw else ""
    why_items = [x.strip() for x in re.split(r"[；;\n]", pts.get("依据", "") or "") if x.strip()]
    why = "".join('<div class="why"><div class="no">%d</div><div>%s</div></div>' % (i, esc(t))
                  for i, t in enumerate(why_items, 1)) or '<div class="why"><div class="no">1</div><div>（依据见存档区）</div></div>'
    dead = _bars(pts.get("落选死因", ""))  # M7 ③：紧凑档对比条不再禁用（轻量≠删减）
    if not dead:
        dead = "".join('<div class="drow"><b>选项</b>：%s</div>' % esc(x.strip())
                       for x in re.split(r"[／/；;]", pts.get("选项", "")) if x.strip()) or \
               '<div class="drow">落选死因未填（渲染可选键：落选死因=选项名＝死于…）</div>'
    if compact:
        shift = _shift_svg_lite(pts)
        _, hitlist = _radar_and_hits(pts.get("风险", ""))
        risk = _radar_lite(pts.get("风险", "")) + hitlist
    else:
        shift = _shift_svg(pts)
        rsvg, hitlist = _radar_and_hits(pts.get("风险", ""))
        risk = '%s%s' % (rsvg, hitlist)
    flip = esc(pts.get("反方意见", "") or "（未填）")
    trace = _steps(pts.get("探讨轨迹", ""))
    assump_raw = [x.strip() for x in re.split(r"[\n；;]", pts.get("假设清单", "") or "") if x.strip()]
    assump = "".join('<div class="assump">%s</div>' % esc(a) for a in assump_raw) or '<div class="assump">无——输入已全部确认</div>'
    fmrefs = " · ".join(sorted(set(re.findall(r"(?:ref|fm)-0[1-6]", pts.get("依据", ""))))) or "（无 ref/fm 标注）"
    chain = pts.get("决策链", "").strip() or "无（单决策）"
    gy = pts.get("归位", "") or "（未填）"
    opt_n = len([x for x in re.split(r"[／/；;]", pts.get("选项", "")) if x.strip()])
    ass_n = len([x for x in re.split(r"[\n；;]", pts.get("假设清单", "")) if x.strip()])
    tt_n = len([x for x in re.split(r"[；;\n]", pts.get("探讨轨迹", "")) if x.strip()])
    audit = ("问题 %s · 选项 %s×%d · 决定 %s（%s） · 依据 %s · 反方 %s 双要素 · 风险 %s 六维 · 假设 %s×%d · "
             "复盘日期 %s %s · 状态 %s %s · 探讨轨迹 %s %d 步 · 归位 %s"
             % (_tick(pts.get("问题")), _tick(pts.get("选项")), opt_n, _tick(pts.get("决定")), st,
                _tick(pts.get("依据")), _tick(pts.get("反方意见")), _tick(pts.get("风险")),
                _tick(pts.get("假设清单")), ass_n, _tick(pts.get("复盘日期")), pts.get("复盘日期", "—") or "—",
                _tick(st), st, _tick(pts.get("探讨轨迹")), tt_n, _tick(pts.get("归位"))))
    scene = _scene(pts)
    btag = ('<div class="btag">⚠️ %s</div>' % B_TAGS[scene]) if scene in B_TAGS else ""
    ledger = "".join("<div>· %s：%s</div>" % (f, esc((pts.get(f, "") or "").strip() or "【待补充】"))
                     for f in FIELDS)
    title = pts.get("问题", "").strip() or "DR-%s" % DR_DATE
    html = (_HTML_V07
            .replace("__THEME__", "light" if theme == "light" else "dark")
            .replace("__DRID__", "DR-%s" % DR_DATE)
            .replace("__TITLE__", esc(title))
            .replace("__PILL__", esc(pill))
            .replace("__OBJ__", esc((pts.get("归位", "").split("→")[0].strip() if "→" in pts.get("归位", "") else "产品决策")))
            .replace("__STATUS__", esc(st))
            .replace("__REVIEW__", esc(pts.get("复盘日期", "") or "待填"))
            .replace("__GAUGE__", gauge)
            .replace("__REC__", esc(rec))
            .replace("__BASIS__", basis)
            .replace("__NEXT__", next_box)
            .replace("__WHY__", why)
            .replace("__DEAD__", dead)
            .replace("__SHIFT__", shift)
            .replace("__RISK__", risk)
            .replace("__FLIP__", flip)
            .replace("__BTAG__", btag)
            .replace("__TRACE__", trace)
            .replace("__GUIWEI__", esc(gy))
            .replace("__ASSUMP__", assump)
            .replace("__FMREF__", esc(fmrefs))
            .replace("__CHAIN__", esc(chain))
            .replace("__AUDIT__", audit)
            .replace("__LEDGER__", ledger))
    return html


def _render_legacy(pts):
    st = pts.get("状态", "").strip() or "草案"
    st_base = st.split("·")[0].strip() or "草案"
    bcls = {"已定": "ok", "复盘": "info", "关闭": "off"}.get(st_base, "draft")
    badges = '<span class="badge %s">状态：%s</span>' % (bcls, esc(st))
    if "快轨" in st:
        badges += '<span class="badge fast">快轨 · 低风险轻决策</span>'
    review = pts.get("复盘日期", "").strip()
    badges += '<span class="badge">复盘日期：%s</span>' % (esc(review) if review else "待填")
    rows = []
    for f in FIELDS + SECTION_FIELDS:
        v = pts.get(f, "").strip() or "【待补充】" + HINTS[f]
        rows.append("<tr><th>%s</th><td>%s</td></tr>" % (f, esc(v)))
    if pts.get("决策链", "").strip():
        rows.append("<tr><th>决策链</th><td>%s</td></tr>" % esc(pts["决策链"].strip()))
    title = pts.get("问题", "").strip() or "DR-%s" % DR_DATE
    return (_HTML_LEGACY
            .replace("__TITLE__", esc(title))
            .replace("__DATEFULL__", datetime.date.today().isoformat())
            .replace("__BADGES__", badges)
            .replace("__ROWS__", "\n".join(rows)))


def self_test():
    good = {"问题": "示例占位：A品要不要砍（场景S2）", "选项": "砍/不砍（含维持现状）", "决定": "推荐先收缩后观察",
            "依据": "ref-02 单品贡献度框架；fm-03 RICE 打分", "反方意见": "若为渠道入场券则砍错；推翻条件=拿到各SKU条码对应的渠道合约条款",
            "风险": "法规未命中（宣称无涉）；市场未命中（需求无反向信号）；竞争（竞品Q4抢合约，盯渠道周报）；供应链：库存积压中；财务未命中（清仓损益可控）；组织未命中（无排产缺口）",
            "假设清单": "⚠️ 假设·待验证：渠道合约Q4到期", "复盘日期": "2026-12-31", "状态": "草案",
            "探讨轨迹": "初步版建议直接砍；用户反驳「竞品 Q4 好像在挖我们经销商」→ 结论更新为砍＋60 天缓冲",
            "归位": "删×产品组合 → S2 ｜ 归位成功 ｜ 三线资源互挤、B 线贡献度连续下滑 ｜ 可逆性=🔴",
            "置信度": "中高 · 贡献度连续四季下滑；扣分项——贡献度口径待财务确认",
            "下一步": "本周内确认渠道合约有无条码数门槛",
            "落选死因": "轻量化改造＝死于换线成本回收期超出预算窗；维持现状＝代价是每月倒贴仓储与陈列（评分=32）",
            "换挡条件": "若大促动销低于品类均值八成 → 改判留线观察"}
    GS = {"schema_version": "5.0.0", "phase": "S6_CONVERGED"}  # R-5 层3 fixture：已收敛态（schema 须与 state-gate 一致）
    m1, p1 = validate(good, state=GS)
    ok = not m1 and not p1
    # 缺探讨轨迹 → 收敛闸 exit 1
    no_tt = {k: v for k, v in good.items() if k != "探讨轨迹"}
    m2, _ = validate(no_tt, state=GS)
    tt_gate = "探讨轨迹" in m2
    # 跳过声明两态
    skip_ok = dict(good); skip_ok["探讨轨迹"] = "用户跳过探讨：原因=直接要结论；用户原话「直接给结论，别问了」"
    skip_bad = dict(good); skip_bad["探讨轨迹"] = "用户跳过探讨"
    sk_ok = not validate(skip_ok, state=GS)[1]
    sk_bad = bool(validate(skip_bad, state=GS)[1])
    # 归位缺
    no_gy = {k: v for k, v in good.items() if k != "归位"}
    gy_bad = "归位" in validate(no_gy, state=GS)[0]
    # 质量下限（自 check_dr 移入的回归防线）
    straw = dict(good); straw["反方意见"] = "如果可能市场不好吧"
    straw_caught = any("稻草人" in x for x in validate(straw, state=GS)[1])
    noctrl = dict(good); noctrl["选项"] = "砍/慢慢砍"
    ctrl_caught = any("不做/维持现状" in x for x in validate(noctrl, state=GS)[1])
    decided = dict(good); decided["状态"] = "已定"
    dec_caught = any("用户拍板" in x for x in validate(decided)[1])
    # 渲染：关键内容点 7/7 grep（信息守恒，终稿 §6.1）
    html = render_html(good)
    points7 = [
        all(f in html for f in FIELDS),
        "反方" in html and "若为渠道入场券则砍错" in html,
        all(d in html for d, _ in RISK_DIMS),
        "假设·待验证" in html,
        "探讨轨迹" in html and "初步版建议直接砍" in html,
        "归位" in html and "删×产品组合" in html,
        "齐性自检" in html,
    ]
    pts7 = sum(points7)
    gauge_ok = ("70%" not in html) and ("90%" not in html) and "中高档" in html and "三档词" in html  # W-03 口径变更：无机械换算读数，仅档位词
    btag_ok = "跨部门确认" not in html  # S2 无 B 类标注
    s5 = dict(good); s5["问题"] = "示例占位：新品上市先铺哪（场景S5）"; s5["归位"] = "增×渠道/上市 → S5 ｜ 归位成功 ｜ 重合度高 ｜ 可逆性=🔴"
    btag5 = "最终上市决策需跨部门确认" in render_html(s5)
    # 双主题 + 回退开关 + 紧凑档
    light_html = render_html(good, {"dr_theme": "light"})
    theme_ok = "--bg:#fcfcfa" in light_html and "data-theme=\"light\"" in light_html
    legacy_html = render_html(good, {"dr_theme_legacy": True})
    legacy_ok = "PM-STRATEGIST · DECISION RECORD" in legacy_html and "探讨轨迹" in legacy_html
    fast = dict(good); fast["状态"] = "草案·快轨"
    fast_html = render_html(fast)
    # M7 ③ L851 断言反转：紧凑档含 ≥3 个 svg 且带轻量标记 class="lite"（原「SVG 全删」废止——可视化不自废）
    lite_n = fast_html.count('class="lite"')
    compact_ok = fast_html.count("<svg") >= 3 and lite_n >= 3
    # M7 测试设计①轻量仪表：含 svg + 置信度文本 + width<190
    mg = re.search(r'<svg class="lite"[^>]*width="(\d+)"[^>]*aria-label="置信度', fast_html)
    m7_gauge = bool(mg) and int(mg.group(1)) < 190 and "置信度" in fast_html
    # M7 测试设计②轻量雷达：网格多边形 + ≥1 命中色块 + 零动画属性
    r_lite = re.search(r'<svg[^>]*风险雷达（轻量）[^>]*>.*?</svg>', fast_html, re.S)
    m7_radar = bool(r_lite) and "<polygon" in r_lite.group(0) and \
        bool(re.search(r'<rect [^>]*fill="#\w+"', r_lite.group(0))) and "animate" not in r_lite.group(0)
    # M7 测试设计③轻量时间线：复盘日节点 + viewBox 高 ≤ 原版 50%（106/2=53）
    mt = re.search(r'<svg class="lite"[^>]*viewBox="0 0 720 (\d+)"', fast_html)
    m7_shift = ("复盘日" in fast_html) and bool(mt) and int(mt.group(1)) <= 53
    # M7 测试设计④对比条回归：紧凑档渲染含条形元素
    m7_bars = 'class="dbar"' in fast_html
    # M7 测试设计⑥双主题：两主题紧凑档都含轻量件
    fast_light = render_html(fast, {"dr_theme": "light"})
    m7_theme = fast_light.count('class="lite"') >= 3 and 'data-theme="light"' in fast_light
    # M7 ②：判类（S3）+ 快轨 → 强制全量档（0 轻量件、全量雷达在场）
    s3_fast = dict(fast)
    s3_fast["问题"] = "示例占位：这个品卖不动怎么办（场景S3）"
    s3_fast["归位"] = "判×现有单品 → S3 ｜ 归位成功 ｜ 诊断不改东西但下游拿它当前提 ｜ 可逆性=🟢"
    s3_html = render_html(s3_fast)
    m7_force_full = s3_html.count('class="lite"') == 0 and 'aria-label="风险雷达"' in s3_html
    # M7 ①：决定字段编号指代必拦
    numbered = dict(good); numbered["决定"] = "选选项2，其余同上"
    m7_num_caught = any("编号指代" in x for x in validate(numbered, state=GS)[1])
    # M12：无 --slug 默认名=对象+动作（≤30 字）；归位缺失退问题字段截 12
    slug1 = _default_slug(good)
    m12_ok = slug1 == "产品组合-删" and len("DR-%s-%s" % (DR_DATE, slug1)) <= 30
    slug_fb = _default_slug({"问题": "晚安蒸汽眼罩上市近半年月销约2000盒内部目标月销怎么办"})
    m12_fb = len(slug_fb) <= 12 and len("DR-%s-%s" % (DR_DATE, slug_fb)) <= 30
    # v4.4.1 盲审B-2/B-4 回归：9字段必填 + 齐性自检实况打勾 + 快轨互证 + 🔴原话引用 + 已定须有复盘日期
    minimal = {k: good[k] for k in ("问题", "选项", "决定", "反方意见", "探讨轨迹", "归位")}
    min_missing = validate(minimal)[0]
    nine_gate = all(f in min_missing for f in ("依据", "风险", "假设清单", "复盘日期", "状态"))
    hollow = render_html({k: good[k] for k in ("问题", "选项", "决定", "探讨轨迹", "归位")})
    audit_honest = "依据 ✗缺" in hollow and "复盘日期 ✗缺" in hollow and "风险 ✗缺" in hollow
    fake_fast = dict(good); fake_fast["探讨轨迹"] = "用户跳过探讨：原因=直接要结论（本会话为快轨）"; fake_fast["状态"] = "草案"
    fake_fast_caught = bool(validate(fake_fast, state=GS)[1])
    legit_fast = dict(good); legit_fast["探讨轨迹"] = "用户跳过探讨：原因=快轨"
    legit_fast["状态"] = "草案·快轨"; legit_fast["归位"] = "改×详情页文案 → S1 ｜ 归位成功 ｜ 单文案小流量 ｜ 可逆性=🟢"
    legit_fast_ok = not validate(legit_fast, state=GS)[1]
    noquote = dict(good); noquote["探讨轨迹"] = "初步版出过，用户反驳过，结论更新为砍"
    rev_caught = any("原话" in x for x in validate(noquote, state=GS)[1])
    # R-5 层1 回归：🟢 可逆 + 无原话同样拦（白名单移除后「反驳过」字面叙述不算证据）
    nq_green = dict(noquote); nq_green["归位"] = "改×详情页文案 → S1 ｜ 归位成功 ｜ 单文案小流量 ｜ 可逆性=🟢"
    l1_caught = any("R-5 层1" in x for x in validate(nq_green, state=GS)[1])
    # R-5 层3 回归：草案落盘的状态断言（fail-closed）
    l3_nostate = bool(validate(good)[1])                       # 无 state → 拦
    l3_err = bool(validate(good, state=None, state_err="session_state 不存在（/x）")[1])  # state 不可读 → 拦
    l3_phase = bool(validate(good, state={"phase": "S4_DRAFT"})[1])                     # 未收敛 → 拦
    l3_msg = any("S6_CONVERGED" in x for x in validate(good, state={"phase": "S4_DRAFT"})[1])
    # 已定/复盘/关闭为终态或历史档案重渲 → 不查 state（向后兼容；样本须带拍板原文过已定质量闸）
    decided_full = dict(good); decided_full["状态"] = "已定"
    decided_full["决定"] = "用户拍板：先收缩后观察"
    decided_nostate_ok = not validate(decided_full)[1]
    d6 = dict(good); d6["状态"] = "已定"; d6["复盘日期"] = "【待补充】YYYY-MM-DD"
    d6_caught = any("复盘日期" in x for x in validate(d6)[1])
    # 落盘演练
    tmp = tempfile.mkdtemp(prefix="drtest_")
    pth = os.path.join(tmp, "DR-test.html")
    open(pth, "w", encoding="utf-8").write(html)
    save_ok = os.path.isfile(pth) and os.path.getsize(pth) > 2000
    # ---- 批次1 渲染断言（W-01/W-05/W-06 + G-3）----
    _HP = importlib.import_module("html.parser")  # 避免 import html.parser 遮蔽下方 html 字符串变量
    class StrictParser(_HP.HTMLParser):
        VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                "param", "source", "track", "wbr"}
        def __init__(self):
            super().__init__(); self.stack = []; self.errs = []
        def handle_starttag(self, tag, attrs):
            if tag not in self.VOID:
                self.stack.append(tag)
        def handle_endtag(self, tag):
            if tag in self.VOID:
                return
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            elif tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.errs.append("mismatch closing " + tag + " @ " + self.stack[-1]); self.stack.pop()
                if self.stack:
                    self.stack.pop()
            else:
                self.errs.append("unexpected closing " + tag)
    def valid_html(h):
        p = StrictParser(); p.feed(h); p.close()
        return (not p.errs) and (not p.stack)
    # W-01：任意 <svg>…</svg> 内无 <div（非法 DOM 直渲）
    def svg_blocks(h):
        return re.findall(r"<svg.*?</svg>", h, re.S)
    def div_in_svg_count(h):
        return sum(b.count("<div") for b in svg_blocks(h))
    w01_full = div_in_svg_count(html) == 0
    w01_compact = div_in_svg_count(fast_html) == 0
    w01_ok = w01_full and w01_compact and html.count('class="item"') >= 1
    # W-05：建议区实质决定无拍板原话引号残留（『…』「…」）
    rec_m = re.search(r'class="rec">建议：<em>(.*?)</em>', html, re.S)
    w05_ok = bool(rec_m) and ("『" not in rec_m.group(1)) and ("「" not in rec_m.group(1))
    # G-3：用户文案黑话清零（不含：归位（只读）/四件套流程/决策记录（DR））
    g3_ok = ("归位（只读）" not in html) and ("四件套流程" not in html) and ("决策记录（DR）" not in html)
    # W-06：HTML 严解析（标准库 html.parser 零依赖）+ div-in-svg 坏样本必拦
    w06_bad_fixture = _radar_and_hits("竞争高风险；法规未命中；组织未命中；财务未命中；市场未命中；供应链未命中")[0]
    w06_ok = valid_html(html) and valid_html(legacy_html) and (div_in_svg_count(w06_bad_fixture) == 0)
    all_ok = all([ok, tt_gate, sk_ok, sk_bad, gy_bad, straw_caught, ctrl_caught, dec_caught,
                  pts7 == 7, gauge_ok, btag_ok, btag5, theme_ok, legacy_ok, compact_ok, save_ok,
                  nine_gate, audit_honest, fake_fast_caught, legit_fast_ok, rev_caught, d6_caught,
                  l1_caught, l3_nostate, l3_err, l3_phase, l3_msg, decided_nostate_ok,
                  m7_gauge, m7_radar, m7_shift, m7_bars, m7_theme, m7_force_full, m7_num_caught,
                  m12_ok, m12_fb, w01_ok, w05_ok, g3_ok, w06_ok])
    print("self: 收敛闸+9字段+两段 %s（缺探讨轨迹拦%s 跳过声明合法%s/缺证据拦%s 归位缺拦%s）质量下限（稻草人%s 无对照%s 已定无拍板%s）"
          "渲染（关键内容点 %d/7 仪表%s B类标注 S2无/S5有%s 双主题%s 回退%s 紧凑档%s 落盘%s）"
          "v4.4.1回归（9字段全必填%s 自检实况打勾%s 假快轨拦%s 真快轨过%s 🔴无原话拦%s 已定缺复盘%s）"
          "R-5三层（层1🟢无原话拦%s 层3无state拦%s/err拦%s/S4拦%s·提示S6%s 已定免state%s）"
          "M7轻量（仪表%s 雷达%s 时间线%s 对比条%s 双主题%s S3强制全量%s 编号指代拦%s）"
          "M12slug（对象+动作%s 无归位退截断%s）"
          "批次1（div-in-svg清零%s W05拍板引号%s G3黑话%s HTML严解析%s）" % (
              "✓" if ok else "✗", "✓" if tt_gate else "✗", "✓" if sk_ok else "✗", "✓" if sk_bad else "✗",
              "✓" if gy_bad else "✗", "✓" if straw_caught else "✗", "✓" if ctrl_caught else "✗", "✓" if dec_caught else "✗",
              pts7, "✓" if gauge_ok else "✗", "✓" if (btag_ok and btag5) else "✗",
              "✓" if theme_ok else "✗", "✓" if legacy_ok else "✗", "✓" if compact_ok else "✗", "✓" if save_ok else "✗",
              "✓" if nine_gate else "✗", "✓" if audit_honest else "✗", "✓" if fake_fast_caught else "✗",
              "✓" if legit_fast_ok else "✗", "✓" if rev_caught else "✗", "✓" if d6_caught else "✗",
              "✓" if l1_caught else "✗", "✓" if l3_nostate else "✗", "✓" if l3_err else "✗",
              "✓" if l3_phase else "✗", "✓" if l3_msg else "✗", "✓" if decided_nostate_ok else "✗",
              "✓" if m7_gauge else "✗", "✓" if m7_radar else "✗", "✓" if m7_shift else "✗",
              "✓" if m7_bars else "✗", "✓" if m7_theme else "✗", "✓" if m7_force_full else "✗",
              "✓" if m7_num_caught else "✗", "✓" if m12_ok else "✗", "✓" if m12_fb else "✗",
              "✓" if w01_ok else "✗", "✓" if w05_ok else "✗", "✓" if g3_ok else "✗", "✓" if w06_ok else "✗"))
    return all_ok


def main():
    ap = argparse.ArgumentParser(
        description="pm-strategist 决策档案 DR：收敛闸+9字段+探讨轨迹/归位校验、v0.7 双主题 HTML 落盘（DR 校验唯一入口；默认 ./决策记录/，首次问一次）")
    ap.add_argument("input", nargs="?", help="要点文件（key: value 或 JSON），或 - 读 stdin")
    ap.add_argument("--template", action="store_true", help="打印文本模板（9字段+探讨轨迹+归位+渲染可选键）")
    ap.add_argument("--out", dest="out_dir", help="落盘目录（默认 ./决策记录；可用 PM_STRATEGIST_DR_DIR 覆盖）")
    ap.add_argument("--slug", help="文件名 slug（默认=对象+动作，取归位字段原语对：DR-YYYYMMDD-<对象≤10字>-<动作≤6字>，"
                                    "文件名≤30字；归位无原语对退问题字段截断）")
    ap.add_argument("--state", default=None, help="session_state.json 路径（R-5 层3 状态断言；默认 PM_STRATEGIST_STATE 环境变量 > <skill根>/config/session_state.json）")
    ap.add_argument("--stdout", action="store_true", help="HTML 打到 stdout，不落盘")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.template:
        print(TEMPLATE)
        return 0
    if not a.input:
        ap.print_help()
        return 2
    try:
        text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    except OSError as e:
        print("读入失败: %s" % e)
        return 2
    pts = parse_points(text)
    state, state_err = _load_session_state(a.state)
    missing, problems = validate(pts, state=state, state_err=state_err)
    if missing or problems:
        print(render_text(pts))
        msg = ("必填缺：%s" % "/".join(missing)) if missing else ""
        if problems:
            msg += ("；" if msg else "") + "；".join(problems)
        print("FAIL — %s" % msg)
        if not pts:
            print("提示：一行一条「字段：内容」，字段名限 %s（9 字段全必填 + 探讨轨迹/归位；%s 为可选）"
                  % ("/".join(FIELDS + SECTION_FIELDS), "/".join(OPTIONAL)))
        return 1
    html = render_html(pts)
    if a.stdout:
        sys.stdout.write(html)
        sys.stderr.write("PASS — HTML 已输出（未落盘，--stdout 模式）\n")
        present, missk = render_key_status(pts)
        sys.stderr.write("渲染键齐备度（台面四区→DR 搬运）：%d/%d 齐全（%s）%s\n"
                         % (len(present), len(RENDER_KEYS), "/".join(present) or "—",
                            ("；缺：%s" % "、".join(missk)) if missk else ""))
        sys.stderr.write("覆盖边界：本次校验=DR 结构（9字段全必填+探讨轨迹/归位格式+R-5 收敛闸三层+质量下限）；"
                         "未覆盖=发布台面文本（走 check_output.py --publish 三步硬序列）。\n")
        return 0
    if a.out_dir:
        out_dir, src = a.out_dir, "--out 参数"
    else:
        out_dir, src = resolve_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    slug = a.slug or _default_slug(pts)  # M12 脚本默认值层：对象+动作（无归位原语对退问题字段截断）
    path = os.path.join(out_dir, "DR-%s-%s.html" % (DR_DATE, slug))
    n = 2
    base = path[:-5]
    while os.path.exists(path):
        path = "%s-%d.html" % (base, n)
        n += 1
    open(path, "w", encoding="utf-8").write(html)
    s = load_settings()
    theme = "旧版回退模板" if s.get("dr_theme_legacy") else ("浅色" if s.get("dr_theme") == "light" else "暗黑横版")
    print("PASS — DR 渲染成功，已落盘：%s（目录来源：%s；主题：%s）" % (path, src, theme))
    print("档案含：9 字段/反方/风险六维/假设/探讨轨迹/归位；复盘日期到点对照 fm-04 复盘。")
    present, missk = render_key_status(pts)
    print("渲染键齐备度（台面四区→DR 搬运）：%d/%d 齐全（%s）%s"
          % (len(present), len(RENDER_KEYS), "/".join(present) or "—",
             ("；缺：%s" % "、".join(missk)) if missk else ""))
    print("覆盖边界：本次校验=DR 结构（9字段全必填+探讨轨迹/归位格式+R-5 收敛闸三层+质量下限+M7-1 编号指代）；"
          "未覆盖=发布台面文本（走 check_output.py --publish 三步硬序列）与档案内容真伪（引用数据不验真）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
