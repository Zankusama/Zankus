#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
usage: python3 check_progress.py <progress.md 路径>
功能: 校验 oxhorse-polisher 打磨进度文件 progress.md 结构
  - 含任务信息（任务/任务类型）
  - 至少 1 轮记录（第N轮）
  - 每轮含执行内容 + 自查结果 + 进度判定/决策
退出码: 0=通过 / 1=校验失败（可机器化验收用）
"""
import re
import sys
import os


def main() -> int:
    if len(sys.argv) < 2:
        print("❌ 用法: python3 check_progress.py <progress.md 路径>")
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"❌ progress.md 不存在: {path}")
        return 1
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    errors = []
    warns = []

    if not re.search(r"任务[:：]", text):
        warns.append("缺任务信息（任务: …）")

    rounds = re.findall(r"^#{1,4}\s*第\s*(\d+)\s*轮", text, re.M)
    if not rounds:
        errors.append("无轮次记录（应有「第N轮」标题）")
    else:
        nums = [int(r) for r in rounds]
        if nums != sorted(nums) or len(set(nums)) != len(nums):
            errors.append(f"轮次不连续/重复: {nums}")
        if not re.search(r"执行内容|执行了|做了什么", text):
            warns.append("缺执行内容记录")
        if not re.search(r"自查|找茬|审查|反馈", text):
            warns.append("缺自查/找茬结果记录")
        if not re.search(r"决策|判定|达标|继续|终止", text):
            warns.append("缺进度判定/决策记录")

    if errors:
        for e in errors:
            print(f"❌ {e}")
        print("校验失败: 退出码 1")
        return 1
    for w in warns:
        print(f"⚠️ {w}")
    print(f"✅ progress.md 结构校验通过（{len(rounds)} 轮记录，轮次连续）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
