#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acceptance_check.py — baton 可机器化验收一键跑（SKILL.md §可机器化验收 的脚本化闭环）。

声明节纪律：「未跑上述命令不得声称已验证」——本脚本把各命令顺序跑一遍并汇总退出码，
让「验收过」是一个可执行判定，而不是 AI 口头自证。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (名称, 命令, 输出期望子串[None=只看退出码])
CHECKS = [
    ("落盘/脱敏/state 自检", [PY, str(ROOT / "scripts" / "handoff.py"), "--selftest"], "自检全通"),
    ("客观体量代理可用", [PY, str(ROOT / "scripts" / "baton_tick.py"), "--detect-provider", "."], None),
    ("送达对账守卫六案", [PY, str(ROOT / "hooks" / "baton_delivery_guard.py"), "--self-test"], "6/6"),
    ("源同步守卫八案", [PY, str(ROOT / "hooks" / "source_sync_guard.py"), "--self-test"], "8/8"),
    ("安装器 dry-run 预览", [PY, str(ROOT / "hooks" / "install_reminder.py"), "--dry-run", "--quiet"], None),
    ("完整性自检（无外部锚点时应声明未验证）", [PY, str(ROOT / "hooks" / "baton_reminder.py"), "--selfcheck"], None),
]


def main() -> int:
    fails = 0
    for name, cmd, expect in CHECKS:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            out = (r.stdout or "") + (r.stderr or "")
            ok = r.returncode == 0 and (expect is None or expect in out)
        except (OSError, subprocess.SubprocessError) as exc:
            out = str(exc)
            r, ok = None, False
        print("%s %s%s" % ("✅" if ok else "❌", name,
                           "" if ok else " → rc=%s out=%s" % (getattr(r, "returncode", "ERR"), out[:80])))
        fails += 0 if ok else 1
    print("acceptance: %d/%d 通过" % (len(CHECKS) - fails, len(CHECKS)))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
