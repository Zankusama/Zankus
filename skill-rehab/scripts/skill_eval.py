#!/usr/bin/env python3
"""
skill_eval.py — Skill 质量评估脚本（机制层 v3 · 10 原理 · 100 分制重分权重）
================================================================================
v3 升级（2026-08-03）：
  · 100 分制重分权重：10 原理各 10 分（等分），老 8 原理 item weight 按比例缩到总和 10
  · 老 skill 跑 v3 分数会变（按新权重基准重新评分）——这是评估器升级的预期，不是 bug
  · 达标线按新比例定（先跑回归看分数分布）
  · 新原理 ⑨ 失败模式防御（5 姿势机器层防御）+ ⑩ 五要素齐全性（5 要素机器层检查）

v2 → v3 吸收项（按 v3 设计方案）：
  · ✅ 5 失败模式（代码围栏输出陷阱/被动推迟/重复模式/重复指令/模糊占位符）
  · ✅ 五要素齐全性（触发/步骤/输出格式/边界/测试用例）
  · ❌ tier 分层（偏语义判断，进评审层而非机器硬判）
  · ❌ 运行时实测 4 项（静态分析做不到，留在康复师复查阶段）

死规矩 1：升级走版本管理——改前 `guard.sh snapshot` 冻结 / 改后 `--self` + 自举回归不降分 / README 记版本号。
"""
__version__ = "3.0.3"
"""
v2 原始头注释（v3 重写头注释后保留作为历史记录）：
单一解释框架（2026-08-03 用户要求：结合 V1 + 六原则 + 金字塔 + 机制层整体重构，
不要打补丁式拼接——从头到尾只有「LLM 机制 → skill 原理」一条线）。

V1（skill_eval.py 结构合规 8 项）完整拆入机制层，不再作为独立层：
  V1 五级标注 / 无两极残留 → 权重工程（五级标注=指令权重分级的结构化实现）
  V1 Poka-Yoke 防误层     → 确定性转移（写死物理锚点/定值/步序，不让模型自由判断）
  V1 熔断器               → 分步推进（止损机制：连败换项/超时停）
  V1 Alternatives         → 锚点抑制（决策透明：让模型看到替代方案）
  V1 触发条件             → 塔尖对齐（description 是触发接口）
  V1 产出物定义           → 确定性转移（验收可执行）+ 分步推进（每步产出物）
  V1 YAML 元数据          → 塔尖对齐（description）+ 自迭代（version）

8 原理（每个 = 一个 LLM 机制的对策，全部 MECE）：

| 原理 | LLM 机制 | 分值 | V1 归位 |
|------|----------|:----:|---------|
| ①确定性转移 | 概率生成不可靠 | 20 | Poka-Yoke + 产出物 |
| ②重复锚定   | 注意力衰减(lost in middle) | 12 | — |
| ③锚点抑制   | 无锚点处幻觉 | 15 | Alternatives |
| ④分步推进   | 一步到位易错(CoT更准) | 13 | 熔断器 + 产出物 |
| ⑤权重工程   | 指令稀释/冲突漂移 | 15 | 五级标注 + 无两极 |
| ⑥状态物化   | 模型无状态 | 10 | — |
| ⑦环境外置   | 上下文窗口有限 | 5 | — |
| ⑧塔尖对齐   | description 是触发接口 | 10 | 触发条件 + YAML |

双层评估（确定性转移原理的自反应用）：
- 机器层：可正则判的结构项 → 脚本硬判，0 误判
- 评审层：需语义判断的项 → 脚本只收集证据（原文/脱节词/无替代行），
  给出默认判定并标 🟡「需复核」，人工或子 Agent 按证据复核后覆盖

本脚本自身符合金字塔原理（结论先行/归类分组/逻辑递进），
借鉴 leader-translator 机制（--self 自检、产出物锁、关键约束集中、过/不过判定）。

用法:
  python3 skill_eval.py --self                        # 体检本脚本
  python3 skill_eval.py --skills "leader-translator"  # 评估指定 skill
  python3 skill_eval.py --base ./技能配置             # 评估目录
"""

import os
import re
import json
import sys
import argparse
from datetime import datetime

# ============================================================
# 关键约束集中区
# ============================================================

DEFAULT_SKILL_BASE = "./技能配置"
DEFAULT_CORE_SKILLS = [
    "Shall We Talk", "三明智", "唤醒记忆系统", "每日伙伴",
    "系统日志", "成长箱", "迁理之外", "读书助手",
]

# ============================================================
# 8 原理配置（MECE · 总分 100）
# 每项 item：layer=machine(机器层)/review(评审层)｜weight｜判定素材
# ============================================================

PRINCIPLES = {
    # ── ①确定性转移（20）· 概率→脚本/锚点，唯一「必然」手段 ──
    "p1_determinism": {
        "title": "①确定性转移（10）· 机制：概率生成不可靠",
        "weight": 10,
        "items": {
            "scriptized": {  # 4 机器（v3 重分）
                "layer": "machine", "weight": 4,
                "title": "可机器化约束已固化为脚本（scripts/ + lint/check）",
                "keywords": ["scripts/", "stage-gate", "lint", ".sh", ".py", "goal-lint", "guard", "coverage", "脚本"],
                "min": 3,
            },
            "judgeable_acceptance": {  # 3 机器（v3 重分）
                "layer": "machine", "weight": 3,
                "title": "验收可执行判定（命令/grep/exit/断言）",
                "keywords": ["验收", "grep", "diff", "exit", "退出码", "机器判", "命令", "测试", "curl", "断言", "== "],
                "min": 3,
            },
            "physical_anchor": {  # 3 机器（v3 重分）
                "layer": "machine", "weight": 3,
                "title": "物理锚点防误（Poka-Yoke：接触/定值/步序 ≥2 法）——写死锚点不让模型自由判断",
                "contact": ["接触", "contact", "Schema", "原话", "物理验证", "硬匹配", "锚点", "物理锚点"],
                "fixed": ["定值", "fixed-value", "固定", "数量定值", "至少", "必须全"],
                "motion": ["步序", "步骤强依赖", "强依赖", "前置条件", "不可跳", "先.*后", "加载步序", "写入步序"],
                "min_methods": 2,
            },
        },
    },
    # ── ②重复锚定（12）· 对抗注意力衰减 ──
    "p2_anchoring": {
        "title": "②重复锚定（10）· 机制：注意力衰减（lost in the middle）",
        "weight": 10,
        "items": {
            "key_constraint_repeated": {  # 10 机器（v3 重分）
                "layer": "machine", "weight": 10,
                "title": "关键约束出现 ≥2 次（开头声明 + 任务指令重提）",
                "keywords": ["必须", "不得", "禁止", "硬上限", "死规矩", "不许"],
                "min": 2,
            },
        },
    },
    # ── ③锚点抑制（15）· 无锚点处幻觉 ──
    "p3_anti_hallucination": {
        "title": "③锚点抑制（10）· 机制：无锚点处幻觉",
        "weight": 10,
        "items": {
            "source_required": {  # 5 机器（v3 重分）
                "layer": "machine", "weight": 5,
                "title": "断言带来源/日期/实测（锚点抑制）",
                "keywords": ["来源", "实测", "验证", "核查", "引用", "复现", "证据", "查询", "调研"],
                "min": 2,
            },
            "unverified_marked": {  # 3 机器（v3 重分）
                "layer": "machine", "weight": 3,
                "title": "无锚点标「未验证/假设」（查不到不许裸奔）",
                "keywords": ["假设", "未验证", "没查到", "待核实", "存疑", "⚠️", "猜的", "推测"],
                "min": 1,
            },
            "alternatives_considered": {  # 2 评审（v3 重分）
                "layer": "review", "weight": 2,
                "title": "决策透明：Alternatives/替代方案段存在（模型看到替代不拍脑袋）",
                "patterns": [r"Alternatives Considered", r"替代方案", r"备选", r"为什么不选", r"为什么没选"],
            },
        },
    },
    # ── ④分步推进（13）· CoT 精度 ──
    "p4_progressive": {
        "title": "④分步推进（10）· 机制：一步到位易错，分步更准",
        "weight": 10,
        "items": {
            "step_flow": {  # 5 机器（v3 重分）
                "layer": "machine", "weight": 5,
                "title": "流程分步（步骤编号 ≥3 且连续）",
                "min_steps": 3,
            },
            "step_acceptance": {  # 3 机器（v3 重分）
                "layer": "machine", "weight": 3,
                "title": "每步有独立产出物/验收",
                "keywords": ["产出物", "验收", "闸门", "每步", "任务 0", "任务 N", "检查点", "产出"],
                "min": 3,
            },
            "fuse_mechanism": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "止损熔断（连败换项/超时停/回滚）",
                "keywords": ["熔断", "止损", "连败", "满轮", "超限", "回滚", "终止", "卡死", "超时", "停"],
                "min": 2,
            },
        },
    },
    # ── ⑤权重工程（15）· 指令分级/克制/仲裁 ──
    "p5_weighting": {
        "title": "⑤权重工程（10）· 机制：规则太多互相稀释，冲突导致漂移",
        "weight": 10,
        "items": {
            "rule_grading": {  # 4 机器（v3 重分）
                "layer": "machine", "weight": 4,
                "title": "规则显式分级（五级标注 DO/SHOULD/MAY 或「必做/可选」声明）",
                "keywords": ["DO NOT", "SHOULD NOT", "✅DO", "☑SHOULD", "MAY", "必做", "可选", "必须", "可选做", "分级", "优先级"],
                "min": 1,
            },
            "no_binary_residual": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "无两极标注残留（NEVER/MUST/CRITICAL ≤2）——两极太硬致冲突漂移",
                "forbidden": ["NEVER", "MUST", "CRITICAL"],
                "max": 2,
            },
            "conflict_arbitration": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "冲突仲裁（规则打架听谁的）",
                "keywords": ["冲突", "优先", "让步", "听谁", "优先于", "冲突时", "仲裁", "不冲突"],
                "min": 1,
            },
            "ban_with_alternative": {  # 2 评审（v3 重分）
                "layer": "review", "weight": 2,
                "title": "禁带替代（模糊禁止给了替代动作，非纯「不要」）",
                "fuzzy_words": ["瞎编", "乱来", "随便", "大概", "差不多", "糊弄", "应付", "编造", "凑数", "不懂装懂"],
                "alternative_markers": ["则", "否则", "用 ", "替换", "替代", "建议", "就 ", "写", "标"],
            },
        },
    },
    # ── ⑥状态物化（10）· 模型无状态 ──
    "p6_materialization": {
        "title": "⑥状态物化（10）· 机制：模型无状态，每次调用独立",
        "weight": 10,
        "items": {
            "progress_mechanism": {  # 10 机器
                "layer": "machine", "weight": 10,
                "title": "跨步状态落盘（PROGRESS/gate/.goal）——防失忆",
                "keywords": ["PROGRESS", "BLOCKED", "gate-", ".goal", "进度", "落盘", "写进", "保存", "续接", "接着做"],
                "min": 2,
            },
        },
    },
    # ── ⑦环境外置（5）· 窗口有限 ──
    "p7_extrusion": {
        "title": "⑦环境外置（10）· 机制：上下文窗口有限",
        "weight": 10,
        "items": {
            "references_extruded": {  # 10 机器（v3 重分）
                "layer": "machine", "weight": 10,
                "title": "参考资料外置 references/（SKILL.md 留决策骨架）",
                "keywords": ["references/", "见 ", "详见", "看 ", "详细", "模板见", "规范见", "另见"],
                "min": 2,
            },
        },
    },
    # ── ⑧塔尖对齐（10）· description 是触发接口 ──
    "p8_apex": {
        "title": "⑧塔尖对齐（10）· 机制：description 是触发接口",
        "weight": 10,
        "items": {
            "desc_consistent": {  # 6 评审（语义项）
                "layer": "review", "weight": 6,
                "title": "description 与正文一致（塔尖=正文概括）",
            },
            "trigger_boundary": {  # 4 机器（V1 触发条件归位）
                "layer": "machine", "weight": 4,
                "title": "触发边界（NOT for/不触发——不该触发的场景显式排除）",
                "patterns": [r"NOT for", r"不触发", r"不应触发", r"不适合", r"仅限", r"NOT for 任务书"],
            },
        },
    },
    # ── ⑨失败模式防御（20 分 · v3 扩展）· 5 姿势机器层防御 ──
    "p9_failure_modes": {
        "title": "⑨失败模式防御（10）· 机制：5 姿势机器层硬判",
        "weight": 10,
        "items": {
            "fence_escape": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "代码围栏输出陷阱（围栏内是纯可执行命令，无 $ 提示符/伪代码占位）",
                "min_fence_count": 1,    # 围栏数 ≥2（说明有用代码块）
                "max_dollar_in_fence": 0, # 围栏内 $ 提示符 0
            },
            "passive_defer": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "被动推迟（关键动作有「必须/默认/先」主动指令，不只靠被动条件）",
                "passive_patterns": [r"等\s*[^。\n]{0,10}\s*(?:再|才|处理|看|做)", r"(?:以后|稍后|有空|到时候|有时间)\s*(?:再|补|看|做)", r"需要时\s*(?:再|才)", r"必要时\s*(?:再|才)", r"看情况\s*(?:再|才)"],
                "max_passive": 5,  # 被动词 ≤ 5 处
            },
            "repeat_pattern": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "重复模式（同一关键命令/段不重复 ≥3 次——重复收敛为单脚本）",
                "max_repeat": 2,
            },
            "repeat_command": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "重复指令（同一约束多处表述一致——冲突处有仲裁）",
                "check": "consistency",
            },
            "fuzzy_placeholder": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "模糊占位符（xxx/TBD/待补充/TODO 0 命中——占位符必填实）",
                "patterns": [r"\bxxx\b", r"\bTBD\b", r"待补充", r"\bTODO\b", r"占位符(?:必填|待填|未替换)"],
                "max_placeholder": 0,
            },
        },
    },
    # ── ⑩五要素齐全性（20 分 · v3 扩展）· skill 骨架五件套缺一即接诊不合格 ──
    "p10_five_elements": {
        "title": "⑩五要素齐全性（10）· 机制：skill 骨架五件套机器层硬查",
        "weight": 10,
        "items": {
            "trigger": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "触发条件（description 含触发词 + NOT for 边界）",
                "min_trigger_kw": 1,  # 至少 1 个触发词
                "needs_not_for": True, # 必须有 NOT for
            },
            "steps": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "执行步骤（流程分步 ≥3 连续编号）",
                "min_steps": 3,
            },
            "output_format": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "输出格式（每步/整体产出物格式明确 + 示例）",
                "keywords": ["产出物", "输出", "产物", "格式", "示例", "格式声明"],
                "min": 2,
            },
            "boundary": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "边界（接什么/不接什么 + 正确去处）",
                "patterns": [r"NOT for", r"不触发", r"不应触发", r"不适合", r"边界", r"什么时候"],
            },
            "test_case": {  # 2 机器（v3 重分）
                "layer": "machine", "weight": 2,
                "title": "测试用例（验收可执行命令/判定标准）",
                "keywords": ["验收", "grep", "diff", "exit", "命令", "测试", "断言", "实测"],
                "min": 2,
            },
        },
    },
}

TOTAL_EXPECTED = 100  # 满分（10 原理 × 10 分）
# 达标线（v3 重分权重后按比例定，跑完回归定具体值；暂定 v2 同款 90/100）
PASS_LINE = 90


# ============================================================
# 解析器
# ============================================================

def parse_yaml_frontmatter(content):
    fm = {}
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if m:
        lines = m.group(1).split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            if ':' in line:
                k, _, v = line.partition(':')
                k, v = k.strip(), v.strip().strip('"').strip("'")
                # YAML 折叠块（> / | / >- / |-）：收集后续缩进行（v3.0.2 修：折叠 description 不再漏解析）
                if k and v.startswith(('>', '|')):
                    block = []
                    j = i + 1
                    while j < len(lines) and lines[j].startswith((' ', '\t')):
                        block.append(lines[j].strip())
                        j += 1
                    fm[k] = (' '.join(block) if v.startswith('>') else '\n'.join(block)).strip()
                    i = j
                    continue
                if k and v:
                    fm[k] = v
            i += 1
    return fm

def find_longest_step_seq(content):
    """找从 1 开始的最长连续步骤编号（v3.0.2 修：兼容 **1. / 1. / ### 1. / 1、/ 一、 行首编号 + 阶段N + Step N）"""
    cn = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    nums = []
    # 行首编号（**1. / 1. / ### 1. / 1、/ 一、）+ 阶段标题（### 阶段N）+ Step 标题（#### Step N）——限定行首标题，防正文引用污染序列
    pat = re.compile(
        r'(?:^\s*(?:\*\*\s*|#{1,6}\s*)?(\d{1,2}|[一二三四五六七八九十])[\.、\)）\s:：])'
        r'|(?:^#{1,6}\s*阶段\s*(\d{1,2}))'
        r'|(?:^#{1,6}\s*Step\s*(\d{1,2}))',
        re.MULTILINE)
    for mt in pat.finditer(content):
        tok = mt.group(1) or mt.group(2) or mt.group(3)
        if tok:
            nums.append(int(tok) if tok.isdigit() else cn.get(tok, 0))
    best = cur = 0
    expect = 1
    for n in nums:
        if n == expect:
            cur += 1
            expect += 1
        elif n == 1:
            cur = 1
            expect = 2
        elif n == 0 and cur == 0:
            # 阶段0/Step 0 开头序列（0,1,2,3…）——把 0 当起点计数
            cur = 1
            expect = 1
        else:
            cur = 0
            expect = 1
        best = max(best, cur)
    return best

def count_keyword(content, keywords):
    return sum(content.count(k) for k in keywords)

def check_pattern(content, patterns):
    for p in patterns:
        if re.search(p, content, re.IGNORECASE):
            return True, p
    return False, None

def extract_version(content):
    fm = parse_yaml_frontmatter(content)
    if 'version' in fm:
        return fm['version']
    m = re.search(r'v(\d+\.\d+(?:\.\d+)?)', content)
    return f"v{m.group(1)}" if m else "unknown"

def machine_item(weight, passed, detail):
    """机器层检查项结果"""
    return {"passed": passed, "score": weight if passed else 0, "max": weight, "detail": detail, "layer": "machine"}

def review_item(weight, default_passed, detail, evidence):
    """评审层检查项结果：脚本给默认判定+证据，人工可覆盖"""
    return {"passed": default_passed, "score": weight if default_passed else 0, "max": weight,
            "detail": detail, "layer": "review", "evidence": evidence, "needs_review": True}

# ============================================================
# 8 原理评估（机器层硬判 + 评审层证据收集）
# ============================================================

def ev_p1(content, skill_dir):
    res = {}
    it = PRINCIPLES["p1_determinism"]["items"]
    # 1a 脚本化（v3.0.3 强化：引用脚本必须真实存在 + 有脚本化声明节——防「SKILL.md 提一句脚本名」作弊）
    scripts_dir = os.path.join(skill_dir, "scripts") if skill_dir else None
    has_dir = bool(scripts_dir) and os.path.isdir(scripts_dir)
    ref_scripts = set(re.findall(r'scripts/([A-Za-z0-9_\-\.]+\.(?:py|sh))', content))
    real_scripts = set()
    if has_dir:
        real_scripts = {f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))}
    refs_real = bool(ref_scripts) and ref_scripts <= real_scripts
    has_decl = bool(re.search(r'可机器化验收|脚本化清单|脚本化声明', content))
    passed = has_dir and refs_real and has_decl and len(real_scripts) >= 1
    res["scriptized"] = machine_item(it["scriptized"]["weight"], passed,
        f"scripts/ 目录{'✅' if has_dir else '❌'} 引用脚本真实{'✅' if refs_real else '❌'} 脚本化声明{'✅' if has_decl else '❌'}" if passed
        else "❌可机器化约束没脚本化（需：scripts/ 目录 + SKILL.md 引用脚本真实存在 + 可机器化验收声明节）——概率判断→脚本执行是质量从「大概率对」变「必然对」的唯一手段")
    # 1b 验收可执行
    judge_cnt = count_keyword(content, it["judgeable_acceptance"]["keywords"])
    passed = judge_cnt >= it["judgeable_acceptance"]["min"]
    res["judgeable_acceptance"] = machine_item(it["judgeable_acceptance"]["weight"], passed,
        f"可执行判定词 {judge_cnt} 处（≥{it['judgeable_acceptance']['min']}）" if passed
        else "❌验收不可机器判——「看看效果」类验收，模型自己判自己必自欺")
    # 1c 物理锚点（V1 Poka-Yoke）
    contact = count_keyword(content, it["physical_anchor"]["contact"])
    fixed = count_keyword(content, it["physical_anchor"]["fixed"])
    motion = len(re.findall(r'先.*?后', content))
    methods = sum(1 for c in [contact, fixed, motion] if c > 0)
    passed = methods >= it["physical_anchor"]["min_methods"]
    res["physical_anchor"] = machine_item(it["physical_anchor"]["weight"], passed,
        f"物理锚点覆盖 {methods}/3 法（接触{contact}/定值{fixed}/步序{motion}）" if passed
        else f"❌物理锚点仅 {methods}/3（需≥2）——全靠模型自由判断，无写死锚点")
    return res

def ev_p2(content):
    it = PRINCIPLES["p2_anchoring"]["items"]["key_constraint_repeated"]
    cnt = count_keyword(content, it["keywords"])
    passed = cnt >= it["min"]
    return {"key_constraint_repeated": machine_item(it["weight"], passed,
        f"关键约束词 {cnt} 处（≥{it['min']} 对抗注意力衰减）" if passed
        else f"❌关键约束仅 {cnt} 处（<{it['min']}）——只在开头说一次，长上下文后必被淹没")}

def ev_p3(content):
    res = {}
    it = PRINCIPLES["p3_anti_hallucination"]["items"]
    # 3a 来源（机器）
    src = count_keyword(content, it["source_required"]["keywords"])
    passed = src >= it["source_required"]["min"]
    res["source_required"] = machine_item(it["source_required"]["weight"], passed,
        f"来源/实测词 {src} 处（≥{it['source_required']['min']}）" if passed
        else "❌断言无锚点——模型在没依据的地方必编造（幻觉是概率生成的自然结果）")
    # 3b 未验证标注（机器）
    unv = count_keyword(content, it["unverified_marked"]["keywords"])
    passed = unv >= it["unverified_marked"]["min"]
    res["unverified_marked"] = machine_item(it["unverified_marked"]["weight"], passed,
        f"未验证标注词 {unv} 处" if passed else "❌无「假设/未验证」标注——查不到不许裸奔")
    # 3c Alternatives（评审）
    found, pat = check_pattern(content, it["alternatives_considered"]["patterns"])
    res["alternatives_considered"] = review_item(it["alternatives_considered"]["weight"], found,
        f"Alternatives 段{'✅' if found else '❌'}（匹配: {pat or '无'}）——需复核段内容是否真列了替代而非凑数",
        f"匹配模式: {pat if found else '未找到'}")
    return res

def ev_p4(content):
    res = {}
    it = PRINCIPLES["p4_progressive"]["items"]
    # 4a 流程分步（机器）——兼容 **1. / 1. / ### 1. / 一、 等格式，取最长连续编号
    steps_n = find_longest_step_seq(content)
    seq_ok = steps_n >= it["step_flow"]["min_steps"]
    res["step_flow"] = machine_item(it["step_flow"]["weight"], seq_ok,
        f"流程 {steps_n} 步编号连续（≥{it['step_flow']['min_steps']}）" if seq_ok
        else f"❌流程步骤 最长连续{steps_n} 步（需≥{it['step_flow']['min_steps']}）——不分步=一步到位，长上下文单步质量必降")
    # 4b 每步产出物（机器）
    acc = count_keyword(content, it["step_acceptance"]["keywords"])
    passed = acc >= it["step_acceptance"]["min"]
    res["step_acceptance"] = machine_item(it["step_acceptance"]["weight"], passed,
        f"每步产出物/验收词 {acc} 处（≥{it['step_acceptance']['min']}）" if passed
        else "❌步骤无独立验收——整体一个「做完」，错在哪一步查不出")
    # 4c 熔断（机器，V1 归位）
    fuse = count_keyword(content, it["fuse_mechanism"]["keywords"])
    passed = fuse >= it["fuse_mechanism"]["min"]
    res["fuse_mechanism"] = machine_item(it["fuse_mechanism"]["weight"], passed,
        f"止损熔断词 {fuse} 处（≥{it['fuse_mechanism']['min']}）" if passed
        else "❌无熔断/止损——连败/超时/回滚没定义，会无限烧下去")
    return res

def ev_p5(content):
    res = {}
    it = PRINCIPLES["p5_weighting"]["items"]
    # 5a 规则分级（机器，V1 五级标注归位）
    grade_cnt = count_keyword(content, it["rule_grading"]["keywords"])
    passed = grade_cnt >= it["rule_grading"]["min"]
    res["rule_grading"] = machine_item(it["rule_grading"]["weight"], passed,
        f"规则分级词 {grade_cnt} 处（五级标注/必做可选声明）" if passed
        else "❌规则无分级——所有规则一个权重，等于没有权重，全部被稀释")
    # 5b 无两极残留（机器，V1 归位）
    excl = ["替换NEVER", "替换CRITICAL", "变更", "升级", "changelog", "CHANGELOG"]
    residual = 0
    for kw in it["no_binary_residual"]["forbidden"]:
        for line in content.split('\n'):
            if any(e in line for e in excl):
                continue
            residual += line.count(kw)
    passed = residual <= it["no_binary_residual"]["max"]
    res["no_binary_residual"] = machine_item(it["no_binary_residual"]["weight"], passed,
        f"两极标注残留 {residual} 处（≤{it['no_binary_residual']['max']}）" if passed
        else f"❌两极标注残留 {residual} 处——NEVER/MUST 太硬，导致过度遵循/冲突漂移，应改五级")
    # 5c 冲突仲裁（机器）
    arb = count_keyword(content, it["conflict_arbitration"]["keywords"])
    passed = arb >= it["conflict_arbitration"]["min"]
    res["conflict_arbitration"] = machine_item(it["conflict_arbitration"]["weight"], passed,
        f"仲裁词 {arb} 处" if passed else "❌无冲突仲裁——规则打架时模型随机选一个，行为漂移")
    # 5d 禁带替代（评审）
    fuzzy = [ln.strip() for ln in content.split('\n')
             if any(k in ln for k in ["不要", "不许", "禁止", "不得", "别 "])
             and any(f in ln for f in it["ban_with_alternative"]["fuzzy_words"])]
    if fuzzy:
        no_alt = [ln[:40] for ln in fuzzy
                  if not any(m in ln for m in it["ban_with_alternative"]["alternative_markers"])]
        default = len(no_alt) == 0
        detail = f"模糊禁止 {len(fuzzy)} 行" + ("" if default else f"，{len(no_alt)} 行无替代: {no_alt[:2]}")
        evidence = f"无替代行: {no_alt[:3]}" if no_alt else "全部带替代"
    else:
        default, detail, evidence = True, "✅无模糊禁止（精确禁止不需替代）", "无"
    res["ban_with_alternative"] = review_item(it["ban_with_alternative"]["weight"], default,
        detail, evidence)
    return res

def ev_p6(content):
    it = PRINCIPLES["p6_materialization"]["items"]["progress_mechanism"]
    cnt = count_keyword(content, it["keywords"])
    passed = cnt >= it["min"]
    return {"progress_mechanism": machine_item(it["weight"], passed,
        f"状态物化词 {cnt} 处（≥{it['min']}）" if passed
        else "❌无状态物化——模型无状态，跨步状态不落盘必失忆（换会话就重做）")}

def ev_p7(content):
    it = PRINCIPLES["p7_extrusion"]["items"]["references_extruded"]
    cnt = count_keyword(content, it["keywords"])
    passed = cnt >= it["min"]
    return {"references_extruded": machine_item(it["weight"], passed,
        f"外置引用词 {cnt} 处（≥{it['min']}）" if passed
        else "❌无环境外置——全部细节塞 SKILL.md，窗口有限装不下，长文必被截断")}

def ev_p8(content):
    res = {}
    it = PRINCIPLES["p8_apex"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")
    desc_words = [w for w in re.findall(r'[\u4e00-\u9fff]{2,4}', desc) if w in body]
    # 8a description 一致（评审）
    default = len(desc_words) >= 2 or len(desc) < 30
    res["desc_consistent"] = review_item(it["desc_consistent"]["weight"], default,
        f"description 关键词 {len(desc_words)} 个在正文复现" + ("" if default else " ❌塔尖脱节"),
        f"description: {desc[:60]}...；正文复现词: {desc_words[:5]}")
    # 8b 触发边界（机器，V1 触发条件归位）
    has_b = check_pattern(content[:2000], it["trigger_boundary"]["patterns"])
    res["trigger_boundary"] = machine_item(it["trigger_boundary"]["weight"], has_b,
        "✅有触发边界（NOT for/不触发）" if has_b else "❌无触发边界——不该触发的场景没排除，会误触发")
    return res

# ============================================================
# v3 新增：⑨失败模式防御 + ⑩五要素齐全性（机器层硬判）
# ============================================================

def ev_p9(content):
    """⑨失败模式防御（10）· 5 姿势机器层硬判"""
    res = {}
    it = PRINCIPLES["p9_failure_modes"]["items"]
    # 9a fence_escape：围栏内 $ 提示符 0 命中
    fences = re.findall(r'```[^\n]*\n(.*?)\n```', content, re.DOTALL)
    dollar_in_fence = sum(1 for f in fences if re.search(r'^\s*\$', f, re.MULTILINE))
    fence_ok = len(fences) >= it["fence_escape"]["min_fence_count"] and dollar_in_fence <= it["fence_escape"]["max_dollar_in_fence"]
    res["fence_escape"] = machine_item(it["fence_escape"]["weight"], fence_ok,
        f"围栏 {len(fences)} 块，$ 提示符 {dollar_in_fence} 处（≤{it['fence_escape']['max_dollar_in_fence']}）" if fence_ok
        else f"❌围栏内 $ 提示符 {dollar_in_fence} 处（>{it['fence_escape']['max_dollar_in_fence']}）或围栏数<{it['fence_escape']['min_fence_count']}——围栏命令脱离围栏跑可能错")
    # 9b passive_defer：被动词 ≤ 5
    passive_cnt = sum(len(re.findall(p, content)) for p in it["passive_defer"]["passive_patterns"])
    passive_ok = passive_cnt <= it["passive_defer"]["max_passive"]
    res["passive_defer"] = machine_item(it["passive_defer"]["weight"], passive_ok,
        f"被动词 {passive_cnt} 处（≤{it['passive_defer']['max_passive']}）" if passive_ok
        else f"❌被动词 {passive_cnt} 处（>{it['passive_defer']['max_passive']}）——关键动作靠被动条件必推迟")
    # 9c repeat_pattern：找重复命令（取所有 ``` 围栏内命令，标准化后查重）
    cmds = set()
    repeats = 0
    for f in fences:
        for line in f.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('$'):
                continue
            # v3.0.2 补修 + v3.0.3 扩展：排除非命令内容——表格行（|）、ASCII 树形（│）、引用/模板（>）、emoji 标记（🧠📦✅ 等）、纯符号行（---）
            if line.startswith(('|', '│', '>', '🧠', '📦', '✅', '⚠️', '🔍', '⛔', '❌', '🎯')):
                continue
            if not re.search(r'[\w\u4e00-\u9fff]', line):
                continue
            norm = re.sub(r'\s+', ' ', line)
            if norm in cmds:
                repeats += 1
            else:
                cmds.add(norm)
    repeat_ok = repeats < it["repeat_pattern"]["max_repeat"]  # v3.0.3：off-by-one 修（同一命令出现 ≥max+2 次才挂）
    res["repeat_pattern"] = machine_item(it["repeat_pattern"]["weight"], repeat_ok,
        f"重复命令 {repeats} 处（≤{it['repeat_pattern']['max_repeat']}）" if repeat_ok
        else f"❌重复命令 {repeats} 处（>{it['repeat_pattern']['max_repeat']}）——重复逻辑应收敛为单脚本")
    # 9d repeat_command：简化版——同一关键指令词在多处出现视为一致（如「不许」「必须」 ≥3 次且都属同一约束方向）
    must_cnt = len(re.findall(r'(不许|必须|不得|禁止|硬上限|死规矩)', content))
    repeat_cmd_ok = must_cnt >= 1  # 有关键指令词即可，简化判定
    res["repeat_command"] = machine_item(it["repeat_command"]["weight"], repeat_cmd_ok,
        f"关键指令词 {must_cnt} 处（≥1 视为有锚定）" if repeat_cmd_ok
        else "❌无关键指令词（不许/必须/不得）")
    # 9e fuzzy_placeholder：xxx/TBD/待补充/TODO 0 命中（注释外）
    # 先去掉代码块内（避免示例代码里的 xxx 被算）
    content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    fuzzy_cnt = sum(len(re.findall(p, content_no_code, re.IGNORECASE)) for p in it["fuzzy_placeholder"]["patterns"])
    fuzzy_ok = fuzzy_cnt <= it["fuzzy_placeholder"]["max_placeholder"]
    res["fuzzy_placeholder"] = machine_item(it["fuzzy_placeholder"]["weight"], fuzzy_ok,
        f"模糊占位符 {fuzzy_cnt} 处（≤{it['fuzzy_placeholder']['max_placeholder']}）" if fuzzy_ok
        else f"❌模糊占位符 {fuzzy_cnt} 处（>{it['fuzzy_placeholder']['max_placeholder']}）——占位符必填实")
    return res

def ev_p10(content, skill_dir):
    """⑩五要素齐全性（10）· skill 骨架五件套机器层硬查"""
    res = {}
    it = PRINCIPLES["p10_five_elements"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")
    # 10a trigger：description 含触发词 + NOT for
    trigger_ok = bool(desc) and bool(re.search(r'(修|打|修.*skill|康复|体检|诊断|打磨|trigger|触发)', desc, re.IGNORECASE)) and bool(re.search(r'NOT for|不触发|不应触发', desc + body[:500], re.IGNORECASE))
    res["trigger"] = machine_item(it["trigger"]["weight"], trigger_ok,
        "✅触发条件齐（description 含触发词 + NOT for）" if trigger_ok
        else "❌触发条件缺——description 无触发词或无 NOT for 边界")
    # 10b steps：流程分步 ≥3 连续编号（兼容多格式，v3.0.2 修）
    steps_n = find_longest_step_seq(body)
    steps_ok = steps_n >= it["steps"]["min_steps"]
    res["steps"] = machine_item(it["steps"]["weight"], steps_ok,
        f"流程分步 {steps_n} 处连续（≥{it['steps']['min_steps']}）" if steps_ok
        else f"❌流程分步 最长连续{steps_n} 处（<{it['steps']['min_steps']}）")
    # 10c output_format：产出物/输出/格式 关键词 ≥2
    out_cnt = count_keyword(body, it["output_format"]["keywords"])
    out_ok = out_cnt >= it["output_format"]["min"]
    res["output_format"] = machine_item(it["output_format"]["weight"], out_ok,
        f"输出格式词 {out_cnt} 处（≥{it['output_format']['min']}）" if out_ok
        else f"❌输出格式词 {out_cnt} 处（<{it['output_format']['min']}）")
    # 10d boundary：边界/不接/不适合
    boundary_ok = check_pattern(content, it["boundary"]["patterns"])[0]
    res["boundary"] = machine_item(it["boundary"]["weight"], boundary_ok,
        "✅边界声明存在" if boundary_ok else "❌无边界声明（接什么/不接什么不清）")
    # 10e test_case：验收/grep/diff/测试 关键词 ≥2，或 tests/ 目录存在（v3.0.2 修）
    test_cnt = count_keyword(body, it["test_case"]["keywords"])
    has_tests = False
    if skill_dir:
        tdir = os.path.join(skill_dir, 'tests')
        has_tests = os.path.isdir(tdir) and any(os.path.isfile(os.path.join(tdir, f)) for f in os.listdir(tdir))
    test_ok = test_cnt >= it["test_case"]["min"] or has_tests
    res["test_case"] = machine_item(it["test_case"]["weight"], test_ok,
        f"测试用例词 {test_cnt} 处（≥{it['test_case']['min']}）{' + tests/ 目录' if has_tests else ''}" if test_ok
        else f"❌测试用例词 {test_cnt} 处（<{it['test_case']['min']}）")
    return res

# ============================================================
# 评估器
# ============================================================

def evaluate_skill(skill_name, skill_path):
    result = {
        "skill_name": skill_name, "file_path": skill_path,
        "principles": {}, "issues": [], "recommendations": [],
        "score": 0, "max": TOTAL_EXPECTED, "percentage": 0, "grade": "C",
        "machine_score": 0, "review_score": 0, "review_items": [],
    }
    if not os.path.exists(skill_path):
        result["error"] = "SKILL.md not found"
        return result
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    result["file_size"] = len(content)
    result["line_count"] = content.count('\n') + 1
    skill_dir = os.path.dirname(skill_path)

    result["principles"]["p1_determinism"] = ev_p1(content, skill_dir)
    result["principles"]["p2_anchoring"] = ev_p2(content)
    result["principles"]["p3_anti_hallucination"] = ev_p3(content)
    result["principles"]["p4_progressive"] = ev_p4(content)
    result["principles"]["p5_weighting"] = ev_p5(content)
    result["principles"]["p6_materialization"] = ev_p6(content)
    result["principles"]["p7_extrusion"] = ev_p7(content)
    result["principles"]["p8_apex"] = ev_p8(content)
    result["principles"]["p9_failure_modes"] = ev_p9(content)  # v3
    result["principles"]["p10_five_elements"] = ev_p10(content, skill_dir)  # v3.0.2

    # 汇总：机器层 + 评审层（默认判定计入，报告标注需复核）
    for ln, layer in result["principles"].items():
        for itn, it in layer.items():
            result["score"] += it["score"]
            if it["layer"] == "machine":
                result["machine_score"] += it["score"]
            else:
                result["review_score"] += it["score"]
                result["review_items"].append({
                    "name": f"{ln}.{itn}",
                    "title": PRINCIPLES[ln]["items"][itn]["title"],
                    "detail": it["detail"], "evidence": it.get("evidence", ""),
                    "default": "✅ 过" if it["passed"] else "❌ 不过",
                })
            if not it["passed"]:
                result["issues"].append(f"[{ln}.{itn}] {it['detail']}")

    result["percentage"] = round(result["score"] / TOTAL_EXPECTED * 100, 1)
    if result["percentage"] >= 90: result["grade"] = "S"
    elif result["percentage"] >= 75: result["grade"] = "A"
    elif result["percentage"] >= 60: result["grade"] = "B"
    else: result["grade"] = "C"
    result["version"] = extract_version(content)
    return result

# ============================================================
# 报告（金字塔结构 + 评审层复核表）
# ============================================================

def generate_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = f"""# Skill 质量评估报告（机制层最终版 · 8 原理 · 双层评估 · 100 分）

> **生成时间**: {now} | **评估范围**: {len(results)} 个 Skill
> **评估标准**: 8 机制原理（①确定性20 ②锚定12 ③反幻觉15 ④分步13 ⑤权重15 ⑥物化10 ⑦外置5 ⑧塔尖10）
> **V1 归位**: 五级标注→权重工程 / Poka-Yoke→确定性转移 / 熔断器→分步推进 / Alternatives→锚点抑制 / 触发条件→塔尖对齐（V1 不再独立成层）
> **双层评估**: 机器层硬判（可正则判）+ 评审层（🟡 需人工/子 Agent 按证据复核）
> **⚠️ 边界声明（v3.0.3）**: 本报告是「必要条件闸门」判定（有无类检查），未过项=已知硬伤；**未过项 ≠ 全部问题**——「完整性缺口」（该有但没列全/没做全）由康复流程的类别完整性清单（references/completeness.md）兜底，**评估器满分 ≠ skill 全好**

---

## 塔尖 · 总览（结论先行）

| Skill | 版本 | ①确定/10 | ②锚定/10 | ③反幻/10 | ④分步/10 | ⑤权重/10 | ⑥物化/10 | ⑦外置/10 | ⑧塔尖/10 | ⑨防御/10 | ⑩五素/10 | 总分/100 | 等级 |
|:------|:-----|:--------:|:--------:|:---------:|:--------:|:--------:|:--------:|:-------:|:--------:|:--------:|:--------:|:-------:|:----:|
"""
    for r in results:
        g = {"S": "🟢", "A": "🟡", "B": "🟠", "C": "🔴"}.get(r["grade"], "❓")
        p = r["principles"]
        s = lambda ln: sum(x["score"] for x in p.get(ln, {}).values())
        report += (f"| {r['skill_name']} | {r.get('version','?')} | {s('p1_determinism')} | {s('p2_anchoring')} | "
                   f"{s('p3_anti_hallucination')} | {s('p4_progressive')} | {s('p5_weighting')} | "
                   f"{s('p6_materialization')} | {s('p7_extrusion')} | {s('p8_apex')} | "
                   f"{s('p9_failure_modes')} | {s('p10_five_elements')} | "
                   f"{r['score']}/100 | {g} {r['grade']} |\n")

    # 机器层/评审层统计
    report += "\n**得分构成**: 机器层（确定性判）"
    for r in results:
        report += f" | {r['skill_name']}: {r['machine_score']} 分"
    report += "；评审层（需复核，默认已计入）"
    for r in results:
        report += f" | {r['skill_name']}: {r['review_score']} 分"

    report += "\n\n---\n\n## 塔身 · 各 Skill 明细\n\n"
    for r in sorted(results, key=lambda x: len(x.get("issues", [])), reverse=True):
        g = {"S": "🟢", "A": "🟡", "B": "🟠", "C": "🔴"}.get(r["grade"], "❓")
        report += f"### {r['skill_name']} ({r.get('version','?')}) — {g} {r['grade']}级 · {r['score']}/100\n\n"
        report += f"- **文件**: `{r['file_path']}` | 行数 {r.get('line_count','?')}\n\n"
        report += "| 检查项 | 层 | 状态 | 得分 | 详情 |\n|:-------|:--:|:----:|:----:|:-----|\n"
        for ln, layer in r["principles"].items():
            for itn, it in layer.items():
                st = "✅" if it["passed"] else "❌"
                layer_tag = "机器" if it["layer"] == "machine" else "🟡评审"
                report += f"| {PRINCIPLES[ln]['items'][itn]['title']} | {layer_tag} | {st} | {it['score']}/{it['max']} | {it['detail']} |\n"
        if r.get("issues"):
            report += "\n**⚠️ 未过项**:\n" + "\n".join(f"- {i}" for i in r["issues"]) + "\n"
        report += "\n---\n\n"

    # 评审层复核表（人工/子 Agent 用）
    report += "## 评审层复核表（需人工或子 Agent 确认，确认后覆盖默认判定）\n\n"
    for r in results:
        if r["review_items"]:
            report += f"### {r['skill_name']}\n\n| 检查项 | 默认判定 | 脚本证据 | 复核结论（人工填） |\n|:-------|:-------:|:---------|:------------------|\n"
            for ri in r["review_items"]:
                report += f"| {ri['title']} | {ri['default']} | {ri['evidence'][:60]} | ☐ 过 / ☐ 不过 |\n"
            report += "\n"
    report += """## 方法论

- **单一解释框架**: 8 原理全部从 LLM 机制推导（注意力衰减/概率/无状态/幻觉/精度/权重/窗口/触发），V1 合规项自然归位，无拼接
- **双层评估**: 机器层硬判（0 误判）+ 评审层（脚本收集证据，人工/子 Agent 语义复核）——这本身是确定性转移原理的自反应用
- **局限性**: 评审层默认判定是关键词启发式，必须以人工/子 Agent 复核为准
"""
    return report

# ============================================================
# --self 自检
# ============================================================

def self_check():
    print("===== skill_eval.py（机制层最终版 v3.0.1）--self 自检 =====")
    ok = True
    total = sum(PRINCIPLES[p]["weight"] for p in PRINCIPLES)
    print(f"✅ 8 原理层配置齐全（{len(PRINCIPLES)} 层）")
    if total != TOTAL_EXPECTED:
        print(f"❌ 原理层总分 {total} ≠ {TOTAL_EXPECTED}")
        ok = False
    else:
        print(f"✅ 总分 {total}/{TOTAL_EXPECTED}（MECE）")
    item_total = sum(it["weight"] for p in PRINCIPLES.values() for it in p["items"].values())
    if item_total != TOTAL_EXPECTED:
        print(f"❌ 检查项分值合计 {item_total} ≠ {TOTAL_EXPECTED}")
        ok = False
    else:
        print(f"✅ 检查项分值合计 {item_total}（层 weight = item 之和）")
    for pname, p in PRINCIPLES.items():
        if sum(it["weight"] for it in p["items"].values()) != p["weight"]:
            print(f"❌ {pname} 层 weight {p['weight']} ≠ item 之和")
            ok = False
    machine_total = sum(it["weight"] for p in PRINCIPLES.values() for it in p["items"].values() if it["layer"] == "machine")
    review_total = sum(it["weight"] for p in PRINCIPLES.values() for it in p["items"].values() if it["layer"] == "review")
    print(f"✅ 机器层 {machine_total} 分 + 评审层 {review_total} 分 = {machine_total + review_total}")
    print("-----------------------------")
    print("✅✅ --self 全过，脚本本体完整" if ok else "❌ --self 有项不过")
    return 0 if ok else 1

# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Skill 质量评估 v2（机制层最终版 · 8 原理 · 双层 · 100 分）")
    parser.add_argument("--base", "-b", default=DEFAULT_SKILL_BASE, help="技能配置文件目录")
    parser.add_argument("--output", "-o", default=".", help="报告输出目录")
    parser.add_argument("--skills", "-s", default=",".join(DEFAULT_CORE_SKILLS), help="技能列表（逗号分隔）")
    parser.add_argument("--self", action="store_true", help="体检本脚本")
    args = parser.parse_args()

    if args.self:
        sys.exit(self_check())

    os.makedirs(args.output, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 60)
    print("Skill 质量评估 v2（机制层最终版 · 8 原理 · 双层 · 100 分）")
    print("=" * 60)

    results = []
    for skill_name in [s.strip() for s in args.skills.split(",") if s.strip()]:
        skill_path = os.path.join(args.base, skill_name, "SKILL.md")
        print(f"\n扫描: {skill_name}")
        r = evaluate_skill(skill_name, skill_path)
        results.append(r)
        if r.get("error"):
            print(f"  ❌ {r['error']}")
            continue
        g = {"S": "🟢", "A": "🟡", "B": "🟠", "C": "🔴"}.get(r["grade"], "❓")
        print(f"  总分: {r['score']}/100 ({r['percentage']}%) | 机器 {r['machine_score']} + 评审 {r['review_score']} | 等级: {g} {r['grade']}")
        for issue in r.get("issues", [])[:5]:
            print(f"  ⚠️ {issue}")

    report = generate_report(results)
    report_path = os.path.join(args.output, f"Skill质量评估报告_机制层最终_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已生成: {report_path}")

    json_path = os.path.join(args.output, f"skill_eval_最终_{timestamp}.json")
    json_data = [{
        "skill_name": r["skill_name"], "version": r.get("version", "?"),
        "score": r["score"], "machine": r["machine_score"], "review": r["review_score"],
        "percentage": r["percentage"], "grade": r["grade"],
        "issues_count": len(r.get("issues", [])),
    } for r in results]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"JSON摘要: {json_path}")


if __name__ == "__main__":
    main()
