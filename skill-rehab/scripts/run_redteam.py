#!/usr/bin/env python3
"""
run_redteam.py — 已知盲区召回检测器（保底闸 A · 确定性 · 不挑人）
=============================================================
独立于主评估器（skill_eval.py），用模式规则扫描目标 skill 的已知盲区，
弥补「评估器 + LLM 主 agent 可能漏看的文档一致性 / 硬编码类缺陷」。
与 goldens 互补：goldens 测评估器 rubric 正确性（同源）；本集测已知盲区完整性（独立）。

两种模式:
  run_redteam.py <目标skill目录>      # 扫描真实 skill，输出盲区发现（保底闸，每次诊断必跑）
  run_redteam.py --self               # 对 tests/adversarial/ 夹具回归，断言每个已知盲区被抓（验证检测器本身）

退出码:
  真实扫描: 0（报告型，不阻塞；但输出 P0 发现供主 agent 纳入诊断，不得忽略）
  --self:    0 = 所有夹具均被对应检测器抓出；1 = 有夹具漏抓（检测器退化，须修）

已知盲区检测器（取自 v1.8.5 真实 bug + 皮叔审计，均为低误报模式）:
  HARDCODED_PATH       包内 .md 含真实硬编码绝对路径（≥2 段，/Users/zankus/WorkBuddy 才抓；/Users/xxx 占位示例不抓）
  GATE_CONTRADICTION  同文档同时出现「四闸门」与「五闸门」（计数矛盾）
  CWD_CONFLICT         诊断命令同时含相对 scripts/ 调用 + --output output/（cwd 互斥）
  ABSOLUTE_OUTPUT_PATH --output 后跟绝对路径（违反死规矩5 + v1.8.3 修复）
  GREP_DIALECT         测试/脚本依赖 GNU BRE 的 \\|（无 -E），BSD/GNU/toybox/busybox 方言不一致（2026-09-01 三方实测：toybox 不认 \\| → 测试假红假绿）
"""
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADVERSARIAL_DIR = os.path.join(SCRIPT_DIR, "..", "tests", "adversarial")
# 排除故意写烂的夹具 / 快照 / VCS 目录，避免扫到预期内的破损样本
EXCLUDE_DIRS = {"tests", ".snapshots", ".git"}

SEVERITY = {
    "HARDCODED_PATH": "P0",
    "ABSOLUTE_OUTPUT_PATH": "P0",
    "GATE_CONTRADICTION": "P1",
    "CWD_CONFLICT": "P1",
    "GREP_DIALECT": "P1",
}

# unix 绝对路径须 ≥2 段真实路径（/Users/zankus/WorkBuddy 才抓；/Users/xxx 占位示例不抓，避免命中禁令本身的举例文字）
ABS_PATH_RE = re.compile(
    r"(/Users/[A-Za-z0-9_.]+/[A-Za-z0-9_.]+"
    r"|/home/[A-Za-z0-9_.]+/[A-Za-z0-9_.]+"
    r"|/root/[A-Za-z0-9_.]+/[A-Za-z0-9_.]+"
    r"|[A-Z]:\\\\)"
)
GATE_4_RE = re.compile(r"四闸门")
GATE_5_RE = re.compile(r"五闸门")
REL_SCRIPT_RE = re.compile(r"scripts/\w+\.py")
OUTPUT_REL_RE = re.compile(r"--output\s+\S*output/")
OUTPUT_ABS_RE = re.compile(r"--output\s+(/|\w:\\|~/)")
# grep 无 -E/-e 且引号内带 \| → 依赖 GNU BRE 方言（BSD/toybox/busybox 行为不一致）
GREP_PIPE_RE = re.compile(r"grep\s+(?!-E\b|-e\b)[^\"'\n]*[\"'][^\"']*\\\|")


def scan_target(target_dir: str) -> list:
    """扫描目标 skill 目录，返回命中列表 [(check_id, path, line, detail)]。"""
    findings = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            if not fn.endswith((".md", ".sh")):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                continue
            # HARDCODED_PATH
            for m in ABS_PATH_RE.finditer(text):
                ln = text.count("\n", 0, m.start()) + 1
                findings.append(("HARDCODED_PATH", fp, ln, m.group(0)))
                break
            # GATE_CONTRADICTION
            if GATE_4_RE.search(text) and GATE_5_RE.search(text):
                findings.append(("GATE_CONTRADICTION", fp, 0, "同文档既含「四闸门」又含「五闸门」"))
            # CWD_CONFLICT
            if REL_SCRIPT_RE.search(text) and OUTPUT_REL_RE.search(text):
                findings.append(("CWD_CONFLICT", fp, 0, "相对 scripts/ 调用 与 --output output/ 同现（cwd 互斥）"))
            # ABSOLUTE_OUTPUT_PATH
            for m in OUTPUT_ABS_RE.finditer(text):
                ln = text.count("\n", 0, m.start()) + 1
                findings.append(("ABSOLUTE_OUTPUT_PATH", fp, ln, m.group(0).strip()))
                break
            # GREP_DIALECT（grep 无 -E 却用 \|）
            for m in GREP_PIPE_RE.finditer(text):
                ln = text.count("\n", 0, m.start()) + 1
                findings.append(("GREP_DIALECT", fp, ln, m.group(0).strip()[:60]))
                break
    return findings


def triggered_ids(findings: list) -> set:
    return {f[0] for f in findings}


def run_self() -> int:
    """对 tests/adversarial/ 夹具回归：每个夹具的 redteam-expect.txt 必须被抓出。"""
    adv = os.path.normpath(ADVERSARIAL_DIR)
    if not os.path.isdir(adv):
        print(f"✗ 找不到夹具目录: {adv}", file=sys.stderr)
        return 1
    failures = []
    fixtures = sorted(d for d in os.listdir(adv) if os.path.isdir(os.path.join(adv, d)))
    print(f"=== redteam 夹具回归（{len(fixtures)} 个）===")
    for fx in fixtures:
        fdir = os.path.join(adv, fx)
        exp_path = os.path.join(fdir, "redteam-expect.txt")
        if not os.path.isfile(exp_path):
            print(f"  ⚠️ {fx}: 缺 redteam-expect.txt，跳过")
            continue
        with open(exp_path, encoding="utf-8") as f:
            expected = {l.strip() for l in f if l.strip()}
        got = triggered_ids(scan_target(fdir))
        missing = expected - got
        if missing:
            failures.append((fx, missing))
            print(f"  ❌ {fx}: 期望 {sorted(expected)} 漏抓 {sorted(missing)}")
        else:
            print(f"  ✅ {fx}: 期望 {sorted(expected)} 全抓出")
    if failures:
        print(f"\n✗ redteam 检测器退化：{len(failures)} 个夹具漏抓，须修 run_redteam.py")
        return 1
    print(f"\n✓ redteam 检测器完好：{len(fixtures)} 夹具全抓出（已知盲区召回 100%）")
    return 0


def run_real(target_dir: str) -> int:
    if not os.path.isdir(target_dir):
        print(f"✗ 目标目录不存在: {target_dir}", file=sys.stderr)
        return 2
    findings = scan_target(target_dir)
    p0 = [f for f in findings if SEVERITY.get(f[0]) == "P0"]
    print(f"=== 盲区召回扫描：{target_dir} ===")
    if not findings:
        print("✅ 未触发已知盲区模式")
        return 0
    for cid, path, line, detail in findings:
        loc = f"{path}:{line}" if line else path
        print(f"  [{SEVERITY.get(cid, 'P2')}] {cid} @ {loc} — {detail}")
    if p0:
        print(f"\n⚠️ 发现 {len(p0)} 个 P0 级已知盲区，主 agent 须纳入诊断、不得忽略（保底闸）")
    else:
        print(f"\nℹ️ 发现 {len(findings)} 个 P1 级已知盲区，建议纳入诊断")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "--self":
        return run_self()
    if args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args[0] == "--json":
        target = args[1] if len(args) > 1 else "."
        findings = scan_target(target)
        import json
        print(json.dumps(
            [{"id": c, "severity": SEVERITY.get(c, "P2"), "path": p, "line": l, "detail": d}
             for c, p, l, d in findings], ensure_ascii=False, indent=2))
        return 0
    return run_real(args[0])


if __name__ == "__main__":
    sys.exit(main())
