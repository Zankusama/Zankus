#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baton_delivery_guard.py — v4/D3 送达对账守卫（Stop 钩子·只登记不拦截·miss 时向 stderr 响亮告警）。

为什么存在：
  baton_reminder 的 stdout 只进模型、对人类不可见（v4/D1 实证）。D1 因此把提醒做成
  「AI 专用指令行 + 🎒 信封本体」两段式，要求 AI 把信封逐字贴进回复末尾。但"要求"
  本身可以被模型忽略——没有机器代价的义务只是建议。本守卫就是那个机器代价：
  Stop 时扫本轮回复文本，pending 已置位却查不到信封特征串 → 台账留痕。

纪律：
  * **只读只记，⛔不拦截不修改回复**：exit 恒 0，stdout 恒空（Stop 钩子的 stdout 会进模型，本守卫不往对话塞东西）；**miss 时向 stderr 响亮告警**（供运行时/代理捕获后驱动 AI 补贴信封），仍 fail-open 不阻塞宿主。
    进模型，本守卫不该往对话里塞东西）。
  * **fail-open**：stdin 缺失/非法/任何异常 → 静默退出 0，绝不阻塞宿主。
  * **空转可检**：拿不到回复文本时留痕但⛔不结账（分不清"没贴"还是"载荷没这个键"，
    判成漏贴=假红）。若无文本且从不留痕，"键名不对→全程零命中"这种失效永不显形
    （判例：doenglingz_level_declare_guard v1.0 因键名表漏 last_assistant_message
    而全程空转，v1.1 才修）。
  * **不误伤**：每笔曝光只对账一次（reconciled 幂等门）；超过新鲜窗的 pending 直接
    结清不判（多为同 workspace 别的会话留下的账）。
  * 隐私：只看特征串与计数，⛔不落盘回复正文。

用法：
  python3 baton_delivery_guard.py                 # 挂载形态：宿主经 stdin 传 JSON 载荷
  python3 baton_delivery_guard.py --stats [ws]    # 打印对账计数（供周报消费）
  python3 baton_delivery_guard.py --self-test
环境变量：
  BATON_WORKSPACE   载荷无 cwd 时的 workspace 回退
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _baton_common as common  # noqa: E402
import baton_reminder as rem  # noqa: E402

# 文本键表：与同域已成熟运行的 Stop 守卫逐键对齐（⛔不自拟——v1.0 的教训就是自拟键表漏了真键）
TEXT_KEYS = ("last_assistant_message", "responseText", "text", "prompt", "content",
             "response", "message", "last_message", "responsePreview",
             "output", "assistant_message")

STDIN_MAX_BYTES = 4_000_000      # 载荷上限（防超大 stdin 拖死钩子）
PENDING_FRESH_MIN = 30.0         # 曝光后多久内仍算"本轮该贴"（跨会话错配的保险窗）
MAX_STDIN_KEYS_LOG = 24


def _read_payload() -> dict:
    try:
        raw = sys.stdin.read(STDIN_MAX_BYTES)
    except Exception:
        return {}
    if not raw or not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return obj if isinstance(obj, dict) else {}


def _get_text(obj: dict) -> str:
    for k in TEXT_KEYS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def _resolve_ws(obj: dict) -> Path:
    raw = obj.get("cwd") or os.environ.get("BATON_WORKSPACE") or os.getcwd()
    return Path(str(raw)).expanduser()


def reconcile(ws: Path, text: str, st: dict) -> str:
    """返回判定：ok / miss / no_text。no_text 不结账（假红比漏红更贵）。"""
    if not text:
        return "no_text"
    if common.ENVELOPE_MARK in text:
        rem.settle_into(st)       # 幂等记账：同一笔曝光只记一次 delivered
        return "ok"
    st["reconciled"] = st.get("pending_exposure_epoch")   # 本轮就是那笔曝光的答复
    return "miss"


def _handle(payload: dict, now: float | None = None) -> str:
    """一次对账：silent / already / expired / ok / miss / no_text。
    cmd_runtime 与自测走同一条路径——⛔不让自测只测零件、测不到真判定链。"""
    ws = _resolve_ws(payload)
    st = rem._load_state(ws)
    pending = st.get("pending_exposure_epoch")
    if not isinstance(pending, (int, float)):
        return "silent"
    now = now if now is not None else time.time()
    if (now - pending) > PENDING_FRESH_MIN * 60:
        # 陈旧 pending → 不判、就地结清，防别的会话的账长期挂着误伤本轮
        st["pending_exposure_epoch"] = None
        rem._save_state(ws, st)
        common.ledger(ws, "delivery_pending_expired")
        return "expired"
    if st.get("reconciled") == pending:
        return "already"          # 这笔曝光已对过账：Stop 每轮都跑，⛔不重复计

    text = _get_text(payload)
    verdict = reconcile(ws, text, st)
    if verdict == "no_text":
        keys = sorted(str(k) for k in payload)[:MAX_STDIN_KEYS_LOG]
        common.ledger(ws, "delivery_no_text keys=" + ",".join(keys))
        return "no_text"          # 不落账：留给下一轮 Stop 再对
    common.ledger(ws, "delivery_ok" if verdict == "ok" else "delivery_miss")
    if verdict == "miss":
        sys.stderr.write(
            "\n\n⚠️ [baton_delivery_guard] 送达漏贴：pending 曝光未结清，但本轮回复不含 🎒 信封特征串。"
            "这是送达失败——按 SKILL.md §1.6 硬规则，AI 必须在本轮或下一轮把信封补贴进可见回复，"
            "否则用户看不到提醒。已写台账 delivery_miss。\n\n")
    rem._save_state(ws, st)
    return verdict


def cmd_runtime() -> int:
    _handle(_read_payload())
    return 0


def cmd_stats(ws: Path) -> int:
    """对账计数：exposure/delivered 读 state，miss 从台账现算——
    台账是唯一事实源，⛔在 state 里另存一份会分叉。"""
    st = rem._load_state(ws)
    out = {k: st.get(k) for k in
           ("exposure", "delivered", "handover_conversion", "ignore", "count", "muted")}
    try:
        rows = [json.loads(l) for l in
                (common.state_root(ws) / "ledger.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, json.JSONDecodeError):
        rows = []
    for ev in ("delivery_miss", "delivery_ok", "delivery_no_text",
               "delivery_pending_expired"):
        out[ev] = sum(1 for r in rows if str(r.get("event", "")).startswith(ev))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def _self_test() -> int:
    """六案全打真判定链 _handle（⛔不只测零件）：ok/miss/no_text/silent/expired/already。"""
    import tempfile
    ws = Path(tempfile.mkdtemp(prefix="baton_guard_selftest_"))
    os.environ["BATON_WORKSPACE"] = str(ws)
    mark = common.ENVELOPE_MARK
    body = "正文若干。\n━━━ %s ━━━\n提醒：已连续 3 个工作单元未落盘。是否打包你定。" % mark
    now = time.time()
    # (名称, 载荷, 期望判定, pending 时刻, 特殊前置)
    cases = [
        ("S1 pending置位+回复含信封 → ok 且 delivered+1",
         {"cwd": str(ws), "last_assistant_message": body}, "ok", now, "fresh"),
        ("S2 pending置位+回复无信封 → miss",
         {"cwd": str(ws), "last_assistant_message": "普通回复没有信封"}, "miss", now, "fresh"),
        ("S3 pending置位+载荷无文本键 → no_text（不结账·可复检）",
         {"cwd": str(ws), "session_id": "x"}, "no_text", now, "fresh"),
        ("S4 无 pending → silent",
         {"cwd": str(ws), "last_assistant_message": body}, "silent", None, "fresh"),
        ("S5 pending 超新鲜窗 → expired（不误伤他会话的账）",
         {"cwd": str(ws), "last_assistant_message": "无信封"}, "expired",
         now - (PENDING_FRESH_MIN + 5) * 60, "fresh"),
        ("S6 同笔曝光二次 Stop → already（不重复计）",
         {"cwd": str(ws), "last_assistant_message": "无信封"}, "already", now, "reconciled"),
    ]
    fails = 0
    for name, payload, expect, pend_at, pre in cases:
        st = rem._fresh_state()
        if pre == "reconciled":
            st["pending_exposure_epoch"] = pend_at
            st["reconciled"] = pend_at
        elif pend_at is not None:
            st["pending_exposure_epoch"] = pend_at
        rem._save_state(ws, st)

        got = _handle(payload, now=now)
        ok = got == expect
        if ok and name.startswith("S1"):
            ok = int(rem._load_state(ws).get("delivered") or 0) == 1
        print(("  ✅ " if ok else "  ❌ ") + name + " → 实得 %s" % got)
        fails += 0 if ok else 1
    passed = len(cases) - fails
    print("self-test: %d/%d 通过" % (passed, len(cases)))
    return 1 if fails else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="baton_delivery_guard.py",
        description="baton 送达对账守卫（Stop·只登记不拦截·fail-open）")
    parser.add_argument("workspace", nargs="?", default=None,
                        help="--stats 用：workspace（默认 cwd 或 BATON_WORKSPACE）")
    parser.add_argument("--stats", action="store_true",
                        help="打印该 workspace 的对账计数（JSON 一行）")
    parser.add_argument("--self-test", action="store_true",
                        help="内置自测（只写系统临时目录，不动宿主配置）")
    parser.add_argument("--hook-marker", metavar="TEXT", default=None,
                        help="安装幂等标记（仅用于识别，运行时忽略）")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    try:
        if args.stats:
            return cmd_stats(rem.resolve_workspace(args.workspace))
        return cmd_runtime()
    except Exception:
        return 0                    # 守卫自身故障绝不阻塞宿主


if __name__ == "__main__":
    raise SystemExit(main())
