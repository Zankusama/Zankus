#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kano-classify.py — KANO 需求分类器（Kano et al., 1984 评估表）

输入需求 + 正反题答案（五档：喜欢/理应如此/无所谓/勉强接受/不喜欢），
按经典 KANO 评估表分类：基本/期望/兴奋/无差异/反向/可疑。

正题=「如果具备该功能/属性，你的感受？」
反题=「如果不具备该功能/属性，你的感受？」

用法:
  python3 scripts/kano-classify.py --pos 喜欢 --neg 不喜欢
  python3 scripts/kano-classify.py --input answers.json    # [{name, positive, negative}, ...]
  python3 scripts/kano-classify.py --self
退出码: 0=成功, 2=输入错误
"""
import sys, json, argparse

ALIAS = {
    "喜欢": "L", "like": "L",
    "理应如此": "M", "本来就这样": "M", "must": "M", "理应": "M",
    "无所谓": "N", "neutral": "N", "都行": "N",
    "勉强接受": "W", "能忍受": "W", "live": "W",
    "不喜欢": "D", "不喜欢这样": "D", "dislike": "D",
}
# 经典 KANO 评估表：F(正题)×D(反题) → 类别
TABLE = {
    ("L", "L"): "可疑", ("L", "M"): "兴奋", ("L", "N"): "兴奋", ("L", "W"): "兴奋", ("L", "D"): "期望",
    ("M", "L"): "反向", ("M", "M"): "无差异", ("M", "N"): "无差异", ("M", "W"): "无差异", ("M", "D"): "基本",
    ("N", "L"): "反向", ("N", "M"): "无差异", ("N", "N"): "无差异", ("N", "W"): "无差异", ("N", "D"): "兴奋",
    ("W", "L"): "反向", ("W", "M"): "无差异", ("W", "N"): "无差异", ("W", "W"): "无差异", ("W", "D"): "兴奋",
    ("D", "L"): "反向", ("D", "M"): "反向", ("D", "N"): "反向", ("D", "W"): "反向", ("D", "D"): "可疑",
}


NEG_PREFIX = ("不太", "不是很", "不怎么", "不", "没")


def norm(ans):
    a = ans.strip().lower()
    if a in ALIAS:
        return ALIAS[a]
    # 否定前缀优先：先剥离否定前缀再匹配档位词，避免子串回退把「不太喜欢」吞成「喜欢」
    for pre in NEG_PREFIX:
        if a.startswith(pre):
            rest = a[len(pre):]
            for k, v in ALIAS.items():
                if rest and (k == rest or k in rest):
                    return "D"
            break
    for k, v in ALIAS.items():
        if k in a:
            return v
    return None


def classify(positive, negative):
    f, d = norm(positive), norm(negative)
    if f is None or d is None:
        return None
    return TABLE[(f, d)]


def self_test():
    cases = [("喜欢", "不喜欢", "期望"), ("喜欢", "理应如此", "兴奋"), ("理应如此", "不喜欢", "基本"),
             ("无所谓", "无所谓", "无差异"), ("理应如此", "喜欢", "反向"),
             ("不太喜欢", "理应如此", "反向"), ("不是很喜欢", "无所谓", "反向")]
    ok = all(classify(p, n) == exp for p, n, exp in cases)
    print("self: 5类各1例+否定2例 %s（期望 期望/兴奋/基本/无差异/反向/反向×2 全中）" % ("PASS✓" if ok else "FAIL✗"))
    return ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist KANO 需求分类器（经典评估表）")
    ap.add_argument("--pos", help="正题答案：喜欢/理应如此/无所谓/勉强接受/不喜欢")
    ap.add_argument("--neg", help="反题答案：同上五档")
    ap.add_argument("--input", help="JSON 文件：[{name, positive, negative}, ...]")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.input:
        try:
            items = json.load(open(a.input, encoding="utf-8"))
        except (OSError, ValueError) as e:
            print("读入失败: %s" % e)
            return 2
        if not isinstance(items, list):
            print("输入应为 JSON 数组")
            return 2
        print("| 需求 | 正题 | 反题 | 分类 |")
        print("|---|---|---|---|")
        bad = False
        for it in items:
            cls = classify(str(it.get("positive", "")), str(it.get("negative", "")))
            if cls is None:
                cls, bad = "输入非法", True
            print("| %s | %s | %s | %s |" % (it.get("name", "?"), it.get("positive", ""), it.get("negative", ""), cls))
        print("（分类依据：Kano 评估表，Kano et al., 1984）")
        return 2 if bad else 0
    if a.pos and a.neg:
        cls = classify(a.pos, a.neg)
        if cls is None:
            print("答案非法：五档为 喜欢/理应如此/无所谓/勉强接受/不喜欢")
            return 2
        print("分类：%s（正题=%s，反题=%s；依据：Kano 评估表 Kano et al., 1984）" % (cls, a.pos, a.neg))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
