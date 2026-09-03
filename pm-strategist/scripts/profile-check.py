#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""profile-check.py — 决策前提库身份层校验（总案 v2.1 闸口 C + P2-3）

闸口 C（全强制）：会话载入前提库时校验——
  L0 必填 2 个：行业大类 + 品类名称
  L1 关键变量：品牌阶段/渠道结构/拍板权(组织分工)/定位禁区(品牌定位)
      —— 必须带确认时间戳，超期 90 天 → 关键决策前必须重验
路径解析顺序（P2-3：路径为可配置默认值，脚本内不硬编码死路径）：
  1) --profile 参数   2) 环境变量 PM_STRATEGIST_PROFILE   3) 默认 ~/.workbuddy/pm-strategist/profile.md
退出码: 0=可载入; 1=未固化/缺字段/超期（附重验提示）; 2=用法错误
"""
import sys, os, re, argparse, datetime

DEFAULT_PROFILE_DIR = os.path.expanduser("~/.workbuddy/pm-strategist")  # 可配置默认值（P2-3）
L0 = ["行业", "品类"]
L1 = ["品牌阶段", "渠道结构", "组织分工", "品牌定位"]
TIMESTAMP_KEYS = ["固化日期", "上次确认"]
STALE_DAYS = 90


def profile_path(args):
    if getattr(args, "profile", None):
        return args.profile
    env = os.environ.get("PM_STRATEGIST_PROFILE")
    if env:
        return env
    return os.path.join(DEFAULT_PROFILE_DIR, "profile.md")


def parse_profile(text):
    fields = {}
    for line in text.splitlines():
        m = re.match(r"^[-•]?\s*([^：:]{1,20})[：:]\s*(.*)$", line.strip())
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def check(text, today=None):
    today = today or datetime.date.today()
    fields = parse_profile(text)
    problems, warns = [], []
    for f in L0:
        v = fields.get(f, "")
        if not v or "【待固化】" in v:
            problems.append("L0 必填缺失：%s（首次使用须采集：行业大类+品类名称，5e 引导见 SKILL.md 身份层）" % f)
    for f in L1:
        v = fields.get(f, "")
        if not v or "【待固化】" in v:
            warns.append("L1 关键变量未固化：%s（用到时必须现场确认，⚠️假设·待验证）" % f)
    ts = None
    for k in TIMESTAMP_KEYS:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", fields.get(k, ""))
        if m:
            try:
                ts = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                ts = None
            break
    if ts is None:
        problems.append("无确认时间戳（固化日期/上次确认）——L1 关键变量视为未确认，关键决策前必须重验")
    else:
        age = (today - ts).days
        if age > STALE_DAYS:
            problems.append("确认戳已超期 %d 天（>%d 天，%s）→ 闸口 C：关键决策前必须重验 L1（品牌阶段/渠道结构/拍板权/定位禁区）" % (age, STALE_DAYS, ts.isoformat()))
        else:
            warns.append("确认戳 %s（%d 天前）有效" % (ts.isoformat(), age))
    return fields, problems, warns


def self_test():
    today = datetime.date.today()
    fresh = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 组织分工：示例占位\n- 品牌定位：示例占位\n- 固化日期：%s\n" % today.isoformat()
    stale = fresh.replace(today.isoformat(), (today - datetime.timedelta(days=120)).isoformat())
    placeholder = "- 行业：【待固化】\n- 品类：【待固化】\n- 固化日期：%s\n" % today.isoformat()
    nostamp = fresh.replace("- 固化日期：%s\n" % today.isoformat(), "")
    ok = True
    def chk(name, cond):
        nonlocal ok
        if not cond:
            ok = False
            print("  ❌ " + name)
    _, p1, _ = check(fresh, today)
    chk("新鲜样本通过", not p1)
    _, p2, _ = check(stale, today)
    chk("超期120天被拦", any("超期" in x for x in p2))
    _, p3, _ = check(placeholder, today)
    chk("占位未固化被拦", any(("必填缺失" in x or "待固化" in x) for x in p3))
    _, p4, _ = check(nostamp, today)
    chk("无确认戳被拦", any("时间戳" in x for x in p4))
    print("self: profile-check 闸口C（L1确认戳+90天重验） %s" % ("PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 决策前提库校验（闸口C：L1确认戳+超期90天重验）")
    ap.add_argument("--profile", help="前提库路径（默认顺序：--profile > PM_STRATEGIST_PROFILE > ~/.workbuddy/pm-strategist/profile.md）")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    pp = profile_path(a)
    if not os.path.isfile(pp):
        print("FAIL — 前提库不存在：%s" % pp)
        print("→ 未固化。首次使用走 SKILL.md「三层引导·身份层」采集（必填仅 2 个：行业大类+品类名称），")
        print("  结果写入包外前提库（路径可配置：--profile 或环境变量 PM_STRATEGIST_PROFILE，默认 %s）" % os.path.join(DEFAULT_PROFILE_DIR, "profile.md"))
        return 1
    text = open(pp, encoding="utf-8").read()
    fields, problems, warns = check(text)
    for f in L0 + L1:
        v = fields.get(f, "")
        show = (v[:30] + "…") if len(v) > 30 else (v if v else "（未固化）")
        print("%s：%s" % (f, show))
    for w in warns:
        print("  ⚠️ " + w)
    if problems:
        print("FAIL — 闸口C 拦下 %d 项：" % len(problems))
        for x in problems:
            print("  ❌ " + x)
        return 1
    print("PASS — 前提库可载入（闸口C）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
