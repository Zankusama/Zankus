#!/usr/bin/env python3
"""
run_goldens.py — 评估器 golden 回归测试集（防「评估器越改越瞎」「盲区无人知」）

遍历 tests/golden/*/SKILL.md，用评估器跑每个样本，断言指定检查项的
passed 与期望一致。升级评估器必须全过——任一 FAIL 不许发版（死规矩 1 强化）。

用法: python3 scripts/run_goldens.py
退出码: 0 = 全过 | 1 = 有 FAIL
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_eval

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "golden")

# 每个样本的期望判定：{(principle, item): 期望 passed}
# v1.2.0-D（2026-08-03 元层信任）：g14-g46 新增 33 样本，10 原理全覆盖（每原理 ≥3，正例/反例）
# 所有 EXPECT 均先跑评估器验证实际判定后写入（死规矩：先验证后写期望）
EXPECT = {
    "g01_scriptized_ok":    {("p1_determinism", "scriptized"): True},
    "g02_scriptized_fake":  {("p1_determinism", "scriptized"): False},
    "g03_steps_arabic":     {("p4_progressive", "step_flow"): True, ("p10_five_elements", "steps"): True},
    "g04_steps_phase":      {("p4_progressive", "step_flow"): True},
    "g05_steps_step":       {("p4_progressive", "step_flow"): True},
    "g06_steps_none":       {("p4_progressive", "step_flow"): False},
    "g07_trigger_folded":   {("p10_five_elements", "trigger"): True},
    "g08_trigger_none":     {("p10_five_elements", "trigger"): False},
    "g09_repeat_table":     {("p9_failure_modes", "repeat_pattern"): True},
    "g10_repeat_cmd":       {("p9_failure_modes", "repeat_pattern"): False},
    "g11_placeholder_ban":  {("p9_failure_modes", "fuzzy_placeholder"): True},
    "g12_placeholder_real": {("p9_failure_modes", "fuzzy_placeholder"): False},
    "g13_emoji_template":  {("p9_failure_modes", "repeat_pattern"): True},
    # ── p2 锚定（新增 3 样本）──
    "g14_anchor_repeat_ok":    {("p2_anchoring", "key_constraint_repeated"): True},
    "g15_anchor_repeat_fail":  {("p2_anchoring", "key_constraint_repeated"): False},
    "g16_anchor_repeat_multi": {("p2_anchoring", "key_constraint_repeated"): True},
    # ── p3 反幻觉（新增 6 样本）──
    "g17_source_ok":           {("p3_anti_hallucination", "source_required"): True},
    "g18_source_fail":         {("p3_anti_hallucination", "source_required"): False},
    "g19_unverified_ok":       {("p3_anti_hallucination", "unverified_marked"): True},
    "g20_unverified_fail":     {("p3_anti_hallucination", "unverified_marked"): False},
    "g21_alternatives_ok":     {("p3_anti_hallucination", "alternatives_considered"): True},
    "g22_alternatives_fail":   {("p3_anti_hallucination", "alternatives_considered"): False},
    # ── p5 权重（新增 6 样本）──
    "g23_grading_ok":          {("p5_weighting", "rule_grading"): True},
    "g24_grading_fail":        {("p5_weighting", "rule_grading"): False},
    "g25_binary_ok":           {("p5_weighting", "no_binary_residual"): True},
    "g26_binary_fail":         {("p5_weighting", "no_binary_residual"): False},
    "g27_arbitration_ok":      {("p5_weighting", "conflict_arbitration"): True},
    "g28_arbitration_fail":    {("p5_weighting", "conflict_arbitration"): False},
    # ── p6 物化（新增 3 样本）──
    "g29_progress_ok":         {("p6_materialization", "progress_mechanism"): True},
    "g30_progress_fail":       {("p6_materialization", "progress_mechanism"): False},
    "g31_progress_multi":      {("p6_materialization", "progress_mechanism"): True},
    # ── p7 外置（新增 3 样本）──
    "g32_extrusion_ok":        {("p7_extrusion", "references_extruded"): True},
    "g33_extrusion_fail":      {("p7_extrusion", "references_extruded"): False},
    "g34_extrusion_multi":     {("p7_extrusion", "references_extruded"): True},
    # ── p8 塔尖（新增 4 样本）──
    "g35_desc_ok":             {("p8_apex", "desc_consistent"): True},
    "g36_desc_fail":           {("p8_apex", "desc_consistent"): False},
    "g37_boundary_ok":         {("p8_apex", "trigger_boundary"): True},
    "g38_boundary_fail":       {("p8_apex", "trigger_boundary"): False},
    # ── p1 确定性补多样本（新增 2）──
    "g39_judge_ok":            {("p1_determinism", "judgeable_acceptance"): True},
    "g40_judge_fail":          {("p1_determinism", "judgeable_acceptance"): False},
    # ── p4 分步补多样本（新增 2）──
    "g41_accept_ok":           {("p4_progressive", "step_acceptance"): True},
    "g42_accept_fail":         {("p4_progressive", "step_acceptance"): False},
    # ── p10 五要素补多样本（新增 2）──
    "g43_output_ok":           {("p10_five_elements", "output_format"): True},
    "g44_output_fail":         {("p10_five_elements", "output_format"): False},
    # ── p9 失败模式补多样本（新增 2）──
    "g45_fence_ok":            {("p9_failure_modes", "fence_escape"): True},
    "g46_fence_fail":          {("p9_failure_modes", "fence_escape"): False},
}


def main():
    fails = 0
    total = 0
    for name in sorted(EXPECT):
        sk = os.path.join(GOLDEN_DIR, name, "SKILL.md")
        if not os.path.isfile(sk):
            print(f"❌ {name}: 样本缺失 {sk}")
            fails += 1
            continue
        result = skill_eval.evaluate_skill(name, sk)
        for (pn, itn), exp in EXPECT[name].items():
            total += 1
            try:
                got = bool(result["principles"][pn][itn]["passed"])
            except KeyError:
                print(f"❌ {name}.{pn}.{itn}: 判定不存在（评估器没这项？）")
                fails += 1
                continue
            mark = "✅" if got == exp else "❌"
            if got != exp:
                fails += 1
            print(f"{mark} {name}.{pn}.{itn}: 期望={exp} 实际={got}")
    print(f"\n结果: {total} 项断言，{fails} 处 FAIL —— {'✅ 全过，可发版' if fails == 0 else '❌ 不许发版'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
