#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_baton_common.py — baton 主动提醒 hook 的内部共享工具。

仅被 hooks/ 下三个脚本使用（私有模块，不对外暴露）。集中存放：
  * 路径解析（skill 根 / scripts / tick 多候选回退）
  * 状态根 <ws>/.baton-state/<ws-hash>/<agent-id>/（权限 700）
  * 标记（offered / installed）与最小化台账（不含 prompt）
  * 信任门（owner / 权限 / 可写性，P0-ε）
  * 跨平台辅助

设计约定：
  * 状态根永不落 skill 包内（只读 / 共享 / 版本控制目录不可写）。
  * 台账最小化：只记 ws-hash / 事件 / 时间戳，不记 prompt 全文或摘要。
  * BATON_SCRIPTS 回退仅在"显式、绝对、受信任"时启用（P0-η）。
"""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat as _stat
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

HOOK_MARKER = "# baton-reminder-hook-v1"
STATE_DIRNAME = ".baton-state"
DIR_MODE = 0o700
FILE_MODE = 0o600

# 送达信封特征串（v4/D1 构造方 = baton_reminder，v4/D3 对账方 = baton_delivery_guard）。
# 放这里是为了单一事实源：两边各写一份字面量 = 又一个"源↔副本漂移"标本。
ENVELOPE_MARK = "🎒 baton 交接提醒"


# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

def skill_root() -> Path:
    """skill 根（hooks/ 的上一层）。"""
    return Path(__file__).resolve().parent.parent


def scripts_dir() -> Path:
    return skill_root() / "scripts"


def tick_path() -> Path | None:
    """定位 baton_tick.py（多候选回退，首个 is_file 选用）。

    候选：包内 scripts/ → 相对 ../scripts/ → BATON_SCRIPTS（仅当显式、绝对、
    受信任，否则取消该回退，P0-η）。
    """
    candidates = [
        scripts_dir() / "baton_tick.py",
        skill_root() / ".." / "scripts" / "baton_tick.py",
    ]
    env = os.environ.get("BATON_SCRIPTS", "").strip()
    if env:
        p = Path(os.path.expanduser(env))
        if p.is_absolute() and path_is_trusted(p):
            candidates.append(p / "baton_tick.py" if p.is_dir() else p)
    for c in candidates:
        try:
            c = c.resolve()
        except OSError:
            continue
        if c.is_file():
            return c
    return None


def reminder_path() -> Path:
    return Path(__file__).resolve().parent / "baton_reminder.py"


# ---------------------------------------------------------------------------
# 状态根
# ---------------------------------------------------------------------------

def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def ws_hash(ws: os.PathLike | str) -> str:
    try:
        raw = str(Path(ws).resolve())
    except OSError:
        raw = str(ws)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def agent_id() -> str:
    for key in ("BATON_AGENT_ID", "AGENT_ID"):
        v = os.environ.get(key, "").strip()
        if v:
            return hashlib.sha256(v.encode("utf-8")).hexdigest()[:16]
    return hashlib.sha256(b"default-agent").hexdigest()[:16]


def state_root(ws: os.PathLike | str) -> Path:
    return Path(ws) / STATE_DIRNAME / ws_hash(ws) / agent_id()


def _chmod_safe(path: Path, mode: int) -> None:
    try:
        os.chmod(str(path), mode)
    except OSError:
        pass


def ensure_state(ws: os.PathLike | str) -> Path:
    """创建状态根并把链上目录设为 700，返回根。"""
    root = state_root(ws)
    root.mkdir(parents=True, exist_ok=True)
    target = root
    for _ in range(3):
        _chmod_safe(target, DIR_MODE)
        target = target.parent
    return root


def has_marker(ws: os.PathLike | str, name: str) -> bool:
    return (state_root(ws) / name).is_file()


def set_marker(ws: os.PathLike | str, name: str) -> Path:
    p = ensure_state(ws) / name
    p.write_text(iso_now() + "\n", encoding="utf-8")
    _chmod_safe(p, FILE_MODE)
    return p


def clear_marker(ws: os.PathLike | str, name: str) -> bool:
    p = state_root(ws) / name
    try:
        p.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def ledger(ws: os.PathLike | str, event: str) -> None:
    """追加最小化台账（ws-hash / 事件 / 时间戳；不记 prompt）。"""
    p = ensure_state(ws) / "ledger.jsonl"
    rec = {"ws": ws_hash(ws), "event": event, "at": iso_now()}
    # O_APPEND 原子追加
    fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_APPEND, FILE_MODE)
    try:
        os.write(fd, (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    _chmod_safe(p, FILE_MODE)


# ---------------------------------------------------------------------------
# 信任门（P0-ε）
# ---------------------------------------------------------------------------

def _stat_trusted(p: Path) -> bool:
    """对已存在路径做 POSIX / Windows 受信任判定。"""
    try:
        st = p.stat()
    except OSError:
        return False

    if os.name == "posix":
        # 不得被 group / other 写入（防替换）
        if st.st_mode & (_stat.S_IWGRP | _stat.S_IWOTH):
            return False
        # owner 须为当前用户或 root（系统级只读二进制属正常）；拒绝其他 uid
        if st.st_uid not in (os.geteuid(), 0):
            return False
        return True

    # Windows：stdlib 无法读 ACL；要求路径位于用户配置内（best-effort，
    # 深层 ACL 校验需 pywin32 / icacls，超出 stdlib 范围，TESTED 已声明）
    try:
        p.resolve().relative_to(Path(os.path.expanduser("~")).resolve())
    except (OSError, ValueError):
        return False
    return True


def _dir_chain_trusted(p: Path, depth: int = 4) -> bool:
    """检查父目录链不可被 group/other 写入（防同级替换）。

    例外：world-writable 但设置了粘滞位（S_ISVTX，如系统临时目录）的目录，只有文件
    属主/root 才能重命名或删除，同级替换面被粘滞位封住，予以放行。
    """
    if os.name != "posix":
        return True
    parent = p
    for _ in range(depth):
        try:
            ps = parent.stat()
            if ps.st_mode & (_stat.S_IWGRP | _stat.S_IWOTH):
                if not (ps.st_mode & _stat.S_ISVTX):
                    return False
        except OSError:
            return False
        if parent == parent.parent:
            break
        parent = parent.parent
    return True


def path_is_trusted(target: os.PathLike | str, *, must_exist: bool = False) -> bool:
    """判断路径是否受信任。

    路径不存在时：must_exist=True 判 False；否则检查其父目录链（用于尚未创建
    的 settings 文件）。
    """
    p = Path(target)
    if p.exists() or p.is_symlink():
        try:
            real = p.resolve()
        except OSError:
            return False
        if not real.exists():
            return False
        return _stat_trusted(real) and _dir_chain_trusted(real.parent)
    if must_exist:
        return False
    return _dir_chain_trusted(p.parent)


def untrusted(paths) -> list:
    """返回不可信路径列表（空=全部受信任）。"""
    bad = []
    for p in paths:
        if not path_is_trusted(p):
            bad.append(str(p))
    return bad


# ---------------------------------------------------------------------------
# 跨平台
# ---------------------------------------------------------------------------

def quote_cmd(parts: list, for_posix: bool | None = None) -> str:
    """把命令片段拼成跨平台命令字符串。

    POSIX：shlex.quote；Windows：subprocess.list2cmdline + 反斜杠。
    """
    posix = sys.platform != "win32" if for_posix is None else for_posix
    if posix:
        return " ".join(shlex.quote(str(x)) for x in parts)
    import subprocess
    return subprocess.list2cmdline([str(x) for x in parts])


def file_sha256(path: os.PathLike | str) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
