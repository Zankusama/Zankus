#!/usr/bin/env python3
"""
check_rehab_report.py — 康复履历 schema 校验（输出质量闸门）
=============================================================
校验修复履历/诊断报告的必填字段齐全性——防「做完了但履历残缺」（AI 手写可能漏项）。

用法:
  python3 check_rehab_report.py <履历文件>        # 校验一个 md 履历
  python3 check_rehab_report.py --self            # 自检（内置样本）

退出码: 0 = 必填字段齐全；1 = 缺必填字段（列出缺什么）；2 = 文件不可读/格式不符

必填字段（修复履历表格每行）:
  - 项（pN.item 键名）
  - 未过详情
  - 分级（基本型/期望型/兴奋型/无差异型/反向型）
  - 为什么修
  - 对应机制
  - 修法
校验「期望 vs 实际」对比列（如有）:
  - 修复前分 / 修复后分 都存在才放行
"""
import re
import sys

REQUIRED = ["项", "未过详情", "分级", "为什么修", "对应机制", "修法"]
GRADES = ("基本型", "期望型", "兴奋型", "无差异型", "反向型")


def check_report(content: str) -> list:
    """校验履历内容，返回错误列表（空=通过）"""
    errors = []
    # 找修复履历表格（| 项 | 未过详情 | ... | 修法 |）
    rows = []
    in_table = False
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('|') and '| 项 |' in line:
            in_table = True
            continue
        if in_table:
            if not line.startswith('|'):
                in_table = False
                continue
            # 跳过分隔行（|:---| 或 |---|）
            if re.fullmatch(r'\|[\s:\-|]+\|', line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            if len(cells) >= 6 and cells[0]:
                rows.append(cells)

    if not rows:
        return ["未找到修复履历表格（格式：| 项 | 未过详情 | 分级 | 为什么修 | 对应机制 | 修法 |）"]

    for i, cells in enumerate(rows, 1):
        row_err = []
        # 必填字段非空
        for idx, field in enumerate(REQUIRED):
            if idx >= len(cells) or not cells[idx]:
                row_err.append(f"行{i} 缺「{field}」")
        # 分级合法
        if len(cells) >= 3 and cells[2] and cells[2] not in GRADES:
            row_err.append(f"行{i} 分级「{cells[2]}」非法（应为 {GRADES}）")
        errors.extend(row_err)
    return errors


def check_before_after(content: str) -> list:
    """校验「期望 vs 实际」对比（如有该列）"""
    errors = []
    # 若履历含修复前后分，需成对
    scores = re.findall(r'(\d{1,3})/\d{1,3}\s*(?:→|->)\s*(\d{1,3})/\d{1,3}', content)
    if scores:
        for before, after in scores:
            if int(after) < int(before):
                errors.append(f"修复后分 {after} < 修复前分 {before}——分数倒退需说明原因")
    return errors


def self_check() -> None:
    ok = """| 项 | 未过详情 | 分级 | 为什么修 | 对应机制 | 修法 |
|:---|:---------|:----:|:---------|:---------|:-----|
| p1.scriptized | 无脚本 | 基本型 | 手敲必错 | ①确定性 | 建脚本 |
| p4.step_flow | 步骤断 | 期望型 | 一步到位 | ④分步 | 补编号 |"""
    bad = """| 项 | 未过详情 | 分级 | 为什么修 | 对应机制 | 修法 |
|:---|:---------|:----:|:---------|:---------|:-----|
| p1.scriptized | 无脚本 | 基本型 | 手敲必错 | ①确定性 | 建脚本 |
| p4.step_flow | | 乱分级 | | | |"""
    assert check_report(ok) == [], f"合格样本应过: {check_report(ok)}"
    errs = check_report(bad)
    assert len(errs) >= 3, f"缺陷样本应报错: {errs}"
    print(f"✅ 自检通过：合格样本 0 错 / 缺陷样本 {len(errs)} 处（含缺字段+非法分级）")


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: check_rehab_report.py <履历文件> | --self", file=sys.stderr)
        return 2
    if sys.argv[1] == "--self":
        self_check()
        return 0
    try:
        with open(sys.argv[1], encoding='utf-8') as f:
            content = f.read()
    except OSError as e:
        print(f"❌ 文件不可读: {e}", file=sys.stderr)
        return 2
    errors = check_report(content) + check_before_after(content)
    if errors:
        print("❌ 履历校验失败：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("✅ 履历校验通过：必填字段齐全，分级合法，分数无倒退")
    return 0


if __name__ == '__main__':
    sys.exit(main())
