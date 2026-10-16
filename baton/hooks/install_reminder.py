#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""install_reminder.py — baton 主动提醒 hook 安装器。

行为（与运行时 hook 相反，本脚本 **fail-closed**：任何失败都保持原配置）：
  1. 探测 provider（baton_tick.py --detect-provider）；仅对"可自动写"的标准
     settings 格式自动接线；其余打印手动片段并记录"未挂载"（P1-10）。
  2. 信任门（P0-ε）：写 settings 前校验 skill / tick / python / settings 路径的
     owner / 权限 / 可写性；任一不可信 → 拒绝写入并退出非零。
  3. settings 作用域（P0-ζ）：显式 user / project，与每 workspace 提示粒度一致；
     文件锁 + JSON schema 校验 + 备份 + 原子替换 + 失败回滚 + 并发安全。
  4. 非交互：--yes/--no/--dry-run；无 TTY 默认"否"且不写 offered（P1-4）。
  5. 幂等：命令带稳定标记（旧标记备份后替换，P1-3）。
  6. 跨平台：命令片段用 shlex / list2cmdline；可执行名取 sys.executable。

用法：
  python3 install_reminder.py [workspace] [--yes|--no|--dry-run]
  python3 install_reminder.py [workspace] --settings <path> [--scope user|project]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _baton_common as common  # noqa: E402

HOOK_TIMEOUT_MS = 5000
EVENT = "Stop"   # 回退事件：未接线 provider 打印手动片段时使用


# ---------------------------------------------------------------------------
# Provider 接线表（按客户端适配 · 2026-10-11 A/B/C 改造）
# ---------------------------------------------------------------------------
# 每个 provider 声明：settings 落点（user / project）、hook 事件名、条目是否带
# timeout、默认作用域。未列入表且无 .claude 的 provider → wiring=None → 转手动
# 片段（fail-closed：未实测的落点/事件一律不自动写，不为填满而编）。
PROVIDER_WIRING = {
    "workbuddy": {
        # 实测（2026-10-10）：~/.workbuddy/settings.json 存在；事件组 UserPromptSubmit；
        # 条目形态 {type, command} —— 不带 timeout。
        "user": "~/.workbuddy/settings.json",
        "project": ".workbuddy/settings.json",
        "event": "UserPromptSubmit",
        "timeout": False,
        # 项目级 <ws>/.workbuddy/settings.json 是否被 WorkBuddy 读取未实测 → 默认用户级
        "default_scope": "user",
    },
    "claude": {
        # Claude Code 标准形态；仅当 .claude 真实存在才命中（不臆造目录）
        "user": "~/.claude/settings.json",
        "project": ".claude/settings.json",
        "event": "Stop",
        "timeout": True,
        "default_scope": "project",
    },
}

# 未接线 provider（doubaowork / qoder 家族 / zcode / ...）打印手动片段时的回退形态
DEFAULT_WIRING = {"event": EVENT, "timeout": True}


# ---------------------------------------------------------------------------
# v4/S3 发布校验：装/升级时比对实件 hash
# ---------------------------------------------------------------------------
# 纪律：锚点必须**来自外部**（本安装器认两个：--manifest / BATON_MANIFEST；
#   BATON_EXPECTED_HASH 是 §7.1 selfcheck 的单人锚，只管 baton_reminder.py，安装器不读）。
#   ⛔ 不在 hooks 目录里写一份"自己证明自己没被改"的清单——同目录自证等于没有验证
#   （SKILL §7.1 selfcheck 同一原则）。本安装器只读清单、只打印待发签名的实算值。
# 与 selfcheck 共用同一份清单：两个消费方的取键规则必须互通，否则发布方按 §2.6
#   的扁平形态签名、安装器却判"清单缺件"拒装合法包（2026-10-14 实测假红，见 FLAT_ALIASES）。
FLAT_ALIASES = {"reminder_sha256": "baton_reminder.py", "tick_sha256": "baton_tick.py"}
VERIFY_BASENAMES = ("baton_reminder.py", "baton_delivery_guard.py",
                    "source_sync_guard.py", "_baton_common.py")


def collect_hashes() -> dict:
    """实算发布面哈希（供发布方签名成外部 manifest）。缺件 → 该键值为 None。"""
    root = common.skill_root()
    out = {}
    for name in VERIFY_BASENAMES:
        p = root / "hooks" / name
        out["hooks/%s" % name] = common.file_sha256(p) if p.is_file() else None
    tick = common.tick_path()
    out["scripts/baton_tick.py"] = common.file_sha256(tick) if tick and tick.is_file() else None
    return out


def _manifest_expected(manifest: dict) -> dict:
    """宽松取期望值：支持 {"files": {"hooks/x.py": sha}} 与扁平 {"x.py": sha}。

    扁平形态另认 §2.6 selfcheck 的两个别名键（reminder_sha256 / tick_sha256）——
    同一份清单喂两个消费方时，⛔ 一方绿灯一方假红拒装。
    """
    files = manifest.get("files")
    if isinstance(files, dict):
        src = files
    else:
        src = {k: v for k, v in manifest.items() if isinstance(v, str)}
    exp = {}
    for k, v in src.items():
        base = str(k).replace("\\", "/").split("/")[-1]
        exp[base] = str(v)
    for alias, real in FLAT_ALIASES.items():
        if alias in src and real not in exp:
            exp[real] = str(src[alias])
    return exp


def verify_install(manifest_path: Path | None) -> int:
    """0=一致，或清单未覆盖的件（如实报"未验证"，不阻塞）；3=与外部清单不符（调用方须 fail-closed）。

    作用域规则：清单**覆盖到**的件必须全对；未列出的件只登记不判——清单由外部发布方署名，
    老包清单本就可能只列自家两件（§2.6 形态），缺键≠被篡改，据此拒装是假红。
    """
    actual = collect_hashes()
    if manifest_path is None:
        raw = os.environ.get("BATON_MANIFEST")
        if raw:
            manifest_path = Path(raw).expanduser()
    if manifest_path is None:
        print("install: 未提供外部发布清单 → 实件 hash **未验证**（不是"
              "已验证通过）。发布面实算值：")
        print(json.dumps(actual, ensure_ascii=False, indent=1))
        return 0
    if not manifest_path.is_file():
        print("install: 指定了发布清单但文件不存在（%s）→ 与清单损坏同级，"
              "拒绝在未验证状态下接线" % manifest_path, file=sys.stderr)
        return 3
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("install: 发布清单读不了（%s）→ 拒绝在"
              "未验证状态下接线" % exc, file=sys.stderr)
        return 3
    if not isinstance(manifest, dict):
        print("install: 发布清单非对象 → 拒绝接线", file=sys.stderr)
        return 3
    exp = _manifest_expected(manifest)
    bad, uncovered = [], []
    for key, sha in actual.items():
        base = key.split("/")[-1]
        want = exp.get(base)
        if want is None:
            uncovered.append(key)
        elif sha != want:
            bad.append((key, want[:12], (sha or "")[:12]))
    if bad:
        print("install: ❌ 与外部发布清单不一致（%d 件），拒绝写入 settings：" % len(bad),
              file=sys.stderr)
        for key, want, got in bad:
            print("  - %s 期望=%s 实得=%s" % (key, want, got), file=sys.stderr)
        return 3
    checked = len(actual) - len(uncovered)
    if checked == 0:
        print("install: ⚠️ 清单未覆盖任何发布面文件 → 本次**未验证**"
              "（不是校验通过）。实算值：%s" % json.dumps(actual, ensure_ascii=False))
        return 0
    tail = "，另有 %d 件清单未列出=未验证" % len(uncovered) if uncovered else ""
    print("install: ✅ 发布清单校验通过（比对 %d 件%s）" % (checked, tail))
    return 0


# ---------------------------------------------------------------------------
# 跨平台文件锁
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def file_lock(path: Path):
    """对 settings 加锁防并发写（POSIX flock / Windows msvcrt）。"""
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(str(lock_path), "a+")
    try:
        if os.name == "posix":
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        else:
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            if os.name == "posix":
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            else:
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        fh.close()


# ---------------------------------------------------------------------------
# Provider / settings
# ---------------------------------------------------------------------------

def detect_provider(ws: Path) -> tuple[str | None, int]:
    """调用 tick --detect-provider，返回 (provider_key, 退出码)。"""
    tick = common.tick_path()
    if tick is None:
        return None, 3
    try:
        proc = subprocess.run(
            [sys.executable, str(tick), "--detect-provider", str(ws)],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None, 3
    key = None
    try:
        key = json.loads(proc.stdout).get("provider")
    except (json.JSONDecodeError, ValueError):
        key = None
    return key, proc.returncode


def wiring_for(provider: str | None, ws: Path) -> dict | None:
    """返回该 provider 的接线配置；未接线返回 None → 转手动片段。

    'claude' 不是 detect 出来的 provider key，而是按「.claude 目录真实存在」判定的
    历史形态，故单独处理：只有目录真的在，才算命中（不臆造目录、不凭 provider 名猜）。
    """
    if provider and provider in PROVIDER_WIRING:
        return PROVIDER_WIRING[provider]
    w = PROVIDER_WIRING["claude"]
    user_dir = Path(w["user"]).expanduser().parent
    if user_dir.is_dir() or (ws / ".claude").is_dir():
        return w
    return None


def resolve_settings(ws: Path, scope: str, explicit: str | None,
                     provider: str | None = None) -> Path | None:
    """决定 settings 路径。返回 None 表示该 provider 不支持自动写（转手动）。

    落点按 provider 查 PROVIDER_WIRING；未接线 provider → None（转手动）。
    """
    if explicit:
        return Path(explicit).expanduser()
    w = wiring_for(provider, ws)
    if w is None:
        return None
    raw = w.get(scope) or w.get("user")
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = ws / p
    return p


# v4/R4 B3：hook 注册表——默认装 reminder + delivery_guard；--full 加 source_sync_guard
HOOK_REGISTRY = [
    {"key": "reminder", "script": "baton_reminder.py",
     "event_from_wiring": True, "default": True},
    {"key": "delivery_guard", "script": "baton_delivery_guard.py",
     "event": "Stop", "default": True},
    {"key": "source_sync_guard", "script": "source_sync_guard.py",
     "event": "SessionStart", "default": False},
]


def hook_script_path(script: str) -> Path:
    """注册表脚本名 → 包内 hooks/ 绝对路径。"""
    return Path(__file__).resolve().parent / script


def build_hook_entry(ws: Path, script: str = "baton_reminder.py", *,
                     use_timeout: bool = True,
                     include_ws: bool = True) -> dict:
    """构造 hook 命令（仅位置参数 + 幂等标记，不含 --prompt，P0-γ）。

    use_timeout=False 时条目不带 timeout 键——WorkBuddy 实测条目形态就是
    {type, command}；多一个键会不会被忽略未实测，故按 wiring 决定、不加就不加。

    include_ws=False 时命令里不写 ws 位置参数（2026-10-11 修）：
    用户级 settings 是**全局**文件，把某个 ws 路径烧进去，会让其他 workspace
    的会话也拿这个 ws 去跑 tick（扫错 session）。省掉 ws 后由 baton_reminder
    的 resolve_workspace 回退到 cwd —— 这是用户级挂载的正确形态。
    项目级（<ws>/.workbuddy/settings.json）作用域唯一，才烧 ws。
    """
    script_path = (common.reminder_path() if script == "baton_reminder.py"
                   else hook_script_path(script))
    parts = [
        sys.executable,
        str(script_path),
    ]
    if include_ws:
        parts.append(str(ws))
    parts += ["--hook-marker", common.HOOK_MARKER]
    command = common.quote_cmd(parts)
    entry = {"type": "command", "command": command}
    if use_timeout:
        entry["timeout"] = HOOK_TIMEOUT_MS
    return entry


def upsert_hook(data: dict, entry: dict, event: str = EVENT) -> tuple[dict, str]:
    """插入或替换 hook（同标记→替换；已做整文件备份）。返回 (data, added|replaced)。

    event 随 provider 走（WorkBuddy=UserPromptSubmit / Claude=Stop），不再全局写死。
    """
    hooks = data.setdefault("hooks", {})
    events = hooks.setdefault(event, [])
    for group in events:
        inner = group.get("hooks", [])
        for i, h in enumerate(inner):
            if common.HOOK_MARKER in (h.get("command") or ""):
                inner[i] = entry
                return data, "replaced"
    events.append({"hooks": [entry]})
    return data, "added"


# ---------------------------------------------------------------------------
# 写 settings（锁 / schema / 备份 / 原子 / 回滚）
# ---------------------------------------------------------------------------

def load_settings(path: Path) -> dict | None:
    """读现有 settings；非空且解析失败 → None（放弃写，转手动）。"""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def write_atomic(path: Path, text: str, backup: Path | None) -> None:
    """临时文件 + 原子替换。失败时保留原文件并告知备份路径。"""
    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                        prefix=".baton-set-", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp_name, str(path))
    except OSError as exc:
        # 原子替换失败 → 原文件通常仍在；清理临时文件
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        if backup and backup.exists():
            raise RuntimeError(
                "写入失败（%s）。原配置应仍在；备份见 %s，可手工恢复。" % (exc, backup))
        raise RuntimeError("写入失败（%s），原配置应仍在。" % exc)


def auto_install(ws: Path, settings: Path, *, event: str = EVENT,
                 use_timeout: bool = True, include_ws: bool = True,
                 dry_run: bool, quiet: bool, full: bool = False) -> int:
    """自动接线（v4/R4：按注册表装 N 件）；失败 fail-closed（不改原配置）。"""
    specs = [s for s in HOOK_REGISTRY if s["default"] or full]
    entries = []
    for spec in specs:
        ev = spec.get("event") or event
        to = use_timeout if spec.get("event_from_wiring") else True
        entries.append({"key": spec["key"], "event": ev,
                        "hook": build_hook_entry(ws, spec["script"],
                                                 use_timeout=to,
                                                 include_ws=include_ws)})

    if dry_run:
        preview = {"settings": str(settings), "include_ws": include_ws,
                   "mode": "full" if full else "default", "hooks": entries}
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    # 信任门（P0-ε）：skill 根 / 各脚本 / 解释器 / settings
    tick = common.tick_path()
    check_paths = [common.skill_root(), common.reminder_path(),
                   sys.executable, settings]
    for spec in specs:
        check_paths.append(hook_script_path(spec["script"]))
    if tick:
        check_paths.append(tick)
    bad = common.untrusted(check_paths)
    if bad:
        print("install: 信任门拒绝写入（路径不可信，可能被他人写入/替换）：",
              file=sys.stderr)
        for b in bad:
            print("  - %s" % b, file=sys.stderr)
        return 2

    settings.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(settings):
        data = load_settings(settings)
        if data is None:
            print("install: 现有 settings 无法解析（非 JSON / JSONC），放弃自动写。"
                  "请手动粘贴下方片段。", file=sys.stderr)
            print_manual(ws, event=event, use_timeout=use_timeout)
            return 2

        backup = None
        if settings.exists():
            backup = settings.with_name(
                settings.name + ".bak-baton-%d" % int(os.times().elapsed))
            try:
                backup.write_text(settings.read_text(encoding="utf-8"),
                                  encoding="utf-8")
            except OSError:
                backup = None

        actions = []
        for item in entries:
            data, action = upsert_hook(data, item["hook"], item["event"])
            actions.append("%s@%s:%s" % (item["key"], item["event"], action))
        text = json.dumps(data, ensure_ascii=False, indent=2)
        try:
            write_atomic(settings, text, backup)
        except RuntimeError as exc:
            # fail-closed：明确告知，不宣称成功
            print("install: %s" % exc, file=sys.stderr)
            return 2

    common.set_marker(ws, "installed")
    common.ledger(ws, "hook-installed")
    if not quiet:
        print("已挂载 baton 主动提醒（%d 件：%s）。" % (len(actions), ", ".join(actions)))
        if backup:
            print("原配置备份：%s" % backup)
    return 0


# ---------------------------------------------------------------------------
# 手动片段
# ---------------------------------------------------------------------------

def print_manual(ws: Path, *, event: str = EVENT, use_timeout: bool = True,
                 include_ws: bool = True, full: bool = False) -> None:
    """打印当前宿主无法自动写入时的手动接线片段（v4/R4：按注册表出 N 件）。"""
    specs = [s for s in HOOK_REGISTRY if s["default"] or full]
    snippet = {"hooks": {}}
    for spec in specs:
        ev = spec.get("event") or event
        to = use_timeout if spec.get("event_from_wiring") else True
        entry = build_hook_entry(ws, spec["script"], use_timeout=to,
                                 include_ws=include_ws)
        snippet["hooks"].setdefault(ev, []).append({"hooks": [entry]})
    print("\n# 手动挂载：把下面片段并入你的 settings.json（hooks 字段）")
    print(json.dumps(snippet, ensure_ascii=False, indent=2))
    print("# 说明：若你的宿主不支持 hook（如豆包办公端），可忽略——核心交接"
          "功能不依赖 hook。")


# ---------------------------------------------------------------------------
# 交互
# ---------------------------------------------------------------------------

def ask_proceed(args) -> bool:
    """--yes/--no/--dry-run 优先；无 TTY 默认否（不写 offered）。"""
    if args.yes:
        return True
    if args.no:
        return False
    if args.dry_run:
        return False
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            ans = input("是否挂载 baton 主动提醒？[y/N] ").strip().lower()
            return ans in ("y", "yes")
        except EOFError:
            return False
    return False


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="install_reminder.py",
        description="baton 主动提醒 hook 安装器（fail-closed；不传输 prompt）。")
    parser.add_argument("workspace", nargs="?", default=None,
                        help="workspace 目录（默认 cwd）")
    parser.add_argument("--yes", action="store_true", help="非交互确认挂载")
    parser.add_argument("--no", action="store_true", help="非交互取消")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将要写入的片段，不修改")
    parser.add_argument("--scope", choices=["user", "project"], default=None,
                        help="settings 作用域（默认按 provider：workbuddy→user，其余→project）")
    parser.add_argument("--settings", metavar="PATH", default=None,
                        help="显式指定 settings 文件（标准 hooks 格式）")
    parser.add_argument("--quiet", action="store_true", help="少输出")
    parser.add_argument("--full", action="store_true",
                        help="v4/R4：加装 source_sync_guard@SessionStart（仅多端部署者需要；"
                             "默认只装 reminder@UserPromptSubmit + delivery_guard@Stop）")
    parser.add_argument("--manifest", metavar="PATH", default=None,
                        help="v4/S3：外部发布清单路径（含各实件 sha256）；不符则拒绝接线")
    parser.add_argument("--print-hashes", action="store_true",
                        help="v4/S3：打印发布面实算 hash（JSON），供发布方签名，不安装不写文件")
    args = parser.parse_args(argv)

    if args.print_hashes:
        print(json.dumps(collect_hashes(), ensure_ascii=False, indent=1))
        return 0

    # v4/S3：装/升级前置校验——外部锚点不符 → fail-closed，不写 settings。
    # 放在 provider/scope 解析之前，任何路径（自动或转手动）都不带未验证件出门。
    has_anchor = bool(args.manifest or os.environ.get("BATON_MANIFEST"))
    if has_anchor:
        vrc = verify_install(Path(args.manifest).expanduser() if args.manifest else None)
        if vrc != 0:
            return vrc
    elif not args.quiet:
        print("install: 无外部信任锚（manifest / BATON_MANIFEST）→ hash 未验证。")

    ws = Path(args.workspace).expanduser() if args.workspace else Path.cwd()
    ws = ws.resolve()

    provider, _code = detect_provider(ws)
    w = wiring_for(provider, ws)
    # scope 默认按 provider 走：workbuddy→user（项目级是否生效未实测，故默认用户级）
    scope = args.scope or ((w or {}).get("default_scope") or "project")
    event = (w or DEFAULT_WIRING)["event"]
    use_timeout = (w or DEFAULT_WIRING)["timeout"]
    settings = resolve_settings(ws, scope, args.settings, provider)
    # 用户级 = 全局文件：⛔不要把 ws 烧进命令（否则其他 workspace 的会话扫错 ws）
    include_ws = (scope != "user")

    if settings is None:
        # 该 provider 不支持自动写：打印手动片段 + 记录未挂载（P1-10）
        if not args.quiet:
            print("当前 provider（%s）不在自动接线名单；转手动挂载。"
                  % (provider or "unknown"))
        print_manual(ws, event=event, use_timeout=use_timeout,
                     include_ws=include_ws, full=args.full)
        common.ledger(ws, "hook-not-mounted")
        return 0

    if args.dry_run:
        return auto_install(ws, settings, event=event, use_timeout=use_timeout,
                            include_ws=include_ws,
                            dry_run=True, quiet=args.quiet, full=args.full)

    if not ask_proceed(args):
        common.ledger(ws, "hook-declined")
        if not args.quiet:
            print("未挂载（默认不挂）。核心交接功能不依赖 hook。")
        return 0

    return auto_install(ws, settings, event=event, use_timeout=use_timeout,
                        include_ws=include_ws,
                        dry_run=False, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
