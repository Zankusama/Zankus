#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decision-record.py — 决策记录（DR）9字段生成与完整性校验

输入对话要点（key: value 文本或 JSON），按 9 字段渲染结构化 DR 模板；
校验完整性：缺必填字段（问题/选项/决定）→ 提示缺哪些，退出码 1。

9字段契约（与 SKILL.md/fm-02 逐字一致）：
  问题/选项/决定/依据/反方意见/风险/假设清单/复盘日期/状态
  状态枚举：草案/已定/复盘/关闭；假设清单每条 ⚠️ 前缀（显式"无"合法）

用法:
  python3 scripts/decision-record.py --template            # 打印空模板
  python3 scripts/decision-record.py <要点文件>             # 渲染+校验
  cat 要点.txt | python3 scripts/decision-record.py -
  python3 scripts/decision-record.py --self
退出码: 0=渲染成功且必填齐, 1=缺必填字段, 2=读入错误
"""
import sys, json, argparse, datetime

DR_DATE = datetime.date.today().strftime("%Y%m%d")

FIELDS = ["问题", "选项", "决定", "依据", "反方意见", "风险", "假设清单", "复盘日期", "状态"]
REQUIRED = ["问题", "选项", "决定"]
STATUS = ["草案", "已定", "复盘", "关闭"]
HINTS = {
    "问题": "一句决策问题（含场景号与决策者/截止时间）",
    "选项": "≥2个，必须含不做/维持现状",
    "决定": "用户拍板原文；未拍板写推荐倾向",
    "依据": "引用哪个 ref/fm 的哪条（标注文件与条目）",
    "反方意见": "最强反方+什么数据/条件会推翻本决定",
    "风险": "6维度命中的风险点+验证方式（不替用户做风险结论）",
    "假设清单": "每条 ⚠️ 前缀「假设·待验证」；确无假设写「无——输入已全部确认」",
    "复盘日期": "YYYY-MM-DD",
    "状态": "草案/已定/复盘/关闭",
}
TEMPLATE = "# DR-%s-<slug>（日期已自动填入，编号/主题 slug 请落盘时补）\n" % DR_DATE + "".join("- %s：%s\n" % (f, ("【待补充】" + HINTS[f])) for f in FIELDS)


def parse_points(text):
    """key: value / key：value 逐行解析（冒号全半角兼容）；JSON 对象也认。"""
    pts = {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {k: str(v) for k, v in obj.items()}
    except (ValueError, TypeError):
        pass
    for line in text.splitlines():
        line = line.strip().lstrip("-• ")
        if not line or line.startswith("#"):
            continue
        for sep in ("：", ":"):
            if sep in line:
                k, v = line.split(sep, 1)
                k = k.strip()
                if k in FIELDS:
                    pts[k] = v.strip()
                break
    return pts


def validate(pts):
    missing = [f for f in REQUIRED if not pts.get(f)]
    problems = []
    st = pts.get("状态", "")
    if st and not any(x in st for x in STATUS):
        problems.append("状态非法（应为 草案/已定/复盘/关闭 之一，当前: %s）" % st[:20])
    d = pts.get("复盘日期", "")
    if d and "待补充" not in d:
        import re
        if not re.search(r"\d{4}-\d{2}-\d{2}", d):
            problems.append("复盘日期格式应为 YYYY-MM-DD（当前: %s）" % d[:20])
    return missing, problems


def render(pts):
    lines = ["# DR-%s-<slug>（日期由脚本自动填入，slug 请落盘时补）" % DR_DATE]
    for f in FIELDS:
        v = pts.get(f, "").strip() or "【待补充】%s" % HINTS[f]
        lines.append("- %s：%s" % (f, v))
    return "\n".join(lines)


def self_test():
    good = {"问题": "示例占位：A品要不要砍（S2）", "选项": "砍/不砍（含维持现状）", "决定": "推荐先收缩后观察",
            "依据": "ref-02+fm-03", "反方意见": "若为渠道入场券则砍错", "风险": "供应链：库存", "假设清单": "⚠️ 假设·待验证：渠道合约Q4到期",
            "复盘日期": "2026-12-31", "状态": "草案"}
    ok = not validate(good)[0] and not validate(good)[1]
    bad_missing, _ = validate({"问题": "x"})
    caught = bad_missing == ["选项", "决定"]
    print("self: 齐全样本 %s；缺项拦截 %s（期望拦 选项/决定）" % ("PASS✓" if ok else "FAIL✗", "PASS✓" if caught else "FAIL✗"))
    return ok and caught


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 决策记录9字段生成与校验")
    ap.add_argument("input", nargs="?", help="要点文件（key: value 或 JSON），或 - 读 stdin")
    ap.add_argument("--template", action="store_true", help="打印空模板")
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
    missing, problems = validate(pts)
    print(render(pts))
    if missing or problems:
        print("FAIL — 必填缺：%s%s" % ("/".join(missing) if missing else "", ("；" + "；".join(problems)) if problems else ""))
        if not pts:
            print("提示：一行一条「字段：内容」，字段名限 %s" % "/".join(FIELDS))
        return 1
    print("PASS — 必填齐（问题/选项/决定）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
