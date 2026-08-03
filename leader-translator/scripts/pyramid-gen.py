#!/usr/bin/env python3
# pyramid-gen.py — 参数化金字塔结构图生成器（路径预览用）
# 用法:
#   pyramid-gen.py --apex "这活为什么干" \
#       --pillars "搭收集表单,汇总展示页,验收" \
#       --base "写书规则,防五种死法" \
#       --out preview.svg
#   pyramid-gen.py --apex "一句话结论" --pillars "A,B,C"   # 输出到 stdout
#
# 设计原则（用户 2026-08-03 拍板）：
#   - 参数化不写死：柱子 1-7 根自适应高度/宽度，任何任务书结构都能表达
#   - 颜色语义固定：塔尖红 / 塔身橙 / 塔底规则黄·护栏绿——这是「语言」不是「模板」
#   - AI 可手画定制：本脚本是快捷默认，特殊情况仍可自由画
# 零依赖（仅标准库）。

import sys
import argparse
import html

W, H = 680, 0
MARGIN = 16

COLORS = {
    "apex": "#b91c1c",     # 塔尖红
    "pillar": "#c2410c",   # 塔身橙
    "rule": "#a16207",     # 规则黄
    "guard": "#4d7c0f",    # 护栏绿
    "script": "#0e7490",   # 脚本青
    "bg": "#f8fafc",
    "text": "#0f172a",
    "sub": "#334155",
}


def esc(s):
    return html.escape(s, quote=True)


def build(apex, pillars, base, guard=None):
    """返回完整 SVG 字符串。pillars/base/guard 为字符串列表。guard 为空则不渲染护栏行。"""
    guard = guard or []
    if not pillars:
        pillars = ["（空塔身）"]
    n = len(pillars)
    col_w = (W - 2 * MARGIN) / n

    y = 18
    h1 = 34   # 塔尖高
    h2 = 52   # 塔身柱高
    h3 = 26   # 塔底规则/护栏行高

    out = []
    out.append(f'<svg viewBox="0 0 {W} {y + h1 + h2 + 2*h3 + 46}" '
               f'xmlns="http://www.w3.org/2000/svg" '
               f'font-family="ui-sans-serif, -apple-system, sans-serif">')
    out.append(f'<rect width="{W}" height="{y + h1 + h2 + 2*h3 + 46}" fill="{COLORS["bg"]}"/>')

    # 塔尖
    apex_x = (W - min(W * 0.62, 420)) / 2
    apex_w = min(W * 0.62, 420)
    out.append(f'<rect x="{apex_x:.0f}" y="{y}" width="{apex_w:.0f}" height="{h1}" rx="3" fill="{COLORS["apex"]}"/>')
    out.append(f'<text x="{W/2:.0f}" y="{y + 22}" fill="#fff" font-size="13" font-weight="700" '
               f'text-anchor="middle">{esc(apex)}</text>')

    # 塔身（支柱）
    y2 = y + h1 + 10
    for i, p in enumerate(pillars):
        x = MARGIN + i * col_w
        w = col_w - 6
        out.append(f'<rect x="{x:.0f}" y="{y2}" width="{w:.0f}" height="{h2}" rx="3" fill="{COLORS["pillar"]}"/>')
        # 柱子文字：太长分行（每行 ≤5 字）
        txt = p
        lines = [txt[j:j + 5] for j in range(0, len(txt), 5)][:2]
        ty = y2 + 22
        for ln in lines:
            out.append(f'<text x="{x + w/2:.0f}" y="{ty}" fill="#fff" font-size="11" font-weight="600" '
                       f'text-anchor="middle">{esc(ln)}</text>')
            ty += 16

    # 塔底：规则行（黄 #a16207）+ 护栏行（绿 #4d7c0f）——两行分开，绿护栏不再死代码
    y3 = y2 + h2 + 10
    rows = []
    if base:
        rows.append(base)
    else:
        rows.append(["写书规则", "防五种死法"])
    if guard:
        rows.append(guard)   # 护栏行（绿色），有 --guard 才渲染
    for r_i, row in enumerate(rows):
        seg_w = (W - 2 * MARGIN) / len(row)
        color = COLORS["rule"] if r_i == 0 else COLORS["guard"]
        for j, seg in enumerate(row):
            x = MARGIN + j * seg_w
            w = seg_w - 6
            out.append(f'<rect x="{x:.0f}" y="{y3 + r_i * (h3 + 4)}" width="{w:.0f}" '
                       f'height="{h3}" rx="3" fill="{color}"/>')
            out.append(f'<text x="{x + w/2:.0f}" y="{y3 + r_i * (h3 + 4) + 17}" fill="#fff" '
                       f'font-size="10" font-weight="600" text-anchor="middle">{esc(seg)}</text>')

    out.append('</svg>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="金字塔结构图生成器（路径预览）")
    ap.add_argument("--apex", required=True, help="塔尖：这活为什么干（一句话结论）")
    ap.add_argument("--pillars", required=True, help="塔身支柱，逗号分隔（如: 搭表单,汇总页,验收）")
    ap.add_argument("--base", default="", help="塔底规则行（黄色），逗号分隔（如: 写书规则,防五种死法）")
    ap.add_argument("--guard", default="", help="护栏行（绿色），逗号分隔（如: 防五种死法）——有才渲染")
    ap.add_argument("--out", default="", help="输出文件路径；缺省打印到 stdout")
    args = ap.parse_args()

    pillars = [p.strip() for p in args.pillars.split(",") if p.strip()]
    base = [p.strip() for p in args.base.split(",") if p.strip()] if args.base else []
    guard = [p.strip() for p in args.guard.split(",") if p.strip()] if args.guard else []

    svg = build(args.apex, pillars, base, guard)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"✅ 已生成: {args.out}（{len(pillars)} 根支柱）")
    else:
        print(svg)


if __name__ == "__main__":
    main()
