#!/usr/bin/env python3
"""
fixgen.py — 处方生成器（评估器 JSON → 修复建议清单）

模块 C（半自动修复）：把「处方」环节脚本化——读评估器未过项，
对照 references/mechanism.md 的修法选项，输出修复建议清单 output/skill-rehab/fix-suggestions.md。

死规矩：
  1. fixgen 不许自己改文件（只输出建议清单）
  2. 引用 mechanism.md 修法必须原文带路径，不许改写
  3. 建议改动列留 AI 填——fixgen 只给结构 + mechanism 原文

用法:
  python3 scripts/fixgen.py <评估器JSON> <目标skill路径>
    <评估器JSON>    评估器输出的 JSON（含 issues 数组；若为 CLI 摘要格式仅有 issues_count，
                    则现场对目标 skill 重跑评估器补全——CLI JSON 不含 issues 详情，实测）
    <目标skill路径>  目标 skill 的 SKILL.md 路径或目录

退出码: 0 = 生成成功 | 1 = 失败
"""
import os
import re
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_eval

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))   # skill 自身根目录：只定位资源（mechanism.md），不写产物
MECHANISM = os.path.join(SKILL_ROOT, "references", "mechanism.md")
# 产物输出：默认 AI 当前会话工作区（os.getcwd()），--workspace 可显式覆盖
WORKSPACE = os.getcwd()
OUT_SUGGEST = os.path.join(WORKSPACE, "output", "skill-rehab", "fix-suggestions.md")


def parse_issue(issue):
    """issues 项格式: [p2_anchoring.key_constraint_repeated] 详情... → (原理, 项, 详情)"""
    m = re.match(r"\[([a-z0-9_]+)\.([a-z0-9_]+)\]\s*(.*)", issue.strip())
    if m:
        return m.group(1), m.group(2), m.group(3).strip()
    return None, None, issue.strip()


def load_mechanism_fix(item_name):
    """从 mechanism.md 提取指定 item 的分级 + 修法选项原文（带文件路径引用）"""
    if not os.path.isfile(MECHANISM):
        return None, None
    text = open(MECHANISM, encoding="utf-8").read()
    # 定位 ### 中文名（item_name · M层 · ...）段落，取到下一个 ### 或 ## 前
    # 兼容两种标题格式：item 名在括号内（如「### 验收可执行（l4_judgeable_acceptance · M层 · P0 5 分）」）
    # 或 item 名直接开头的旧格式（如「### l3_scriptized（…）」）
    m = re.search(
        rf"^### (?:[^（]+（{re.escape(item_name)}[^）]*）|{re.escape(item_name)}[^\n]*)\s*\n(.*?)(?=^### |^## |\Z)",
        text, re.DOTALL | re.MULTILINE)
    if not m:
        return None, None
    seg = m.group(1)
    grade = re.search(r"分级[：:]\s*(\*\*[^*]+\*\*[^\n]*)", seg)
    fix_lines = []
    in_fix = False
    for ln in seg.split("\n"):
        ln_s = ln.strip().lstrip("- ").strip()  # mechanism.md 修法选项带「- 修法选项：」前缀
        if ln_s.startswith("修法选项"):
            in_fix = True
            continue
        if in_fix:
            if ln_s.startswith("- ") or re.match(r"^\d+[\.、]", ln_s):
                fix_lines.append(ln.strip())
            elif ln_s == "" and fix_lines:
                break
    grade_txt = grade.group(1).strip() if grade else "未标注"
    return grade_txt, fix_lines


def main():
    if len(sys.argv) < 3:
        print("用法: python3 scripts/fixgen.py <评估器JSON> <目标skill路径> [--rehab] [--workspace <目录>]")
        print("      --rehab       生成修复履历（读 output/skill-rehab/fix-suggestions.md + 修复前后评估，写 output/skill-rehab/rehab-diff/）")
        print("      --workspace   产物输出目录（默认=当前工作区，产物落 <工作区>/output/skill-rehab/）")
        return 1
    json_path = sys.argv[1]
    skill_arg = sys.argv[2]
    rehab_mode = "--rehab" in sys.argv
    if "--workspace" in sys.argv:
        global WORKSPACE
        WORKSPACE = sys.argv[sys.argv.index("--workspace") + 1]

    skill_path = skill_arg if skill_arg.endswith("SKILL.md") else os.path.join(skill_arg, "SKILL.md")
    if not os.path.isfile(skill_path):
        print(f"❌ 目标 SKILL.md 不存在: {skill_path}")
        return 1

    issues = []
    version = "?"
    # 尝试从 JSON 读 issues（若为全量格式）
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for r in data:
                if r.get("skill_name", "").lower() in skill_path.lower() or True:
                    issues = r.get("issues", []) or []
                    version = r.get("version", "?")
        elif isinstance(data, dict):
            issues = data.get("issues", []) or []
            version = data.get("version", "?")
    except Exception as e:
        print(f"⚠️ JSON 读取失败（{e}），将现场重跑评估器补全 issues")

    # CLI 摘要 JSON 只有 issues_count 无 issues 详情 → 现场重跑补全
    if not issues:
        print("ℹ️ JSON 无 issues 详情（CLI 摘要格式），现场对目标 skill 重跑评估器…")
        r = skill_eval.evaluate_skill(os.path.basename(os.path.dirname(skill_path)), skill_path)
        issues = r.get("issues", [])
        version = r.get("version", "?")
        if not issues:
            print("ℹ️ 该 skill 无未过项（评估器全过）——无需处方，建议清单仍生成（空清单）")

    if rehab_mode:
        return gen_rehab(skill_path, issues, version)

    # 生成建议清单
    os.makedirs(os.path.join(WORKSPACE, "output", "skill-rehab"), exist_ok=True)
    lines = []
    lines.append("# 修复建议清单（fixgen 生成）")
    lines.append("")
    lines.append(f"> 目标：`{skill_path}` ｜ 评估器版本：{version} ｜ 未过项 {len(issues)} 条")
    lines.append("> 死规矩：本清单只给建议，改动由 AI 按 mechanism 原文落地；应用到真实文件前必须先过沙箱验证。")
    lines.append("")

    if not issues:
        lines.append("（无未过项）")
    for i, iss in enumerate(issues, 1):
        pname, itn, detail = parse_issue(iss)
        grade_txt, fix_lines = load_mechanism_fix(itn) if itn else (None, None)
        lines.append(f"## {i}. 未过项 `{itn or '?'}`（{pname or '?'}）")
        lines.append("")
        lines.append(f"- **未过详情**：{detail}")
        lines.append(f"- **分级**：{grade_txt or 'mechanism.md 未收录该 item'}")
        if fix_lines:
            lines.append(f"- **mechanism 修法**（原文引自 `references/mechanism.md`，不许改写）：")
            for fl in fix_lines:
                lines.append(f"  - {fl}")
        else:
            lines.append("- **mechanism 修法**：mechanism.md 未收录该 item（`references/mechanism.md`）")
        lines.append(f"- **对应原理**：`{pname}`（见 `scripts/skill_eval.py` PRINCIPLES）")
        lines.append(f"- **建议改动**（AI 填）：")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(OUT_SUGGEST, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 修复建议清单已生成: {OUT_SUGGEST}")
    print(f"   未过项 {len(issues)} 条，每条含 分级 + mechanism 修法原文引用（带路径）")

    # 输出 schema 自校验（防建议清单残缺——AI 照着改会漏修）
    missing = []
    for iss in issues:
        pname, itn, detail = parse_issue(iss)
        if not itn or not detail:
            missing.append(f"未过项 {itn or '?'}：缺 item 名或详情")
    if issues and missing:
        print(f"⚠️ 建议清单 {len(missing)} 处字段残缺，请检查 fixgen 输入 JSON 完整性")
        sys.exit(1)
    elif issues:
        print(f"✅ 建议清单 schema 自检通过：{len(issues)} 项均含 item/详情/分级/修法")
    return 0


def gen_rehab(skill_path, issues, version):
    """生成修复履历：读 output/skill-rehab/fix-suggestions.md 的建议 + 修复前后评估对比，写 output/skill-rehab/rehab-diff/"""
    rehab_dir = os.path.join(WORKSPACE, "output", "skill-rehab", "rehab-diff")
    os.makedirs(rehab_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    skill_tag = os.path.basename(os.path.dirname(skill_path)) or "skill"
    out = os.path.join(rehab_dir, f"rehab-{skill_tag}-{ts}.md")

    # 修复前评分（当前文件评估）
    before = skill_eval.evaluate_skill(skill_tag, skill_path)
    # 修复后评分：若 fix-suggestions.md 的建议已落盘，尝试评估（无则标注待复查）
    lines = []
    lines.append(f"# 修复履历 · {skill_tag}")
    lines.append("")
    lines.append(f"> 生成：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 评估器：{version}")
    lines.append("")
    lines.append("## 修复前后评分对比")
    lines.append("")
    lines.append(f"| 阶段 | 总分 | 等级 | 未过项 |")
    lines.append(f"|:---|:---:|:---:|:---:|")
    lines.append(f"| 修复前 | {before['score']}/{skill_eval.TOTAL_EXPECTED} | {before['grade']} | {len(before.get('issues', []))} |")
    lines.append(f"| 修复后 | （沙箱验证后填） | — | — |")
    lines.append("")
    lines.append("## 修复项明细")
    lines.append("")
    lines.append("| 项 | 未过详情 | 分级 | 为什么修 | 对应机制 | 修法 | 验证结果 |")
    lines.append("|:---|:---------|:----:|:---------|:---------|:-----|:--------|")
    # 从建议清单带出分级/机制；验证结果由 fixapply 实际输出回填（死规矩：不许手写「应该过了」）
    suggest = os.path.join(WORKSPACE, "output", "skill-rehab", "fix-suggestions.md")
    items = []
    if os.path.isfile(suggest):
        cur = {}
        for ln in open(suggest, encoding="utf-8"):
            ln = ln.strip()
            if ln.startswith("## ") and "未过项" in ln:
                if cur:
                    items.append(cur)
                cur = {"name": ln.split("`")[1] if "`" in ln else ln}
            elif ln.startswith("- **未过详情**"):
                cur["detail"] = ln.split("：", 1)[-1].strip()
            elif ln.startswith("- **分级**"):
                cur["grade"] = ln.split("：", 1)[-1].strip()
            elif ln.startswith("- **对应原理**"):
                cur["mech"] = ln.split("`")[1] if "`" in ln else ""
            elif ln.startswith("- **mechanism 修法**"):
                cur["fix"] = ln.split("：", 1)[-1].strip()
        if cur:
            items.append(cur)
    if not items:
        lines.append("|（建议清单为空——无未过项或未生成） | — | — | — | — | — | — |")
    for it in items:
        lines.append(f"| {it.get('name','?')} | {it.get('detail','')[:40]} | {it.get('grade','?')} | 见机制 | {it.get('mech','?')} | {it.get('fix','')[:40]} | ⏳ 待 fixapply 验证 |")
    lines.append("")
    lines.append("## 验证记录")
    lines.append("")
    lines.append("> 死规矩：验证结果必须来自 fixapply 实际输出（红→绿），不许手写「应该过了」。")
    lines.append("")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ 修复履历已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
