#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_sync_guard.py — v4/S2 存活层兜底：源同步漂移守卫（SessionStart 钩子·只告警不修）。

为什么存在：
  触发层与送达层跑的都是 hooks/ 下的**实件**。历史上这些实件是从技能配置中心
  （技能配置中心 <skill>/hooks|scripts）拷出去的，拷贝一旦落后源，跑的就是旧代码
  —— 前面所有层的修复都对一个没在跑的旧副本生效。S1 已把已知硬拷改成软链，本守卫管的是
  **残余与新复发**：任何"派生自中心但非软链"的件，哈希落后即出声。
  ⛔ mtime 不作判据（实测 touch 未重拷仍会更新 mtime）→ 只用 sha256 比对。

纪律：
  * **只读只报，⛔不修不删不覆盖**：修法有取向（源新→软链 / 副本新→回灌 / 双方都有实质内容→三方合并），
    判定权在维护者，不在钩子。本脚本只把"哪件、哪端、差多少"摆出来。
  * **fail-open**：stdin 缺失/非法/中心不可读/任何异常 → 静默退出 0，绝不阻塞宿主。
  * **告警必须可见**（v4 与送达层协同）：stdout 只进模型，所以输出 = 「AI 专用指令行」+
    「🧬 可见块」，块内含逐字可贴的告警行——与 D1 同一构造权在脚本的原则。
  * 隐私：只看路径与哈希，⛔不落盘文件内容。
  * 频控：同一 (客户端, 文件, 副本哈希) 组合只出声一次，防每次会话开头重复刷屏。

用法：
  python3 source_sync_guard.py                    # 挂载形态：扫全盘，有漂移则输出告警块
  python3 source_sync_guard.py --json             # 机器可读（供周报/巡检消费）
  python3 source_sync_guard.py --self-test        # 内置自测（临时目录，不碰真实客户端）
环境变量：
  BATON_SKILL_CENTER   覆盖技能配置中心根（默认 = 本 skill 包的父目录）
  BATON_CLIENT_ROOTS   冒号分隔的客户端 hooks 目录列表（覆盖自动发现）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import _baton_common as common
except Exception:                      # 公共层故障也不许拖垮宿主
    common = None

GUARD_MARK = "🧬 baton 源同步告警"
TOP = "━━━ %s ━━━" % GUARD_MARK
BOT = "━" * 18
INSTRUCTION = ("【baton 送达指令·AI 专用·本行⛔不进回复】把下方 🧬 告警块**逐字原样**追加到本轮回复的末尾"
               "（置于产出签名与署名行之前），⛔不改写、不合并；本块只报漂移不代做决定。")

# 已知客户端 hooks 目录（相对家目录）；自动发现只认这些，避免扫全盘
CLIENT_HOOK_DIRS = (".workbuddy/hooks", ".qoder/hooks", ".claude/hooks",
                    ".trae/hooks", ".trae-cn/hooks", ".qwenworkcn/hooks",
                    ".zcode/hooks", ".openclaw/hooks")
STATE_NAME = "source_sync_state.json"


def _center() -> Path:
    raw = os.environ.get("BATON_SKILL_CENTER")
    if raw:
        return Path(raw).expanduser()
    if common is not None:
        return common.skill_root().parent
    return Path(__file__).resolve().parents[2]


def _client_dirs() -> list:
    raw = os.environ.get("BATON_CLIENT_ROOTS")
    if raw:
        return [Path(p).expanduser() for p in raw.split(os.pathsep) if p]
    home = Path.home()
    return [home / rel for rel in CLIENT_HOOK_DIRS]


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _index_center(center: Path) -> dict:
    """技能中心 *.py 索引：basename → [绝对路径]。中心不可读 → 空表（不抛）。"""
    idx: dict = {}
    if not center.is_dir():
        return idx
    for skill in sorted(center.iterdir()):
        for sub in ("hooks", "scripts"):
            d = skill / sub
            if not d.is_dir():
                continue
            try:
                for p in sorted(d.iterdir()):
                    if p.is_file() and p.suffix == ".py":
                        idx.setdefault(p.name, []).append(p)
            except OSError:
                continue
    return idx


def scan(client_dirs: list | None = None, center: Path | None = None) -> list:
    """返回漂移记录 [{client_dir,file,copy,source,copy_sha,source_sha,symlink}]，只含实体非软链件。"""
    center = center if center is not None else _center()
    dirs = client_dirs if client_dirs is not None else _client_dirs()
    idx = _index_center(center)
    if not idx:
        return []
    out = []
    for d in dirs:
        if not d.is_dir():
            continue
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_symlink() or not p.is_file() or p.suffix != ".py":
                continue
            srcs = idx.get(p.name)
            if not srcs:
                continue                      # 非中心派生件（如端专属脚本）→ 不归本守卫管
            try:
                copy_sha = _sha(p)
            except OSError:
                continue
            src = srcs[0]
            try:
                src_sha = _sha(src)
            except OSError:
                continue
            if copy_sha != src_sha:
                out.append({"client_dir": str(d), "file": p.name, "copy": str(p),
                            "source": str(src), "copy_sha": copy_sha[:12],
                            "source_sha": src_sha[:12], "symlink": False})
    return out


def _state_path(ws: Path) -> Path:
    """去重账本沿用既有状态约定（<ws>/.baton-state/<hash>/），⛔不开第三个落点。"""
    if common is not None:
        try:
            return common.ensure_state(ws) / STATE_NAME
        except Exception:
            pass
    base = Path(os.environ.get("BATON_STATE_DIR") or (Path.home() / ".baton" / "state"))
    base.mkdir(parents=True, exist_ok=True)
    return base / STATE_NAME


def _load_state(p: Path) -> dict:
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _save_state(p: Path, st: dict) -> None:
    try:
        p.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def build_block(rows: list) -> str:
    lines = [TOP]
    lines.append("以下 %d 件是「派生自技能中心但不是软链」的实件，且哈希落后源 → 跑的是旧代码：" % len(rows))
    for r in rows:
        lines.append("  · %s（副本 %s vs 源 %s）" % (r["file"], r["copy_sha"], r["source_sha"]))
        lines.append("    源：%s" % r["source"])
    lines.append("  处置由你定：源新→改软链／副本新→先回灌源／双方都有实质内容→合并后再同步。")
    lines.append(BOT)
    return "\n".join(lines)


def cmd_runtime(ws: Path) -> int:
    """SessionStart 形态：有漂移且该组合未报过 → 出声；否则静默。全程 fail-open。"""
    try:
        rows = scan()
    except Exception:
        return 0
    if not rows:
        return 0
    sp = _state_path(ws)
    st = _load_state(sp)
    seen = st.get("seen") or {}
    fresh = [r for r in rows if seen.get(r["file"]) != r["copy_sha"]]
    if not fresh:
        return 0                               # 同一漂移已报过 → 不重复刷屏
    for r in fresh:
        seen[r["file"]] = r["copy_sha"]
    st["seen"] = seen
    _save_state(sp, st)
    print(INSTRUCTION)
    print(build_block(fresh))
    if common is not None:
        try:
            common.ledger(ws, "source_drift n=%d" % len(fresh))
        except Exception:
            pass
    return 0


def orphans(client_dirs: list | None = None, center: Path | None = None) -> list:
    """无源实体件：客户端 hooks 下的 .py 实体，但技能中心**没有同名真源**。

    这类件 S2 主判据（"派生自中心且哈希落后"）结构性抓不到——它们没有源可比，
    多端各一份时只能靠交叉哈希互比显形。实测判例：route_unknown_unknown.py
    在 .qoder/.qwenworkcn/.zcode 三端各一份、三份哈希互异、中心无真源。
    只报不修（归属常属其他 skill），⛔不进 SessionStart 告警块，仅供 --orphans/周报取数。
    """
    center = center if center is not None else _center()
    dirs = client_dirs if client_dirs is not None else _client_dirs()
    idx = _index_center(center)
    out = []
    for d in dirs:
        if not d.is_dir():
            continue
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_symlink() or not p.is_file() or p.suffix != ".py":
                continue
            if idx.get(p.name):
                continue
            try:
                out.append({"file": p.name, "path": str(p), "sha": _sha(p)[:12]})
            except OSError:
                continue
    by_name: dict = {}
    for r in out:
        by_name.setdefault(r["file"], []).append(r)
    return [r for name, rs in by_name.items() for r in rs]


def cmd_orphans() -> int:
    """按 basename 归组打印无源实体件，组内哈希是否一致一并报出（不一致=多端互相漂移）。"""
    rows = orphans()
    by_name: dict = {}
    for r in rows:
        by_name.setdefault(r["file"], []).append(r)
    out = []
    for name, rs in sorted(by_name.items()):
        shas = sorted({r["sha"] for r in rs})
        out.append({"file": name, "copies": len(rs), "distinct_hashes": len(shas),
                    "paths": [r["path"] for r in rs]})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


def _self_test() -> int:
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="baton_sync_guard_selftest_"))
    center = root / "center"
    client = root / ".fakeclient" / "hooks"
    skill = center / "demo" / "hooks"
    import shutil
    shutil.rmtree(root, ignore_errors=True)
    skill.mkdir(parents=True)
    client.mkdir(parents=True)
    os.environ["BATON_SKILL_CENTER"] = str(center)
    os.environ["BATON_CLIENT_ROOTS"] = str(client)
    os.environ["BATON_STATE_DIR"] = str(root / "state")

    src = skill / "a.py"
    src.write_text("V1\n", encoding="utf-8")
    (client / "a.py").write_text("V1\n", encoding="utf-8")       # 实件但同步 → 不该报
    (client / "b.py").write_text("V1\n", encoding="utf-8")
    src2 = skill / "b.py"
    src2.write_text("V2-源已前进\n", encoding="utf-8")            # 落后源 → 该报
    (client / "c.py").symlink_to(src)                            # 软链 → 不管
    (client / "d.py").write_text("端专属\n", encoding="utf-8")     # 非中心派生 → 不管

    tstate = root / "ws"
    tstate.mkdir(parents=True)
    fails = 0
    rows = scan()
    ok = [r["file"] for r in rows] == ["b.py"]
    print(("  ✅ " if ok else "  ❌ ") + "T1 只报「实体+中心派生+哈希不符」→ %s" % [r["file"] for r in rows])
    fails += 0 if ok else 1

    import io, contextlib

    def quiet_run(ws):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cmd_runtime(ws)
        return buf.getvalue()

    first = quiet_run(tstate)
    ok = GUARD_MARK in first and INSTRUCTION[:8] in first
    print(("  ✅ " if ok else "  ❌ ") + "T2 首次漂移出声（指令行 + 可见块）")
    fails += 0 if ok else 1

    ok = quiet_run(tstate) == ""
    print(("  ✅ " if ok else "  ❌ ") + "T3 同一份旧副本再跑 → 静默（去重键=副本哈希·防刷屏 by design）")
    fails += 0 if ok else 1

    src2.write_text("V3\n", encoding="utf-8")          # 源又前进，副本仍是那份旧件
    ok = quiet_run(tstate) == ""
    print(("  ✅ " if ok else "  ❌ ") + "T4 源再前进但副本未变 → 仍静默（不为同一旧件重复打扰）")
    fails += 0 if ok else 1

    (client / "b.py").write_text("V1-副本被本地改过\n", encoding="utf-8")   # 副本变化 = 新组合
    txt = quiet_run(tstate)
    ok = GUARD_MARK in txt
    print(("  ✅ " if ok else "  ❌ ") + "T5 副本内容变化后重新出声")
    fails += 0 if ok else 1

    (client / "b.py").write_text("V3\n", encoding="utf-8")                  # 手动同步回源
    ok = scan() == [] and quiet_run(tstate) == ""
    print(("  ✅ " if ok else "  ❌ ") + "T6 副本对齐源后 → 不再报（同步即消音）")
    fails += 0 if ok else 1

    client2 = root / ".fakeclient2" / "hooks"
    client2.mkdir(parents=True)
    (client / "e.py").write_text("端A\n", encoding="utf-8")
    (client2 / "e.py").write_text("端B-与端A不同\n", encoding="utf-8")
    os.environ["BATON_CLIENT_ROOTS"] = os.pathsep.join([str(client), str(client2)])
    orows = orphans()
    e = [r for r in orows if r["file"] == "e.py"]
    ok = len(e) == 2 and len({r["sha"] for r in e}) == 2
    print(("  ✅ " if ok else "  ❌ ") + "T7 无中心真源的多端实体件 → orphans 抓到且报出互异哈希")
    fails += 0 if ok else 1

    os.environ["BATON_CLIENT_ROOTS"] = str(root / "不存在的目录")
    ok = scan() == [] and quiet_run(tstate) == ""
    print(("  ✅ " if ok else "  ❌ ") + "T8 客户端目录缺失 → 空表不抛、静默（fail-open）")
    fails += 0 if ok else 1

    shutil.rmtree(root, ignore_errors=True)
    total = 8
    print("self-test: %d/%d 通过" % (total - fails, total))
    return 1 if fails else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="source_sync_guard.py",
                                     description="baton 存活层源同步漂移守卫（SessionStart·只告警不修·fail-open）")
    parser.add_argument("--json", action="store_true", help="输出机器可读漂移清单 JSON")
    parser.add_argument("--orphans", action="store_true",
                        help="只报「无中心真源的实体件」（不进告警块，供巡检/周报取数）")
    parser.add_argument("--hook-marker", metavar="TEXT", default=None,
                        help="安装幂等标记（仅用于识别，运行时忽略）")
    parser.add_argument("--self-test", action="store_true", help="内置自测（临时目录，不碰真实客户端）")
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return _self_test()
        if args.orphans:
            return cmd_orphans()
        if args.json:
            print(json.dumps(scan(), ensure_ascii=False))
            return 0
        return cmd_runtime(Path(os.environ.get("BATON_WORKSPACE") or os.getcwd()))
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
