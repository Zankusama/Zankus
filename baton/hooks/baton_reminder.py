#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baton_reminder.py — baton 主动提醒 hook（运行时，可选增强件）。

定位：
  * 被宿主在合适事件（推荐 Stop）调用。读取客观数据与自报账，按信号层级双分支输出：
      - L2 级信号（l2_objective_hit / contradictions 含"应判 L2"）→ 催办一行：
        指示直接落盘交接文档（SKILL.md §1.1：L2 是主动义务，不问不请示）；
      - sub-L2 信号（packaging_advisory 临界区软信号 / 自报失真等数据质量问题）→ 询问一行：
        "是否打包"由用户定（与 SKILL.md §1.6 定稿文案同稿）。
    正常情况下静默。v2.3.0 起频控为 **1+1+静默**：每会话最多 2 次（第 2 次需
    距上次 ≥30 分钟且信号增强，换版文案点明具体信号），两次后静默；检测到
    交接文档落盘（LATEST 更新）重置计数。退出通道：行末附「（说「别提醒」本
    会话不再提醒）」，agent 识别后调 `--mute` 写 per-session 关闭 flag。
    埋点只计 exposure / handover_conversion / ignore 三个数，⛔ 不记 prompt。
  * **fail-open**：任何异常 / 超时 / 不可用都静默退出，绝不阻塞 agent。
  * 不需要也不接受 prompt 内容（无 --prompt 参数，P0-γ）；stdin 不读取。
  * 不做交接判定，只做"提示"；判定权仍在 agent。

用法：
  python3 baton_reminder.py [workspace]
  python3 baton_reminder.py --mute [workspace]        # 关闭本会话提醒
  python3 baton_reminder.py --unmute [workspace]      # 恢复提醒
  python3 baton_reminder.py --selfcheck
  python3 baton_reminder.py --selfcheck --manifest <path>
环境变量：
  BATON_WORKSPACE       覆盖 workspace（默认 cwd）
  BATON_TIMEOUT         运行 tick 的超时秒（默认 5）
  BATON_EXPECTED_HASH   外部提供的期望 hash（自检锚点，非同目录自证）
  BATON_MANIFEST        外部发布清单路径（JSON，含 reminder/tick hash）
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _baton_common as common  # noqa: E402

# 询问行：与 SKILL.md §1.6 同一行定稿，不临场自创；{reasons} 由 tick 的白话原因填充
REMINDER_ASK_LINE = "提醒：{reasons}。是否打包你定，说「交接」我出文档。"
# 催办行：L2 级信号专用——SKILL.md §1.1 规定 L2 是主动义务，此行指示直接打包、不再询问
REMINDER_L2_LINE = ("baton 对撞：已到必须交接的程度（{reasons}）。"
                    "接下来直接落盘交接文档并打印绝对路径，不用再等确认。")
# 第 2 次提醒（1+1+静默的"1"）：换版文案 + 点明具体信号（{n}=当前 streak）
REMINDER_ASK_LINE_V2 = ("提醒（第 2 次）：已连续 {n} 个工作单元未落盘，信号较上次增强。"
                        "是否打包你定，说「交接」我出文档。")
REMINDER_L2_LINE_V2 = ("baton 对撞（第 2 次）：已连续 {n} 个工作单元未落盘，已达必须交接的程度。"
                       "现在直接落盘交接文档并打印绝对路径，不用再等确认。")

# ============================================================
#  频控与退出通道常量（v2.3.0 任务3/4/5）
# ============================================================
# 每会话提醒上限：1 次常规 + 1 次升级 = 2 次，之后本会话静默（交接落盘则重置）
MAX_REMINDERS_PER_SESSION = 2      # 工程启发式（依据：证据报告 1+1+静默定稿；"每会话一次"无最优值证据）
# 二次提醒冷却：距上次提醒 ≥ 该分钟数，且信号增强（streak 增加）才出第 2 次
SECOND_COOLDOWN_MIN = 30           # 工程启发式（依据：证据报告；学术查无阈值；1+1+静默的 30-60 分钟带取下沿）
# 退出通道提示（逐字，附在每条提醒行末尾；agent 识别「别提醒」后调 --mute 写关闭 flag）
EXIT_HINT = "（说「别提醒」本会话不再提醒）"

# 频控状态文件（<ws>/.baton-state/<ws-hash>/<agent-id>/ 下；只计数，⛔ 不记 prompt）
STATE_NAME = "reminder_state.json"

DEFAULT_TIMEOUT = 5.0


def resolve_workspace(cli_ws: str | None) -> Path:
    raw = cli_ws or os.environ.get("BATON_WORKSPACE") or os.getcwd()
    return Path(raw).expanduser()


def run_tick(ws: Path, timeout: float) -> dict | None:
    """运行 tick 并解析 JSON；任何失败返回 None（fail-open）。"""
    tick = common.tick_path()
    if tick is None:
        return None
    try:
        proc = subprocess.run(
            [sys.executable, str(tick), str(ws)],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _fresh_state() -> dict:
    return {"count": 0, "last_at": None, "last_at_epoch": None, "last_streak": None,
            "muted": False, "exposure": 0, "handover_conversion": 0, "ignore": 0,
            "pending_exposure_epoch": None}


def _state_path(ws: Path) -> Path:
    return common.state_root(ws) / STATE_NAME


def _load_state(ws: Path) -> dict:
    st = _fresh_state()
    try:
        p = _state_path(ws)
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                st.update({k: data.get(k, st[k]) for k in st})
    except Exception:
        pass
    return st


def _save_state(ws: Path, st: dict) -> None:
    try:
        root = common.ensure_state(ws)
        p = root / STATE_NAME
        p.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        os.chmod(str(p), 0o600)
    except Exception:
        pass


def _handoff_dir(ws: Path) -> Path:
    env = os.environ.get("HANDOFF_DIR")
    return Path(env) if env else (Path(ws) / "handoff")


def _settle_handover(ws: Path, st: dict) -> bool:
    """交接落盘检测：LATEST 更新时间晚于未结清的曝光 → 记 handover_conversion、
    重置提醒计数（1+1+静默 的新循环）。返回是否发生状态变化。"""
    pending = st.get("pending_exposure_epoch")
    if not isinstance(pending, (int, float)):
        return False
    try:
        m = (_handoff_dir(ws) / "LATEST").stat().st_mtime
    except OSError:
        return False
    if m <= pending:
        return False
    st["handover_conversion"] = int(st.get("handover_conversion") or 0) + 1
    st.update({"pending_exposure_epoch": None, "count": 0,
               "last_at": None, "last_at_epoch": None, "last_streak": None})
    return True


def _is_l2(data: dict) -> bool:
    cs = [str(c) for c in (data.get("contradictions") or []) if c]
    return bool(data.get("l2_objective_hit")) or any("L2" in c for c in cs)


def build_reminder(data: dict) -> str | None:
    """双分支（对应 SKILL.md 两档语义；判定权仍不在本 hook，fail-open）：
      · L2 级信号（tick 的 l2_objective_hit，或 contradictions 文本含"应判 L2"）
        → 催办行：直接打包，不再询问；
      · sub-L2（临界区软信号 packaging_advisory / 自报失真、漏报等数据质量问题）
        → 询问行：是否打包用户定。
    streak 取值已由 tick 回正（自报优先、客观兜底，streak_source 标注）。
    结构不符 / 无信号一律返回 None（静默）。
    """
    if not isinstance(data, dict):
        return None
    cs = [str(c) for c in (data.get("contradictions") or []) if c]
    adv_raw = data.get("packaging_advisory")
    adv = [str(r) for r in ((adv_raw or {}).get("reasons") or []) if r]
    if _is_l2(data):
        reasons = "；".join(cs + adv) or "客观对撞命中 L2 硬触发"
        return REMINDER_L2_LINE.format(reasons=reasons)
    if cs or adv:
        return REMINDER_ASK_LINE.format(reasons="；".join(adv + cs))
    return None


def cmd_runtime(ws: Path, timeout: float) -> int:
    """fail-open：正常静默（0），需提醒时打印一行。

    1+1+静默（v2.3.0 任务3）：
      第 1 次 → 出声并记账；第 2 次需「距上次 ≥SECOND_COOLDOWN_MIN 且信号增强
      （streak 增加）」，换版文案点明具体信号；两次后本会话静默；
      检测到交接文档落盘（LATEST 更新）→ 重置计数。
    埋点（任务4，只计数不记 prompt）：exposure / handover_conversion / ignore。
    """
    try:
        data = run_tick(ws, timeout)
        line = build_reminder(data) if data is not None else None

        st = _load_state(ws)
        if _settle_handover(ws, st):
            _save_state(ws, st)

        if line is None:
            return 0
        if st.get("muted"):
            return 0

        now = time.time()
        n = int(st.get("count") or 0)
        streak = data.get("streak") if isinstance(data, dict) else None

        if n >= MAX_REMINDERS_PER_SESSION:
            return 0                      # 两次后本会话静默
        if n <= 0:
            text = line                   # 第 1 次
        else:
            last_epoch = st.get("last_at_epoch")
            cooled = (isinstance(last_epoch, (int, float))
                      and (now - last_epoch) >= SECOND_COOLDOWN_MIN * 60)
            prev_streak = st.get("last_streak")
            enhanced = (isinstance(streak, int) and isinstance(prev_streak, int)
                        and streak > prev_streak)
            if not (cooled and enhanced):
                return 0                  # 冷却未到 / 信号未增强 → 静默
            if not isinstance(streak, int):
                return 0                  # 换版文案要报具体信号，拿不到就不出声（不编数）
            tpl = REMINDER_L2_LINE_V2 if _is_l2(data) else REMINDER_ASK_LINE_V2
            text = tpl.format(n=streak)

        # 记账：新曝光前先结清上一笔（既未转化也未出第 2 次就被越过 → ignore）
        if isinstance(st.get("pending_exposure_epoch"), (int, float)):
            st["ignore"] = int(st.get("ignore") or 0) + 1
        st["count"] = n + 1
        st["exposure"] = int(st.get("exposure") or 0) + 1
        st["pending_exposure_epoch"] = now
        st["last_at"] = common.iso_now()
        st["last_at_epoch"] = now
        if isinstance(streak, int):
            st["last_streak"] = streak
        _save_state(ws, st)

        sys.stdout.write(text + EXIT_HINT + "\n")
    except Exception:
        # 运行时绝不因自身故障影响宿主
        return 0
    return 0


def cmd_set_mute(ws: Path, muted: bool) -> int:
    """退出通道（任务4）：agent 识别用户「别提醒」后调 --mute 写 per-session 关闭
    flag；--unmute 恢复。⛔ hook 自身不读 prompt（P0-γ 隐私边界不变）。"""
    try:
        st = _load_state(ws)
        st["muted"] = bool(muted)
        _save_state(ws, st)
    except Exception:
        return 0
    return 0


def _load_manifest() -> dict | None:
    path = os.environ.get("BATON_MANIFEST")
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cmd_selfcheck(manifest_path: str | None) -> int:
    """完整性自检：hash 仅与外部锚点比对；无外部锚点时明确声明非安全边界。

    期望 hash 来自：--manifest / BATON_MANIFEST / BATON_EXPECTED_HASH
    （外部签名 / 发布清单 / 只读信任源），杜绝同目录 hash 自证循环。
    """
    own = common.reminder_path()
    tick = common.tick_path()
    own_hash = common.file_sha256(own)
    tick_hash = common.file_sha256(tick) if tick else None

    manifest = None
    if manifest_path:
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print("selfcheck: 读不到清单：%s" % exc, file=sys.stderr)
            return 2
    if manifest is None:
        manifest = _load_manifest()

    print("reminder sha256: %s" % own_hash)
    if tick_hash:
        print("tick     sha256: %s" % tick_hash)

    def _expected_for(manifest: dict, basename: str, flat_key: str) -> str | None:
        """从 manifest 取期望 hash。支持两种形态：
          · flat：{"reminder_sha256": "...", "tick_sha256": "..."}
          · files map：{"files": {"hooks/baton_reminder.py": "...", ...}}
            （key 按 basename 或相对路径末段宽松匹配）
        """
        if flat_key in manifest:
            return manifest.get(flat_key)
        files = manifest.get("files") or {}
        if isinstance(files, dict):
            if basename in files:
                return files[basename]
            for k, v in files.items():
                if str(k).rstrip("/").endswith(basename):
                    return v
        return None

    if manifest is not None:
        want_own = _expected_for(manifest, "baton_reminder.py", "reminder_sha256")
        want_tick = _expected_for(manifest, "baton_tick.py", "tick_sha256")
        if want_own is None:
            print("selfcheck: 清单中缺少 baton_reminder.py 的期望 hash", file=sys.stderr)
            return 2
        ok = (want_own == own_hash) and (not tick_hash or want_tick == tick_hash)
        if not ok:
            print("❌ selfcheck: 与外部发布清单不一致（脚本可能被改动）", file=sys.stderr)
            return 1
        print("✅ selfcheck: 与外部发布清单一致")
        return 0

    expected = os.environ.get("BATON_EXPECTED_HASH", "").strip()
    if expected:
        if expected != own_hash:
            print("❌ selfcheck: 与外部 BATON_EXPECTED_HASH 不一致", file=sys.stderr)
            return 1
        print("✅ selfcheck: 与外部 BATON_EXPECTED_HASH 一致")
        return 0

    # 无任何外部锚点：仅完整性提示，不构成安全边界
    print("⚠️ 未配置外部信任锚（manifest / BATON_EXPECTED_HASH）。"
          "以上 hash 仅为完整性提示，非安全边界。")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="baton_reminder.py",
        description="baton 主动提醒 hook（运行时，fail-open；不含 prompt 传输）。")
    parser.add_argument("workspace", nargs="?", default=None,
                        help="workspace 目录（默认 cwd 或 BATON_WORKSPACE）")
    parser.add_argument("--selfcheck", action="store_true",
                        help="完整性自检（hash 与外部锚点比对）")
    parser.add_argument("--manifest", metavar="PATH", default=None,
                        help="外部发布清单（JSON，含 reminder/tick sha256）")
    parser.add_argument("--hook-marker", metavar="TEXT", default=None,
                        help="安装幂等标记（仅用于识别，运行时忽略）")
    parser.add_argument("--mute", action="store_true",
                        help="写 per-session 关闭 flag：本会话不再提醒（用户说「别提醒」时由 agent 调用）")
    parser.add_argument("--unmute", action="store_true",
                        help="撤销关闭 flag，恢复提醒")
    args = parser.parse_args(argv)

    if args.selfcheck:
        return cmd_selfcheck(args.manifest)

    ws = resolve_workspace(args.workspace)
    if args.mute or args.unmute:
        return cmd_set_mute(ws, bool(args.mute))

    try:
        timeout = float(os.environ.get("BATON_TIMEOUT", DEFAULT_TIMEOUT))
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    return cmd_runtime(ws, timeout)


if __name__ == "__main__":
    raise SystemExit(main())
