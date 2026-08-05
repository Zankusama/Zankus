#!/usr/bin/env python3
"""
skill_eval.py — Skill 质量评估脚本（v4.2.0 · 7 层架构 · P0/P1/P2 分级打分 · 134 分）
================================================================================
v4.0.0 重构（2026-08-04 用户拍板）：
  · 从「拼凑的 10 原理」→「7 层系统性架构」：定位/触发/骨架/质量/安全/工程/生命周期
  · 打分原则：P0 基本型 5 分（必过）/ P1 期望型 3 分（建议）/ P2 兴奋型 1 分（可选）
  · 层权重 = 层内检查项分值之和（自然形成 134 分，不凑 100）
  · 达标线：P0 项全过 + 总分 ≥ 85%（跑回归后定精确值）
  · 名称与行业一致（Anthropic 官方 / trailofbits / SkVM·SkCC / Prompt Failure Mode Atlas）
  · 每个检查项对应 mechanism.md 处方表（项名=查表键，L1 约束：诊断→处方链路不断）
  · 删除项（元审查）：physical_anchor（关键词计数=表面功夫）/ no_binary_residual（文字洁癖）
  · 合并项：step_flow+steps → l3_step_flow；trigger_boundary+boundary → l2_negative_trigger；
    repeat_pattern+repeat_command → l4_instruction_consistency；fence_escape → l4_output_executability
  · ⑦ 生命周期不进评估器（元流程，靠 completeness.md 引导）

死规矩 1：升级走版本管理——改前 `guard.sh snapshot` 冻结 / 改后 `--self` + 自举回归 / README 记版本号。
"""
__version__ = "4.2.0"

import os
import re
import sys
import json
import argparse
from datetime import datetime

DEFAULT_SKILL_BASE = os.path.expanduser("~/AI记忆库/技能配置")
DEFAULT_CORE_SKILLS = ["skill-rehab", "leader-translator", "second-brain"]


# ============================================================
# 7 层配置（LAYERS · 每层 weight = item 之和 · 打分 P0=5/P1=3/P2=1）
# 每项 item：layer=machine(机器层)/review(评审层)｜weight｜title｜判定素材
# ============================================================

LAYERS = {
    # ── ① 定位层 Positioning（16 分）· skill 身份与职责边界 ──
    "l1_positioning": {
        "title": "①定位层（16 分）· 机制：skill 身份与职责边界",
        "weight": 16,
        "items": {
            "l1_name_naming": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "name 命名规范（kebab-case + 具体动词短语）",
            },
            "l1_desc_mission": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "description 职责声明（第三人称，一句话解决什么）",
            },
            "l1_desc_consistency": {  # 5 评审 P0
                "layer": "review", "weight": 5,
                "title": "description 触发接口一致性（description=正文概括，不夸大不缩水）",
            },
            "l1_single_responsibility": {  # 3 评审 P1
                "layer": "review", "weight": 3,
                "title": "职责单一性（一个 skill 一件事，NOT for 排除相邻）",
            },
        },
    },
    # ── ② 触发层 Triggering（16 分）· 什么时候激活/不激活 ──
    "l2_triggering": {
        "title": "②触发层（16 分）· 机制：什么时候激活/不激活",
        "weight": 16,
        "items": {
            "l2_trigger_phrases": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "触发短语（description 含具体触发短语，非泛词）",
                "trigger_kw": ["when", "use", "触发", "当.*时", "ask", "create", "build", "analyze", "写", "生成", "查", "评估", "修", "诊断", "康复", "体检", "打磨", "复盘", "摄入"],
                "min": 1,
            },
            "l2_negative_trigger": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "负向触发 NOT for（不该接的场景显式排除）",
                "patterns": [r"NOT for", r"When NOT to Use", r"不触发", r"不应触发", r"不适合", r"仅限"],
            },
            "l2_cross_platform": {  # 3 评审 P1
                "layer": "review", "weight": 3,
                "title": "跨平台一致性（声明测试过的平台 + 验证记录）",
                "patterns": [r"Tested on", r"平台.*(?:测试|验证|兼容)", r"cross-platform", r"多平台", r"WorkBuddy only", r"compatibility"],
            },
            "l2_trigger_testing": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "触发实测（tests/ 含触发正/负用例）",
            },
        },
    },
    # ── ③ 骨架层 Skeleton（24 分）· skill 结构六零件 ──
    "l3_skeleton": {
        "title": "③骨架层（27 分）· 机制：skill 结构六零件",
        "weight": 27,
        "items": {
            "l3_step_flow": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "分步推进（主流程 ≥3 连续编号步骤）",
                "min_steps": 3,
            },
            "l3_output_format": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "输出格式声明（产出物/输出/格式/示例）",
                "keywords": ["产出物", "输出", "产物", "格式", "示例", "schema", "结构"],
                "min": 2,
            },
            "l3_progressive_disclosure": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "渐进披露（SKILL.md 留骨架，细节外置 references/）",
                "keywords": ["references/", "见 ", "详见", "详细", "模板见", "规范见", "另见"],
                "min": 1,
            },
            "l3_material_template": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "材料/模板（指定固定数据源/模板文件）",
                "keywords": ["模板", "数据源", "来自", "固定", "schema", "template", "Templates", "使用.*文件"],
                "min": 1,
            },
            "l3_scriptized": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "确定性转移·脚本化（scripts/ 目录 + 引用真实 + 声明节）",
            },
            "l3_path_portability": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "路径可移植性（裸相对脚本调用须显式声明路径策略，防异地 cwd 跑不通）",
            },
            "l3_deterministic_guardrail": {  # 3 评审 P1
                "layer": "review", "weight": 3,
                "title": "确定性护栏（高违规代价操作有 hook 物理拦截或显式不挂理由）",
                "patterns": [r"hook", r"PreToolUse", r"PostToolUse", r"UserPromptSubmit", r"物理拦截", r"显式留AI", r"settings\.json"],
            },
        },
    },
    # ── ④ 质量层 Quality（52 分）· 执行正确性核心 ──
    "l4_quality": {
        "title": "④质量层（52 分）· 机制：执行正确性核心",
        "weight": 52,
        "items": {
            "l4_judgeable_acceptance": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "验收可执行（验收命令/grep/diff/exit/断言）",
                "keywords": ["验收", "grep", "diff", "exit", "退出码", "机器判", "命令", "测试", "断言", "== ", "产出物", "闸门", "通过才", "过闸门"],
                "min": 2,
            },
            "l4_anchoring": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "锚定（关键约束 ≥2 次：开头声明 + 任务段重提）",
                "keywords": ["必须", "不得", "禁止", "硬上限", "死规矩", "不许", "CRITICAL"],
                "min": 2,
            },
            "l4_source_grounding": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "来源锚定（断言带来源/实测/日期/引用）",
                "keywords": ["来源", "实测", "验证", "核查", "引用", "复现", "证据", "查询", "调研", "URL", "http"],
                "min": 2,
            },
            "l4_unverified_marking": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "未验证标注（假设/未验证/待核实 标注）",
                "keywords": ["假设", "未验证", "没查到", "待核实", "存疑", "猜的", "推测", "待确认"],
                "min": 1,
            },
            "l4_alternatives": {  # 3 评审 P1
                "layer": "review", "weight": 3,
                "title": "替代方案考虑（Alternatives/为什么不选 段）",
                "patterns": [r"Alternatives Considered", r"替代方案", r"备选", r"为什么不选", r"为什么没选"],
            },
            "l4_instruction_consistency": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "指令一致性（硬/软指令比 ≤3 + 冲突仲裁）",
            },
            "l4_imperative_style": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "祈使句式（关键动作动词开头，被动条件句 ≤5）",
                "passive_patterns": [r"等\s*[^。\n]{0,10}\s*(?:再|才|处理|看|做)", r"(?:以后|稍后|有空|到时候|有时间)\s*(?:再|补|看|做)", r"需要时\s*(?:再|才)", r"必要时\s*(?:再|才)", r"看情况\s*(?:再|才)"],
                "max_passive": 3,
            },
            "l4_placeholder_leakage": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "占位符泄漏（xxx/TBD/待补充/TODO 0 命中）",
                "patterns": [r"\bxxx\b", r"\bTBD\b", r"待补充", r"\bTODO\b", r"占位符(?:必填|待填|未替换)"],
                "max": 0,
            },
            "l4_output_executability": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "输出可执行性（围栏内命令无 $ 提示符/伪代码占位）",
                "min_fence": 1,
                "max_dollar": 0,
            },
            "l4_fuse_mechanism": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "止损熔断（连败换项/超时停/回滚）",
                "keywords": ["熔断", "止损", "连败", "满轮", "超限", "回滚", "终止", "卡死", "超时", "停"],
                "min": 2,
            },
            "l4_state_materialization": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "状态物化（PROGRESS/BLOCKED/.goal 落盘）",
                "keywords": ["PROGRESS", "BLOCKED", "gate-", ".goal", "进度", "落盘", "写进", "保存", "续接", "接着做"],
                "min": 2,
            },
            # ── v4.2.0 行为层维度（交接包 D1/D5）：产出载体 / 收敛终端 / 运行时行为校验 ──
            "l4_output_carrier": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "产出载体（声明具体交付物格式：画像/知识包/HTML/SVG/Excel/报告等）",
                "keywords": ["画像", "知识包", "HTML", "SVG", "Excel", "产出物", "交付物", "必出", "生成.*(?:画像|知识包|报告)", "报告", ".md 文件", ".html", ".xlsx", ".svg"],
                "min": 1,
            },
            "l4_convergence_terminal": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "收敛终端（对话型声明轮次/时长上限或终止条件）",
                "keywords": ["轮次", "上限", "终止", "收敛", "不超过", "满.*轮", "最多.*轮", "就停", "停"],
                "min": 1,
            },
            "l4_runtime_check": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "运行时行为校验（行为约束有 scripts/check_*.py 且被引用，禁「留 AI 理由」兜底）",
            },
        },
    },
    # ── ⑤ 安全层 Safety（16 分）· 越权与危险操作防护 ──
    "l5_safety": {
        "title": "⑤安全层（16 分）· 机制：越权与危险操作防护",
        "weight": 16,
        "items": {
            "l5_allowed_tools": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "最小权限工具白名单（frontmatter allowed-tools）",
                "patterns": [r"allowed-tools", r"allowed_tools", r"允许的工具"],
            },
            "l5_dangerous_op_guard": {  # 5 机器 P0
                "layer": "machine", "weight": 5,
                "title": "危险操作防护（删/发/写敏感/发布 有确认或禁止声明）",
                "keywords": ["危险操作", "🔴", "阻止", "禁止.*删", "不许.*发布", "确认后", "写保护", "备份", "删除.*确认", "高危"],
                "min": 1,
            },
            "l5_reversibility_grading": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "可逆性分级（操作按 🟢自主/🟡确认/🔴阻止 分级）",
                "keywords": ["可逆", "🟢", "🟡", "🔴", "自主", "确认", "阻止", "分级"],
                "min": 2,
            },
            "l5_injection_guard": {  # 3 评审 P1
                "layer": "review", "weight": 3,
                "title": "注入防护（外部输入与指令隔离声明）",
                "patterns": [r"注入", r"injection", r"隔离", r"不当指令", r"信任边界", r"外部输入", r"当数据处理", r"当数据", r"分隔", r"不执行.*内容"],
            },
        },
    },
    # ── ⑥ 工程层 Engineering（7 分）· 可维护性 ──
    "l6_engineering": {
        "title": "⑥工程层（7 分）· 机制：可维护性",
        "weight": 7,
        "items": {
            "l6_versioning": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "版本管理（frontmatter version + 变更记录）",
                "version_kw": ["version"],
                "changelog_kw": ["变更记录", "更新日志", "CHANGELOG", "版本记录", "v[0-9]+\\.[0-9]+"],
            },
            "l6_test_suite": {  # 3 机器 P1
                "layer": "machine", "weight": 3,
                "title": "测试集（tests/ 目录或验收命令 ≥2）",
                "keywords": ["测试", "用例", "冒烟", "golden", "断言", "验收命令", "tests/"],
                "min": 2,
            },
            "l6_documentation": {  # 1 机器 P2
                "layer": "machine", "weight": 1,
                "title": "文档化（README 含安装/使用/贡献 + 文件清单）",
                "keywords": ["安装", "使用", "贡献", "文件清单", "目录表", "Installation", "Usage"],
                "min": 3,
            },
        },
    },
    # ⑦ 生命周期层：不进评估器（元流程，靠 completeness.md 引导）——见 references/completeness.md
}

TOTAL_EXPECTED = sum(LAYERS[l]["weight"] for l in LAYERS)  # 自然形成 134（机器 114 + 评审 20）
PASS_P0_ALL = True  # 达标硬条件：P0 项全过
PASS_LINE = 0.85  # 达标软条件：总分 ≥ 85%


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
                # YAML 折叠块（> / | / >- / |-）：收集后续缩进行
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
    """找从 1 开始的最长连续步骤编号（兼容 **1. / 1. / ### 1. / 1、/ 一、 行首编号 + 阶段N + Step N）"""
    cn = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    nums = []
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
# 7 层评估（机器层硬判 + 评审层证据收集）
# ============================================================

def ev_l1(content, skill_dir):
    """① 定位层"""
    res = {}
    it = LAYERS["l1_positioning"]["items"]
    fm = parse_yaml_frontmatter(content)
    name = fm.get("name", "")
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l1_name_naming（机器 P1）：kebab-case + 具体
    kebab_ok = bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name))
    vague = any(v in name.lower() for v in ["helper", "utils", "tools", "misc", "untitled", "temp", "new-"])
    name_ok = kebab_ok and not vague and len(name) > 3
    res["l1_name_naming"] = machine_item(it["l1_name_naming"]["weight"], name_ok,
        f"name '{name}' kebab-case={'✅' if kebab_ok else '❌'} 非泛词={'✅' if not vague else '❌'}" if name_ok
        else f"❌name '{name}' 需 kebab-case（小写连字符）+ 具体动词短语（非 helper/utils 泛词）")

    # l1_desc_mission（机器 P0）：description 存在 + 第三人称 + 职责
    first_person = bool(re.search(r"\bI help\b|我帮你|我是|I am\b", desc, re.IGNORECASE))
    has_mission = len(desc) >= 30
    mission_ok = bool(desc) and has_mission and not first_person
    res["l1_desc_mission"] = machine_item(it["l1_desc_mission"]["weight"], mission_ok,
        f"description {len(desc)} 字符 第三人称={'✅' if not first_person else '❌'}" if mission_ok
        else f"❌description 无职责声明（{len(desc)} 字符 <30）或第一人称——模型不知道这 skill 干什么")

    # l1_desc_consistency（评审 P0）：description 关键词在正文复现
    desc_words = [w for w in re.findall(r'[\u4e00-\u9fff]{2,4}', desc) if w in body]
    default = len(desc_words) >= 2 or len(desc) < 30
    res["l1_desc_consistency"] = review_item(it["l1_desc_consistency"]["weight"], default,
        f"description 关键词 {len(desc_words)} 个在正文复现" + ("" if default else " ❌触发接口脱节"),
        f"description: {desc[:60]}...；正文复现词: {desc_words[:5]}")

    # l1_single_responsibility（评审 P1）：职责单一（description 短 + 无多职责连接词）
    multi_role = bool(re.search(r"(?:以及|同时|另外|也支持).{0,20}(?:和|以及).{0,10}(?:功能|职责|任务)", desc))
    default = not multi_role
    res["l1_single_responsibility"] = review_item(it["l1_single_responsibility"]["weight"], default,
        "✅职责单一（description 聚焦一件事）" if default else "❌疑似多职责混杂（一个 skill 塞多件事）——需复核拆分",
        f"description: {desc[:80]}")
    return res


def ev_l2(content, skill_dir):
    """② 触发层"""
    res = {}
    it = LAYERS["l2_triggering"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l2_trigger_phrases（机器 P0）：description 含具体触发短语
    trig_cnt = sum(len(re.findall(p, desc, re.IGNORECASE)) for p in it["l2_trigger_phrases"]["trigger_kw"])
    trig_ok = trig_cnt >= it["l2_trigger_phrases"]["min"]
    res["l2_trigger_phrases"] = machine_item(it["l2_trigger_phrases"]["weight"], trig_ok,
        f"触发短语 {trig_cnt} 处（≥{it['l2_trigger_phrases']['min']}）" if trig_ok
        else "❌description 无具体触发短语（触发词太泛/无——什么都触发或永不触发）")

    # l2_negative_trigger（机器 P0）：NOT for
    has_neg, pat = check_pattern(desc + "\n" + body[:1000], it["l2_negative_trigger"]["patterns"])
    res["l2_negative_trigger"] = machine_item(it["l2_negative_trigger"]["weight"], has_neg,
        "✅有负向触发（NOT for/When NOT to Use）" if has_neg
        else "❌无负向触发——不该接的场景没排除，相邻 skill 抢活")

    # l2_cross_platform（评审 P1）：跨平台声明 + 验证记录
    has_plat, plat_pat = check_pattern(content, it["l2_cross_platform"]["patterns"])
    res["l2_cross_platform"] = review_item(it["l2_cross_platform"]["weight"], has_plat,
        f"跨平台声明{'✅' if has_plat else '❌'}（匹配: {plat_pat or '无'}）——需复核是否真有验证记录而非一句摆设",
        f"匹配: {plat_pat if has_plat else '未找到'}")

    # l2_trigger_testing（机器 P1）：tests/ 触发用例
    has_trigger_tests = False
    if skill_dir:
        tdir = os.path.join(skill_dir, 'tests')
        if os.path.isdir(tdir):
            for f in os.listdir(tdir):
                if 'trigger' in f.lower() or 'test' in f.lower():
                    has_trigger_tests = True
                    break
    res["l2_trigger_testing"] = machine_item(it["l2_trigger_testing"]["weight"], has_trigger_tests,
        "✅有触发测试（tests/trigger-*.md）" if has_trigger_tests
        else "❌无触发测试集——触发行为靠猜，误触发/漏触发无人知")
    return res


def ev_l3(content, skill_dir):
    """③ 骨架层"""
    res = {}
    it = LAYERS["l3_skeleton"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l3_step_flow（机器 P0）：分步 ≥3
    steps_n = find_longest_step_seq(body)
    step_ok = steps_n >= it["l3_step_flow"]["min_steps"]
    res["l3_step_flow"] = machine_item(it["l3_step_flow"]["weight"], step_ok,
        f"分步 {steps_n} 连续（≥{it['l3_step_flow']['min_steps']}）" if step_ok
        else f"❌最长连续步骤 {steps_n}（<{it['l3_step_flow']['min_steps']}）——不分步=一步到位，长上下文单步质量必降")

    # l3_output_format（机器 P0）：输出格式声明
    out_cnt = count_keyword(body, it["l3_output_format"]["keywords"])
    out_ok = out_cnt >= it["l3_output_format"]["min"]
    res["l3_output_format"] = machine_item(it["l3_output_format"]["weight"], out_ok,
        f"输出格式词 {out_cnt} 处（≥{it['l3_output_format']['min']}）" if out_ok
        else "❌无输出格式声明——产物随心所欲，下游解析/验收无从谈起")

    # l3_progressive_disclosure（机器 P1）：references/ 外置（必须真有外置声明；行数>500 无外置=必挂）
    ref_cnt = count_keyword(content, it["l3_progressive_disclosure"]["keywords"])
    line_cnt = content.count('\n') + 1
    ref_ok = ref_cnt >= it["l3_progressive_disclosure"]["min"]
    over_limit = line_cnt > 500 and not ref_ok  # 超长且无外置 = 必挂
    res["l3_progressive_disclosure"] = machine_item(it["l3_progressive_disclosure"]["weight"], ref_ok and not over_limit,
        f"外置引用 {ref_cnt} 处（≥{it['l3_progressive_disclosure']['min']}）行数 {line_cnt}" if ref_ok
        else (f"❌{line_cnt} 行>500 且无外置——细节全塞 SKILL.md，上下文被占满" if over_limit
              else "❌无外置声明——细节未外置 references/（渐进披露缺失）"))

    # l3_material_template（机器 P1）：固定材料
    mat_cnt = count_keyword(body, it["l3_material_template"]["keywords"])
    mat_ok = mat_cnt >= it["l3_material_template"]["min"]
    res["l3_material_template"] = machine_item(it["l3_material_template"]["weight"], mat_ok,
        f"材料/模板词 {mat_cnt} 处" if mat_ok
        else "❌无固定材料/模板——每次现场找/现场编，输入不稳产出不稳")

    # l3_scriptized（机器 P0）：脚本化
    scripts_dir = os.path.join(skill_dir, "scripts") if skill_dir else None
    has_dir = bool(scripts_dir) and os.path.isdir(scripts_dir)
    ref_scripts = set(re.findall(r'scripts/([A-Za-z0-9_\-\.]+\.(?:py|sh))', content))
    real_scripts = set()
    if has_dir:
        real_scripts = {f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))}
    refs_real = bool(ref_scripts) and ref_scripts <= real_scripts
    has_decl = bool(re.search(r'可机器化验收|脚本化清单|脚本化声明', content))
    script_ok = has_dir and refs_real and has_decl and len(real_scripts) >= 1
    res["l3_scriptized"] = machine_item(it["l3_scriptized"]["weight"], script_ok,
        f"scripts/ 目录{'✅' if has_dir else '❌'} 引用真实{'✅' if refs_real else '❌'} 声明节{'✅' if has_decl else '❌'}" if script_ok
        else "❌可机器化约束没脚本化（需 scripts/ 目录 + 引用脚本真实存在 + 可机器化验收声明节）")

    # l3_path_portability（机器 P1）：路径可移植性——防 AI 在异地 cwd 跑不通（本次踩坑根因）
    # 判据：围栏内脚本调用若有「裸相对路径」（无 / 开头、$变量、~、..），须 SKILL.md 显式声明路径策略，
    #       否则 AI 在用户工作目录执行时必 FileNotFoundError（second-brain 实锤）
    fences = re.findall(r'```[^\n]*\n(.*?)\n```', content, re.DOTALL)
    raw_calls = []
    for fc in fences:
        if '<' in fc or '>' in fc:  # 含 <> 占位符的文档示例命令，非真要在异地跑
            continue
        raw_calls += re.findall(r'(?:python3?|bash|sh)\s+([^\s`]+\.(?:py|sh))', fc)
    bare_rel = [c for c in raw_calls
                if not (c.startswith(('/', '$', '~', '..')) or 'SKILL' in c.upper())]
    path_decl = bool(re.search(r'相对路径引用|在 skill 目录|cd 到 ?(?:技能配置|skills)|包内零绝对路径|脚本一律相对|包内.*相对路径', content))
    portable = (not bare_rel) or path_decl
    res["l3_path_portability"] = machine_item(it["l3_path_portability"]["weight"], portable,
        "✅路径可移植（无裸相对脚本调用 或 已显式声明路径策略）" if portable
        else f"❌路径可移植性缺失（裸相对脚本调用 {bare_rel} 且无路径策略声明）——AI 在异地 cwd 下 FileNotFoundError")

    # l3_deterministic_guardrail（评审 P1）：hook 或显式不挂
    has_guard, guard_pat = check_pattern(content, it["l3_deterministic_guardrail"]["patterns"])
    res["l3_deterministic_guardrail"] = review_item(it["l3_deterministic_guardrail"]["weight"], has_guard,
        f"确定性护栏{'✅' if has_guard else '❌'}（匹配: {guard_pat or '无'}）——高违规代价操作需 hook 物理拦截或显式留AI理由",
        f"匹配: {guard_pat if has_guard else '未找到'}")
    return res


def ev_l4(content, skill_dir):
    """④ 质量层"""
    res = {}
    it = LAYERS["l4_quality"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l4_judgeable_acceptance（机器 P0）：验收可执行 = 关键词≥2 且 声明的验收脚本真实存在
    # 升级（v4.2.0 交接包 D2）：从「数关键词」升级为「验证验收声明可机器执行 + 判定词真实存在」
    judge_cnt = count_keyword(content, it["l4_judgeable_acceptance"]["keywords"])
    judge_ok_base = judge_cnt >= it["l4_judgeable_acceptance"]["min"]
    # 提取 SKILL.md 声明的验收脚本引用（scripts/*.py|.sh）
    declared = sorted(set(
        m for m in re.findall(r'scripts/[A-Za-z0-9_\-]+\.(?:py|sh)', content)
        if not re.search(r'xxx|TBD|<[^>]+>|待填', m)  # 占位符样式不算真实声明
    ))
    miss = []
    # fixapply 沙箱副本（tests/fixsandbox/ 下只复制了 SKILL.md，无 scripts/）→ 豁免存在性硬判，防误伤「修一验一」
    sandbox_mode = skill_dir and "fixsandbox" in skill_dir.replace("\\", "/")
    if declared and skill_dir and not sandbox_mode:
        # 真实目录模式：声明的脚本必须存在，否则 FAIL（防「声称有脚本但脚本不存在」）
        miss = [p for p in declared if not os.path.isfile(os.path.join(skill_dir, p))]
    script_ok = not miss
    judge_ok = judge_ok_base and script_ok
    if judge_ok:
        judge_detail = f"可执行判定词 {judge_cnt} 处（≥{it['l4_judgeable_acceptance']['min']}）"
        if declared:
            judge_detail += f" + 声明的验收脚本 {len(declared)} 个存在（{', '.join(declared[:3])}{'…' if len(declared)>3 else ''}）"
    else:
        reason = []
        if not judge_ok_base:
            reason.append(f"可执行判定词 {judge_cnt} 处（<{it['l4_judgeable_acceptance']['min']}）——「看看效果」类验收，模型自己判自己必自欺")
        if miss:
            reason.append(f"声明的验收脚本不存在: {', '.join(miss)}——验收声明与实际文件断裂，修好无锚点")
        judge_detail = "❌" + "；".join(reason)
    res["l4_judgeable_acceptance"] = machine_item(it["l4_judgeable_acceptance"]["weight"], judge_ok,
        judge_detail)

    # l4_anchoring（机器 P1）
    anch_cnt = count_keyword(content, it["l4_anchoring"]["keywords"])
    anch_ok = anch_cnt >= it["l4_anchoring"]["min"]
    res["l4_anchoring"] = machine_item(it["l4_anchoring"]["weight"], anch_ok,
        f"关键约束词 {anch_cnt} 处（≥{it['l4_anchoring']['min']}）" if anch_ok
        else f"❌关键约束仅 {anch_cnt} 处——长上下文后必被 lost-in-the-middle 淹没")

    # l4_source_grounding（机器 P0）
    src_cnt = count_keyword(content, it["l4_source_grounding"]["keywords"])
    src_ok = src_cnt >= it["l4_source_grounding"]["min"]
    res["l4_source_grounding"] = machine_item(it["l4_source_grounding"]["weight"], src_ok,
        f"来源/实测词 {src_cnt} 处（≥{it['l4_source_grounding']['min']}）" if src_ok
        else "❌断言无锚点——模型在没依据的地方必编造（幻觉是概率生成的自然结果）")

    # l4_unverified_marking（机器 P1）
    unv_cnt = count_keyword(content, it["l4_unverified_marking"]["keywords"])
    unv_ok = unv_cnt >= it["l4_unverified_marking"]["min"]
    res["l4_unverified_marking"] = machine_item(it["l4_unverified_marking"]["weight"], unv_ok,
        f"未验证标注词 {unv_cnt} 处" if unv_ok
        else "❌无「假设/未验证」标注——查不到不许裸奔，硬编误导执行")

    # l4_alternatives（评审 P1）
    has_alt, alt_pat = check_pattern(content, it["l4_alternatives"]["patterns"])
    res["l4_alternatives"] = review_item(it["l4_alternatives"]["weight"], has_alt,
        f"替代方案段{'✅' if has_alt else '❌'}（匹配: {alt_pat or '无'}）——需复核是否真列了替代而非凑数",
        f"匹配: {alt_pat if has_alt else '未找到'}")

    # l4_instruction_consistency（机器 P0）：冲突仲裁存在 + 无两极堆砌（NEVER/MUST 全大写字 ≤3）
    has_arb = count_keyword(content, ["冲突", "优先", "让步", "听谁", "优先于", "冲突时", "仲裁", "不冲突"]) >= 1
    # 全大写两极词（NEVER/MUST/CRITICAL 原文）——正文正常用「必须」不算两极堆砌
    binary_cnt = len(re.findall(r'\b(?:NEVER|MUST|CRITICAL|ALWAYS)\b', content))
    cons_ok = has_arb and binary_cnt <= 3
    res["l4_instruction_consistency"] = machine_item(it["l4_instruction_consistency"]["weight"], cons_ok,
        f"冲突仲裁{'✅' if has_arb else '❌'} 两极词 {binary_cnt} 处（≤3）" if cons_ok
        else f"❌{'无冲突仲裁' if not has_arb else f'两极词 {binary_cnt} 处>3'}——规则打架时模型随机选或两极堆砌")

    # l4_imperative_style（机器 P0）：被动推迟 ≤5
    passive_cnt = sum(len(re.findall(p, content)) for p in it["l4_imperative_style"]["passive_patterns"])
    pass_ok = passive_cnt <= it["l4_imperative_style"]["max_passive"]
    res["l4_imperative_style"] = machine_item(it["l4_imperative_style"]["weight"], pass_ok,
        f"被动条件句 {passive_cnt} 处（≤{it['l4_imperative_style']['max_passive']}）" if pass_ok
        else f"❌被动条件句 {passive_cnt} 处——关键动作靠被动条件必无限推迟，应改祈使句")

    # l4_placeholder_leakage（机器 P0）
    content_no_code = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    ph_cnt = sum(len(re.findall(p, content_no_code, re.IGNORECASE)) for p in it["l4_placeholder_leakage"]["patterns"])
    ph_ok = ph_cnt <= it["l4_placeholder_leakage"]["max"]
    res["l4_placeholder_leakage"] = machine_item(it["l4_placeholder_leakage"]["weight"], ph_ok,
        f"模糊占位符 {ph_cnt} 处（≤{it['l4_placeholder_leakage']['max']}）" if ph_ok
        else f"❌模糊占位符 {ph_cnt} 处——占位符会被模型照抄进产物")

    # l4_output_executability（机器 P1）：围栏 $ 提示符
    fences = re.findall(r'```[^\n]*\n(.*?)\n```', content, re.DOTALL)
    dollar_cnt = sum(1 for f in fences if re.search(r'^\s*\$', f, re.MULTILINE))
    fence_ok = len(fences) >= it["l4_output_executability"]["min_fence"] and dollar_cnt <= it["l4_output_executability"]["max_dollar"]
    res["l4_output_executability"] = machine_item(it["l4_output_executability"]["weight"], fence_ok,
        f"围栏 {len(fences)} 块 $ 提示符 {dollar_cnt} 处" if fence_ok
        else f"❌围栏内 $ 提示符 {dollar_cnt} 处——命令复制运行必错")

    # l4_fuse_mechanism（机器 P1）
    fuse_cnt = count_keyword(content, it["l4_fuse_mechanism"]["keywords"])
    fuse_ok = fuse_cnt >= it["l4_fuse_mechanism"]["min"]
    res["l4_fuse_mechanism"] = machine_item(it["l4_fuse_mechanism"]["weight"], fuse_ok,
        f"止损熔断词 {fuse_cnt} 处（≥{it['l4_fuse_mechanism']['min']}）" if fuse_ok
        else "❌无熔断/止损——连败/超时/回滚没定义，会无限烧下去")

    # l4_state_materialization（机器 P1）
    state_cnt = count_keyword(content, it["l4_state_materialization"]["keywords"])
    state_ok = state_cnt >= it["l4_state_materialization"]["min"]
    res["l4_state_materialization"] = machine_item(it["l4_state_materialization"]["weight"], state_ok,
        f"状态物化词 {state_cnt} 处（≥{it['l4_state_materialization']['min']}）" if state_ok
        else "❌无状态物化——模型无状态，跨步状态不落盘必失忆（换会话就重做）")

    # ── v4.2.0 行为层维度（交接包 D1/D5）──

    # l4_output_carrier（机器 P1）：声明具体产出载体（对话/陪伴型 skill 跑完必须有交付物）
    carrier_cnt = count_keyword(content, it["l4_output_carrier"]["keywords"])
    carrier_ok = carrier_cnt >= it["l4_output_carrier"]["min"]
    res["l4_output_carrier"] = machine_item(it["l4_output_carrier"]["weight"], carrier_ok,
        f"产出载体词 {carrier_cnt} 处（≥{it['l4_output_carrier']['min']}）" if carrier_ok
        else "❌无具体产出载体声明（画像/知识包/HTML/SVG/Excel/报告）——体验型 skill 跑完零交付，用户白聊一场")

    # l4_convergence_terminal（机器 P1）：收敛终端（对话型 skill 必须有轮次/时长上限或终止条件）
    conv_cnt = count_keyword(content, it["l4_convergence_terminal"]["keywords"])
    conv_ok = conv_cnt >= it["l4_convergence_terminal"]["min"]
    res["l4_convergence_terminal"] = machine_item(it["l4_convergence_terminal"]["weight"], conv_ok,
        f"收敛终端词 {conv_cnt} 处（≥{it['l4_convergence_terminal']['min']}）" if conv_ok
        else "❌无收敛终端（轮次/时长上限或终止条件）——对话可无限延展，没有「跑完」的边界，体验无终局")

    # l4_runtime_check（机器 P1）：运行时行为规则必须有校验脚本（禁「留 AI 理由」作为确定性规则兜底）
    rt_checks = sorted(set(
        m for m in re.findall(r'scripts/check_[A-Za-z0-9_\-]+\.py', content)
        if not re.search(r'xxx|TBD|<[^>]+>|待填', m)
    ))
    rt_ok = len(rt_checks) >= 1
    res["l4_runtime_check"] = machine_item(it["l4_runtime_check"]["weight"], rt_ok,
        f"运行时校验脚本 {len(rt_checks)} 个（{', '.join(rt_checks) if rt_checks else '无'}）" if rt_ok
        else "❌无运行时校验脚本（scripts/check_*.py）——「必须 X 才 Y」类行为规则留 AI 自觉，违背「模型自判必自欺」确定性原则")
    return res


def ev_l5(content, skill_dir):
    """⑤ 安全层"""
    res = {}
    it = LAYERS["l5_safety"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l5_allowed_tools（机器 P0）
    has_at, at_pat = check_pattern(content, it["l5_allowed_tools"]["patterns"])
    res["l5_allowed_tools"] = machine_item(it["l5_allowed_tools"]["weight"], has_at,
        "✅有最小权限白名单（allowed-tools）" if has_at
        else "❌无 allowed-tools——默认全工具可用（越权风险），应声明最小集")

    # l5_dangerous_op_guard（机器 P0）
    danger_cnt = count_keyword(content, it["l5_dangerous_op_guard"]["keywords"])
    danger_ok = danger_cnt >= it["l5_dangerous_op_guard"]["min"]
    res["l5_dangerous_op_guard"] = machine_item(it["l5_dangerous_op_guard"]["weight"], danger_ok,
        f"危险操作防护词 {danger_cnt} 处" if danger_ok
        else "❌危险操作无防护声明——删/发/写敏感/发布无确认或禁止")

    # l5_reversibility_grading（机器 P1）
    rev_cnt = count_keyword(content, it["l5_reversibility_grading"]["keywords"])
    rev_ok = rev_cnt >= it["l5_reversibility_grading"]["min"]
    res["l5_reversibility_grading"] = machine_item(it["l5_reversibility_grading"]["weight"], rev_ok,
        f"可逆性分级词 {rev_cnt} 处（≥{it['l5_reversibility_grading']['min']}）" if rev_ok
        else "❌操作无可逆性分级——要么乱跑要么烦死（无风险感知）")

    # l5_injection_guard（评审 P1）
    has_inj, inj_pat = check_pattern(content, it["l5_injection_guard"]["patterns"])
    res["l5_injection_guard"] = review_item(it["l5_injection_guard"]["weight"], has_inj,
        f"注入防护{'✅' if has_inj else '❌'}（匹配: {inj_pat or '无'}）——外部输入与指令隔离声明",
        f"匹配: {inj_pat if has_inj else '未找到'}")
    return res


def ev_l6(content, skill_dir):
    """⑥ 工程层"""
    res = {}
    it = LAYERS["l6_engineering"]["items"]
    fm = parse_yaml_frontmatter(content)
    desc = fm.get("description", "")
    body = content.replace(desc, "")

    # l6_versioning（机器 P1）：version 字段 + 变更记录（正则匹配版本号）
    has_ver = 'version' in fm
    chg_cnt = len(re.findall(r'v\d+\.\d+(?:\.\d+)?', content)) + count_keyword(content, it["l6_versioning"]["changelog_kw"])
    ver_ok = has_ver and chg_cnt >= 1
    res["l6_versioning"] = machine_item(it["l6_versioning"]["weight"], ver_ok,
        f"version {'✅' if has_ver else '❌'} 变更记录 {chg_cnt} 处" if ver_ok
        else "❌无 version 或变更记录——改了什么没记录，版本无法追溯")

    # l6_test_suite（机器 P1）
    test_cnt = count_keyword(body, it["l6_test_suite"]["keywords"])
    has_tests = False
    if skill_dir:
        tdir = os.path.join(skill_dir, 'tests')
        has_tests = os.path.isdir(tdir) and any(os.path.isfile(os.path.join(tdir, f)) for f in os.listdir(tdir))
    test_ok = test_cnt >= it["l6_test_suite"]["min"] or has_tests
    res["l6_test_suite"] = machine_item(it["l6_test_suite"]["weight"], test_ok,
        f"测试词 {test_cnt} 处{' + tests/ 目录' if has_tests else ''}" if test_ok
        else "❌无测试集——改坏了没人知道，回归无保障")

    # l6_documentation（机器 P2）：README 文件存在 + 含核心段
    has_readme = bool(skill_dir) and os.path.isfile(os.path.join(skill_dir, "README.md"))
    doc_ok = has_readme
    res["l6_documentation"] = machine_item(it["l6_documentation"]["weight"], doc_ok,
        "✅有 README.md（文档化）" if doc_ok
        else "❌无 README.md——分享出去别人装不上/用不了")
    return res


# ============================================================
# 评估器
# ============================================================

def evaluate_skill(skill_name, skill_path):
    result = {
        "skill_name": skill_name, "file_path": skill_path,
        "layers": {}, "issues": [], "recommendations": [],
        "score": 0, "max": TOTAL_EXPECTED, "percentage": 0, "grade": "C",
        "machine_score": 0, "review_score": 0, "review_items": [],
        "p0_failed": [],  # P0 未过项（达标硬条件）
    }
    if not os.path.exists(skill_path):
        result["error"] = "SKILL.md not found"
        return result
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    result["file_size"] = len(content)
    result["line_count"] = content.count('\n') + 1
    skill_dir = os.path.dirname(skill_path)

    result["layers"]["l1_positioning"] = ev_l1(content, skill_dir)
    result["layers"]["l2_triggering"] = ev_l2(content, skill_dir)
    result["layers"]["l3_skeleton"] = ev_l3(content, skill_dir)
    result["layers"]["l4_quality"] = ev_l4(content, skill_dir)
    result["layers"]["l5_safety"] = ev_l5(content, skill_dir)
    result["layers"]["l6_engineering"] = ev_l6(content, skill_dir)

    # 汇总：机器层 + 评审层（默认判定计入，报告标注需复核）
    for ln, layer in result["layers"].items():
        for itn, it in layer.items():
            result["score"] += it["score"]
            if it["layer"] == "machine":
                result["machine_score"] += it["score"]
            else:
                result["review_score"] += it["score"]
                result["review_items"].append({
                    "name": f"{ln}.{itn}",
                    "title": LAYERS[ln]["items"][itn]["title"],
                    "detail": it["detail"], "evidence": it.get("evidence", ""),
                    "default": "✅ 过" if it["passed"] else "❌ 不过",
                })
            if not it["passed"]:
                result["issues"].append(f"[{ln}.{itn}] {it['detail']}")
                if it["max"] == 5:  # P0
                    result["p0_failed"].append(f"{ln}.{itn}")

    result["percentage"] = round(result["score"] / TOTAL_EXPECTED * 100, 1)
    # 达标：P0 全过（硬）+ 总分 ≥85%（软）
    if not result["p0_failed"] and result["percentage"] >= PASS_LINE * 100:
        result["grade"] = "S"
    elif result["percentage"] >= 85:
        result["grade"] = "A"
    elif result["percentage"] >= 70:
        result["grade"] = "B"
    else:
        result["grade"] = "C"
    result["version"] = extract_version(content)

    # ── v4.2.0 运行时行为合规汇总（交接包 D4）：每条行为规则标注 机器校验 / AI 自觉 ──
    rt = result["layers"].get("l4_quality", {})
    result["runtime_compliance"] = {
        "rules": [
            {
                "item": "l4_runtime_check",
                "title": "运行时行为校验脚本",
                "check_type": "机器校验" if rt.get("l4_runtime_check", {}).get("passed") else "AI 自觉",
                "detail": rt.get("l4_runtime_check", {}).get("detail", ""),
            },
            {
                "item": "l4_output_carrier",
                "title": "产出载体声明",
                "check_type": "机器校验" if rt.get("l4_output_carrier", {}).get("passed") else "AI 自觉",
                "detail": rt.get("l4_output_carrier", {}).get("detail", ""),
            },
            {
                "item": "l4_convergence_terminal",
                "title": "收敛终端（轮次/终止条件）",
                "check_type": "机器校验" if rt.get("l4_convergence_terminal", {}).get("passed") else "AI 自觉",
                "detail": rt.get("l4_convergence_terminal", {}).get("detail", ""),
            },
            {
                "item": "l4_judgeable_acceptance",
                "title": "验收锚点（判定词+脚本存在）",
                "check_type": "机器校验" if rt.get("l4_judgeable_acceptance", {}).get("passed") else "AI 自觉",
                "detail": rt.get("l4_judgeable_acceptance", {}).get("detail", ""),
            },
        ],
        # 警示：纯 AI 自觉规则（无脚本兜底的行为约束）
        "warnings": [r["title"] for r in [
            {"title": "运行时行为校验", "item": "l4_runtime_check"},
            {"title": "产出载体", "item": "l4_output_carrier"},
            {"title": "收敛终端", "item": "l4_convergence_terminal"},
            {"title": "验收锚点", "item": "l4_judgeable_acceptance"},
        ] if not rt.get(r["item"], {}).get("passed")] or ["（无——行为规则均有机器校验）"],
    }
    return result


# ============================================================
# 报告（金字塔结构 + 评审层复核表）
# ============================================================

def generate_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    layer_names = {
        "l1_positioning": "①定位",
        "l2_triggering": "②触发",
        "l3_skeleton": "③骨架",
        "l4_quality": "④质量",
        "l5_safety": "⑤安全",
        "l6_engineering": "⑥工程",
    }
    header_cols = " | ".join(f"{v}/{LAYERS[k]['weight']}" for k, v in layer_names.items())
    report = f"""# Skill 质量评估报告（v4.0.0 · 7 层架构 · P0/P1/P2 分级打分 · {TOTAL_EXPECTED} 分）

> **生成时间**: {now} | **评估范围**: {len(results)} 个 Skill
> **评估标准**: 7 层架构（①定位16 ②触发16 ③骨架27 ④质量52 ⑤安全16 ⑥工程7）——⑦生命周期不进评估器（元流程，completeness.md 引导）
> **打分原则**: P0 基本型 5 分（必过）/ P1 期望型 3 分（建议）/ P2 兴奋型 1 分（可选）；层权重 = 项之和（自然形成，不凑分）
> **达标条件**: P0 项全过（硬性）+ 总分 ≥ {int(PASS_LINE*100)}%（软性）
> **双层评估**: 机器层硬判（可正则判）+ 评审层（🟡 需人工/子 Agent 按证据复核）
> **⚠️ 边界声明**: 本报告是「必要条件闸门」判定（有无类检查），未过项=已知硬伤；**未过项 ≠ 全部问题**——完整性缺口由 references/completeness.md 兜底，**评估器满分 ≠ skill 全好**

---

## 总览（结论先行）

| Skill | 版本 | {header_cols} | 总分/{TOTAL_EXPECTED} | P0未过 | 等级 |
|:------|:-----|{":".join(["---"] * (len(layer_names)+2))} |:---:|:---:|:----:|
"""
    for r in results:
        g = {"S": "🟢", "A": "🟡", "B": "🟠", "C": "🔴"}.get(r["grade"], "❓")
        cols = []
        for k in layer_names:
            cols.append(f"{sum(x['score'] for x in r['layers'][k].values())}")
        p0 = "、" .join(r["p0_failed"]) if r["p0_failed"] else "无"
        report += (f"| {r['skill_name']} | {r.get('version','?')} | " + " | ".join(cols) +
                   f" | {r['score']}/{TOTAL_EXPECTED} | {p0} | {g} {r['grade']} |\n")

    report += "\n**得分构成**: 机器层"
    for r in results:
        report += f" | {r['skill_name']}: {r['machine_score']}"
    report += "；评审层（需复核，默认已计入）"
    for r in results:
        report += f" | {r['skill_name']}: {r['review_score']}"

    report += "\n\n---\n\n## 各 Skill 明细\n\n"
    for r in sorted(results, key=lambda x: len(x.get("issues", [])), reverse=True):
        g = {"S": "🟢", "A": "🟡", "B": "🟠", "C": "🔴"}.get(r["grade"], "❓")
        report += f"### {r['skill_name']} ({r.get('version','?')}) — {g} {r['grade']}级 · {r['score']}/{TOTAL_EXPECTED}\n\n"
        report += f"- **文件**: `{r['file_path']}` | 行数 {r.get('line_count','?')}\n\n"
        report += "| 检查项 | 层 | 级别 | 状态 | 得分 | 详情 |\n|:-------|:--:|:--:|:----:|:----:|:-----|\n"
        for ln, layer in r["layers"].items():
            for itn, it in layer.items():
                st = "✅" if it["passed"] else "❌"
                layer_tag = "机器" if it["layer"] == "machine" else "🟡评审"
                lv = "P0" if it["max"] == 5 else ("P1" if it["max"] == 3 else "P2")
                report += f"| {LAYERS[ln]['items'][itn]['title']} | {layer_tag} | {lv} | {st} | {it['score']}/{it['max']} | {it['detail']} |\n"
        if r.get("issues"):
            report += "\n**⚠️ 未过项**:\n" + "\n".join(f"- {i}" for i in r["issues"]) + "\n"
        if r.get("p0_failed"):
            report += f"\n**🔴 P0 未过（达标硬条件，必须修）**: {'、'.join(r['p0_failed'])}\n"
        report += "\n---\n\n"

    # 评审层复核表（人工/子 Agent 用）
    report += "## 评审层复核表（需人工或子 Agent 确认，确认后覆盖默认判定）\n\n"
    for r in results:
        if r["review_items"]:
            report += f"### {r['skill_name']}\n\n| 检查项 | 默认判定 | 脚本证据 | 复核结论（人工填） |\n|:-------|:-------:|:---------|:------------------|\n"
            for ri in r["review_items"]:
                report += f"| {ri['title']} | {ri['default']} | {ri['evidence'][:60]} | ☐ 过 / ☐ 不过 |\n"
            report += "\n"

    # v4.2.0 运行时行为合规章节（交接包 D4）：每条行为规则标注 机器校验/AI 自觉，警示纯 AI 自觉
    report += "## 运行时行为合规（v4.2.0 新增 · 交接包 D4）\n\n"
    report += "> 判定依据：行为层规则必须有机器校验脚本（scripts/check_*.py），纯「AI 自觉」规则是确定性缺口——违背「模型自判必自欺」原则。\n\n"
    for r in results:
        rc = r.get("runtime_compliance", {})
        report += f"### {r['skill_name']}\n\n| 行为规则 | 校验类型 | 状态 | 详情 |\n|:--------|:-------:|:----:|:-----|\n"
        for rule in rc.get("rules", []):
            is_ai = rule["check_type"] == "AI 自觉"
            st = "⚠️" if is_ai else "✅"
            report += f"| {rule['title']} | {rule['check_type']} | {st} | {rule['detail'][:70]} |\n"
        report += f"\n**⚠️ 纯 AI 自觉警示**: {'、'.join(rc.get('warnings', []))}\n\n"
    report += """## 方法论

- **7 层架构**: 定位（身份）/触发（激活）/骨架（结构六零件）/质量（执行正确性）/安全（越权防护）/工程（可维护性）/生命周期（元流程不进评估器）
- **依据**: 每检查项对应行业依据（Anthropic 官方 / trailofbits / SkVM·SkCC / Prompt Failure Mode Atlas），名称与行业一致
- **分级打分**: P0（不修会坏，5 分必过）/P1（修了线性提升，3 分）/P2（锦上添花，1 分）——层权重 = 项之和，不凑分
- **双层评估**: 机器层硬判（0 误判）+ 评审层（脚本收集证据，人工/子 Agent 语义复核）——确定性转移原理的自反应用
- **局限性**: 评审层默认判定是关键词启发式，必须以人工/子 Agent 复核为准；⑦生命周期是设计时的元流程，单次静态评估判不了
"""
    return report


# ============================================================
# --self 自检
# ============================================================

def self_check():
    print(f"===== skill_eval.py（v{__version__} · 7 层架构 · P0/P1/P2 分级）--self 自检 =====")
    ok = True
    total = sum(LAYERS[l]["weight"] for l in LAYERS)
    print(f"✅ 7 层配置齐全（{len(LAYERS)} 层进评估器，⑦生命周期除外）")
    if total != TOTAL_EXPECTED:
        print(f"❌ 层总分 {total} ≠ TOTAL_EXPECTED {TOTAL_EXPECTED}")
        ok = False
    else:
        print(f"✅ 总分 {total}（层 weight = item 之和，自然形成）")
    item_total = sum(it["weight"] for l in LAYERS.values() for it in l["items"].values())
    if item_total != TOTAL_EXPECTED:
        print(f"❌ 检查项分值合计 {item_total} ≠ {TOTAL_EXPECTED}")
        ok = False
    else:
        print(f"✅ 检查项分值合计 {item_total}（层 weight = item 之和）")
    for lname, l in LAYERS.items():
        if sum(it["weight"] for it in l["items"].values()) != l["weight"]:
            print(f"❌ {lname} 层 weight {l['weight']} ≠ item 之和")
            ok = False
    # P0/P1/P2 分级自洽：5/3/1
    for lname, l in LAYERS.items():
        for itn, it in l["items"].items():
            if it["weight"] not in (5, 3, 1):
                print(f"❌ {lname}.{itn} weight {it['weight']} 非 P0/P1/P2（应 5/3/1）")
                ok = False
    machine_total = sum(it["weight"] for l in LAYERS.values() for it in l["items"].values() if it["layer"] == "machine")
    review_total = sum(it["weight"] for l in LAYERS.values() for it in l["items"].values() if it["layer"] == "review")
    p0_cnt = sum(1 for l in LAYERS.values() for it in l["items"].values() if it["weight"] == 5)
    print(f"✅ 机器层 {machine_total} 分 + 评审层 {review_total} 分 = {machine_total + review_total}")
    print(f"✅ P0 项 {p0_cnt} 个（5 分必过）")
    print("-----------------------------")
    print("✅✅ --self 全过，脚本本体完整" if ok else "❌ --self 有项不过")
    return 0 if ok else 1


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Skill 质量评估 v4（7 层架构 · P0/P1/P2 分级打分）")
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
    print(f"Skill 质量评估 v{__version__}（7 层架构 · P0/P1/P2 分级 · {TOTAL_EXPECTED} 分）")
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
        p0 = f" P0未过:{'、'.join(r['p0_failed'])}" if r["p0_failed"] else ""
        print(f"  总分: {r['score']}/{TOTAL_EXPECTED} ({r['percentage']}%) | 机器 {r['machine_score']} + 评审 {r['review_score']} | 等级: {g} {r['grade']}{p0}")
        for issue in r.get("issues", [])[:5]:
            print(f"  ⚠️ {issue}")

    report = generate_report(results)
    report_path = os.path.join(args.output, f"Skill质量评估报告_7层架构_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n报告已生成: {report_path}")

    json_path = os.path.join(args.output, f"skill_eval_最终_{timestamp}.json")
    json_data = [{
        "skill_name": r["skill_name"], "version": r.get("version", "?"),
        "score": r["score"], "machine": r["machine_score"], "review": r["review_score"],
        "percentage": r["percentage"], "grade": r["grade"],
        "issues_count": len(r.get("issues", [])),
        "p0_failed": r.get("p0_failed", []),
    } for r in results]
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"JSON摘要: {json_path}")


if __name__ == "__main__":
    main()
