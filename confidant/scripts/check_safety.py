#!/usr/bin/env python3
# check_safety.py — Confidant 安全红线自检脚本（可机器化验收）
# 用法:
#   python3 scripts/check_safety.py                              （在 skill 根目录下运行，校验本体）
#   python3 scripts/check_safety.py --output <画像文件.html>      （校验交付画像：无占位符残留 + 热线 + 免责）
# 退出码: 0 = 红线全过；1 = 有红线失守（输出 ❌ 明细）
# 校验项:
#   1. 热线号码一字不差（crisis.md 必须含 12356 / 800-810-1117 / 010-82951332）
#   2. 免责声明恰好 1 处（report_template.html 的「不是医疗诊断」=1）
#   3. 禁区词只在禁区清单出现（SKILL.md 中「诊断/治疗/痊愈/疾病」仅出现在禁区段与 NOT for）
#   4. 关键锚点存在（SKILL.md 含 双模式 / 每 4-6 轮 / 白名单 / WebSearch）
#   5. references 五文件齐全（crisis/anchors/practices/report.md/report_template.html）
#   6. （--output）交付画像：无 {{ 占位符残留 + 含三条热线 + 含免责声明
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
REF = ROOT / "references"

# 可选参数：--output <画像文件> → 额外校验交付成品
OUTPUT_FILE = None
args = sys.argv[1:]
if "--output" in args:
    i = args.index("--output")
    if i + 1 < len(args):
        OUTPUT_FILE = Path(args[i + 1])

FAILS = []

def check(name, cond, detail=""):
    if cond:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        FAILS.append(name)

print("===== Confidant 安全红线自检 =====")

# 1. 热线号码
crisis = (REF / "crisis.md").read_text(encoding="utf-8")
hotlines = ["12356", "800-810-1117", "010-82951332"]
for h in hotlines:
    check(f"热线号码 {h}", h in crisis, f"(crisis.md 缺 {h})")

# 2. 免责声明恰好 1 处（在交付模板 report_template.html 中）
tpl = (REF / "report_template.html").read_text(encoding="utf-8") if (REF / "report_template.html").exists() else ""
n_disclaimer = tpl.count("不是医疗诊断")
check("免责声明『不是医疗诊断』=1（模板）", n_disclaimer == 1, f"(实际 {n_disclaimer} 处)")

# 3. 禁区词只在禁区清单与 NOT for（元数据标注）——正文话术区（## 1-3、## 5-6）零使用
skill_text = SKILL.read_text(encoding="utf-8")
# 禁区段：## 4 禁区 之后到 ## 5 之前
zone = skill_text.split("## 4 禁区", 1)[1].split("## 5", 1)[0] if "## 4 禁区" in skill_text else ""
# 正文话术区 = 去除 frontmatter、NOT for 行、禁区段之后的全部文本
body = skill_text.split("---", 2)[2] if skill_text.count("---") >= 3 else skill_text
body = body.split("## 4 禁区", 1)[0] + (skill_text.split("## 5", 1)[1] if "## 5" in skill_text else "")
FORBIDDEN = ["诊断", "治疗", "痊愈", "疾病",
             "想太多", "矫情", "玻璃心", "这没什么大不了"]
for w in FORBIDDEN:
    in_body = body.count(w)
    check(f"禁区词『{w}』正文话术区零使用", in_body == 0, f"(正文话术区 {in_body} 处)")

# 3b. 「诊断报告」四字全仓库=0（画像交付物措辞统一为「个案概念化/概念化梳理」，绝不允许出现「诊断报告」）
all_md = "\n".join(
    (ROOT / f).read_text(encoding="utf-8", errors="ignore")
    for f in ["SKILL.md", "README.md"]
)
all_ref = "\n".join(
    (REF / f).read_text(encoding="utf-8", errors="ignore")
    for f in ["crisis.md", "anchors.md", "practices.md", "report.md",
              "report_template.html", "report_narrative_template.html"]
)
check("『诊断报告』全文件=0", "诊断报告" not in (all_md + all_ref),
      "(出现于非免责/非禁区上下文)")

# 4. 关键锚点
for k in ["双模式", "每 4-6 轮", "白名单", "WebSearch"]:
    check(f"SKILL 锚点『{k}』", k in skill_text)

# 5. references 齐全
for f in ["crisis.md", "anchors.md", "practices.md", "report.md", "report_template.html"]:
    check(f"references/{f}", (REF / f).exists())

# 6. 画像模板含热线（交付物也须带红线）
if (REF / "report_template.html").exists():
    tpl = (REF / "report_template.html").read_text(encoding="utf-8")
    for h in hotlines:
        check(f"模板含热线 {h}", h in tpl, f"(report_template.html 缺 {h})")
    # 概念化型模板（v0.6.0 起）强制板块：5-P / 谱系 / 机制图 / 新洞见 / 可试方向 / 文档标题
    for sec in ["情绪画像", "个案概念化（5-P 模型）", "症状谱系定位", "机制图", "给你没说出口的重新框定", "可以试试的方向（有依据"]:
        check(f"模板含板块『{sec}』", sec in tpl, f"(report_template.html 缺板块 {sec})")
    # 叙事性回望版板块（独立文件，同视觉风格，由 check_readiness.py 按深度自动选）
    narr = (REF / "report_narrative_template.html").read_text(encoding="utf-8") if (REF / "report_narrative_template.html").exists() else ""
    for sec in ["情绪画像", "回望", "关键瞬间", "重新框定", "今天就能做的一件"]:
        check(f"叙事模板含板块『{sec}』", sec in narr, f"(report_narrative_template.html 缺板块 {sec})")
else:
    check("references/report_template.html", False, "(文件不存在)")

# 7. （可选 --output）交付画像校验：无占位符残留 + 热线 + 免责
if OUTPUT_FILE is not None:
    if OUTPUT_FILE.exists():
        out = OUTPUT_FILE.read_text(encoding="utf-8")
        n_ph = out.count("{{")
        check("交付画像无占位符残留（{{ = 0）", n_ph == 0, f"(残留 {n_ph} 处占位符)")
        for h in hotlines:
            check(f"交付画像含热线 {h}", h in out, f"(缺 {h})")
        check("交付画像含免责声明『不是医疗诊断』", "不是医疗诊断" in out)
    else:
        check(f"交付画像文件存在（{OUTPUT_FILE}）", False, "(文件不存在)")

print("-----------------------------")
if FAILS:
    print(f"❌ 红线失守 {len(FAILS)} 项: {', '.join(FAILS)}")
    sys.exit(1)
print("✅✅ 安全红线全过（exit 0）")
sys.exit(0)
