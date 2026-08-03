#!/usr/bin/env python3
"""
run_runtime_tests.py — 评估器运行时测试（触发测试集 + 跳步骤探测 + 路径审查）

模块 B（评估器深化）：让评估从「读文档」进到「跑起来验证」（静态近似）。

⚠️ 边界声明：本脚本是**静态近似**——只读 SKILL.md 文本做可机器判的判定，
   不真触发模型。真正的动态触发/跳步实测走康复流程 R1-R4（人工），本脚本
   是 R1-R4 的前置筛网：把「description 覆盖了触发词吗、强制步骤声明了吗、
   路径健康项齐了吗」这类可机器判的项先自动化。

用法:
  python3 scripts/run_runtime_tests.py <skill名> [--base <技能目录>]

测试用例目录: tests/runtime/<skill名>/
  trigger-positive.md   该 skill 应该触发的问法（≥5 条）
  trigger-negative.md   该 skill 不该触发的问法（≥3 条，description 应显式排除）
  steps-probe.md        跳步骤探测，标注该 skill 的强制步骤名

退出码: 0 = 全过 | 1 = 有 FAIL
"""
import os
import re
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_eval

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(SCRIPT_DIR, "..", "tests", "runtime")
# 默认 base：脚本(scripts/)向上两级 = skill 集合根目录（脚本可整包挪动，不预埋绝对路径）
DEFAULT_BASE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))


def resolve_skill_dir(skill_name, base):
    """定位目标 skill 目录：--base 优先，否则默认 脚本/../技能配置/<skill>"""
    if base:
        d = os.path.join(base, skill_name)
    else:
        d = os.path.join(DEFAULT_BASE, skill_name)
    if not os.path.isdir(d):
        raise SystemExit(f"❌ skill 目录不存在: {d}")
    return d


def read_questions(path):
    """读用例文件，提取有效问法行（跳过注释/空行/标题）"""
    if not os.path.isfile(path):
        return []
    lines = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith(("#", ">")):
            continue
        # 去掉编号前缀（1. 2. 3. ... 或 - 或 * ）
        ln = re.sub(r"^(\d+\.|\d+、|[-*])\s*", "", ln)
        ln = ln.strip()
        if ln and not ln.startswith("##"):
            lines.append(ln)
    return lines


def main():
    ap = argparse.ArgumentParser(description="评估器运行时测试（静态近似）")
    ap.add_argument("skill", help="目标 skill 名（如 second-brain）")
    ap.add_argument("--base", default=None, help="技能根目录（默认脚本/../技能配置）")
    args = ap.parse_args()

    skill_dir = resolve_skill_dir(args.skill, args.base)
    sk_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(sk_path):
        raise SystemExit(f"❌ 无 SKILL.md: {sk_path}")

    content = open(sk_path, encoding="utf-8").read()
    fm = skill_eval.parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    fails = 0
    total = 0

    def check(passed, label, detail):
        nonlocal fails, total
        total += 1
        mark = "PASS" if passed else "FAIL"
        if not passed:
            fails += 1
        print(f"[{mark}] {label}: {detail}")

    print(f"═══ 运行时测试（静态近似）· {args.skill} ═══")
    print(f"⚠️ 静态近似：基于 description 文本 + 用例关键词比对，不真触发模型；动态触发走 R1-R4 人工\n")

    # ── ① 触发测试（description 关键词 vs 正/负用例）──
    print("── 触发测试 ──")
    rt = os.path.join(RUNTIME_DIR, args.skill)
    pos = read_questions(os.path.join(rt, "trigger-positive.md"))
    neg = read_questions(os.path.join(rt, "trigger-negative.md"))

    # 从 description 提取触发词集合（触发词段 + NOT for 段）
    desc_full = desc + body[:1500]
    pos_hits = 0
    for q in pos:
        hit = any(k in desc for k in q.split()) if len(q) <= 8 else (q[:6] in desc or q in desc)
        # 简化：问法含 2-4 字关键词，description 命中任一关键词 = 可触发
        kws = [q] if len(q) <= 8 else [q[:6], q[-6:]]
        hit = any(k in desc for k in kws)
        if hit:
            pos_hits += 1
        check(hit, f"正例触发「{q[:20]}」", "description 含触发词 → 可触发" if hit else "description 未命中该问法")
    if pos:
        print(f"  （正例 {pos_hits}/{len(pos)} 条 description 可触发；触发判定仅基于 description 文本，不真触发模型）\n")

    not_for_hits = 0
    for q in neg:
        # 负例：description 的 NOT for 段应显式排除该场景
        nf = re.search(r"NOT for[^\n。]*", desc)
        nf_text = nf.group(0) if nf else ""
        # 问法可能带括号类别（如「帮我读书（NOT for 读书）」）——优先取括号内类别词比对
        m = re.search(r"[（(]([^）)]+)[）)]", q)
        keys = []
        if m:
            keys = [k for k in re.split(r"[,，/、]", m.group(1)) if len(k) >= 2]
        if not keys:
            # 无括号类别：取问法中与 NOT for 类别词同义的子串
            keys = [k for k in ["读书", "聊天", "代码", "文件", "图", "聊天", "编辑", "操作"] if k in q]
        kw_in_nf = any(k in nf_text for k in keys)
        if kw_in_nf:
            not_for_hits += 1
        check(kw_in_nf, f"负例排除「{q[:20]}」", "description NOT for 显式排除 → 不触发" if kw_in_nf else "description 未显式排除该场景")

    # ── ② 跳步骤探测（steps-probe.md 强制步骤名是否声明）──
    print("── 跳步骤探测 ──")
    probe = os.path.join(rt, "steps-probe.md")
    if os.path.isfile(probe):
        probe_text = open(probe, encoding="utf-8").read()
        # 只取「## 强制步骤名」节（首个二级标题到下一个二级标题之间），排除「跳步拦截语义」人工复核节
        section = re.search(r"## 强制步骤名[^\n]*\n(.*?)(?=\n## |\Z)", probe_text, re.DOTALL)
        forced = []
        if section:
            for ln in section.group(1).split("\n"):
                ln = ln.strip().lstrip("-* ").strip()
                if not ln or ln.startswith("#"):
                    continue
                # 去掉括号注释，只留步骤名本体（如「Ingest Step 0（读 SCHEMA）」→「Ingest Step 0」）
                ln = re.split(r"[（(]", ln)[0].strip()
                if ln:
                    forced.append(ln)
        if forced:
            for fs in forced:
                present = fs in content
                check(present, f"强制步骤声明「{fs}」", "SKILL.md 含该步骤名 → 跳步可被定位" if present else "SKILL.md 未声明该步骤名")
        else:
            print("  （steps-probe.md 未标注强制步骤名，跳过）\n")

    # ── ③ 路径审查 3 项（aiaci path quality 思路，静态近似）──
    print("── 路径审查 3 项 ──")
    # 3a 步骤序列：最长连续编号 ≥3
    steps_n = skill_eval.find_longest_step_seq(content)
    check(steps_n >= 3, "路径·步骤序列", f"最长连续步骤 {steps_n} 处（≥3）")
    # 3b 工具声明：allowed-tools 存在
    tools = re.search(r"allowed-tools:\s*\[([^\]]+)\]", content)
    check(bool(tools), "路径·工具声明", f"allowed-tools: {tools.group(1).strip()[:50]}" if tools else "无 allowed-tools 声明")
    # 3c 回退/降级：回退、降级、熔断、兜底、备选 关键词 ≥1
    fallback_kws = ["回退", "降级", "熔断", "兜底", "备选", "退化"]
    fb_cnt = sum(content.count(k) for k in fallback_kws)
    check(fb_cnt >= 1, "路径·回退/降级", f"回退类关键词 {fb_cnt} 处（≥1，跳步/失败有降级路径）")

    print(f"\n结果: {total} 项检查，{fails} 处 FAIL —— {'✅ 全过' if fails == 0 else '❌ 有 FAIL'}")
    print("⚠️ 以上均为静态近似（description/结构文本判定），动态触发/跳步实测走 R1-R4 人工。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
