#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""info-gate.py — G 闸·信息准入（v5.0 批次一 #2/#6；R-4 三态台账判定）

替代 unknown-info-check.py 的判定职能：判定输入从「AI 输出文本」（关键词子串包含=假绿
根源——AI 把词写进自己的假设清单脚本就判"已问"）改为 session_state.json 的 info_ledger
（状态由会话过程机器记录，AI 文本自证不算数）。unknown-info-check.py 保留为词法引导
参考，不再承担"信息是否收集齐"的判定。

三态台账：已确认 / 已问待答 / 未问 —— 只有「已确认」计入满足。
「问了没答」在决策上等价于「没问」，但补救动作不同：未问 → 开口问；
已问待答 → 追问（连续 2 轮仍待答 → 转显式假设 + 置信度强制=中）。

critical 预置（每场景 3 条，硬编码本表——动态判定=回到 AI 自觉，等于没闸；
快消之外的业务可用 --profile-critical <json文件> 外部覆盖）。

G 闸卡结论不卡对话：critical 未确认 → 禁止输出【建议】区（本轮只做定向补问 ≤2），
对话照常继续；非 critical 缺口 ≥3 → 放行但置信度封顶=中（confidence_cap）。
🔴红线闸（RC-9）：可逆性=🔴 AND critical 未确认 → exit 1 硬拦——
不可逆决策在关键信息未确认时下结论是红线，不是降级项。

用法:
  python3 scripts/info-gate.py <session_state.json> [--profile-critical <file>]
  python3 scripts/info-gate.py --init-ledger --scene S3     # 打印该场景初始台账 JSON
  python3 scripts/info-gate.py --critical-list [--scene S3] # 打印 critical 清单（人读）
  python3 scripts/info-gate.py --self
退出码: 0=critical 全确认（可出【建议】）；1=critical 有缺口 / 🔴红线（禁出【建议】，只补问）；
        2=非 critical 缺口 ≥3（放行但置信度封顶=中）
"""
import sys, os, json, argparse

SCHEMA_VERSION = "5.0.0"
STATUSES = ("已确认", "已问待答", "未问")  # 三态，唯一合法值集

# 每场景 3 条 critical（"不给就没法判"项）+ 2 条默认非 critical（--init-ledger 预置，可增删）
CRITICAL = {
    "S1": ["市场规模口径", "目标人群画像", "成本结构"],
    "S2": ["单品贡献度", "增长趋势", "战略定位"],
    "S3": ["月销趋势", "渠道构成", "复购"],  # W-08 口径变更：月销趋势替换上市时长（3条；第一判据=连续3个月增速档位）
    "S4": ["价格带", "成本与毛利目标", "需求弹性"],
    "S5": ["渠道结构", "上市节奏", "资源预算"],
    "C": ["决策目标", "时间窗", "约束条件"],
}
NON_CRITICAL = {
    "S1": ["竞品对照", "渠道适配"],
    "S2": ["产能约束"],
    "S3": ["获客成本", "利润趋势"],
    "S4": ["竞品价格"],
    "S5": ["物料准备"],
    "C": [],
}


def scene_of(state):
    """场景号：显式 routing.ai_primitive.scene > state.scene > None（None 按 C 处理并提示）。"""
    r = state.get("routing") or {}
    s = (r.get("ai_primitive") or {}).get("scene") or state.get("scene")
    return s if s in CRITICAL else None


def status_of(item):
    """台账项状态（fail-closed：值非法/缺失 → 按「未问」处理并返回告警）。"""
    st = (item or {}).get("status")
    return (st, None) if st in STATUSES else ("未问", "台账项状态非法（%r），按「未问」处理" % st)


def load_critical(scene, profile_critical_path=None):
    """critical 清单：--profile-critical 外部覆盖 > 内置表。返回 (清单, 来源)。"""
    if profile_critical_path:
        try:
            data = json.load(open(profile_critical_path, encoding="utf-8"))
            items = data.get(scene) if isinstance(data, dict) else None
            if isinstance(items, list) and items and all(isinstance(x, str) for x in items):
                return list(items), profile_critical_path
            print("⚠️ --profile-critical 文件缺「%s」有效清单，回落内置表" % scene)
        except (OSError, ValueError) as e:
            print("⚠️ --profile-critical 读取失败（%s），回落内置表" % e)
    return list(CRITICAL.get(scene, CRITICAL["C"])), "内置表"


def judge(state, critical_names):
    """G 闸判定。返回 (exit_code, 结论行列表)。
    exit 0=critical 全确认；1=critical 缺口或🔴红线；2=非 critical 缺口≥3。"""
    ledger = state.get("info_ledger") or {}
    scene = scene_of(state)
    rev = state.get("reversibility")
    lines = ["G 闸判定（场景=%s · 可逆性=%s · 台账项 %d）"
             % (scene or "未知", rev or "未标", len(ledger))]
    confirmed, pending, unasked, noncrit_gap, warns = [], [], [], [], []
    # critical 清单为准（fail-closed：清单项不在台账 = 未问）
    for name in critical_names:
        item = ledger.get(name) or {}
        st, warn = status_of(item)
        if warn:
            warns.append("%s：%s" % (name, warn))
        if st == "已确认":
            confirmed.append(name)
        elif st == "已问待答":
            pending.append(name)
        else:
            unasked.append(name)
    # 非 critical 项 = 台账里不在 critical 清单的项
    for name, item in ledger.items():
        if name in critical_names:
            continue
        st, warn = status_of(item)
        if warn:
            warns.append("%s：%s" % (name, warn))
        if st == "已确认":
            confirmed.append(name)
        elif st == "已问待答":
            pending.append(name)
        else:
            unasked.append(name)
            noncrit_gap.append(name)
    lines.append("  已确认  (%d)：%s" % (len(confirmed), "、".join(confirmed) or "—"))
    lines.append("  已问待答(%d)：%s" % (len(pending), "、".join(pending) or "—"))
    lines.append("  未问    (%d)：%s" % (len(unasked), "、".join(unasked) or "—"))
    for w in warns:
        lines.append("  ⚠️ " + w)
    crit_gap = pending_and_unasked = [x for x in (pending + unasked) if x in critical_names]
    if rev == "🔴" and crit_gap:
        lines.append("  🔴红线闸：不可逆决策 + critical 未确认（%s）——硬拦，禁出【建议】，先补关键信息"
                     % "、".join(crit_gap))
    if crit_gap:
        lines.append("  critical 缺口：%s → 禁止输出【建议】区，本轮只做定向补问 ≤2（对话照常，卡结论不卡对话）"
                     % "、".join(crit_gap))
        lines.append("  建议先问：%s" % "、".join("①%s" % x for x in crit_gap[:2]))
        return 1, lines
    if len(noncrit_gap) >= 3:
        lines.append("  非 critical 缺口 %d 项（%s）→ 放行，但置信度封顶=中（confidence_cap）"
                     % (len(noncrit_gap), "、".join(noncrit_gap)))
        return 2, lines
    lines.append("  critical 全确认（%d/%d）→ 可出【建议】区" % (len(critical_names), len(critical_names)))
    return 0, lines


def init_ledger(scene):
    """该场景初始台账（3 critical + 默认非 critical，全部「未问」，AI 会话中逐项更新）。"""
    ledger = {}
    for name in CRITICAL.get(scene, CRITICAL["C"]):
        ledger[name] = {"critical": True, "status": "未问", "value": None, "src": None}
    for name in NON_CRITICAL.get(scene, []):
        ledger[name] = {"critical": False, "status": "未问", "value": None, "src": None}
    return ledger


def self_test():
    ok = True
    def chk(name, cond):
        nonlocal ok
        print("  %s %s" % ("✓" if cond else "✗ 未拦住/误报", name))
        ok = ok and cond
    crit = CRITICAL["S3"]
    # 1 全确认 → 0
    s1 = {"scene": "S3", "reversibility": "🟢",
          "info_ledger": {n: {"critical": True, "status": "已确认"} for n in crit}}
    code, _ = judge(s1, crit)
    chk("critical 全确认 → exit 0", code == 0)
    # 2 缺 1 critical（已问待答）→ 1
    s2 = json.loads(json.dumps(s1)); s2["info_ledger"]["复购"]["status"] = "已问待答"
    code, lines = judge(s2, crit)
    chk("critical 已问待答 → exit 1（问了没答=没问）", code == 1)
    chk("输出含「建议先问」补问指引", any("建议先问" in x for x in lines))
    # 3 🔴红线：不可逆 + critical 缺 → exit 1 且红线消息
    s3 = json.loads(json.dumps(s2)); s3["reversibility"] = "🔴"
    code, lines = judge(s3, crit)
    chk("🔴红线闸（不可逆+缺critical）→ exit 1 且含红线消息", code == 1 and any("红线" in x for x in lines))
    # 4 非 critical 缺 ≥3 → exit 2
    s4 = {"scene": "S1", "reversibility": "🟢", "info_ledger": {
        n: {"critical": True, "status": "已确认"} for n in CRITICAL["S1"]}}
    for extra in ["竞品对照", "渠道适配", "产能约束"]:
        s4["info_ledger"][extra] = {"critical": False, "status": "未问"}
    code, lines = judge(s4, CRITICAL["S1"])
    chk("非 critical 缺 3 项 → exit 2（放行+置信度封顶）", code == 2 and any("封顶" in x for x in lines))
    # 5 假绿防线：文本写满关键词不进台账 → 仍拦（台账说了算，fail-closed）
    s5 = {"scene": "S3", "reversibility": "🟢", "info_ledger": {}}
    code, _ = judge(s5, crit)
    chk("台账为空（AI 文本自证不算数）→ exit 1（3 critical 全按未问）", code == 1)
    # 6 fail-closed：非法 status 值按未问
    s6 = json.loads(json.dumps(s1)); s6["info_ledger"]["复购"]["status"] = "大概问过"
    code, _ = judge(s6, crit)
    chk("非法状态值（「大概问过」）→ 按未问 → exit 1", code == 1)
    # 7 routing.ai_primitive.scene 优先于 state.scene
    s7 = {"scene": "S1", "reversibility": "🟢",
          "routing": {"ai_primitive": {"action": "判", "object": "现有单品", "scene": "S3"}},
          "info_ledger": {n: {"critical": True, "status": "已确认"} for n in crit}}
    chk("场景取 routing.ai_primitive.scene（S3 非 S1）", scene_of(s7) == "S3")
    code, _ = judge(s7, crit)
    chk("按 routing 场景判定 → exit 0", code == 0)
    # 8 --profile-critical 覆盖
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"S3": ["甲", "乙", "丙"]}, f); pf = f.name
    got, src = load_critical("S3", pf)
    chk("--profile-critical 覆盖生效（甲乙丙）", got == ["甲", "乙", "丙"])
    os.unlink(pf)
    print("self: G 闸三态台账 %s（三态判定+critical 预置+🔴红线+fail-closed+外部覆盖）%s"
          % ("8 项", "PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(
        description="pm-strategist G 闸·信息准入：读 session_state.json 的 info_ledger 做三态判定（critical 未确认禁出【建议】；🔴红线硬拦）")
    ap.add_argument("state", nargs="?", help="session_state.json 路径（判定输入=台账，非 AI 输出文本）")
    ap.add_argument("--profile-critical", dest="profile_critical", default=None,
                    help="critical 清单外部覆盖（JSON：{\"S3\": [\"项1\",...]}；快消外业务用）")
    ap.add_argument("--init-ledger", dest="init_ledger_flag", action="store_true",
                    help="打印指定场景初始台账 JSON（配合 --scene）")
    ap.add_argument("--critical-list", dest="critical_list", action="store_true",
                    help="打印 critical 清单（人读格式）")
    ap.add_argument("--scene", choices=list(CRITICAL), default=None,
                    help="场景号（--init-ledger/--critical-list 用；判定模式从 state 内读）")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.init_ledger_flag:
        if not a.scene:
            print("用法：--init-ledger 须配 --scene S1-S5/C"); return 2
        print(json.dumps(init_ledger(a.scene), ensure_ascii=False, indent=2))
        return 0
    if a.critical_list:
        for sc in ([a.scene] if a.scene else list(CRITICAL)):
            print("%s：%s" % (sc, "、".join(CRITICAL[sc])))
        return 0
    if not a.state:
        ap.print_help()
        return 2
    try:
        state = json.load(open(a.state, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("读入失败: %s", e); return 2
    if not isinstance(state, dict):
        print("FAIL — state 文件不是 JSON 对象"); return 2
    scene = scene_of(state)
    if scene is None:
        print("⚠️ state 缺场景信息（routing.ai_primitive.scene / scene），按 C 类清单判定")
    critical_names, src = load_critical(scene or "C", a.profile_critical)
    code, lines = judge(state, critical_names)
    for x in lines:
        print(x)
    verdict = {0: "PASS — critical 全确认，可出【建议】",
               1: "FAIL — critical 有缺口：禁出【建议】区，只做定向补问 ≤2",
               2: "PASS(封顶) — 放行但置信度封顶=中"}
    print(verdict[code])
    print("覆盖边界：本次=信息台账三态判定（已确认/已问待答/未问，critical 清单=%s）；"
          "未覆盖=台账项内容真伪（只记状态不验数据）与台面四区形态（走 check_output.py）。" % (src or "内置表"))
    return code


if __name__ == "__main__":
    sys.exit(main())
