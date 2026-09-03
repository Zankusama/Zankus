#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""profile-check.py — 决策前提库身份层校验（总案 v2.1 闸口 C + P2-3）

闸口 C（全强制）：会话载入前提库时校验——准确优先（前提库允许不完整、不允许不准确）：
  拦（problems，exit 1）仅三类不可信/伪固化：
    ① L0 必填缺失（行业大类 + 品类名称，空模板未首采）
    ② 无确认时间戳（固化日期/上次确认）——文件未走回显确认流程，整体不可信
    ③ 确认戳超期 90 天——旧确认须重验
  其余一律不拦流程（warn 缺失清单）：
    L1 真缺失（品牌阶段/渠道结构/拍板权/定位禁区，字段名对齐 SKILL.md）→ 清单 warn，
    决策命中该字段时由 AI 显式「假设·未验证」或现场补问，不得当作已确认；
    宽松字段（目标客群/公司规模）缺失 → warn 现场确认。含旧字段名（组织分工/品牌定位，
    语义漂移坑：分工≠拍板权、定位描述≠禁区）存在而规则名缺 → 迁移 warn + 去向指引（旧值
    信息价值 → 新位语义映射，非裸删）。历史判据（如 v4.1.x「L1≥1 则缺项拦」）已被本版取代，
    变更史见 git log，不在文件内叠历史。
  未固化判据：字段值空、或含「【待固化】」「【待补采…」占位标记 → 一律视为未固化。
    「待补采」是 AI 侧标注——只许记在当次输出/缺失清单，写进字段值会被本判据按未固化处理，
    防静默绕过（写了不等于已确认）。
路径解析顺序（路径为可配置默认值，脚本内不硬编码死路径）：
  1) --profile 参数   2) 环境变量 PM_STRATEGIST_PROFILE   3) 默认 ~/.workbuddy/pm-strategist/profile.md
退出码: 0=可载入; 1=L0 必填缺失/无确认戳/确认戳超期（附重验提示）; 2=用法错误
"""
import sys, os, re, argparse, datetime

DEFAULT_PROFILE_DIR = os.path.expanduser("~/.workbuddy/pm-strategist")  # 可配置默认值（P2-3）
L0_REQUIRED = ["行业", "品类"]  # 必填拦截（首采轻门槛，仅此 2 个）
L0_OPTIONAL = ["目标客群", "公司规模"]  # 宽松字段：缺失 → warn 现场确认，不拦（记忆分层 P3）
L0 = L0_REQUIRED + L0_OPTIONAL  # 打印用全集
# v4.1.3 对齐 SKILL.md：L1 = 品牌阶段/渠道结构/拍板权/定位禁区。
# 旧版误用「组织分工/品牌定位」当 L1 字段名，语义漂移（分工≠拍板权、定位描述≠禁区）→ 2026-09-03 验收发现
L1 = ["品牌阶段", "渠道结构", "拍板权", "定位禁区"]
LEGACY_L1_MAP = {"组织分工": "拍板权", "品牌定位": "定位禁区"}  # 旧字段名 → 规则字段名（迁移检测用）
# 去向指引（B 语义迁移：旧行信息价值 → 新位，非裸删；随迁移检测文案输出）
LEGACY_MIGRATION_GUIDE = {
    "组织分工": "旧行信息（谁负责产品战略/组织风险输入）→ 并入「拍板权」补采起点（谁对品类/定价/品牌架构真正拍板），迁移确认后删旧行",
    "品牌定位": "旧行品牌描述性内容（品类/定位）→ 并入品类备注；禁区红线类（绝不做什么）→ 并入「定位禁区」补采；迁移确认后删旧行",
}
TIMESTAMP_KEYS = ["固化日期", "上次确认"]
STALE_DAYS = 90
EXP_MAX = 5  # 经验句区 LRU 上限（记忆分层 P3 #17）
# 未固化占位标记：值含任一下列标记 → 视为未固化（「待补采」写进字段值
# 会被旧判据当"已确认"静默绕过准确性闸门；现只许记 AI 侧输出，写字段值=按未固化处理）
UNSET_MARKERS = ("【待固化】", "【待补采")


def filled(v):
    """True=字段有可信值（非空且不含未固化占位标记）"""
    return bool(v) and not any(m in v for m in UNSET_MARKERS)


def profile_path(args):
    if getattr(args, "profile", None):
        return args.profile
    env = os.environ.get("PM_STRATEGIST_PROFILE")
    if env:
        return env
    return os.path.join(DEFAULT_PROFILE_DIR, "profile.md")


def parse_profile(text):
    """段解析（记忆分层 P3 #14/#18）：只解析首个 `## ` 之前为身份段（字段键取冒号前裸名，容忍「字段名（括注）：值」
    写法不失配）；`## 经验句` 之后独立成经验句段，不误判为身份字段（F5 修复）。返回 (fields, experiences)。"""
    fields = {}
    experiences = []
    # 切身份段：首个二级标题之前
    first_h2 = text.find("\n## ")
    if first_h2 != -1:
        identity_text = text[:first_h2]
        rest = text[first_h2:]
    else:
        identity_text = text
        rest = ""
    for line in identity_text.splitlines():
        m = re.match(r"^[-•]?\s*([^：:]{1,20})[：:]\s*(.*)$", line.strip())
        if m:
            key = re.sub(r"[（(].*$", "", m.group(1)).strip()  # 裸名做键（N8：去括注）
            if key:
                fields[key] = m.group(2).strip()
    # 经验句段：`## 经验句` 之后逐行收集 `- 经验句：xxx`
    exp_marker = re.search(r"^## 经验句[^\n]*\n(.*)$", rest, re.M | re.S)
    if exp_marker:
        for line in exp_marker.group(1).splitlines():
            m2 = re.match(r"^[-•]?\s*经验句[：:]\s*(.*)$", line.strip())
            if m2:
                experiences.append(m2.group(1).strip())
    return fields, experiences


def check(text, today=None):
    today = today or datetime.date.today()
    fields, experiences = parse_profile(text)
    problems, warns = [], []
    # L0 必填（首采门槛，始终拦截；宽松字段只 warn 现场确认——P3 #15）
    for f in L0_REQUIRED:
        v = fields.get(f, "")
        if not filled(v):
            problems.append("L0 必填缺失：%s（首次使用须采集：行业大类+品类名称，5e 引导见 SKILL.md 身份层）" % f)
    for f in L0_OPTIONAL:
        v = fields.get(f, "")
        if not filled(v):
            warns.append("L0 宽松字段未固化：%s（缺失不拦，用到时现场确认——首采轻门槛=必填仅 2 个）" % f)
    # 时间戳（先算：L1 缺失的处置依赖"是否已固化"状态）
    ts = None
    for k in TIMESTAMP_KEYS:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", fields.get(k, ""))
        if m:
            try:
                ts = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                ts = None
            break
    # 拦截二分（v2 问答纪律，见文件头 docstring）：真缺失（从未被确认/含未固化标记）→ warn 缺失清单
    #   不拦流程；决策命中时 AI 显式「假设·未验证」或现场补问，不得当作已确认；答不出=留空不猜。
    # 旧名在而规则名缺时，该字段的通用 L1 缺失 warn 由「迁移去向 warn」覆盖（同字段不去重双响，B3 盲审修复）
    legacy_covering = {}
    for legacy, new in LEGACY_L1_MAP.items():
        legacy_covering[new] = filled(fields.get(legacy, "").strip())
    for f in L1:
        if legacy_covering.get(f):  # 旧字段残留：迁移去向 warn 已带该字段缺失语义，避免双响
            continue
        if not filled(fields.get(f, "")):
            warns.append("L1 未固化：%s（缺失清单——决策命中该字段[如定价/上市涉拍板权、新渠道涉定位禁区]须显式「假设·未验证」或现场补问，不得当作已确认；答不出=留空不猜）" % f)
    # 废字段双条件（P3 #16）：①旧名在而规则名缺 → warn 迁移提示（内容语义不等：分工≠拍板权、定位描述≠禁区）；
    #                         ②旧名与规则名共存（已补采但旧行未删）→ warn 提示清理（不拦截，防老文件卡死）
    for legacy, new in LEGACY_L1_MAP.items():
        lv = fields.get(legacy, "").strip()
        nv = fields.get(new, "").strip()
        has_legacy = filled(lv)
        has_new = filled(nv)
        if has_legacy and not has_new:
            warns.append("旧字段「%s」残留但规则字段「%s」未固化——旧行≠新字段真值（分工≠拍板权、定位描述≠禁区），「%s」按未固化处理（缺失清单），决策命中时显式假设/补问。去向指引：%s" % (legacy, new, new, LEGACY_MIGRATION_GUIDE.get(legacy, "旧行信息价值应并入对应新字段，确认后删旧行")))
        elif has_legacy and has_new:
            warns.append("字段名清理：旧字段「%s」与新字段「%s」共存（已补采但旧行未删）→ 建议清理旧行，新口径以规则字段为准（不拦截）" % (legacy, new))
    if ts is None:
        problems.append("无确认时间戳（固化日期/上次确认）——L1 关键变量视为未确认，关键决策前必须重验")
    else:
        age = (today - ts).days
        if age > STALE_DAYS:
            problems.append("确认戳已超期 %d 天（>%d 天，%s）→ 闸口 C：关键决策前必须重验 L1（品牌阶段/渠道结构/拍板权/定位禁区）" % (age, STALE_DAYS, ts.isoformat()))
        else:
            warns.append("确认戳 %s（%d 天前）有效" % (ts.isoformat(), age))
    # 经验句区超限（P3 #17）：>5 → warn 回显确认淘汰最旧
    if len(experiences) > EXP_MAX:
        warns.append("经验句超限：%d 条（上限 %d）→ 须回显确认淘汰最旧 1 条（LRU 纪律）" % (len(experiences), EXP_MAX))
    return fields, problems, warns


def self_test():
    today = datetime.date.today()
    fresh = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 拍板权：示例占位\n- 定位禁区：示例占位\n- 固化日期：%s\n" % today.isoformat()
    stale = fresh.replace(today.isoformat(), (today - datetime.timedelta(days=120)).isoformat())
    placeholder = "- 行业：【待固化】\n- 品类：【待固化】\n- 固化日期：%s\n" % today.isoformat()
    nostamp = fresh.replace("- 固化日期：%s\n" % today.isoformat(), "")
    legacy = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 组织分工：示例占位\n- 品牌定位：示例占位\n- 固化日期：%s\n" % today.isoformat()
    # F1 反例（对抗审查 N1 实证）：合法轻固化 = L0 两项 + 确认戳、无任何 L1
    # （SKILL.md「必填仅 2 个」流程首采产物）→ 不得拦截，降级 warn
    light = "- 行业：示例占位\n- 品类：示例占位\n- 固化日期：%s\n" % today.isoformat()
    # P3 新样本：括注字段名（N8 兼容：键取冒号前裸名）+ 宽松字段缺失 + 经验句超限
    paren = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 拍板权（谁拍板）：示例占位\n- 定位禁区：示例占位\n- 固化日期：%s\n" % today.isoformat()
    exp6 = fresh + "## 经验句\n- 经验句：规则句一\n- 经验句：规则句二\n- 经验句：规则句三\n- 经验句：规则句四\n- 经验句：规则句五\n- 经验句：规则句六\n"
    ok = True
    def chk(name, cond):
        nonlocal ok
        if not cond:
            ok = False
            print("  ❌ " + name)
    _, p1, _ = check(fresh, today)
    chk("新鲜样本（规则字段齐）通过", not p1)
    _, p2, _ = check(stale, today)
    chk("超期120天被拦", any("超期" in x for x in p2))
    _, p3, _ = check(placeholder, today)
    chk("占位未固化被拦", any(("必填缺失" in x or "待固化" in x) for x in p3))
    _, p4, _ = check(nostamp, today)
    chk("无确认戳被拦", any("时间戳" in x for x in p4))
    _, p5, w5 = check(legacy, today)
    chk("旧字段名迁移降 warn 不拦流程（拍板权/定位禁区真值从未被确认=真缺失，v2 二分）", not p5)
    chk("迁移 warn 含去向指引（旧值→新位语义映射，非裸删）", any("去向指引" in x for x in w5))
    chk("同字段去重：迁移去向 warn 已覆盖拍板权/定位禁区时，不叠通用 L1 缺失 warn（B3）", not any(("L1 未固化：拍板权" in x) or ("L1 未固化：定位禁区" in x) for x in w5))
    _, p6, w6 = check(light, today)
    chk("轻固化反例不拦（L0两项+戳、L1全缺=首采渐进期）", not p6)
    chk("轻固化降级为 L1 缺失清单 warn", any("L1 未固化" in x for x in w6))
    _, p7, w7 = check(paren, today)
    chk("括注字段名（拍板权（谁拍板）：值）解析到裸名键不失配（N8）", not p7 and not any("拍板权" in x and "缺失" in x for x in p7))
    _, p8, w8 = check(fresh, today)
    chk("宽松字段（目标客群/公司规模）缺失不拦，warn 现场确认（首采轻门槛保住）", not p8 and any("宽松字段未固化" in x for x in w8))
    _, p9, w9 = check(exp6, today)
    chk("经验句 6 条超限 → warn LRU 淘汰提示（身份段不受污染）", any("经验句超限" in x for x in w9))
    # v4.2.2 新增：部分 L1 已固化、缺拍板权/定位禁区（真实 profile 形态）→ 降 warn 不拦（v2 真缺失）
    partial = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 固化日期：%s\n" % today.isoformat()
    _, p10, w10 = check(partial, today)
    chk("部分 L1 已固化缺项 → 降 warn 不拦（v2 真缺失：拍板权缺失清单，不再撞墙）", not p10 and any("拍板权" in x and "未固化" in x for x in w10))
    # 待补采占位写进字段值 → 按未固化处理（防静默绕过准确性闸门）
    pending = "- 行业：示例占位\n- 品类：示例占位\n- 品牌阶段：示例占位\n- 渠道结构：示例占位\n- 拍板权：示例占位\n- 定位禁区：【待补采：此信息问老板】\n- 固化日期：%s\n" % today.isoformat()
    _, p11, w11 = check(pending, today)
    chk("待补采占位不当已确认（【待补采…】写进字段值 → 仍按未固化 warn，不拦流程）", not p11 and any("定位禁区" in x and "未固化" in x for x in w11))
    print("self: profile-check 闸口C（L0必填+确认戳90天+真缺失二分+迁移去向去重+待补采判据+轻固化+宽松字段+括注N8+经验句超限） %s" % ("PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 决策前提库校验（闸口C：L0必填+确认戳90天；真缺失列清单不拦流程）")
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
