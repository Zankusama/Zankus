#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""uninstall_reminder.py — 卸载 baton 主动提醒 hook。

  * 从 settings 中移除含幂等标记的命令（先备份）；
  * 清空该 workspace 的 .baton-state/（--all 则清所有 workspace）；
  * 幂等：未挂载 / 已清理也正常退出。
  * fail-closed：解析失败不动原配置，转提示手工处理。

用法：
  python3 uninstall_reminder.py [workspace] [--settings <path>]
  python3 uninstall_reminder.py --all
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _baton_common as common  # noqa: E402
from install_reminder import (  # noqa: E402
    DEFAULT_WIRING,
    EVENT,
    detect_provider,
    file_lock,
    load_settings,
    resolve_settings,
    wiring_for,
)


def remove_hook(data: dict, event: str = EVENT) -> tuple[dict, bool]:
    """移除含标记的命令；返回 (data, 是否有移除)。

    event 随 provider 走（与 install 同一张 PROVIDER_WIRING）——否则 WorkBuddy 下会
    去 Stop 组找、而 hook 实际挂在 UserPromptSubmit 组 → 漏删。
    """
    changed = False
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return data, False
    groups = hooks.get(event)
    if not isinstance(groups, list):
        return data, False
    new_groups = []
    for group in groups:
        inner = group.get("hooks")
        if isinstance(inner, list):
            kept = [h for h in inner
                    if common.HOOK_MARKER not in (h.get("command") or "")]
            if len(kept) != len(inner):
                changed = True
            group = dict(group)
            if kept:
                group["hooks"] = kept
                new_groups.append(group)
            # 该组没有其他 hook 时整组删除
        else:
            new_groups.append(group)
    if changed:
        if new_groups:
            hooks[event] = new_groups
        else:
            hooks.pop(event, None)
    return data, changed


def uninstall_settings(settings: Path, quiet: bool, event: str = EVENT) -> int:
    settings.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(settings):
        if not settings.exists():
            return 0
        data = load_settings(settings)
        if data is None:
            print("uninstall: 现有 settings 无法解析，未改动；请手工删除含 %s 的命令。"
                  % common.HOOK_MARKER, file=sys.stderr)
            return 2

        backup = settings.with_name(
            settings.name + ".bak-baton-uninst-%d" % int(os.times().elapsed))
        try:
            backup.write_text(settings.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            backup = None

        data, changed = remove_hook(data, event)
        if changed:
            try:
                settings.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                    encoding="utf-8", newline="\n")
            except TypeError:
                # Python <3.10：write_text 无 newline 参数
                with open(str(settings), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(data, ensure_ascii=False, indent=2))
            if not quiet:
                print("已从 settings 移除 hook（备份：%s）。" % backup)
    return 0


def wipe_state(ws: Path, quiet: bool) -> None:
    root = common.state_root(ws)
    if root.exists():
        try:
            shutil.rmtree(str(root))
            if not quiet:
                print("已清 .baton-state：%s" % root)
        except OSError as exc:
            print("uninstall: 清理状态失败：%s" % exc, file=sys.stderr)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="uninstall_reminder.py",
        description="卸载 baton 主动提醒 hook（幂等；含标记/状态清理）。")
    parser.add_argument("workspace", nargs="?", default=None,
                        help="workspace 目录（默认 cwd）")
    parser.add_argument("--settings", metavar="PATH", default=None,
                        help="settings 文件路径（默认按标准位置推断）")
    parser.add_argument("--all", action="store_true",
                        help="清所有 workspace 的状态（需配合 workspace 给状态根上层）")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    ws = Path(args.workspace).expanduser() if args.workspace else Path.cwd()
    ws = ws.resolve()

    # 与 install 用同一张 PROVIDER_WIRING 定位 settings + event。
    # 原实现 hardcode resolve_settings(ws, "project", None) → WorkBuddy 下既找不到
    # <ws>/.workbuddy/settings.json（项目级未实测），又去 Stop 组删（实际在
    # UserPromptSubmit 组），两头都漏。
    provider, _code = detect_provider(ws)
    w = wiring_for(provider, ws)
    scope = (w or {}).get("default_scope") or "project"
    event = (w or DEFAULT_WIRING)["event"]
    settings = Path(args.settings).expanduser() if args.settings else \
        resolve_settings(ws, scope, None, provider)

    rc = 0
    if settings is not None:
        rc = uninstall_settings(settings, args.quiet, event)

    if args.all:
        top = ws / common.STATE_DIRNAME
        if top.exists():
            try:
                shutil.rmtree(str(top))
                if not args.quiet:
                    print("已清全部状态：%s" % top)
            except OSError as exc:
                print("uninstall: %s" % exc, file=sys.stderr)
                rc = rc or 2
    else:
        wipe_state(ws, args.quiet)

    common.ledger(ws, "hook-uninstalled")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
