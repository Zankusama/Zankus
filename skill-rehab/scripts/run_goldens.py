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
