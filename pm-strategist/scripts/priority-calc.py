#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""priority-calc.py — RICE / WSJF 优先级计算器（fm-03 公式对齐）

RICE = Reach × Impact × Confidence ÷ Effort
WSJF = (用户商业价值 + 时间关键性 + 风险降低/机会启用) ÷ 工作量

输入 JSON 数组（文件或 stdin），字段：
  RICE:  name, reach, impact, confidence, effort        （impact: 3/2/1/0.5；confidence: 1/0.8/0.5）
  WSJF:  name, user_business_value, time_criticality, risk_reduction, effort
输出：按分值降序的 Markdown 表格（含公式回显）。示例数据一律"示例占位"。

用法:
  python3 scripts/priority-calc.py --method rice --input 项目.json
  python3 scripts/priority-calc.py --method wsjf --demo
  python3 scripts/priority-calc.py --self
退出码: 0=成功, 2=输入/读入错误
"""
import sys, json, argparse


def calc_rice(items):
    rows = []
    for it in items:
        try:
            r, i, c, e = float(it["reach"]), float(it["impact"]), float(it["confidence"]), float(it["effort"])
        except (KeyError, TypeError, ValueError) as ex:
            raise ValueError("RICE 字段缺失/非法（name=%s）：%s" % (it.get("name", "?"), ex))
        if e <= 0:
            raise ValueError("effort 必须 > 0（name=%s）" % it.get("name", "?"))
        rows.append((it["name"], r * i * c / e))
    rows.sort(key=lambda x: -x[1])
    return rows


def calc_wsjf(items):
    rows = []
    for it in items:
        try:
            bv = float(it.get("user_business_value", it.get("商业价值")))
            tc = float(it.get("time_criticality", it.get("时间关键性")))
            rr = float(it.get("risk_reduction", it.get("风险降低")))
            e = float(it.get("effort", it.get("job_size", it.get("工作量"))))
        except (KeyError, TypeError, ValueError) as ex:
            raise ValueError("WSJF 字段缺失/非法（name=%s）：%s" % (it.get("name", "?"), ex))
        if e <= 0:
            raise ValueError("effort 必须 > 0（name=%s）" % it.get("name", "?"))
        rows.append((it["name"], (bv + tc + rr) / e))
    rows.sort(key=lambda x: -x[1])
    return rows


DEMO = [{"name": "示例占位·SKU-A", "reach": 500, "impact": 3, "confidence": 0.8, "effort": 2},
        {"name": "示例占位·SKU-B", "reach": 300, "impact": 2, "confidence": 1.0, "effort": 3},
        {"name": "示例占位·SKU-C", "reach": 800, "impact": 1, "confidence": 0.5, "effort": 5}]
DEMO_W = [{"name": "示例占位·项目甲", "user_business_value": 8, "time_criticality": 5, "risk_reduction": 3, "effort": 4},
          {"name": "示例占位·项目乙", "user_business_value": 5, "time_criticality": 8, "risk_reduction": 5, "effort": 5},
          {"name": "示例占位·项目丙", "user_business_value": 3, "time_criticality": 2, "risk_reduction": 2, "effort": 1}]


def render(method, rows):
    head = "公式：%s\n| 排名 | 项目 | 分值 |\n|---|---|---|\n" % (
        "RICE = Reach×Impact×Confidence÷Effort" if method == "rice" else "WSJF = (商业价值+时间关键性+风险降低)÷工作量")
    body = "".join("| %d | %s | %.2f |\n" % (i + 1, n, s) for i, (n, s) in enumerate(rows))
    return head + body + "（注：示例数据为示例占位，打分口径需写入决策记录依据）"


def self_test():
    rows_r = calc_rice(DEMO)
    rows_w = calc_wsjf(DEMO_W)
    ok_r = rows_r[0][0] == "示例占位·SKU-A" and [n for n, _ in rows_r] == ["示例占位·SKU-A", "示例占位·SKU-B", "示例占位·SKU-C"]
    ok_w = rows_w[0][0] == "示例占位·项目丙" and rows_w[1][0] == "示例占位·项目甲" and rows_w[2][0] == "示例占位·项目乙"
    print("self: RICE排序 %s（期望 SKU-A→B→C：%.2f/%.2f/%.2f）；WSJF排序 %s（期望 项目丙>甲>乙：%.2f/%.2f/%.2f）" % (
        "PASS✓" if ok_r else "FAIL✗", rows_r[0][1], rows_r[1][1], rows_r[2][1],
        "PASS✓" if ok_w else "FAIL✗", rows_w[0][1], rows_w[1][1], rows_w[2][1]))
    return ok_r and ok_w


def main():
    ap = argparse.ArgumentParser(description="pm-strategist RICE/WSJF 优先级计算器")
    ap.add_argument("--method", choices=["rice", "wsjf"], default="rice", help="计算方法（缺省 rice）")
    ap.add_argument("--input", help="JSON 数组文件路径；缺 stdin 需配 -")
    ap.add_argument("--demo", action="store_true", help="内置3项目示例（示例占位）")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.demo:
        items = DEMO if a.method == "rice" else DEMO_W
    else:
        if not a.input:
            ap.print_help()
            return 2
        try:
            raw = open(a.input, encoding="utf-8").read() if a.input != "-" else sys.stdin.read()
        except OSError as e:
            print("读入失败: %s" % e)
            return 2
        try:
            items = json.loads(raw)
            assert isinstance(items, list)
        except (ValueError, AssertionError):
            print("输入应为 JSON 数组：[{name, reach, impact, confidence, effort}, ...]")
            return 2
    try:
        rows = calc_rice(items) if a.method == "rice" else calc_wsjf(items)
    except ValueError as e:
        print("输入错误: %s" % e)
        return 2
    print(render(a.method, rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
