#!/usr/bin/env python3
"""tests/replay.py — 流程回归骨架（v5.0 批次一 RC-5 / 防线 1+2 的可自动化部分）

流程回归（v5.0 §4.1「流程测试怎么做」）：
  全自动：喂预置 state 文件，断言各闸门判定；AI 参与走查属半自动人核项，不假装能自动化。

覆盖剧本（D1-D5 场景，样本内嵌于本文件）：
  D1 正常收敛路径：S0→S1→…→S7 七门全过、每门留痕（缺条件必拦）
  D2 信息未收集全就出结论：G 闸拦（禁出【建议】区）
  D3 初步版未探讨就落档案：收敛闸硬拦，DR 不生成
  D4 假设冒充已问 / 置信度虚高：台账说了算 + 置信度封顶（T12 全量断言在批次二）
  D5 20 轮长 session：计数/台账/phase 落盘不漂移

用法：python3 tests/replay.py [--self 视为同义]；退出码 0=全绿，1=有红。
"""
import json
import os
import subprocess
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SC = os.path.join(SKILL_DIR, "scripts")

PASS = 0
FAIL = 0


def ok(name):
    global PASS
    PASS += 1
    print("  ✅ %s" % name)


def bad(name, detail=""):
    global FAIL
    FAIL += 1
    print("  ❌ %s%s" % (name, ("｜" + detail) if detail else ""))


def run(script, args, env_state=None):
    """跑一个脚本，返回 (exit_code, stdout)。env_state=传 PM_STRATEGIST_STATE。"""
    env = dict(os.environ)
    if env_state:
        env["PM_STRATEGIST_STATE"] = env_state
    else:
        env.pop("PM_STRATEGIST_STATE", None)
    p = subprocess.run([sys.executable, os.path.join(SC, script)] + args,
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def load(path):
    return json.load(open(path, encoding="utf-8"))


def save(path, st):
    json.dump(st, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def confirm_all_critical(st):
    for n, it in st["info_ledger"].items():
        if it.get("critical"):
            it["status"] = "已确认"
            it["value"] = "示例值"
            it["src"] = "用户"
    return st


def gate_log_append(st, gate, verdict):
    st.setdefault("gate_log", []).append({"gate": gate, "verdict": verdict})
    return st


def d1_happy_path(T):
    print("— D1 正常收敛路径（七门全过 + 缺条件必拦）—")
    st_path = os.path.join(T, "d1_state.json")
    # 初始化
    code, out = run("state-gate.py", ["--init", "--scene", "S2", "--question",
                                      "砍不砍B线", "--reversibility", "🔴"],
                    env_state=st_path)
    st = load(st_path)
    if code == 0 and st["phase"] == "S0_IDLE" and len(st["info_ledger"]) >= 3:
        ok("D1-01 初始化：S0_IDLE + S2 critical 台账预置")
    else:
        bad("D1-01 初始化失败", out.strip()[:120])
    # 门① 缺原语必拦
    code, _ = run("state-gate.py", ["--to", "S1_ROUTED", "--state", st_path])
    if code == 1:
        ok("D1-02 门① 缺 ai_primitive → FAIL（先拦后过的先红半边）")
    else:
        bad("D1-02 门① 缺原语未拦")
    # AI 补原语（模拟 AI 判定动作×对象）
    st["routing"]["ai_primitive"] = {"action": "删", "object": "产品组合", "scene": "S2"}
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S1_ROUTED", "--state", st_path])
    if code == 0:
        st["phase"] = "S1_ROUTED"
        gate_log_append(st, "门①", "PASS")
        save(st_path, st)
        ok("D1-03 门① 原语齐 → S1_ROUTED（留痕 gate_log）")
    else:
        bad("D1-03 门① 误拦")
    # 门② 缺用户确认必拦 → 补原话过
    code, _ = run("state-gate.py", ["--to", "S2_PROFILE_OK", "--state", st_path])
    if code == 1:
        ok("D1-04 门② 缺 confirmed_by_user → FAIL")
    else:
        bad("D1-04 门② 缺确认未拦")
    st["routing"]["confirmed_by_user"] = "对，就是砍产品线这个级别的决定"
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S2_PROFILE_OK", "--state", st_path])
    if code == 0:
        st["phase"] = "S2_PROFILE_OK"
        gate_log_append(st, "门②", "PASS")
        save(st_path, st)
        ok("D1-05 门② 确认原话 → S2_PROFILE_OK")
    else:
        bad("D1-05 门② 误拦")
    # 门③ 缺 profile_ok 必拦 → 置位过
    code, _ = run("state-gate.py", ["--to", "S3_INFO_GATHERING", "--state", st_path])
    if code == 1:
        ok("D1-06 门③ 缺 profile_ok → FAIL")
    else:
        bad("D1-06 门③ 缺 profile_ok 未拦")
    st["profile_ok"] = True
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S3_INFO_GATHERING", "--state", st_path])
    if code == 0:
        st["phase"] = "S3_INFO_GATHERING"
        gate_log_append(st, "门③", "PASS")
        save(st_path, st)
        ok("D1-07 门③ profile_ok → S3_INFO_GATHERING")
    else:
        bad("D1-07 门③ 误拦")
    # 门④ G 闸：critical 未确认必拦（D2 场景同源）→ 全确认过
    code, out = run("info-gate.py", [st_path])
    if code == 1 and "禁出【建议】" in out:
        ok("D1-08 G 闸 critical 未确认 → exit 1 + 禁出【建议】区")
    else:
        bad("D1-08 G 闸未拦", out.strip()[:120])
    confirm_all_critical(st)
    save(st_path, st)
    code, _ = run("info-gate.py", [st_path])
    if code == 0:
        ok("D1-09 G 闸 critical 全确认 → exit 0")
    else:
        bad("D1-09 G 闸全确认误拦")
    code, _ = run("state-gate.py", ["--to", "S4_DRAFT", "--state", st_path])
    if code == 0:
        st["phase"] = "S4_DRAFT"
        gate_log_append(st, "门④", "PASS")
        save(st_path, st)
        ok("D1-10 门④ G 闸过 → S4_DRAFT")
    else:
        bad("D1-10 门④ 误拦")
    # 门⑤ 缺 draft_checked 必拦 → 置位过
    code, _ = run("state-gate.py", ["--to", "S5_DEBATING", "--state", st_path])
    if code == 1:
        ok("D1-11 门⑤ 缺 draft_checked → FAIL（初步版未过闸不得进探讨）")
    else:
        bad("D1-11 门⑤ 缺 draft_checked 未拦")
    st["draft_checked"] = True
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S5_DEBATING", "--state", st_path])
    if code == 0:
        st["phase"] = "S5_DEBATING"
        gate_log_append(st, "门⑤", "PASS")
        save(st_path, st)
        ok("D1-12 门⑤ draft_checked → S5_DEBATING")
    else:
        bad("D1-12 门⑤ 误拦")
    # 门⑥ 收敛缺原话必拦 → 补原话过
    st["converged_evidence"] = "待用户反驳"
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S6_CONVERGED", "--state", st_path])
    if code == 1:
        ok("D1-13 门⑥ 「待用户反驳」无原话 → FAIL（白名单回潮防线）")
    else:
        bad("D1-13 门⑥ 无原话未拦")
    st["converged_evidence"] = "用户拍板：「就按砍B线执行，加60天缓冲」"
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S6_CONVERGED", "--state", st_path])
    if code == 0:
        st["phase"] = "S6_CONVERGED"
        gate_log_append(st, "门⑥", "PASS")
        save(st_path, st)
        ok("D1-14 门⑥ 收敛原话 → S6_CONVERGED")
    else:
        bad("D1-14 门⑥ 误拦")
    # 门⑦ 缺 dr_id 必拦 → 回填过
    code, _ = run("state-gate.py", ["--to", "S7_ARCHIVED", "--state", st_path])
    if code == 1:
        ok("D1-15 门⑦ 缺 dr_id → FAIL（未落盘不得归档）")
    else:
        bad("D1-15 门⑦ 缺 dr_id 未拦")
    st["dr_id"] = "DR-20260907-replay"
    save(st_path, st)
    code, _ = run("state-gate.py", ["--to", "S7_ARCHIVED", "--state", st_path])
    if code == 0:
        st["phase"] = "S7_ARCHIVED"
        save(st_path, st)
        ok("D1-16 门⑦ dr_id 回填 → S7_ARCHIVED（全链 7 门留痕）")
    else:
        bad("D1-16 门⑦ 误拦")
    # 审计一致
    code, _ = run("state-gate.py", ["--audit", "--state", st_path, "--dr-dir", T])
    if code == 0 and len(st.get("gate_log", [])) >= 6:
        ok("D1-17 终态审计一致（phase/台账/gate_log ≥6 条留痕）")
    else:
        bad("D1-17 终态审计红")
    return st_path


def d2_g_gate_blocks(T):
    print("— D2 信息未收集全就出结论（G 闸拦，只补问不出结论）—")
    st_path = os.path.join(T, "d2_state.json")
    code, _ = run("state-gate.py", ["--init", "--scene", "S3", "--reversibility", "🟢"],
                  env_state=st_path)
    st = load(st_path)
    st["phase"] = "S3_INFO_GATHERING"
    st["profile_ok"] = True
    st["routing"] = {"ai_primitive": {"action": "判", "object": "现有单品", "scene": "S3"},
                     "script_candidates": [], "divergence": False,
                     "confirmed_by_user": "对", "arbitration_shown": False}
    save(st_path, st)
    code, out = run("info-gate.py", [st_path])
    if code == 1 and "建议先问" in out and "禁出【建议】" in out:
        ok("D2-01 critical 全未问 → exit 1 + 定向补问指引（≤2）")
    else:
        bad("D2-01 G 闸拦截失效", out.strip()[:120])
    code, out = run("state-gate.py", ["--to", "S4_DRAFT", "--state", st_path])
    if code == 1 and "G 闸" in out:
        ok("D2-02 门④ 联动拦：critical 缺口 → 禁止进 S4 出初步版")
    else:
        bad("D2-02 门④ 未联动 G 闸", out.strip()[:120])
    # 用户答了 1 个 critical（已确认），其余未问 → 仍拦
    st["info_ledger"][list(st["info_ledger"])[0]]["status"] = "已确认"
    save(st_path, st)
    code, _ = run("info-gate.py", [st_path])
    if code == 1:
        ok("D2-03 critical 部分确认（1/3）→ 仍拦（问了没答=没问）")
    else:
        bad("D2-03 部分确认漏拦")


def d3_convergence_gate_blocks(T):
    print("— D3 初步版未探讨就落档案（收敛闸硬拦，DR 不生成）—")
    dr_txt = os.path.join(T, "d3_dr.md")
    open(dr_txt, "w", encoding="utf-8").write(
        "# DR-20260907-replay\n"
        "- 问题：示例占位\n"
        "- 选项：砍B线/维持现状\n"
        "- 决定：砍B线加60天缓冲\n"
        "- 依据：ref-02\n"
        "- 反方意见：若竞品抢签经销商合约则本决定失效；推翻条件=拿到经销商合约扫描\n"
        "- 风险：渠道（进场资格）\n"
        "- 假设清单：⚠️ 假设·待验证：渠道合约Q4到期\n"
        "- 复盘日期：2026-12-31\n"
        "- 状态：草案\n"
        "- 探讨轨迹：初步版建议直接砍；用户反驳「竞品 Q4 好像在挖我们经销商」→ 结论更新为砍＋60 天缓冲\n"
        "- 归位：删×产品组合 → S2 ｜ 归位成功 ｜ 测试 ｜ 可逆性=🔴\n")
    out_dir = os.path.join(T, "d3_out")
    os.makedirs(out_dir, exist_ok=True)
    st_path = os.path.join(T, "d3_state.json")
    code, _ = run("state-gate.py", ["--init", "--scene", "S2", "--reversibility", "🔴"],
                  env_state=st_path)
    st = load(st_path)
    st["phase"] = "S5_DEBATING"  # 探讨中，未收敛
    confirm_all_critical(st)
    st["draft_checked"] = True
    save(st_path, st)
    code, out = run("decision-record.py", [dr_txt, "--out", out_dir], env_state=st_path)
    drs = [f for f in os.listdir(out_dir) if f.startswith("DR-")]
    if code == 1 and not drs:
        ok("D3-01 phase=S5_DEBATING 落草案 → exit 1 且 DR 零生成（R-5 层3）")
    else:
        bad("D3-01 未收敛落盘未被拦", "code=%s drs=%s" % (code, drs))
    # 跳步：S5 → S7 直接归档也拦
    code, out = run("state-gate.py", ["--to", "S7_ARCHIVED", "--state", st_path])
    if code == 1:
        ok("D3-02 S5→S7 跳步归档 → FAIL（须先过门⑥收敛）")
    else:
        bad("D3-02 跳步归档未拦")
    # 收敛后（S6）可落盘
    st["phase"] = "S6_CONVERGED"
    st["converged_evidence"] = "用户拍板：「就按砍B线执行」"
    save(st_path, st)
    code, _ = run("decision-record.py", [dr_txt, "--out", out_dir], env_state=st_path)
    drs = [f for f in os.listdir(out_dir) if f.startswith("DR-")]
    if code == 0 and len(drs) == 1:
        ok("D3-03 S6_CONVERGED → 落盘成功（先红后绿的绿半边）")
    else:
        bad("D3-03 收敛态落盘异常", "code=%s" % code)


def d4_assumption_not_answer(T):
    print("— D4 假设冒充已问（台账说了算；置信度封顶）—")
    # 旧判定器：文本关键词全出现 → 判绿（假绿根源，RC-2 证据）
    assumed = os.path.join(T, "d4_assumed.md")
    open(assumed, "w", encoding="utf-8").write(
        "假设（未经用户确认）：销售增速口径未定，按同比下滑15%估；获客成本按行业均值估；"
        "渗透率按3%估；利润趋势按毛利趋势走平估；复购按留存行业均值估。\n")
    code, out = run("unknown-info-check.py", [assumed, "--scene", "S3"])
    if code == 0:
        ok("D4-01 旧判定器对「全关键词假设文本」判绿（假绿样本在册，RC-2 证据）")
    else:
        bad("D4-01 旧判定器意外判红（假绿前提变化，需复核样本）", out.strip()[:100])
    # 新判定器：同一信息状态（台账全未问）→ 拦
    st_path = os.path.join(T, "d4_state.json")
    code, _ = run("state-gate.py", ["--init", "--scene", "S3"], env_state=st_path)
    code, out = run("info-gate.py", [st_path])
    if code == 1:
        ok("D4-02 新 G 闸：文本写满关键词但台账未问 → 仍拦（台账说了算）")
    else:
        bad("D4-02 新 G 闸被文本自证骗过（RC-2 回潮）")
    # 非 critical 缺 ≥3 → 放行但置信度封顶=中
    st = load(st_path)
    confirm_all_critical(st)
    for n in ["促销史", "陈列", "客诉"]:
        st["info_ledger"][n] = {"critical": False, "status": "未问", "value": None, "src": None}
    save(st_path, st)
    code, out = run("info-gate.py", [st_path])
    if code == 2 and "封顶" in out:
        ok("D4-03 非 critical 缺 3 项 → exit 2 + 置信度封顶=中（假设≥3 不许标中高）")
    else:
        bad("D4-03 置信度封顶失效", "code=%s" % code)


def d5_long_session_no_drift(T):
    print("— D5 20 轮长 session（计数/台账/phase 落盘不漂移）—")
    st_path = os.path.join(T, "d5_state.json")
    code, _ = run("state-gate.py", ["--init", "--scene", "S2"], env_state=st_path)
    st = load(st_path)
    st["phase"] = "S3_INFO_GATHERING"
    st["profile_ok"] = True
    st["routing"] = {"ai_primitive": {"action": "删", "object": "产品组合", "scene": "S2"},
                     "script_candidates": [], "divergence": False,
                     "confirmed_by_user": "对，砍产品线级别", "arbitration_shown": False}
    st["rounds"] = {"total": 20, "no_new_info": 2, "skipped_debate": 0}
    st["asked_this_turn"] = 2
    names = list(st["info_ledger"])
    for i, n in enumerate(names):
        st["info_ledger"][n]["status"] = "已确认" if i == 0 else "已问待答"
    gate_log_append(st, "门④", "G闸 exit 1（已问待答）")
    save(st_path, st)
    # 落盘→重读：字段零漂移（模拟上下文压缩后的恢复）
    reloaded = load(st_path)
    drift = (reloaded["rounds"] != {"total": 20, "no_new_info": 2, "skipped_debate": 0}
             or reloaded["phase"] != "S3_INFO_GATHERING"
             or reloaded["info_ledger"][names[1]]["status"] != "已问待答")
    if not drift:
        ok("D5-01 落盘重读零漂移（rounds/phase/台账三态完整）")
    else:
        bad("D5-01 长会话字段漂移")
    # 20 轮后 G 闸仍按台账判（不按轮次"聊久了就放行"）
    code, out = run("info-gate.py", [st_path])
    if code == 1 and "已问待答" in out:
        ok("D5-02 第 20 轮 critical 已问待答 → 仍 exit 1（轮次不影响判定）")
    else:
        bad("D5-02 长会话判定漂移", "code=%s" % code)
    # 审计：S3 状态一致性
    code, out = run("state-gate.py", ["--audit", "--state", st_path, "--dr-dir", T])
    if code == 0:
        ok("D5-03 20 轮终态审计一致（无绕闸红项）")
    else:
        bad("D5-03 审计红", out.strip()[:120])
    # 连续 2 轮同 critical 已问待答 → SKILL 规则允许转显式假设（exit 仍 1，但这是规则层；此处断言闸不因轮次自动放行）
    st["rounds"]["no_new_info"] = 3  # 熔断口径：连续 3 轮无新信息
    save(st_path, st)
    code, _ = run("info-gate.py", [st_path])
    if code == 1:
        ok("D5-04 熔断触发（3 轮无新信息）也不改变 G 闸物理判定（强制收敛走显式假设路径）")
    else:
        bad("D5-04 熔断改变了闸判定（闸被轮次旁路）")


def main():
    a = sys.argv[1:]
    if "--self" in a or not a or (len(a) == 1 and a[0] in ("--help", "-h")):
        T = tempfile.mkdtemp(prefix="pm_replay_")
        print("== tests/replay.py：流程回归骨架（D1-D5 可自动化断言）==")
        d1_happy_path(T)
        d2_g_gate_blocks(T)
        d3_convergence_gate_blocks(T)
        d4_assumption_not_answer(T)
        d5_long_session_no_drift(T)
        print("═══════════════════════════")
        print("replay 结果：%d 通过，%d 失败" % (PASS, FAIL))
        print("ALL GREEN ✅" if FAIL == 0 else "HAS RED ❌")
        return 0 if FAIL == 0 else 1
    print("用法：python3 tests/replay.py（无参即全量跑）")
    return 2


if __name__ == "__main__":
    sys.exit(main())
