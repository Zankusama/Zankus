#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""state-gate.py — 会话状态机（v5.0 批次一 #3）：七态 + 六道转移门的状态断言

背景（v5.0 一页纸结论）：本 skill 原把「流程」实现成「文档规定 + 文本格式校验器」——
所有闸门都在检查 AI 输出的文字长什么样，没有一个在检查流程走到了哪一步。
本脚本把流程变成显式状态机：输入目标 phase + state 文件 → 判定能否转移 + 缺什么。
跳步（如 S3 未收集齐就出结论、未收敛就落盘）从此有物理阻断。

七态（S0 空态 + 主线七步）：
  S0_IDLE → S1_ROUTED → S2_PROFILE_OK → S3_INFO_GATHERING → S4_DRAFT
  → S5_DEBATING（探讨轮，可循环 ≤N 次）→ S6_CONVERGED → S7_ARCHIVED
  特例回跳：S5→S4（critical 中途补齐 → 强制回 S4 重出初步版，不允许带旧结论走）

转移门（全部可脚本化判定，字段见 frameworks/fm-07会话状态机.md）：
  ① S0→S1   routing.ai_primitive 的 action/object 非空且合法
  ② S1→S2   routing.confirmed_by_user 非空（用户原话）；divergence=true 须已仲裁确认
  ③ S2→S3   profile_ok=true（profile-check exit 0 + 身份层已回显确认）
  ④ S3→S4   info_ledger 的 critical 全「已确认」（G 闸，与 info-gate.py 同判定）
  ⑤ S4→S5   draft_checked=true（check_output 对初步版 PASS）
  ⑤b S4→S6  同 ⑤ 且 skip_declared=true（用户说「直接给结论」跳过探讨，须存原话）
  ⑥ S6→S7   converged 证据（用户原话引用「…」）且 dr_id 非空（落盘后回填）

已知局限（诚实声明）：脚本能校验状态但不能强制 AI 写状态——缓解：
「更新 state」写进每个 phase 的进入动作（SKILL.md 会话状态管理节），本脚本在
state 文件缺失/格式旧时直接 exit 1（不更新就走不动）。

用法:
  python3 scripts/state-gate.py --init --scene S3 [--question "问题"] [--out <file>]
  python3 scripts/state-gate.py --to S4_DRAFT [--state <file>]
  python3 scripts/state-gate.py --audit [--state <file>] [--dr-dir <dir>]
  python3 scripts/state-gate.py --self
state 文件解析顺序：--state 参数 > 环境变量 PM_STRATEGIST_STATE > <skill根>/config/session_state.json
退出码: 0=可转移/审计通过; 1=不可转移（附缺什么）/审计有红项; 2=用法错误/state 文件缺失或损坏
"""
import sys, os, json, argparse, datetime, importlib.util

SCHEMA_VERSION = "5.0.0"
PHASES = ["S0_IDLE", "S1_ROUTED", "S2_PROFILE_OK", "S3_INFO_GATHERING",
          "S4_DRAFT", "S5_DEBATING", "S6_CONVERGED", "S7_ARCHIVED"]
ACTIONS = ["增", "删", "改", "择", "判"]
OBJECTS = ["新品", "产品组合", "现有单品", "价格体系", "渠道/上市", "品牌"]
QUOTE_RE_STR = r"「[^」]{2,}」|“[^”]{2,}”"  # 用户原话引用（≥2 字）

DEFAULT_STATE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_info_gate():
    """importlib 加载 info-gate.py（文件名含连字符，非合法模块名）。"""
    sys.dont_write_bytecode = True  # 动态加载不落 __pycache__（保持包目录零运行时产物）
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "info-gate.py")
    spec = importlib.util.spec_from_file_location("info_gate_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def state_path(args):
    if getattr(args, "state", None):
        return args.state
    env = os.environ.get("PM_STRATEGIST_STATE")
    if env:
        return env
    base = os.path.join(DEFAULT_STATE_DIR, "config")
    # W-25 会话分文件：读态无显式路径时——优先 legacy 单文件（单会话兼容）；否则取最新会话文件。
    # 两端以上并发会话必须各持 --state/PM_STRATEGIST_STATE 隔离，勿依赖自动解析（见 SKILL.md「会话状态管理」）。
    legacy = os.path.join(base, "session_state.json")
    import re as _re
    if os.path.isfile(legacy):
        return legacy
    try:
        cands = [os.path.join(base, f) for f in os.listdir(base)
                 if _re.match(r"^session_state\.[0-9]{8}-[0-9]{6}-[0-9]{6}\.json$", f)]
    except OSError:
        cands = []
    if cands:
        return max(cands, key=os.path.getmtime)
    return legacy


def load_state(path):
    """读 state 文件。返回 (state, err)；err 非空 = 缺失/损坏/schema 落后（fail-closed）。"""
    if not os.path.isfile(path):
        return None, "state 文件不存在（%s）——先 --init 初始化；不更新 state 流程走不动" % path
    try:
        st = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, "state 文件损坏（%s）——JSON 解析失败" % e
    if not isinstance(st, dict):
        return None, "state 文件不是 JSON 对象"
    v = st.get("schema_version")
    if not v:
        return None, "state 缺 schema_version——按旧格式处理，须 --init 重建（不静默读取）"
    if v != SCHEMA_VERSION:
        return None, "state schema_version=%s 落后（当前 %s）——提示迁移：--init 重建后按 fm-07 迁移字段，不静默读取" % (v, SCHEMA_VERSION)
    return st, None


def init_state(scene, question, reversibility):
    """生成初始 state（S0_IDLE + 该场景 info_ledger 预置 + 四动作骨架）。"""
    ig = _load_info_gate()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"),
        "dr_id": None,
        "phase": "S0_IDLE",
        "scene": scene,
        "question": question or "",
        "created": now,
        "last_updated": now,
        "routing": {"ai_primitive": None, "script_candidates": [],
                    "divergence": False, "confirmed_by_user": None,
                    "arbitration_shown": False},
        "reversibility": reversibility,
        "force_full_archive": reversibility == "🔴",
        "profile_ok": False,
        "info_ledger": ig.init_ledger(scene),
        "assumptions": [],
        "rounds": {"total": 0, "no_new_info": 0, "skipped_debate": 0},
        "asked_this_turn": 0,
        "draft_checked": False,
        "skip_declared": False,
        "converged_evidence": None,
        "gate_log": [],
    }


def gate_conditions(st, target):
    """目标态的转移门判定。返回 (ok, missing[])。"""
    miss = []
    routing = st.get("routing") or {}
    ai_prim = routing.get("ai_primitive") or {}
    ledger = st.get("info_ledger") or {}
    if target == "S1_ROUTED":
        act, obj = ai_prim.get("action"), ai_prim.get("object")
        if not act:
            miss.append("routing.ai_primitive.action（AI 判定的动作原语，增/删/改/择/判）")
        elif act not in ACTIONS:
            miss.append("action=%r 非法（合法：%s）" % (act, "/".join(ACTIONS)))
        if not obj:
            miss.append("routing.ai_primitive.object（对象原语；品牌级走跨域拆解出口）")
        elif obj not in OBJECTS:
            miss.append("object=%r 非法（合法：%s）" % (obj, "/".join(OBJECTS)))
    elif target == "S2_PROFILE_OK":
        if not (routing.get("confirmed_by_user") or "").strip():
            miss.append("routing.confirmed_by_user（用户确认归位的原话；两源分歧还须 arbitration_shown）")
        if routing.get("divergence") and not routing.get("arbitration_shown"):
            miss.append("divergence=true 但未走 --arbitrate 呈现对照（禁止 AI 自选后只提一句）")
    elif target == "S3_INFO_GATHERING":
        if not st.get("profile_ok"):
            miss.append("profile_ok=true（profile-check exit 0 + 身份层逐条回显且用户已回应）")
    elif target == "S4_DRAFT":
        ig = _load_info_gate()
        crit = ig.CRITICAL.get(st.get("scene") or "", ig.CRITICAL["C"])
        code, _lines = ig.judge(st, crit)
        if code == 1:
            gap = [n for n, it in list(ledger.items()) + [(n, {}) for n in crit if n not in ledger]
                   if ((it or {}).get("status") != "已确认") and n in crit]
            miss.append("G 闸：critical 未确认（%s）——禁出【建议】，先定向补问 ≤2"
                        % "、".join(sorted(set(gap))))
    elif target == "S5_DEBATING":
        if not st.get("draft_checked"):
            miss.append("draft_checked=true（初步版过 check_output.py 后置位）")
    elif target == "S6_CONVERGED":
        if st.get("skip_declared"):
            if not (st.get("converged_evidence") or "").strip():
                miss.append("skip_declared=true 须存用户原话（「直接给结论」类）于 converged_evidence")
        else:
            if not st.get("draft_checked"):
                miss.append("draft_checked=true（探讨前必须有初步版过闸）")
            ev = st.get("converged_evidence") or ""
            import re
            if not re.search(QUOTE_RE_STR, ev):
                miss.append("converged_evidence 须含用户原话引用「…」（≥2 字；「待用户反驳」不算收敛）")
    elif target == "S7_ARCHIVED":
        import re
        ev = st.get("converged_evidence") or ""
        if not re.search(QUOTE_RE_STR, ev):
            miss.append("converged_evidence 须含用户原话引用「…」（⑥门：探讨轨迹含用户原话才许落盘）")
        if not (st.get("dr_id") or "").strip():
            miss.append("dr_id（decision-record.py 落盘成功后回填 DR id）")
    return (not miss), miss


def can_transition(st, target):
    """顺序合法性 + 门判定。返回 (ok, problems[])。"""
    problems = []
    cur = st.get("phase", "S0_IDLE")
    if target not in PHASES:
        return False, ["目标态 %r 非法（合法：%s）" % (target, "→".join(PHASES))]
    if cur not in PHASES:
        return False, ["当前态 %r 非法" % cur]
    ci, ti = PHASES.index(cur), PHASES.index(target)
    if ti < ci and not (cur == "S5_DEBATING" and target == "S4_DRAFT"):
        problems.append("回跳非法（%s → %s）；唯一合法回跳=S5→S4（critical 补齐强制重出）" % (cur, target))
    if ti > ci + 1 and not (cur == "S4_DRAFT" and target == "S6_CONVERGED"):
        problems.append("跳步非法（%s → %s 跨态；S4→S6 仅限用户明确跳过探讨）" % (cur, target))
    ok, miss = gate_conditions(st, target)
    problems.extend(miss)
    return (not problems), problems


def _session_dr(dr_dir, st):
    """只统计本会话（state.last_updated 之后 mtime）新建的 DR；历史/跨会话 DR 降级不计，
    audit 由此不把上一会话的档案误判为"探讨期零落盘被绕过"。"""
    import datetime
    lu = st.get("last_updated") or ""
    try:
        cutoff = datetime.datetime.strptime(lu, "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        cutoff = None  # 无法解析 last_updated → 保守：全部计入（还原行为）
    res = []
    try:
        names = os.listdir(dr_dir)
    except OSError:
        return res
    for f in names:
        if not (f.startswith("DR-") and f.endswith(".html")):
            continue
        fp = os.path.join(dr_dir, f)
        try:
            mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp))
        except OSError:
            mt = None
        if cutoff is None or (mt is not None and mt >= cutoff):
            res.append(f)
    return res


def audit(st, dr_dir):
    """一致性审计：phase 互证 + 探讨期落盘漂移。返回 problems[]。"""
    import re
    problems = []
    phase = st.get("phase", "S0_IDLE")
    routing = st.get("routing") or {}
    if phase in PHASES[2:] and not (routing.get("confirmed_by_user") or "").strip():
        problems.append("phase=%s 但 routing.confirmed_by_user 为空（②门未走完不应越过 S1）" % phase)
    if phase in PHASES[4:]:
        ig = _load_info_gate()
        crit = ig.CRITICAL.get(st.get("scene") or "", ig.CRITICAL["C"])
        code, _ = ig.judge(st, crit)
        if code == 1:
            problems.append("phase=%s（已出结论）但 critical 有缺口——G 闸被绕过" % phase)
    if phase == "S7_ARCHIVED" and not (st.get("dr_id") or "").strip():
        problems.append("phase=S7 但 dr_id 为空（归档态必须有落盘档案）")
    if phase in ("S4_DRAFT", "S5_DEBATING") and dr_dir and os.path.isdir(dr_dir):
        drs = _session_dr(dr_dir, st)
        if drs and not st.get("dr_id"):
            problems.append("探讨期（%s）目录有 %d 个本会话 DR 文件但 state.dr_id 为空——探讨期零落盘被绕过（R-5③ diff 告警；历史 DR 不计入）"
                            % (phase, len(drs)))
    return problems


def self_test():
    import re, tempfile
    ok = True
    def chk(name, cond):
        nonlocal ok
        print("  %s %s" % ("✓" if cond else "✗", name))
        ok = ok and cond
    base = init_state("S3", "这个品卖不动了怎么办", "🟡")
    chk("初始态=S0_IDLE + ledger 预置 5 项（3 critical+2 非 critical）",
        base["phase"] == "S0_IDLE" and len(base["info_ledger"]) == 5)
    # ① S0→S1 缺原语 → 拦
    ok1, p1 = can_transition(base, "S1_ROUTED")
    chk("① S0→S1 无原语被拦", not ok1 and any("ai_primitive" in x for x in p1))
    # ① 补原语 → 过
    s1 = json.loads(json.dumps(base))
    s1["routing"]["ai_primitive"] = {"action": "判", "object": "现有单品", "scene": "S3"}
    ok1b, _ = can_transition(s1, "S1_ROUTED")
    chk("① S0→S1 原语齐 → 过", ok1b)
    # ② 未确认 → 拦「禁止装弹药」（s1 已推进到 S1_ROUTED）
    s1["phase"] = "S1_ROUTED"
    ok2, p2 = can_transition(s1, "S2_PROFILE_OK")
    chk("② S1→S2 未获用户确认被拦（禁止装弹药）", not ok2 and any("confirmed_by_user" in x for x in p2))
    # ② divergence 未仲裁 → 拦
    s2 = json.loads(json.dumps(s1)); s2["routing"]["confirmed_by_user"] = "对，就是这个品的事"
    s2["routing"]["divergence"] = True
    ok2b, p2b = can_transition(s2, "S2_PROFILE_OK")
    chk("② divergence=true 未仲裁被拦（禁止 AI 自选）", not ok2b and any("arbitrate" in x for x in p2b))
    s2["routing"]["arbitration_shown"] = True
    ok2c, _ = can_transition(s2, "S2_PROFILE_OK")
    chk("② 仲裁后 → 过", ok2c)
    # ③ profile 未过 → 拦
    s2["phase"] = "S2_PROFILE_OK"
    s3 = json.loads(json.dumps(s2))
    ok3, p3 = can_transition(s3, "S3_INFO_GATHERING")
    chk("③ S2→S3 profile 未过被拦", not ok3 and any("profile_ok" in x for x in p3))
    s3["profile_ok"] = True
    ok3b, _ = can_transition(s3, "S3_INFO_GATHERING")
    chk("③ profile_ok → 过", ok3b)
    # ④ G 闸：critical 缺 → 拦出结论
    s3["phase"] = "S3_INFO_GATHERING"
    ok4, p4 = can_transition(s3, "S4_DRAFT")
    chk("④ S3→S4 critical 未确认被拦（禁出【建议】）", not ok4 and any("G 闸" in x for x in p4))
    s4 = json.loads(json.dumps(s3))
    for n, it in s4["info_ledger"].items():
        if it["critical"]:
            it["status"] = "已确认"
    ok4b, _ = can_transition(s4, "S4_DRAFT")
    chk("④ critical 全确认 → 过", ok4b)
    # ⑤ 未过 check_output → 拦
    s4["phase"] = "S4_DRAFT"
    ok5, p5 = can_transition(s4, "S5_DEBATING")
    chk("⑤ S4→S5 初步版未过闸被拦", not ok5 and any("draft_checked" in x for x in p5))
    s5 = json.loads(json.dumps(s4)); s5["draft_checked"] = True
    ok5b, _ = can_transition(s5, "S5_DEBATING")
    chk("⑤ draft_checked → 过", ok5b)
    # ⑥ 收敛证据：无原话 → 拦
    s5["phase"] = "S5_DEBATING"
    ok6, p6 = can_transition(s5, "S6_CONVERGED")
    chk("⑥ S5→S6 无用户原话被拦（待反驳≠收敛）", not ok6 and any("原话" in x for x in p6))
    s6 = json.loads(json.dumps(s5)); s6["converged_evidence"] = "用户拍板「就按收缩单渠道方案做」"
    ok6b, _ = can_transition(s6, "S6_CONVERGED")
    chk("⑥ 含原话引用 → 过", ok6b)
    # ⑥ S6→S7 无 dr_id → 拦
    s6["phase"] = "S6_CONVERGED"
    ok7, p7 = can_transition(s6, "S7_ARCHIVED")
    chk("⑦ S6→S7 无 dr_id 被拦", not ok7 and any("dr_id" in x for x in p7))
    s7 = json.loads(json.dumps(s6)); s7["dr_id"] = "DR-20260907-xxx"
    ok7b, _ = can_transition(s7, "S7_ARCHIVED")
    chk("⑦ dr_id 回填 → 过", ok7b)
    # 跳步/回跳
    okjump, pjump = can_transition(s3, "S5_DEBATING")
    chk("跳步 S3→S5 被拦（跨态）", not okjump and any("跳步" in x for x in pjump))
    okback, _ = can_transition(s7, "S3_INFO_GATHERING")
    chk("回跳 S7→S3 被拦（唯一合法回跳=S5→S4）", not okback)
    okback2, _ = can_transition(s5, "S4_DRAFT")
    chk("S5→S4 回跳放行（critical 补齐强制重出）", okback2)
    # audit：探讨期落盘漂移
    tmp = tempfile.mkdtemp(prefix="sgtest_")
    open(os.path.join(tmp, "DR-20260907-x.html"), "w").write("x")
    ap = audit(s5, tmp)
    chk("audit：探讨期目录有 DR 但 state 无 dr_id → 告警（R-5③）", any("探讨期" in x for x in ap))
    ap2 = audit(s7, None)
    chk("audit：S7 一致态无红项", not ap2)
    # audit W-20：历史/跨会话 DR 不计入探讨期漂移（按 state.last_updated 切本会话边界）
    import time as _t
    s5h = json.loads(json.dumps(s5)); s5h["last_updated"] = _t.strftime("%Y-%m-%d %H:%M")
    olddir = tempfile.mkdtemp(prefix="sgold_")
    oldf = os.path.join(olddir, "DR-20260907-old.html"); open(oldf, "w").write("x")
    _old = _t.time() - 7200
    os.utime(oldf, (_old, _old))
    ap_old = audit(s5h, olddir)
    chk("audit W-20：仅历史 DR（last_updated 前）+无 dr_id → 不计告警（跨会话不误判）", not any("探讨期" in x for x in ap_old))
    newdir = tempfile.mkdtemp(prefix="sgnew_")
    open(os.path.join(newdir, "DR-20260907-new.html"), "w").write("x")
    ap_new = audit(s5h, newdir)
    chk("audit W-20：本会话新 DR（last_updated 后）无 dr_id → 仍告警", any("本会话" in x for x in ap_new))
    # state 文件 fail-closed
    _st, err = load_state(os.path.join(tmp, "nope.json"))
    chk("state 文件缺失 → 报错不静默", err is not None)
    bad = os.path.join(tmp, "bad.json"); open(bad, "w").write("{}")
    _st, err2 = load_state(bad)
    chk("缺 schema_version → 拒读（对齐 profile-check 双闸门思路）", err2 is not None)
    print("self: 七态状态机 %s 项 %s（六门全判定+跳步/回跳+审计+fail-closed）"
          % (22, "PASS✓" if ok else "FAIL✗"))
    return ok


def write_state(path, st):
    """落盘 state（W-09/W-10：EPERM/只读捕获→可读指引，不出裸 traceback）。成功返回 None，失败返回 err。"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        return None
    except OSError as e:
        return "无法写入 %s（%s）——分区只读/权限不足" % (path, e)


def main():
    ap = argparse.ArgumentParser(
        description="pm-strategist 会话状态机：--init 初始化 / --to 判定转移（缺什么）/ --audit 一致性审计")
    ap.add_argument("--init", action="store_true", help="生成初始 session_state（S0_IDLE，配合 --scene）")
    ap.add_argument("--scene", choices=["S1", "S2", "S3", "S4", "S5", "C"], default=None, help="--init 用：场景号")
    ap.add_argument("--question", default=None, help="--init 用：用户决策问题原文")
    ap.add_argument("--reversibility", choices=["🔴", "🟡", "🟢"], default="🟢", help="--init 用：可逆性")
    ap.add_argument("--to", dest="to_phase", default=None, help="目标 phase（如 S4_DRAFT）——判定且（PASS 时）回写 phase")
    ap.add_argument("--audit", action="store_true", help="一致性审计（phase 互证 + 探讨期落盘漂移）")
    ap.add_argument("--dr-dir", dest="dr_dir", default="./决策记录", help="audit 用：DR 落盘目录（默认 ./决策记录）")
    ap.add_argument("--state", default=None, help="session_state.json 路径（默认 config/session_state.json，可用 PM_STRATEGIST_STATE 覆盖）")
    ap.add_argument("--out", default=None, help="--init 用：state 输出路径（默认同 --state 解析路径）")
    ap.add_argument("--stdout", action="store_true", help="--init 用：打印到 stdout 不落盘")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.init:
        # W-09：照抄文档命令（仅 --scene 无 --state）也默认落盘到解析路径，不再只打印；要打印显式 --stdout
        if not a.scene:
            print("用法：--init 须配 --scene S1-S5/C"); return 2
        st = init_state(a.scene, a.question, a.reversibility)
        if a.stdout:
            print(json.dumps(st, ensure_ascii=False, indent=2)); return 0
        # W-25 会话分文件：--init 无显式 --state/PM_STRATEGIST_STATE/--out 时，默认写
        # config/session_state.<session_id>.json（按会话分文件，两端并发各写各的互不踩）；否则随显式路径。
        if a.out:
            path = a.out
        elif getattr(a, "state", None) or os.environ.get("PM_STRATEGIST_STATE"):
            path = state_path(a)
        else:
            path = os.path.join(DEFAULT_STATE_DIR, "config", "session_state.%s.json" % st["session_id"])
        # W-10：EPERM/只读 → 可读指引（含 --stdout 逃生）+ 建议设 PM_STRATEGIST_STATE 到可写路径
        err = write_state(path, st)
        if err:
            print("FAIL — 初始 state 未落盘：%s（%s）。\n"
                  "      可改用 --stdout 打印后自行保存，或先把 PM_STRATEGIST_STATE 指向可写路径（如 ~/工作/PM状态.json）再 --init。"
                  % (path, err))
            return 2
        print("PASS — 初始 state 已落盘：%s（phase=S0_IDLE；每轮对话后更新 last_updated/ledger/rounds，进新 phase 前跑 --to）" % path)
        return 0
    path = state_path(a)
    st, err = load_state(path)
    if err:
        print("FAIL — %s" % err); return 2
    if a.to_phase:
        # W-11：PASS 不只判定，还回写 phase+gate_log（幂等：同态重复跑不报错、审计 phase=目标态）
        ok, problems = can_transition(st, a.to_phase)
        cur = st.get("phase")
        if ok:
            st["phase"] = a.to_phase
            st["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            st.setdefault("gate_log", []).append({"gate": a.to_phase, "verdict": "PASS",
                                                  "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
            werr = write_state(path, st)
            if werr:
                print("FAIL — 转移判定 PASS 但 state 回写失败：%s（%s）——阶段未落盘，先修目录可写性再 --to"
                      % (path, werr))
                return 2
            print("PASS — 可转移 %s → %s（phase 与 gate_log 已回写 %s；--audit 可复核）"
                  % (cur, a.to_phase, path))
            return 0
        print("FAIL — 不可转移 %s → %s，缺：" % (cur, a.to_phase))
        for x in problems:
            print("  ❌ " + x)
        return 1
    if a.audit:
        problems = audit(st, a.dr_dir)
        if problems:
            print("FAIL — 审计发现 %d 个红项：" % len(problems))
            for x in problems:
                print("  ❌ " + x)
            return 1
        print("PASS — 审计一致（phase=%s；探讨期零落盘无漂移）" % st.get("phase"))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
