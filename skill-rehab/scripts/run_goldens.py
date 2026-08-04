#!/usr/bin/env python3
"""
run_goldens.py — 评估器 golden 回归测试集（防「评估器越改越瞎」「盲区无人知」）

遍历 tests/golden/*/SKILL.md，用评估器跑每个样本，断言指定检查项的（v4.0.0 键映射 l*）
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
    "g01_scriptized_ok":    {("l3_skeleton", "l3_scriptized"): True},
    "g02_scriptized_fake":  {("l3_skeleton", "l3_scriptized"): False},
    "g03_steps_arabic":     {("l3_skeleton", "l3_step_flow"): True, ("l3_skeleton", "l3_step_flow"): True},
    "g04_steps_phase":      {("l3_skeleton", "l3_step_flow"): True},
    "g05_steps_step":       {("l3_skeleton", "l3_step_flow"): True},
    "g06_steps_none":       {("l3_skeleton", "l3_step_flow"): False},
    "g07_trigger_folded":   {("l2_triggering", "l2_trigger_phrases"): True},
    "g08_trigger_none":     {("l2_triggering", "l2_trigger_phrases"): False},
    "g09_repeat_table":     {("l4_quality", "l4_instruction_consistency"): False},  # v4: 无仲裁词=不过
    "g10_repeat_cmd":       {("l4_quality", "l4_instruction_consistency"): False},
    "g11_placeholder_ban":  {("l4_quality", "l4_placeholder_leakage"): True},
    "g12_placeholder_real": {("l4_quality", "l4_placeholder_leakage"): False},
    "g13_emoji_template":  {("l4_quality", "l4_instruction_consistency"): False},  # v4: 无仲裁词=不过
    # ── p2 锚定（新增 3 样本）──
    "g14_anchor_repeat_ok":    {("l4_quality", "l4_anchoring"): True},
    "g15_anchor_repeat_fail":  {("l4_quality", "l4_anchoring"): False},
    "g16_anchor_repeat_multi": {("l4_quality", "l4_anchoring"): True},
    # ── p3 反幻觉（新增 6 样本）──
    "g17_source_ok":           {("l4_quality", "l4_source_grounding"): True},
    "g18_source_fail":         {("l4_quality", "l4_source_grounding"): False},
    "g19_unverified_ok":       {("l4_quality", "l4_unverified_marking"): True},
    "g20_unverified_fail":     {("l4_quality", "l4_unverified_marking"): False},
    "g21_alternatives_ok":     {("l4_quality", "l4_alternatives"): True},
    "g22_alternatives_fail":   {("l4_quality", "l4_alternatives"): False},
    # ── p5 权重（新增 6 样本）──
    "g23_grading_ok":          {("l4_quality", "l4_instruction_consistency"): False},  # v4: 无仲裁词=不过
    "g24_grading_fail":        {("l4_quality", "l4_instruction_consistency"): False},
    "g25_binary_ok":           {("l4_quality", "l4_instruction_consistency"): False},  # v4: 无仲裁词=不过
    "g26_binary_fail":         {("l4_quality", "l4_instruction_consistency"): False},
    "g27_arbitration_ok":      {("l4_quality", "l4_instruction_consistency"): True},
    "g28_arbitration_fail":    {("l4_quality", "l4_instruction_consistency"): False},
    # ── p6 物化（新增 3 样本）──
    "g29_progress_ok":         {("l4_quality", "l4_state_materialization"): True},
    "g30_progress_fail":       {("l4_quality", "l4_state_materialization"): False},
    "g31_progress_multi":      {("l4_quality", "l4_state_materialization"): True},
    # ── p7 外置（新增 3 样本）──
    "g32_extrusion_ok":        {("l3_skeleton", "l3_progressive_disclosure"): True},
    "g33_extrusion_fail":      {("l3_skeleton", "l3_progressive_disclosure"): False},
    "g34_extrusion_multi":     {("l3_skeleton", "l3_progressive_disclosure"): True},
    # ── p8 塔尖（新增 4 样本）──
    "g35_desc_ok":             {("l1_positioning", "l1_desc_consistency"): True},
    "g36_desc_fail":           {("l1_positioning", "l1_desc_consistency"): False},
    "g37_boundary_ok":         {("l2_triggering", "l2_negative_trigger"): True},
    "g38_boundary_fail":       {("l2_triggering", "l2_negative_trigger"): False},
    # ── p1 确定性补多样本（新增 2）──
    "g39_judge_ok":            {("l4_quality", "l4_judgeable_acceptance"): True},
    "g40_judge_fail":          {("l4_quality", "l4_judgeable_acceptance"): False},
    # ── p4 分步补多样本（新增 2）──
    "g41_accept_ok":           {("l4_quality", "l4_judgeable_acceptance"): True},
    "g42_accept_fail":         {("l4_quality", "l4_judgeable_acceptance"): False},
    # ── p10 五要素补多样本（新增 2）──
    "g43_output_ok":           {("l3_skeleton", "l3_output_format"): True},
    "g44_output_fail":         {("l3_skeleton", "l3_output_format"): False},
    # ── p9 失败模式补多样本（新增 2）──
    "g45_fence_ok":            {("l4_quality", "l4_output_executability"): True},
    "g46_fence_fail":          {("l4_quality", "l4_output_executability"): False},
    # ── v4.0.0 新检查项样本（g47-g54，7 层新检查项正/反例）──
    "g47_allowed_ok":          {("l5_safety", "l5_allowed_tools"): True},
    "g48_allowed_fail":        {("l5_safety", "l5_allowed_tools"): False},
    "g49_danger_ok":           {("l5_safety", "l5_dangerous_op_guard"): True},
    "g50_danger_fail":         {("l5_safety", "l5_dangerous_op_guard"): False},
    "g51_imperative_ok":       {("l4_quality", "l4_imperative_style"): True},
    "g52_imperative_fail":     {("l4_quality", "l4_imperative_style"): False},
    "g53_platform_ok":         {("l2_triggering", "l2_cross_platform"): True},
    "g54_platform_fail":       {("l2_triggering", "l2_cross_platform"): False},
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
                got = bool(result["layers"][pn][itn]["passed"])
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
