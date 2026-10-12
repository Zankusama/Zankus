#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
baton_tick.py — baton 客观体量代理计数器（多客户端适配版）

## 定位（⛔ 边界与 SKILL.md 一致，不越界）
  · 只读：只读会话文件（JSONL / SQLite）+ handoff/state.json，**不写任何客户端数据**
  · 不测token（只数 function_call / tool_use / tool_calls 条数与字节，不猜 token 数）
  · 不做交接决策：只报客观读数 + 自报/客观矛盾标记，判定权仍归agent
  · 不依赖 hook：可直接手动跑，也可在任何 harness 下用

## 多客户端适配（2026-10-10 新增）
  命令行不变：`python3 baton_tick.py <workspace_dir>`
  输出顶层新增 `provider` 字段，告知本次实际用了哪个解析器。
  v2.3.0 起新增 `streak`（回正后的空转 streak）与 `streak_source`
  （"self_report"=state.json 自报优先 / "objective"=客观时间线兜底）。
  自动路由顺序：workbuddy → doubaowork → qoder/qoder_cn/qwenwork_cn
                → zcode → autoclaw_official → copilot → autoclaw_legacy
  全部 probe 未命中 → 兜底标 provider=workbuddy（保持旧版不可用提示）。

  已接 9 个 provider：
    workbuddy          ~/.workbuddy/projects/<enc>/<sid>.jsonl   (Anthropic function_call 风格)
    doubaowork         ~/.../DoubaoWork/.../.sessions/<sid>/agents/<aid>/system/trajectory.jsonl
    qoder              ~/.qoder/projects/<enc>/<sid>.jsonl        (Anthropic Messages 风格)
    qoder_cn           ~/.qoderworkcn/projects/<enc>/<sid>.jsonl   (同上)
    qwenwork_cn        ~/.qwenworkcn/projects/<enc>/<sid>.jsonl   (同上)
    zcode              ~/.zcode/cli/db/db.sqlite                   (SQLite)
    autoclaw_official  ~/Library/.../AutoClaw-official/accounts/*/runtime/runtime.sqlite
    copilot            ~/.copilot/session-store.db                 (SQLite)
    autoclaw_legacy    ~/.openclaw-autoclaw/agents/*/sessions/*.jsonl (OpenAI 风格)

## 退出码
  0 = 正常（无论是否命中矛盾，都不算失败）；本脚本永不阻断对话。
"""

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HOME = Path.home()

# ============================================================
#  触发阈值常量区（v2.3.0：逐个可调、逐个自标）
#  ⛔ 全部为工程启发式——证据调研（2026-10-12）结论：这些数值学术查无，
#     文档与注释中禁写"有学术/权威依据"。
# ============================================================
# 空转轴：尾部连续「有工具调用且零写盘」工作单元数 ≥ 该值 → 询问行（sub-L2 临界区）
STREAK_ASK_MIN = 2   # 工程启发式（依据：证据报告；学术查无阈值；空转 2-3 与 JetBrains/CoderClaw 惯例量级一致）
# 空转轴：≥ 该值 → L2 催办行（l2_objective_hit=true）
STREAK_L2_MIN = 3    # 工程启发式（依据：证据报告；学术查无阈值；空转 2-3 与 JetBrains/CoderClaw 惯例量级一致）
# 体量轴：会话用户轮数 ≥ 该值 → 仅进询问行，绝不置 l2_objective_hit（拍板：体量轴不出催办行）
TURN_VOLUME_MIN = 15   # 工程启发式（依据：证据报告；学术/工业均查无轮数阈值；定位为 token 占比不可见时的代理指标）
# 体量轴：会话跨度（分钟）≥ 该值 → 仅进询问行（证据报告评为四数值中最弱，只作或条件）
SPAN_VOLUME_MIN = 60   # 工程启发式（依据：证据报告；学术/工业均查无墙钟时长阈值；纯噪声代理，仅作或条件）
# 工作单元切分：相邻事件间隔 ≥ 该分钟数即切段（粒度执行者定，理由见 output/PROGRESS.md）
UNIT_GAP_MIN = 10      # 工程启发式（依据：证据报告对切分粒度查无任何数值；十进制节拍习惯）

# ---------- 各 provider 的根路径常量 ----------
WORKBUDDY_PROJECTS = HOME / ".workbuddy" / "projects"
DOUBAOWORK_SESSIONS = (HOME / "Library/Application Support/DoubaoWork/Default/"
                       ".doubaowork/agent_mode/workspace/.sessions")
QODER_PROJECTS = HOME / ".qoder" / "projects"
QODERCN_PROJECTS = HOME / ".qoderworkcn" / "projects"
QWENWORKCN_PROJECTS = HOME / ".qwenworkcn" / "projects"
ZCODE_DB = HOME / ".zcode" / "cli" / "db" / "db.sqlite"
AUTOCLAW_OFFICIAL_ROOT = HOME / "Library" / "Application Support" / "AutoClaw-official"
COPILOT_DB = HOME / ".copilot" / "session-store.db"
OPENCLAW_ROOT = HOME / ".openclaw-autoclaw"


# ============================================================
#  通用工具
# ============================================================

def _new_obj() -> dict:
    """与旧版 scan_session 输出同 schema 的空读数。"""
    return dict(
        user_turns=0, tool_calls=0, output_bytes=0,
        wall_minutes=0.0, read_total=0, read_dup_paths=0, read_dup_detail={},
        write_calls=0, write_targets=[], no_write_streak=0,
        ts_min=None, ts_max=None, parse_errors=0,
    )


def _finalize(obj: dict, reads: list, write_targets: list):
    """聚合 read_dup / write_targets / wall_minutes。"""
    obj["read_total"] = len(reads)
    c = Counter(reads)
    dup = {k: v for k, v in c.items() if v > 1}
    obj["read_dup_paths"] = len(dup)
    obj["read_dup_detail"] = dup
    obj["write_targets"] = write_targets
    if isinstance(obj["ts_min"], (int, float)) and isinstance(obj["ts_max"], (int, float)):
        span = obj["ts_max"] - obj["ts_min"]
        # 用 ts_min 绝对值判量级：>1e12 毫秒级，>1e9 秒级
        if obj["ts_min"] > 1e12:
            obj["wall_minutes"] = round(span / 60000.0, 1)
        elif obj["ts_min"] > 1e9:
            obj["wall_minutes"] = round(span / 60.0, 1)


def _open_ro_sqlite(db: Path):
    """以只读 URI 模式打开 SQLite，绝不写。"""
    uri = f"file:{db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
#  WorkBuddy（保留旧版函数名与行为，向后兼容）
# ============================================================

def encode_workspace(ws: Path) -> str:
    """workspace 路径 → projects 目录名
    规则（2026-10-05 实测确认）：去掉开头的 '/'，其余 '/' 换 '-'。

    ws 入口统一规范化（expanduser + resolve）：修 '.' / 相对路径 / '~' 的编码陷阱
    ——此前 '.' 会被编码成 '.'，导致 probe 永远找不到 projects/<encoded> 目录。
    """
    try:
        ws = Path(ws).expanduser().resolve()
    except (OSError, RuntimeError):
        ws = Path(ws).expanduser()
    return str(ws).lstrip("/").replace("/", "-")


def pick_session_file(ws: Path):
    """取该 workspace 下 mtime 最新的会话 JSONL（WorkBuddy 旧接口保留）。"""
    d = WORKBUDDY_PROJECTS / encode_workspace(ws)
    if not d.is_dir():
        return None, None
    cands = [p for p in d.glob("*.jsonl")]
    if not cands:
        return None, None
    latest = max(cands, key=lambda p: p.stat().st_mtime)
    return latest, d


def scan_session(path: Path) -> dict:
    """扫描 WorkBuddy 会话 JSONL → 客观读数（行为与旧版完全一致）。"""
    r = _new_obj()
    if not path or not path.is_file():
        return r
    reads = []
    write_targets = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    r["parse_errors"] += 1
                    continue
                t = d.get("type")
                ts = d.get("timestamp")
                if isinstance(ts, (int, float)):
                    r["ts_min"] = ts if r["ts_min"] is None else min(r["ts_min"], ts)
                    r["ts_max"] = ts if r["ts_max"] is None else max(r["ts_max"], ts)
                if t == "message" and d.get("role") == "user":
                    r["user_turns"] += 1
                elif t == "function_call":
                    r["tool_calls"] += 1
                    name = d.get("name")
                    try:
                        a = json.loads(d.get("arguments") or "{}")
                    except Exception:
                        a = {}
                    if name == "Read":
                        fp = a.get("file_path")
                        if fp:
                            reads.append(fp)
                    if name in ("Write", "Edit", "MultiEdit"):
                        r["write_calls"] += 1
                        write_targets.append(
                            str(a.get("file_path") or a.get("path") or "")[:120])
                elif t == "function_call_result":
                    r["output_bytes"] += len(line)
    except OSError:
        return r
    # WorkBuddy 旧版固定按毫秒计算 wall_minutes（保留原行为）
    if r["ts_min"] is not None and r["ts_max"] is not None:
        r["wall_minutes"] = round((r["ts_max"] - r["ts_min"]) / 60000.0, 1)
    r["read_total"] = len(reads)
    c = Counter(reads)
    dup = {k: v for k, v in c.items() if v > 1}
    r["read_dup_paths"] = len(dup)
    r["read_dup_detail"] = dup
    r["write_targets"] = write_targets
    return r


# ============================================================
#  Anthropic Messages 风格 JSONL（Qoder / QoderWorkCN / QwenWorkCN）
# ============================================================

def scan_anthropic_jsonl(path: Path) -> dict:
    """Qoder 家族 JSONL：每行 type∈{user, assistant, ...}，
    assistant.content[].type=tool_use  → tool_calls
    user.content[].type=tool_result    → output_bytes
    """
    r = _new_obj()
    if not path or not path.is_file():
        return r
    reads = []
    write_targets = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    r["parse_errors"] += 1
                    continue
                ts = d.get("timestamp")
                if isinstance(ts, (int, float)):
                    r["ts_min"] = ts if r["ts_min"] is None else min(r["ts_min"], ts)
                    r["ts_max"] = ts if r["ts_max"] is None else max(r["ts_max"], ts)
                t = d.get("type")
                msg = d.get("message") or {}
                content = msg.get("content")
                if t == "user":
                    if isinstance(content, list):
                        real_user = False
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            it = item.get("type")
                            if it == "tool_result":
                                tc = item.get("content")
                                if isinstance(tc, str):
                                    r["output_bytes"] += len(tc)
                                elif isinstance(tc, list):
                                    for sub in tc:
                                        if isinstance(sub, dict) and sub.get("type") == "text":
                                            r["output_bytes"] += len(sub.get("text") or "")
                            elif it in ("text", "input_text"):
                                real_user = True
                        if real_user:
                            r["user_turns"] += 1
                    elif isinstance(content, str) and content.strip():
                        r["user_turns"] += 1
                elif t == "assistant":
                    if isinstance(content, list):
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            if item.get("type") == "tool_use":
                                r["tool_calls"] += 1
                                name = item.get("name") or ""
                                inp = item.get("input") or {}
                                if name == "Read":
                                    fp = inp.get("file_path")
                                    if fp:
                                        reads.append(fp)
                                if name in ("Write", "Edit", "MultiEdit"):
                                    r["write_calls"] += 1
                                    write_targets.append(
                                        str(inp.get("file_path") or inp.get("path") or "")[:120])
    except OSError:
        return r
    _finalize(r, reads, write_targets)
    return r


# ============================================================
#  OpenAI 风格 JSONL（DoubaoWork / AutoClaw 旧版）
# ============================================================

def scan_openai_jsonl(path: Path, *, msg_wrapper: bool = False) -> dict:
    """OpenAI 风格消息数组每行一条。

    msg_wrapper=False（DoubaoWork trajectory）：
        行 = {role, content, tool_calls, tool_call_id, ...}
        无 type 字段、无 timestamp。
    msg_wrapper=True（AutoClaw 旧版）：
        行 = {type:"message", timestamp:..., message:{role, content, tool_calls}}
    """
    r = _new_obj()
    if not path or not path.is_file():
        return r
    reads = []
    write_targets = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    r["parse_errors"] += 1
                    continue
                if msg_wrapper:
                    ts = d.get("timestamp")
                    msg = d.get("message") or {}
                    # AutoClaw legacy 的 timestamp 是 ISO 字符串，跳过数值判定
                    if isinstance(ts, (int, float)):
                        r["ts_min"] = ts if r["ts_min"] is None else min(r["ts_min"], ts)
                        r["ts_max"] = ts if r["ts_max"] is None else max(r["ts_max"], ts)
                else:
                    msg = d
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    r["user_turns"] += 1
                elif role == "assistant":
                    for tc in (msg.get("tool_calls") or []):
                        r["tool_calls"] += 1
                        fn = tc.get("function") or {}
                        name = fn.get("name") or ""
                        args_raw = fn.get("arguments") or "{}"
                        try:
                            args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                        except Exception:
                            args = {}
                        if name == "Read":
                            fp = args.get("file_path")
                            if fp:
                                reads.append(fp)
                        if name in ("Write", "Edit", "MultiEdit"):
                            r["write_calls"] += 1
                            write_targets.append(
                                str(args.get("file_path") or args.get("path") or "")[:120])
                elif role in ("tool", "toolResult"):
                    if isinstance(content, str):
                        r["output_bytes"] += len(content)
                    elif isinstance(content, list):
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                r["output_bytes"] += len(c.get("text") or "")
    except OSError:
        return r
    _finalize(r, reads, write_targets)
    return r


# ============================================================
#  SQLite 家族
# ============================================================

def scan_zcode(db: Path, ws: Path) -> dict:
    """ZCode CLI：~/.zcode/cli/db/db.sqlite
    session.directory = cwd；tool_usage 表直接有 output_bytes。
    """
    r = _new_obj()
    if not db.is_file():
        return r
    try:
        conn = _open_ro_sqlite(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, time_created, time_updated FROM session "
            "WHERE directory=? ORDER BY time_updated DESC LIMIT 1",
            (str(ws),))
        row = cur.fetchone()
        if not row:
            conn.close()
            return r
        sid = row["id"]
        r["ts_min"] = row["time_created"]
        r["ts_max"] = row["time_updated"]
        try:
            cur.execute("SELECT COUNT(*) c FROM turn_usage WHERE session_id=?", (sid,))
            r["user_turns"] = cur.fetchone()["c"]
        except sqlite3.Error:
            pass
        try:
            cur.execute(
                "SELECT COUNT(*) c, "
                "COALESCE(SUM(output_bytes),0) ob, "
                "SUM(CASE WHEN tool_name IN ('Write','Edit','MultiEdit') THEN 1 ELSE 0 END) wc, "
                "SUM(CASE WHEN tool_name='Read' THEN 1 ELSE 0 END) rt "
                "FROM tool_usage WHERE session_id=?", (sid,))
            row2 = cur.fetchone()
            r["tool_calls"] = row2["c"] or 0
            r["output_bytes"] = row2["ob"] or 0
            r["write_calls"] = row2["wc"] or 0
            r["read_total"] = row2["rt"] or 0
        except sqlite3.Error:
            pass
        conn.close()
    except sqlite3.Error:
        r["parse_errors"] += 1
    _finalize(r, [], [])
    return r


def scan_autoclaw_official(db: Path, ws: Path) -> dict:
    """AutoClaw-official：neutral_session_entries.payload 是 JSON 字符串。"""
    r = _new_obj()
    if not db.is_file():
        return r
    try:
        conn = _open_ro_sqlite(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT s.session_id, s.created_at, s.updated_at "
            "FROM work_sessions s JOIN work_workspaces w ON s.workspace_id=w.workspace_id "
            "WHERE w.root_path=? ORDER BY s.updated_at DESC LIMIT 1",
            (str(ws),))
        row = cur.fetchone()
        if not row:
            conn.close()
            return r
        sid = row["session_id"]
        r["ts_min"] = row["created_at"]
        r["ts_max"] = row["updated_at"]
        cur.execute(
            "SELECT entry_type, payload FROM neutral_session_entries WHERE session_id=?",
            (sid,))
        reads = []
        write_targets = []
        for er in cur.fetchall():
            et = er["entry_type"]
            try:
                payload = json.loads(er["payload"] or "{}")
            except Exception:
                r["parse_errors"] += 1
                continue
            data = payload.get("data") or {}
            if et == "request":
                r["user_turns"] += 1
            elif et == "tool_call":
                r["tool_calls"] += 1
                name = (data.get("toolName") or "").lower()
                inp = data.get("input") or {}
                if name == "read":
                    fp = inp.get("path") or inp.get("file_path")
                    if fp:
                        reads.append(fp)
                if name in ("write", "edit", "multiedit"):
                    r["write_calls"] += 1
                    write_targets.append(
                        str(inp.get("path") or inp.get("file_path") or "")[:120])
            elif et == "tool_result":
                content = data.get("content")
                if isinstance(content, str):
                    r["output_bytes"] += len(content)
        conn.close()
        _finalize(r, reads, write_targets)
    except sqlite3.Error:
        r["parse_errors"] += 1
    return r


def scan_copilot(db: Path, ws: Path) -> dict:
    """.copilot / Forge：sessions.cwd 直接查；session_files 有 tool_name + file_path。"""
    r = _new_obj()
    if not db.is_file():
        return r
    try:
        conn = _open_ro_sqlite(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, created_at, updated_at FROM sessions "
            "WHERE cwd=? ORDER BY updated_at DESC LIMIT 1", (str(ws),))
        row = cur.fetchone()
        if not row:
            conn.close()
            return r
        sid = row["id"]
        r["ts_min"] = row["created_at"]
        r["ts_max"] = row["updated_at"]
        try:
            cur.execute("SELECT COUNT(*) c FROM turns WHERE session_id=?", (sid,))
            r["user_turns"] = cur.fetchone()["c"]
        except sqlite3.Error:
            pass
        try:
            cur.execute(
                "SELECT COUNT(*) c, COALESCE(SUM(LENGTH(output)),0) ob "
                "FROM forge_trajectory_events WHERE session_id=?", (sid,))
            row2 = cur.fetchone()
            r["tool_calls"] = row2["c"] or 0
            r["output_bytes"] = row2["ob"] or 0
        except sqlite3.Error:
            pass
        try:
            cur.execute(
                "SELECT tool_name, file_path FROM session_files WHERE session_id=?", (sid,))
            reads = []
            write_targets = []
            for er in cur.fetchall():
                tn = (er["tool_name"] or "").lower()
                fp = er["file_path"] or ""
                if tn == "read":
                    reads.append(fp)
                if tn in ("write", "edit", "multiedit"):
                    r["write_calls"] += 1
                    write_targets.append(str(fp)[:120])
            _finalize(r, reads, write_targets)
        except sqlite3.Error:
            _finalize(r, [], [])
        conn.close()
    except sqlite3.Error:
        r["parse_errors"] += 1
    return r


# ============================================================
#  Provider 抽象
# ============================================================

class WorkBuddyProvider:
    key = "workbuddy"
    ws_specific = True   # probe 依赖 ws：projects/<encoded-ws> 目录

    def probe(self, ws: Path):
        d = WORKBUDDY_PROJECTS / encode_workspace(ws)
        if not d.is_dir():
            return None
        cands = list(d.glob("*.jsonl"))
        if not cands:
            return None
        return max(cands, key=lambda p: p.stat().st_mtime)

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_session(path)


class DoubaoWorkProvider:
    key = "doubaowork"
    ws_specific = False  # 全局启发式：完全不校验 ws，任何 ws 都返回同一最新 trajectory

    def probe(self, ws: Path):
        """按用户指定启发式：扫所有 sessions/<sid>/agents/<aid>/system/trajectory.jsonl，
        取 mtime 最新的那个。不校验 ws（因为 DoubaoWork 的 workspace 路径与
        .sessions 路径不重合，且这是当前端默认行为）。"""
        if not DOUBAOWORK_SESSIONS.is_dir():
            return None
        cands = list(DOUBAOWORK_SESSIONS.glob("*/agents/*/system/trajectory.jsonl"))
        if not cands:
            return None
        return max(cands, key=lambda p: p.stat().st_mtime)

    def scan(self, path: Path, ws: Path) -> dict:
        r = scan_openai_jsonl(path, msg_wrapper=False)
        # trajectory 无 timestamp，用文件 mtime 补 ts_max（wall_minutes 仍不准，属已知限制）
        if r["ts_max"] is None and path.is_file():
            mt = int(path.stat().st_mtime)
            r["ts_max"] = mt
            r["ts_min"] = mt
        return r


class QoderFamilyProvider:
    """Qoder / QoderWorkCN / QwenWorkCN 共用：Anthropic Messages 风格 JSONL。
    目录名编码规则：str(ws).replace('/','-')（保留前导 '-'）。"""

    ws_specific = True   # probe 依赖 ws：root/<encoded-ws> 目录

    def __init__(self, key: str, root: Path):
        self.key = key
        self.root = root

    def probe(self, ws: Path):
        if not self.root.is_dir():
            return None
        # 两种编码都试（Qoder 实测保留前导 '-'，WorkBuddy 风格 lstrip 也兜底）
        for name in (str(ws).replace("/", "-"),
                     str(ws).lstrip("/").replace("/", "-")):
            d = self.root / name
            if d.is_dir():
                cands = list(d.glob("*.jsonl"))
                if cands:
                    return max(cands, key=lambda p: p.stat().st_mtime)
        return None

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_anthropic_jsonl(path)


class ZCodeProvider:
    key = "zcode"
    ws_specific = True   # probe 依赖 ws：SQL WHERE directory=?

    def probe(self, ws: Path):
        if not ZCODE_DB.is_file():
            return None
        try:
            conn = _open_ro_sqlite(ZCODE_DB)
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM session WHERE directory=? ORDER BY time_updated DESC LIMIT 1",
                (str(ws),))
            row = cur.fetchone()
            conn.close()
            if row:
                return ZCODE_DB
        except sqlite3.Error:
            pass
        return None

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_zcode(path, ws)


class AutoClawOfficialProvider:
    key = "autoclaw_official"
    ws_specific = True   # probe 依赖 ws：SQL WHERE w.root_path=?

    def probe(self, ws: Path):
        if not AUTOCLAW_OFFICIAL_ROOT.is_dir():
            return None
        for db in AUTOCLAW_OFFICIAL_ROOT.glob("accounts/*/runtime/runtime.sqlite"):
            try:
                conn = _open_ro_sqlite(db)
                cur = conn.cursor()
                cur.execute(
                    "SELECT s.session_id FROM work_sessions s "
                    "JOIN work_workspaces w ON s.workspace_id=w.workspace_id "
                    "WHERE w.root_path=? ORDER BY s.updated_at DESC LIMIT 1",
                    (str(ws),))
                row = cur.fetchone()
                conn.close()
                if row:
                    return db
            except sqlite3.Error:
                continue
        return None

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_autoclaw_official(path, ws)


class CopilotProvider:
    key = "copilot"
    ws_specific = True   # probe 依赖 ws：SQL WHERE cwd=?

    def probe(self, ws: Path):
        if not COPILOT_DB.is_file():
            return None
        try:
            conn = _open_ro_sqlite(COPILOT_DB)
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM sessions WHERE cwd=? ORDER BY updated_at DESC LIMIT 1",
                (str(ws),))
            row = cur.fetchone()
            conn.close()
            if row:
                return COPILOT_DB
        except sqlite3.Error:
            pass
        return None

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_copilot(path, ws)


class AutoClawLegacyProvider:
    key = "autoclaw_legacy"
    ws_specific = True   # probe 依赖 ws：读首行 session 头过滤 cwd==ws
                         # （注：虽全盘扫，但按 ws 过滤 → 属 ws_specific，非全局启发式）

    def probe(self, ws: Path):
        """全扫 agents/*/sessions/*.jsonl，读首行 session 头找 cwd==ws。"""
        if not OPENCLAW_ROOT.is_dir():
            return None
        best = None
        best_mtime = 0.0
        for jf in OPENCLAW_ROOT.glob("agents/*/sessions/*.jsonl"):
            try:
                with jf.open("r", encoding="utf-8", errors="replace") as fh:
                    head = fh.readline()
                d = json.loads(head)
                if d.get("cwd") == str(ws):
                    mt = jf.stat().st_mtime
                    if mt > best_mtime:
                        best = jf
                        best_mtime = mt
            except Exception:
                continue
        return best

    def scan(self, path: Path, ws: Path) -> dict:
        return scan_openai_jsonl(path, msg_wrapper=True)


# ---------- 路由表（顺序=优先级） ----------
PROVIDERS = [
    WorkBuddyProvider(),
    DoubaoWorkProvider(),
    QoderFamilyProvider("qoder", QODER_PROJECTS),
    QoderFamilyProvider("qoder_cn", QODERCN_PROJECTS),
    QoderFamilyProvider("qwenwork_cn", QWENWORKCN_PROJECTS),
    ZCodeProvider(),
    AutoClawOfficialProvider(),
    CopilotProvider(),
    AutoClawLegacyProvider(),
]


def route(ws: Path):
    """按顺序 probe，第一个命中即返回 (provider_key, session_path)。"""
    for p in PROVIDERS:
        try:
            path = p.probe(ws)
        except Exception:
            path = None
        if path is not None:
            return p.key, path
    return None, None


def detect_all(ws: Path):
    """跑全部 provider 的 probe（不止首个命中），返回命中列表 [(key, path)]。

    供 --detect-provider 判定"唯一可信匹配 / 零匹配 / 多匹配歧义"。
    """
    hits = []
    global_hits = []
    for p in PROVIDERS:
        try:
            path = p.probe(ws)
        except Exception:
            path = None
        if path is None:
            continue
        # ws_specific 命中优先：只要有一个"真的按 ws 定位到"的 provider 命中，
        # 全局启发式（ws_specific=False，如 doubaowork 完全不校验 ws）一律不计入。
        if getattr(p, "ws_specific", True):
            hits.append((p.key, path))
        else:
            global_hits.append((p.key, path))
    # 全局启发式仅在**无任何 ws_specific 命中**时才作兜底
    # → 消除 doubaowork 恒定命中造成的假歧义 exit=4
    return hits if hits else global_hits


def cmd_detect_provider(ws: Path) -> int:
    """--detect-provider：仅在"唯一命中"时给出 key；零/多匹配拒绝（退出码区分）。

    退出码（install_reminder 据此决定是否自动接线）：
      0 = 唯一命中（输出 JSON provider/matches/session_file）
      3 = 零匹配（不自动写，转打印手动片段）
      4 = 多匹配歧义（不自动写，preferred 为路由首选项）
    """
    if not ws.is_dir():
        print(json.dumps({"provider": None, "matches": [],
                          "reason": "workspace-not-a-directory"}, ensure_ascii=False))
        return 3
    hits = detect_all(ws)
    keys = [k for k, _ in hits]
    if len(hits) == 1:
        print(json.dumps({"provider": keys[0], "matches": keys,
                          "session_file": str(hits[0][1])}, ensure_ascii=False))
        return 0
    if not hits:
        print(json.dumps({"provider": None, "matches": [],
                          "reason": "no-provider-matched"}, ensure_ascii=False))
        return 3
    print(json.dumps({"provider": None, "matches": keys,
                      "preferred": keys[0],
                      "reason": "ambiguous-multiple-matches"}, ensure_ascii=False))
    return 4


# ============================================================
#  客观工作单元时间线（v2.3.0 任务1：客观 streak 的数据源）
#  只读旁路：按行扫 JSONL 产出事件时间线，⛔ 不改动上面 9 个 provider 的
#  既有解析与计数逻辑（adapters/ 同样不碰）。SQLite provider 不走本函数。
# ============================================================

def _parse_ts(v):
    """事件时间戳 → epoch（毫秒/秒统一保留原值，比较只看同源差值）；不可解析返回 None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip():
        try:
            from datetime import datetime
            return datetime.fromisoformat(v.strip().replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            return None
    return None


def _is_write_call(name: str) -> bool:
    return str(name or "").lower() in ("write", "edit", "multiedit")


def collect_timeline(path: Path) -> list:
    """通用 JSONL 事件时间线 → [{"ts", "user", "tool", "write"}, ...]（按行序）。

    覆盖四种 JSONL 方言（不改 provider 解析逻辑，只做旁路观测）：
      · workbuddy        type=="function_call" / type=="message"+role
      · anthropic 家族    type=="assistant" + message.content[].type=="tool_use"
      · openai msg 包裹   message.tool_calls（autoclaw_legacy，timestamp 为 ISO 串）
      · openai 平铺       顶层 tool_calls / role（doubaowork trajectory）
    行缺 timestamp → 该事件 ts=None（切分时兜底，见 objective_streak）。
    """
    events = []
    if not path or not path.is_file():
        return events
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                msg = d.get("message") if isinstance(d.get("message"), dict) else {}
                ev = {"ts": _parse_ts(d.get("timestamp")),
                      "user": False, "tool": False, "write": False}
                # --- 用户轮 ---
                role = d.get("role") or msg.get("role")
                if role == "user":
                    c = msg.get("content") if msg else d.get("content")
                    if isinstance(c, list):
                        # 含 tool_result 的 user 行是工具回执，不是用户开口
                        ev["user"] = not any(
                            isinstance(i, dict) and i.get("type") == "tool_result"
                            for i in c)
                    else:
                        ev["user"] = True
                # --- 工具调用 ---
                names = []
                if d.get("type") == "function_call":          # workbuddy
                    names.append(d.get("name") or "")
                if d.get("type") == "assistant":              # anthropic 家族
                    content = msg.get("content")
                    if isinstance(content, list):
                        for it in content:
                            if isinstance(it, dict) and it.get("type") == "tool_use":
                                names.append(it.get("name") or "")
                for tc in (msg.get("tool_calls") or d.get("tool_calls") or []):
                    if isinstance(tc, dict):
                        fn = tc.get("function")
                        if isinstance(fn, dict):
                            names.append(fn.get("name") or "")
                if names:
                    ev["tool"] = True
                    ev["write"] = any(_is_write_call(n) for n in names)
                events.append(ev)
    except OSError:
        return []
    return events


def objective_streak(events: list, gap_min: float = UNIT_GAP_MIN):
    """客观 streak：工作单元切段 → 只数含 ≥1 次工具调用的单元（纯聊天段不计）
    → 尾部连续「有调用且零写盘」的单元数。

    分段主用**时间间隔**（相邻事件间隔 ≥ gap_min 分钟即切段）；
    无时间戳方言（如 doubaowork trajectory 全行无 timestamp）兜底按**用户轮边界**切段
    （每个用户开口开启一个单元）；两者都无从判定 → 返回 None（不可用，⛔ 不冒充 0）。
    """
    if not events:
        return None
    ts_count = sum(1 for e in events if e["ts"] is not None)
    units = []
    if ts_count >= 2:
        gap_ms = gap_min * 60000.0
        cur = {"tool": False, "write": False}
        prev_ts = None
        for e in events:
            if e["ts"] is not None and prev_ts is not None and (e["ts"] - prev_ts) >= gap_ms:
                units.append(cur)
                cur = {"tool": False, "write": False}
            if e["tool"]:
                cur["tool"] = True
            if e["write"]:
                cur["write"] = True
            if e["ts"] is not None:
                prev_ts = e["ts"]
        units.append(cur)
    else:
        # 兜底：按用户轮边界切段
        cur = None
        for e in events:
            if e["user"] or cur is None:
                if cur is not None:
                    units.append(cur)
                cur = {"tool": False, "write": False}
            if e["tool"]:
                cur["tool"] = True
            if e["write"]:
                cur["write"] = True
        if cur is not None:
            units.append(cur)
    countable = [u for u in units if u["tool"]]     # 纯聊天段不计
    streak = 0
    for u in reversed(countable):
        if u["write"]:
            break
        streak += 1
    return streak


# ============================================================
#  自报账 / 矛盾检测（与旧版一致）
# ============================================================

def handoff_state_path(ws: Path) -> Path:
    """定位自报账 state.json，与 handoff.py 的目录解析保持一致（生产-消费契约）。

    解析顺序：$HANDOFF_DIR（受控环境变量）> <ws>/handoff。
    ⛔ 不读旧的隐藏目录（分发包已删除该回退，三方一致）。
    """
    env = os.environ.get("HANDOFF_DIR")
    base = Path(env) if env else (ws / "handoff")
    return base / "state.json"


def read_handoff_state(ws: Path) -> dict:
    p = handoff_state_path(ws)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def objective_stall(obj: dict) -> dict:
    ts_min, ts_max = obj.get("ts_min"), obj.get("ts_max")
    w = obj.get("write_targets") or []
    if not ts_max:
        return {"available": False, "reason": "会话无时间戳数据"}
    if not w:
        return {"available": True, "stall_minutes": None,
                "reason": "本次会话零落盘类调用（Write/Edit/MultiEdit）",
                "write_calls": 0}
    span_min = obj.get("wall_minutes", 0.0)
    return {"available": True, "write_calls": obj.get("write_calls", 0),
            "session_span_min": span_min,
            "reason": f"本次会话共 {obj.get('write_calls',0)} 次落盘类调用"
                      f"（会话跨度 {span_min} 分钟）·非全停滞"}


def contradict(obj: dict, self_report: dict) -> list:
    out = []
    if not self_report:
        return out
    checks = self_report.get("checks") or []
    if not checks:
        return out

    verdicts = [c.get("verdict") for c in checks if c.get("verdict")]
    streak = self_report.get("no_artifact_streak")
    if verdicts and all(v == "HEALTHY" for v in verdicts):
        if isinstance(streak, int) and streak >= 3:
            out.append(
                f"自报 {len(verdicts)} 条全 HEALTHY，但 state.json 的 no_artifact_streak={streak} "
                f"（连续 {streak} 个工作单元无落盘产物）→ SKILL.md 硬触发第3条应判 L2"
            )

    miss = [k for k in ("artifacts", "hits", "verdict")
            if any(c.get(k) is None for c in checks)]
    if miss:
        out.append(f"自报账存在缺失字段：{'、'.join(miss)}（判官漏报职责的早期征兆）")

    if obj.get("tool_calls") and obj.get("tool_calls") > 0:
        rep = self_report.get("tool_calls")
        if isinstance(rep, int) and rep > 0:
            ratio = obj["tool_calls"] / rep
            if ratio >= 3:
                out.append(
                    f"客观 function_call={obj['tool_calls']} vs 自报 tool_calls={rep}"
                    f"（相差 {ratio:.1f} 倍）→ 自报严重失真"
                )
    return out


def resolve_streak(self_report: dict, obj: dict) -> tuple:
    """触发源回正（v2.3.0 任务2）：streak 取值 = 自报优先、客观兜底。

    · state.json 存在且含 no_artifact_streak → 用它，来源标 "self_report"；
    · 否则用任务 1 的客观 no_write_streak，来源标 "objective"（不可得时为 None，
      仍标 "objective"——枚举只此两值，值域靠 streak 本身表达）。
    """
    sr = (self_report or {}).get("no_artifact_streak")
    if isinstance(sr, int) and not isinstance(sr, bool):
        return sr, "self_report"
    ow = (obj or {}).get("no_write_streak")
    if isinstance(ow, int) and not isinstance(ow, bool):
        return ow, "objective"
    return None, "objective"


def packaging_advisory(obj: dict, self_report: dict) -> list:
    """sub-L2 临界区软信号：逼近 L2 但未达硬触发时的"是否打包"建议原因（白话）。

    v2.3.0 触发源回正（v2.1.x 的设计-实现脱节修复）：
      · 空转轴：streak 取值 = 自报（state.json no_artifact_streak）优先、客观兜底
        （resolve_streak，输出标 streak_source）；≥ STREAK_ASK_MIN → 询问行原因。
        ⛔ 无自报账的普通会话同样生效——旧版只认自报账，主场景完全失效。
      · 体量轴：user_turns ≥ TURN_VOLUME_MIN 或 wall_minutes ≥ SPAN_VOLUME_MIN →
        只进询问行，⛔ 绝不置 l2_objective_hit（拍板：体量轴仅出询问行不出催办行）。
    只报原因，不判档位——判定权在 agent（SKILL.md §1.1）。

    ⛔ v2.1.1 删除了原「单轮自报 large + 会话重复读取」子句：read_dup 是全会话
    累计量，客观上测不了"单轮"；"单轮 large+重读"只归 AI 自检路径判 L2
    （SKILL.md §1.3 升级条件）。hook 客观触发只剩空转轴与体量轴（均只出询问行
    或按 STREAK_L2_MIN 置 L2）。
    """
    out = []
    streak, _src = resolve_streak(self_report, obj)
    if isinstance(streak, int) and streak >= STREAK_ASK_MIN:
        if streak >= STREAK_L2_MIN:
            out.append(f"已连续 {streak} 个工作单元没有任何落盘产物"
                       f"（已达 L2 阈值 {STREAK_L2_MIN}）")
        else:
            out.append(f"已连续 {streak} 个工作单元没有任何落盘产物"
                       f"（L2 阈值是 {STREAK_L2_MIN}，正在逼近）")
    if isinstance(obj, dict):
        turns = obj.get("user_turns")
        if isinstance(turns, int) and turns >= TURN_VOLUME_MIN:
            out.append(f"本会话已达 {turns} 个用户轮（体量轴 ≥{TURN_VOLUME_MIN} 轮，仅作询问）")
        span = obj.get("wall_minutes")
        if isinstance(span, (int, float)) and span >= SPAN_VOLUME_MIN:
            out.append(f"本会话跨度已达 {span} 分钟（体量轴 ≥{SPAN_VOLUME_MIN} 分钟，仅作询问）")
    return out


def l2_objective_hit(obj: dict, self_report: dict) -> bool:
    """客观 L2 硬触发布尔：空转轴 streak ≥ STREAK_L2_MIN（SKILL.md §1.1 硬触发第3条），
    取值 = 自报优先、客观兜底（v2.3.0 回正）——不看自报 verdict，空转是客观形状。
    体量轴（轮数/跨度）⛔ 不进本判定，只出询问行。"""
    streak, _src = resolve_streak(self_report, obj)
    return isinstance(streak, int) and streak >= STREAK_L2_MIN


# ============================================================
#  main
# ============================================================

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(
        prog="baton_tick.py",
        description="baton 客观体量代理计数器（多客户端适配）。只读会话文件，不写客户端数据。")
    parser.add_argument("workspace", nargs="?", default=None,
                        help="workspace 目录（默认：当前工作目录）")
    parser.add_argument("--detect-provider", metavar="WS", default=None,
                        help="仅探测 WS 的 provider 并退出（0=唯一命中/3=零匹配/4=多匹配歧义）")
    args = parser.parse_args(argv)

    if args.detect_provider is not None:
        return cmd_detect_provider(Path(args.detect_provider).expanduser())

    ws = Path(args.workspace).expanduser() if args.workspace else Path.cwd()

    provider_key, sess = route(ws)
    if provider_key is None:
        # 全部 probe 未命中 → 兜底 WorkBuddy 标签（保持旧版不可用提示文案）
        provider_key = "workbuddy"
        sess = None

    obj = {}
    if sess is not None:
        for p in PROVIDERS:
            if p.key == provider_key:
                try:
                    obj = p.scan(sess, ws)
                except Exception:
                    obj = _new_obj()
                    obj["parse_errors"] += 1
                break

    rep = read_handoff_state(ws)

    # 任务1：客观 streak（时间线只读旁路；仅 JSONL provider 有时间线，SQLite → None）
    obj_streak = None
    if sess is not None and str(sess).lower().endswith(".jsonl"):
        try:
            obj_streak = objective_streak(collect_timeline(sess))
        except Exception:
            obj_streak = None
    if isinstance(obj, dict) and obj:
        obj["no_write_streak"] = obj_streak   # 填充 L66 死字段（None = 不可用，不冒充 0）

    # 任务2：触发源回正（自报优先、客观兜底）
    streak, streak_source = resolve_streak(rep, obj)
    cs = contradict(obj, rep)
    stall = objective_stall(obj)
    adv = packaging_advisory(obj, rep)
    l2_hit = l2_objective_hit(obj, rep)

    obj_available = bool(obj) and any(obj.get(k) for k in
                                       ("user_turns", "tool_calls", "output_bytes"))
    unavailable_reason = None
    if sess is None:
        enc = encode_workspace(ws)
        sdir = WORKBUDDY_PROJECTS / enc
        unavailable_reason = (
            f"该 workspace 无会话 JSONL（找 {sdir}·编码规则=去开头/后 /→-）。"
            "客观侧不可用 → 对撞降级为仅看自报=静默失效风险"
        )
    elif not obj_available:
        unavailable_reason = "会话文件存在但无任何可读记录（新会话/空会话？）→ 客观侧不可用"

    out = {
        "workspace": str(ws),
        "provider": provider_key,
        "session_file": str(sess) if sess else None,
        "objective_available": obj_available,
        "objective_unavailable_reason": unavailable_reason,
        "objective": obj,
        "objective_stall": stall,
        "self_report": {k: v for k, v in rep.items() if k != "checks"} if rep else None,
        "self_report_checks": len(rep.get("checks") or []) if rep else 0,
        "contradictions": cs,
        "streak": streak,
        "streak_source": streak_source,
        "packaging_advisory": {"reasons": adv},
        "l2_objective_hit": l2_hit,
        "decision": "agent（客观数据仅供对撞·交接判定权不在本脚本）",
        "boundary_note": "只读·不测token·不写文件·不阻断对话",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
