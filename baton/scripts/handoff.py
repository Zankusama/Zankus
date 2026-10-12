#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""handoff.py -- 工作交接（baton）的落盘 / 脱敏 / state 工具。

设计边界（与 SKILL.md §0 一致，⛔ 不要越界）：
  * 本脚本 **不执行压缩**，也无法拦截 harness 的压缩。它只落盘、扫描与指路。
  * 本脚本 **不测量 token**。绝不猜测 token 数并当作已测量上报。
    （--log 记的是「agent 自己数出来的工具调用次数 / 读取文件数 / 输出量级」，
      不是 token 估计——数自己做过的事 ≠ 猜 token。见 SKILL.md §1.3。）
  * 纯 python3 标准库（argparse / os / re / sys / json / datetime / pathlib）。
    ⛔ 不引入 pip 依赖。最低支持 Python 3.6（用 open(newline=)，不用
    write_text(newline=)，后者需要 3.10+）。实测环境以 TESTED.md 为唯一口径。
  * 无硬编码绝对路径。默认输出目录是**相对**目录 ./handoff/，
    可被环境变量 HANDOFF_DIR 或 --dir 覆盖。

这个脚本是**便利设施，不是前置依赖**：没有它，agent 也必须能按 SKILL.md §3
直接手写交接文档。所有功能都必须优雅降级。

v0.1 相对 v0 的关键取舍（详见 CHANGELOG.md）：
  * 脱敏的**第一优先级是"不改坏必须逐字保留的值"**（日期 / 单号 / 版本号 / 包名）。
    因此 PII 规则**默认关闭**，CREDENTIAL 只吃**高熵值**，键名命中只作分级加权。
  * 删掉了「距上次压缩步数」——无 hook 时恒不可达，留着等于把猜测写成事实。
  * 脱敏的唯一推荐实现点是**落盘后扫描并就地替换**（--scan / --redact-file），
    这样"模型直写文件"与"脚本落盘"两条路径收敛到同一行为。

用法速览:
  python3 handoff.py --help
  python3 handoff.py --selftest
  python3 handoff.py --redact-file ./handoff/HANDOFF-20260923-104500.md
  python3 handoff.py --scan --input ./handoff/HANDOFF-20260923-104500.md
  python3 handoff.py --write --input draft.md
  python3 handoff.py --log --turn 12 --verdict WATCH --hits 1 --tool-calls 7
  python3 handoff.py --state-show
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量 / 可调项
# ---------------------------------------------------------------------------

DEFAULT_DIR = "./handoff"           # 相对目录（2026-10-10 去隐藏化·维护者裁定·旧隐藏目录已迁移）
DIR_ENV = "HANDOFF_DIR"             # 覆盖输出目录
DISABLE_ENV = "HANDOFF_DISABLE"     # 置 1 则整体静默退出（便于团队统一关掉）
STATE_FILENAME = "state.json"
LATEST_FILENAME = "LATEST"          # 一行文本，指向最新那份交接文档的文件名
SCHEMA_VERSION = 1                  # v0.1

# 交接文档的固定字段（顺序即文档顺序，⛔ 不要改顺序）
# 依据：SKILL.md §3.1。
#   ⚠️ OPEN_QUESTIONS 必须排在最前 —— 它是"最该被看到的一行"，
#      用**位置**对抗位置效应（R3 §5.2 引 A1）。所以它在 HANDOFF_FIELDS 里 index 0，
#      而且按 §3.1 的口径，它是**正文第一行**，META 让它一让。
HANDOFF_FIELDS = (
    "OPEN_QUESTIONS",   # 正文第一行：留给下一棒的未答问题（≤5 条，按是否阻塞排序）
    "META",             # 生成时间 / 平台 / 档位 / 触发原因 / 下一棒用途 / 路径基准 / 交接链深度(可选)
    "CORE_GOAL",        # 任务目标与验收标准（引用用户原话，逐字）；分叉任务可多条
    "STAKES",           # 为什么急 / 不做的后果（逐字引用用户原话）
    "CONSTRAINTS",      # 会话内用户下达的一切指令与偏好（逐字，带轮次或时间）
    "CURRENT_STATE",    # 已完成 / 进行中 / 未开始；定位用符号名，行号标"截至"
    "WAITING_ON",       # 被阻塞：在等谁、等什么、到了怎么继续
    "KEY_FACTS",        # 数字/日期/ID/人名/金额/版本/报错码 + 称谓与术语口径，逐字
    "DECISIONS",        # 决策 + 理由（理由必写），带轮次或时间
    "DISCARDED",        # 已弃路径 + 为何弃；含"被用户否决的提案"
    "ERRORS",           # 未解决错误，报错原文逐字
    "ARTIFACTS",        # 产物清单：有路径的只写路径；无路径的逐字内联并标 [无路径]
    "NEXT_STEPS",       # 下一步，按依赖排序
    "SUGGESTED_SKILLS", # 该用什么能力（不依赖调用形态）
    "UNVERIFIED",       # 只属"我以为"的断言，⛔ 不要写成事实
)

# ---------------------------------------------------------------------------
# 脱敏 · 第一层：高置信凭据形态（命中即替换，无需上下文）
# ---------------------------------------------------------------------------
# 这些形态的字符集/长度本身已足以判定为凭据，误伤业务值概率极低。
# 顺序 = 优先级：越具体越靠前（保证 TOKEN=<JWT> 打上 JWT 标签而不是泛标签）。
# 私钥正文的一行：行内**只含** base64 字符（可选 `=` 填充），长度 ≥8。
# 这样"吃到文末"就不会顺手把后面的正文（如 `## 表格`、`EOF`）一起吞掉——
# 「有 BEGIN 无 END 也要替换」不需要以牺牲其余内容为代价。
_PRIV_BODY_LINE = r"^[ \t]*[A-Za-z0-9+/]{8,}={0,2}[ \t]*$"

HIGH_CONFIDENCE_RULES = (
    ("PRIVATE_KEY", re.compile(
        # 私钥块。⚠️ 半截块（只有 BEGIN 没有 END）只吃到"最后一个 base64 正文行"为止，
        # 既不泄漏私钥、也不越界吃掉文档其余部分。
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r"(?:(?:\r?\n)" + _PRIV_BODY_LINE + r")*"
        r"(?:(?:\r?\n)[ \t]*-----END [A-Z ]*PRIVATE KEY-----)?",
        re.MULTILINE,
    )),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    ("AWS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{16,}\b")),
    ("STRIPE_KEY", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("HF_TOKEN", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b")),
    ("BEARER", re.compile(
        # 保留 `Bearer` / `Basic` 这个方案名（它是可读上下文），只吃掉凭据本身。
        r"((?:Bearer|Basic)\s+)[A-Za-z0-9._\-+/=]{12,}",
        re.IGNORECASE,
    )),
)

# ---------------------------------------------------------------------------
# 脱敏 · 第二层：KEY=VALUE 形式（分级判定，⛔ 不许"看到长串就替换"）
# ---------------------------------------------------------------------------

# 键名分段（按 _ - . 切）后，某一段命中这些词 → 强凭据键类：**值再短也替换**。
# 理由：`PASSWORD=abc` 这种短口令是真凭据，漏掉就是真泄漏。
_STRICT_SEGMENTS = {
    "password", "passwd", "pwd", "passphrase", "passcode",
    "secret", "credential", "salt", "apikey", "api", "accesskey",
    "privatekey", "clientsecret", "signingkey", "encryptionkey",
}

# 某一段命中这些词 → 弱凭据键类：**只有值是高熵时**才替换。
# 理由：`TICKET_TOKEN=PR-1024` / `NEXT_TOKEN=step-3-fix-login` 是业务 ID，不是凭据。
_TOKENISH_SEGMENTS = {
    "token", "key", "auth", "bearer", "session", "sid", "cookie",
    "sign", "signature", "nonce", "cert", "jwt", "oauth",
    "refresh", "access", "csrf", "state_id",
}

# 键名**最后一段**命中这些词 → 该键装的是业务数据，不是凭据 → 一律不替换。
# 作用：把 `SECRET_ROTATION_DATE=2026-09-23` 从"secret 键"里救出来。
_BIZ_TAIL_SEGMENTS = {
    # 时间
    "date", "datetime", "time", "timestamp", "ts", "at", "day", "week",
    "month", "year", "hour", "minute", "second", "rotation", "rotated",
    "expiry", "expires", "expire", "ttl", "age", "deadline", "due",
    # 标识与刻度
    "id", "no", "num", "number", "count", "size", "length", "len",
    "total", "sum", "avg", "min", "max", "version", "ver", "rev",
    "build", "release", "index", "idx", "seq", "sequence", "code",
    "sha", "checksum", "digest", "ref", "reference", "port", "quota",
    "limit", "threshold", "budget", "timeout", "interval", "retry",
    "retries", "delay", "rate",
    # 位置与命名
    "url", "uri", "link", "href", "path", "dir", "directory", "file",
    "filename", "ext", "name", "label", "tag", "alias", "title", "slug",
    "prefix", "suffix", "pattern", "glob", "host", "hostname", "domain",
    "scheme", "endpoint", "base", "region", "zone", "city", "locale",
    "lang", "language", "env", "environment", "stage", "tier",
    # 分类与管理
    "type", "kind", "category", "status", "state", "mode", "level",
    "grade", "class", "priority", "flag", "enabled", "disabled",
    "active", "policy", "rule", "format", "encoding", "charset",
    "method", "protocol", "provider", "vendor", "service", "scope",
    "owner", "author", "maintainer", "team", "group", "account",
    "org", "organization", "user", "email", "mail", "phone", "mobile",
    "tel", "address", "country",
    "desc", "description", "note", "notes", "comment", "remark", "doc",
    "docs", "reason", "cause", "impact", "severity", "summary",
}

_ALL_MARKERS = _STRICT_SEGMENTS | _TOKENISH_SEGMENTS | _BIZ_TAIL_SEGMENTS

# 键名形如 KEY=VALUE / KEY: VALUE（可选引号）。值里排除空白、引号、逗号、分号、
# 反引号与占位符哨兵 \x00。
_KEYVALUE_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_.\-]*)"
    r"(?P<sep>\s*[:=]\s*)"
    r"(?P<q>[\"']?)"
    r"(?P<val>[^\s\"',;`\x00]+)"
)

# 明显不是"值"的占位（避免噪音替换）：空/占位词/变量引用/已是占位符
_PLACEHOLDER_VALUES = {
    "", "none", "null", "nil", "true", "false", "xxx", "xxxx", "xxxxx",
    "***", "****", "***redacted***", "redacted", "changeme", "todo",
    "<redacted>",
}

# 这些高置信规则需要保留 group(1) 作为可读前缀（只替换凭据本体）
_KEEP_PREFIX_GROUP = {"BEARER"}


def _norm_segment(seg: str) -> str:
    """归一化一个键名分段：小写、去空白、去简单复数。"""
    seg = seg.lower().strip()
    if seg in _ALL_MARKERS:
        return seg
    if seg.endswith("s") and seg[:-1] in _ALL_MARKERS:
        return seg[:-1]
    return seg


def classify_key(key: str) -> str:
    """判定 KEY=VALUE 的键名属于哪一类。

    返回：
      "biz"      —— 最后一段是业务数据标记 → **绝不替换**（第一优先级）
      "strict"   —— 含强凭据词 → 值再短也替换（覆盖 PASSWORD=abc）
      "tokenish" —— 含弱凭据词 → 仅当值高熵时替换（放过 TICKET_TOKEN=PR-1024）
      "none"     —— 不含任何凭据词 → 不动
    """
    segs = [_norm_segment(s) for s in re.split(r"[_.\-]", key) if s]
    if not segs:
        return "none"
    if segs[-1] in _BIZ_TAIL_SEGMENTS:
        # 业务数据尾标优先于一切 —— 这是"不动业务数字"的护栏。
        # 例：SECRET_ROTATION_DATE / API_KEY_VERSION / TOKEN_EXPIRES_AT
        return "biz"
    if any(s in _STRICT_SEGMENTS for s in segs):
        return "strict"
    if any(s in _TOKENISH_SEGMENTS for s in segs):
        return "tokenish"
    return "none"


def _is_high_entropy(value: str) -> bool:
    """弱凭据键类的值判定：**高熵才算凭据**。

    判据（满足其一）：
      1. 长度 ≥20，且同时含小写、大写、数字；
      2. 是 JWT 三段式。

    ⛔ 反例（必须判为"非凭据"，否则击穿逐字保留）：
      PR-1024 / WF-20260923-01 / step-3-fix-login / 2026-09-23 / v2.31.0
      —— 它们缺大写、或长度不足、或字符集太规则。
    """
    if len(value) < 20:
        return False
    if re.fullmatch(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}", value):
        return True
    has_lower = any(c.islower() for c in value)
    has_upper = any(c.isupper() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return has_lower and has_upper and has_digit


# ---------------------------------------------------------------------------
# 脱敏 · 第三层：PII（**默认关闭**，仅在强上下文命中时替换）
# ---------------------------------------------------------------------------
# 为什么默认关：邮箱 / 手机号 / 身份证号这三类正则**极易误伤业务标识**——
# 实测 `requests@2.31.0`（包名@版本）被当成邮箱、`100000202401011234`
#（机构码+日期+序号）被当成身份证、`13912345678`（快递单号）被当成手机号。
# 本 skill 的第一优先级是"关键信息不漏"，所以宁可默认不动，只在**强上下文**下动。
#
# 强上下文 = 显式键名 / 带 +86 前缀 / 带分隔符 / 校验位正确。
PII_RULES = (
    ("EMAIL", re.compile(
        # 显式键，或 TLD 为纯字母的真实邮箱形态（`pkg@1.2.3` 的 TLD 是数字 → 不命中）
        r"(?:(?<=[:=])\s*[\"']?|(?<![\w.@]))"
        r"([\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,24})"
    )),
    ("PHONE_CN", re.compile(
        r"(?:(?<=\+86)|(?<=86))[\s-]?(1[3-9]\d{9})(?!\d)"          # +86/86 前缀
        r"|(\b1[3-9]\d[-\s]\d{4}[-\s]\d{4}\b)"                      # 带分隔符
        r"|((?:phone|mobile|tel|cell|手机|手机号|联系电话)\s*[:=]\s*[\"']?"
        r"(?:\+?86[-\s]?)?(1[3-9]\d{9})[\"']?)"                     # 显式键
    )),
    ("ID_CN", re.compile(
        r"((?:id[_-]?card|idcard|identity|身份证|证件号)\s*[:=]\s*[\"']?"
        r"([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])[\"']?)"
        r"|((?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d))"
    )),
)


def _id_checksum_ok(num: str) -> bool:
    """GB 11643-1999 身份证校验位。用于把"恰好 18 位数字"与"真身份证"分开。"""
    if not re.fullmatch(r"[1-9]\d{16}[\dXx]", num):
        return False
    weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
    codes = "10X98765432"
    total = sum(int(num[i]) * weights[i] for i in range(17))
    return num[17].upper() == codes[total % 11]


# 占位符哨兵：替换先写成哨兵，最后统一还原。
# 目的（Q23）：防止"先被 JWT 规则替换、又被 CREDENTIAL 规则二次吃掉"，
# 把更有排查价值的标签覆盖成泛标签。
_SENTINEL_RE = re.compile(r"\x00HFRED\x00(\d+)\x00")


def redact(text: str, *, pii: bool = False) -> tuple[str, dict[str, int]]:
    """对 text 做凭据（+ 可选 PII）脱敏。

    返回 (脱敏后文本, 各类别命中计数)。计数用于写进 META，**不打印原文**。

    ⛔ 意图边界（本 skill 的第一优先级）：
       只替换上面规则命中的**凭据**。业务数字、金额、日期、issue/PR 号、
       commit sha、包名@版本、路径、行号、单号**一律原样保留**。
       为了"更安全"而扩大规则，就违反了 SKILL.md §3.2 的逐字保留契约。
       因此本实现的默认偏向是「**宁可漏替换，也不改业务值**」；
       代价是自定义凭据格式会漏 —— SKILL.md §5 已把"落盘后自己再扫一眼"写成硬要求。
    """
    counts: dict[str, int] = {}
    store: list[str] = []

    def _emit(label: str) -> str:
        counts[label] = counts.get(label, 0) + 1
        store.append(label)
        return "\x00HFRED\x00%d\x00" % (len(store) - 1)

    # Pass 1：高置信形态（顺序即优先级）
    # ⚠️ BEARER 规则用 group(1) 保留方案名（`Bearer `），只替换凭据本体。
    for label, pattern in HIGH_CONFIDENCE_RULES:
        if label in _KEEP_PREFIX_GROUP:
            text = pattern.sub(lambda m, _l=label: m.group(1) + _emit(_l), text)
        else:
            text = pattern.sub(lambda _m, _l=label: _emit(_l), text)

    # Pass 2：KEY=VALUE 分级判定
    def _kv_sub(m: "re.Match[str]") -> str:
        key, val = m.group("key"), m.group("val")
        kind = classify_key(key)
        if kind == "none" or kind == "biz":
            return m.group(0)
        if val.lower() in _PLACEHOLDER_VALUES:
            return m.group(0)
        if val.startswith("<") or val.startswith("${") or val.startswith("%"):
            return m.group(0)          # 已是占位符 / 变量引用
        if re.fullmatch(r"\{\{[^}]*\}\}", val):
            return m.group(0)          # 模板变量
        if kind == "strict":
            return "%s%s%s" % (m.group("key"), m.group("sep"), _emit("CREDENTIAL"))
        if kind == "tokenish" and _is_high_entropy(val):
            return "%s%s%s" % (m.group("key"), m.group("sep"), _emit("CREDENTIAL"))
        return m.group(0)

    text = _KEYVALUE_RE.sub(_kv_sub, text)

    # Pass 3：PII（默认关；开启时也只吃强上下文命中）
    if pii:
        for label, pattern in PII_RULES:
            def _pii_sub(m: "re.Match[str]", _l: str = label) -> str:
                # ID_CN 的裸 18 位分支要过校验位
                if _l == "ID_CN":
                    groups = [g for g in m.groups() if g]
                    digits = [g for g in groups if re.fullmatch(r"[1-9]\d{16}[\dXx]", g)]
                    if digits and not _id_checksum_ok(digits[-1]):
                        return m.group(0)
                return _emit(_l)

            text = pattern.sub(_pii_sub, text)

    # Pass 4：还原哨兵 → 带「类型 + 用途」的替换标记。
    # ⚠️ 替换**不得无声**：接手方必须能看出"这里原本有个值、且它是什么类型、
    #    原值去原会话里找"。所以不是裸 <REDACTED>，而是带用途槽位的形态。
    def _restore(m: "re.Match[str]") -> str:
        return "<REDACTED:%s｜原值用途：见原会话>" % store[int(m.group(1))]

    text = _SENTINEL_RE.sub(_restore, text)
    return text, counts


def scan_only(text: str, *, pii: bool = False) -> dict[str, int]:
    """只体检不替换。用于 --scan：落盘后自查。

    TODO(v1): 这一层应当在 SKILL.md 的 L1 轻检里被复用，
              但**不允许**因此新增一次模型往返。见 SKILL.md §6 反模式。
    """
    _redacted, counts = redact(text, pii=pii)
    return counts


# ---------------------------------------------------------------------------
# 目录 / 落盘 / LATEST 指针
# ---------------------------------------------------------------------------

def resolve_dir(cli_dir: str | None) -> Path:
    """决定输出目录。优先级：--dir > $HANDOFF_DIR > ./handoff

    ⛔ 不做任何绝对路径硬编码；返回的是用户给的原样路径。
    团队分发场景下，用户在仓库根运行即得 <repo>/handoff/。
    """
    raw = cli_dir or os.environ.get(DIR_ENV) or DEFAULT_DIR
    return Path(raw)


def ensure_dir(path: Path) -> Path:
    """创建输出目录（含父目录）。已存在则静默通过。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp_slug(now: datetime | None = None) -> str:
    """本地时间戳片段，用于文件名：YYYYMMDD-HHMMSS。"""
    now = now or datetime.now()
    return now.strftime("%Y%m%d-%H%M%S")


def iso_now() -> str:
    """ISO 8601 带时区，供 META 使用（逐字保留日期，⛔ 不要简化格式）。"""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_text_lf(path: Path, text: str) -> None:
    """统一 UTF-8 + LF 落盘，避免跨端换行差异。

    ⛔ 用 open(..., newline="\\n") 而不是 Path.write_text(newline=)：
       后者的 newline 参数需要 Python ≥3.10，低版本环境会直接 TypeError 崩掉。
    """
    with open(str(path), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def update_latest(out_dir: Path, target: Path) -> Path:
    """维护 handoff/LATEST 指针（UX-U3/U14）。

    内容就是最新交接文档的**文件名**一行。resume 时先读它，避免用户面对
    5 份时间戳文件不知道接哪份。⛔ 指针只在**成功落盘**后写。
    """
    latest = out_dir / LATEST_FILENAME
    _write_text_lf(latest, target.name + "\n")
    return latest


def read_latest(out_dir: Path) -> Path | None:
    """读 LATEST 指针；无/失效则回退到目录下时间戳最新的 HANDOFF-*.md。"""
    latest = out_dir / LATEST_FILENAME
    if latest.exists():
        try:
            name = latest.read_text(encoding="utf-8").strip()
        except OSError:
            name = ""
        if name:
            cand = out_dir / name
            if cand.exists():
                return cand
    cands = sorted(out_dir.glob("HANDOFF-*.md"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def write_handoff(
    content: str,
    out_dir: Path,
    *,
    pii: bool = False,
    stem: str | None = None,
) -> tuple[Path, dict[str, int]]:
    """把交接文档内容脱敏后落盘，返回 (写入路径, 脱敏计数)。

    行为契约：
      * 脱敏默认开启，但**只脱敏凭据**，且 PII 只有显式 --pii 才动（v0.1 变更）。
      * 文件名 HANDOFF-<YYYYMMDD-HHMMSS>[-<slug>].md；同秒冲突时追加 -1/-2。
      * 落盘成功后同步写 handoff/LATEST。
      * ⛔ 不做 markdown 结构校验、不做 schema 强校验——
        schema 是 SKILL.md 的契约，交给模型遵守；脚本越俎代庖会破坏可移植性。
        （TODO(v1): 若要校验，只做"缺字段就 warn 到 stderr"，绝不 fail。）

    ⚠️ 本函数是**次要路径**。首选路径是：agent 用自己的文件写入工具直写
       ./handoff/HANDOFF-<ts>.md，然后跑 --redact-file 就地脱敏。
       原因见 SKILL.md §4 步骤 5（避免明文草稿留在磁盘上）。
    """
    ensure_dir(out_dir)
    redacted, counts = redact(content, pii=pii)

    slug = stem or timestamp_slug()
    target = out_dir / ("HANDOFF-%s.md" % slug)
    n = 1
    while target.exists():
        target = out_dir / ("HANDOFF-%s-%d.md" % (slug, n))
        n += 1

    _write_text_lf(target, redacted)
    update_latest(out_dir, target)
    return target, counts


def redact_file(path: Path, *, pii: bool = False) -> tuple[Path, dict[str, int]]:
    """**就地**脱敏一个已落盘的交接文档（v0.1 新增，Q7/Q8 的收敛点）。

    为什么这是推荐路径：
      * "模型直写文件"与"脚本落盘"两条路径在脱敏上收敛到同一行为；
      * 不需要把整份文档塞进 stdin（v0 那条推荐命令会挂起或被 shell 注入）；
      * 不会在磁盘上多留一份明文草稿。
    """
    text = path.read_text(encoding="utf-8")
    redacted, counts = redact(text, pii=pii)
    if redacted != text:
        _write_text_lf(path, redacted)
    return path, counts


# ---------------------------------------------------------------------------
# state（自检回查日志 / 客观体量代理）
# ---------------------------------------------------------------------------
# ⚠️ v0.1 **删除**了 v0 的 steps_since_compact / last_compaction_turn：
#    无 hook 时"怎么知道刚压缩了"没有答案 → 该信号恒不可达。
#    保留一个"看起来有、实际恒假"的信号，正好落进 SKILL.md §6 反模式里的
#    「把猜测写成事实」。详见 CHANGELOG.md。

def state_path(out_dir: Path) -> Path:
    return out_dir / STATE_FILENAME


def load_state(out_dir: Path) -> dict:
    """读取 state.json。文件不存在或损坏 → 返回空 state（⛔ 不抛异常、不阻塞交接）。"""
    path = state_path(out_dir)
    if not path.exists():
        return {"schema": SCHEMA_VERSION}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 静默降级：state 丢了也不该影响交接本身
        return {"schema": SCHEMA_VERSION, "state_corrupted": True}


def save_state(out_dir: Path, state: dict) -> Path:
    ensure_dir(out_dir)
    path = state_path(out_dir)
    state["schema"] = SCHEMA_VERSION
    state["updated_at"] = iso_now()
    _write_text_lf(path, json.dumps(state, ensure_ascii=False, indent=2))
    return path


def update_state(
    out_dir: Path,
    *,
    turn: int | None = None,
    hits: int | None = None,
    verdict: str | None = None,
    tool_calls: int | None = None,
    files_read: int | None = None,
    output_scale: str | None = None,
    artifacts: int | None = None,
    note: str | None = None,
) -> dict:
    """追加一条自检记录（L0 静默记账，写文件不算出声，不破静默）。

    字段语义（对应 SKILL.md §1.2 / §1.3）：
      turn          —— 当前用户轮数（agent 自报；零歧义）
      hits          —— 本次自检命中的**症状类别数**（0–5，不是 15 个勾选框）
      verdict       —— HEALTHY / WATCH / DEGRADED / CRITICAL
      tool_calls    —— 本工作单元 agent 自己数出来的工具调用次数（客观代理）
      files_read    —— 本工作单元读取的文件数（客观代理）
      output_scale  —— 本工作单元累计工具输出量级（small / medium / large）
      artifacts     —— 本工作单元新增/修改的落盘产物数（用于算"停滞连续段"）
      note          —— 一句话补充（可选）

    ⚠️ 这里**刻意不实现**任何"≥N 次就触发交接"的判定逻辑：
       该维度无任何来源给出阈值（负结论成立）。触发判断留给模型，
       脚本只做记账。⛔ 不要在这个文件里加阈值门禁。
    """
    state = load_state(out_dir)

    if turn is not None:
        state["turn"] = turn
    if verdict is not None:
        state["verdict"] = verdict
    if tool_calls is not None:
        state["tool_calls"] = tool_calls
    if files_read is not None:
        state["files_read"] = files_read
    if output_scale is not None:
        state["output_scale"] = output_scale

    # "连续多少个工作单元没有落盘产物"：机械记账，供 agent 自己判断是否升级。
    # ⛔ 脚本只报数，不做判断（阈值判断见 SKILL.md §1.3，由模型执行）。
    if artifacts is not None:
        state["artifacts"] = artifacts
        state["no_artifact_streak"] = (state.get("no_artifact_streak", 0) + 1) if artifacts == 0 else 0

    rec = {
        "at": iso_now(),
        "turn": turn,
        "hits": hits,
        "verdict": verdict,
        "tool_calls": tool_calls,
        "files_read": files_read,
        "output_scale": output_scale,
        "artifacts": artifacts,
    }
    if note:
        rec["note"] = note

    hist = state.setdefault("checks", [])
    hist.append(rec)
    del hist[:-20]  # 只留最近 20 条，防 state 自己膨胀

    save_state(out_dir, state)
    return state


# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

_OPEN_QUESTION_LINE = re.compile(r"^\s*(?:>\s*)?未答问题[^\uFF1A:]*[：:]\s*(.*)$", re.MULTILINE)


def extract_open_question(path: Path) -> str:
    """从已落盘文档里抽出第一行未答问题（Q5：resume 指路不得丢掉第一价值项）。

    兼容两种写法：
      `未答问题：…` / `> 未答问题｜…`；取第一条非 `none` 的。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for m in _OPEN_QUESTION_LINE.finditer(text):
        val = m.group(1).strip().strip("*` ")
        if val and val.lower() not in ("none", "无", "n/a"):
            return val
    return ""


def print_resume(path: Path, *, open_question: str = "") -> None:
    """打印路径 + resume 指路 + 未答问题（≤3 行，SKILL.md §4 步骤 8）。

    ⛔ 纪律：**指向文件路径，不要在这里回贴交接内容**。
       含反引号或 $(...) 的内容被塞进 shell 命令会静默截断（不报错）。
    ⚠️ 路径一律打印 resolve() 出来的**绝对路径**（绝对路径是运行时产生的，
       不违反"无硬编码绝对路径"）—— 否则 cwd 一漂，下一棒就找不到文件。
    """
    try:
        shown = path.resolve()
    except OSError:
        shown = path
    print("交接文档：%s" % shown)
    print("新会话接法：把上面这个路径发给我，或直接说 resume。")
    print("未答问题：%s" % (open_question or "（见文档第一行）"))


def build_resume_command(path: str | os.PathLike[str]) -> str:
    """生成给下一棒用的 resume 指路串（供脚本或 agent 直接引用）。"""
    return "读这份交接文档继续：%s" % path


# ---------------------------------------------------------------------------
# 回归样本（第一优先级的可复跑证据）
# ---------------------------------------------------------------------------

# 必须**原样保留**的样本：(说明, 文本)
PRESERVE_CASES = (
    ("包名@版本", "requests@2.31.0"),
    ("含日期的 18 位单号", "100000202401011234"),
    ("*_DATE=YYYY-MM-DD", "SECRET_ROTATION_DATE=2026-09-23"),
    ("*_TOKEN=<业务ID>", "TICKET_TOKEN=PR-1024"),
    ("*_TOKEN=<业务ID>", "NEXT_TOKEN=step-3-fix-login"),
    ("*_TOKEN=<业务ID>", "WORKFLOW_TOKEN=WF-20260923-01"),
    ("金额", "ORDER_AMOUNT=48500.00"),
    ("24 小时制时间戳", "2026-09-23T10:22:16+08:00"),
    ("issue/PR 号", "issue=#1024"),
    ("commit sha", "commit=2eb98a51b97bb5bac461a26ad14828eeac827909"),
    ("范围版本", "@types/node@20.11.0"),
    ("报错码", "errno=ECONNREFUSED"),
    ("文件路径+行号", "src/auth/login.ts:145"),
)

# 必须**被替换**的样本：(说明, 文本, 期望标签)
REDACT_CASES = (
    ("高熵 token", "SESSION_TOKEN=aB3xK9mN2pQ7rT5vW8yZ1cD4fG6hJ0kL", "CREDENTIAL"),
    ("JWT", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk", "JWT"),
    ("短口令（strict 键类）", "PASSWORD=abc", "CREDENTIAL"),
    ("半截私钥（无 END）", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA", "PRIVATE_KEY"),
    ("AWS key", "AKIAIOSFODNN7EXAMPLE", "AWS_KEY"),
    ("GitHub PAT", "ghp_aB3xK9mN2pQ7rT5vW8yZ1cD4fG6hJ0kLmnop", "GITHUB_TOKEN"),
    ("Bearer", "Authorization: Bearer aB3xK9mN2pQ7rT5vW8yZ1cD4", "BEARER"),
)


def selftest(verbose: bool = True) -> int:
    """跑"逐字保留 + 真凭据替换"回归样本。退出码 0=全通 / 1=有失败。

    存在意义（R-Q1 第 4 点）："逐字保留"是本 skill 的第一优先级，
       不能只是一句纸面承诺 —— 它必须有一条可复跑的证据。
       实测环境以 TESTED.md 为唯一口径，改坏立刻红。
    """
    failures: list[str] = []

    for desc, sample in PRESERVE_CASES:
        out, counts = redact(sample)
        ok = out == sample
        if not ok:
            failures.append("应原样保留却被改动：[%s] %r -> %r  %s" % (desc, sample, out, counts))
        if verbose:
            print("%s 保留 [%s] %s" % ("✅" if ok else "❌", desc, sample))

    for desc, sample, want in REDACT_CASES:
        out, counts = redact(sample)
        ok = sample not in out and want in out
        if not ok:
            failures.append("应被替换却未替换：[%s] %r -> %r  %s" % (desc, sample, out, counts))
        if verbose:
            print("%s 替换 [%s] %s" % ("✅" if ok else "❌", desc, out.splitlines()[0][:60]))

    # PII 默认关闭：这三条在默认路径下必须毫发无损
    for desc, sample in (
        ("订单流水号（默认不按身份证动）", "100000202401011234"),
        ("快递单号（默认不按手机号动）", "13912345678"),
        ("包名@版本（默认不按邮箱动）", "jest@29.7.0"),
    ):
        out, _ = redact(sample)
        ok = out == sample
        if not ok:
            failures.append("PII 默认关闭失效：[%s] %r -> %r" % (desc, sample, out))
        if verbose:
            print("%s 默认不误伤 [%s] %s" % ("✅" if ok else "❌", desc, sample))

    if failures:
        print("\n❌ 自检失败 %d 项：" % len(failures), file=sys.stderr)
        for f in failures:
            print("   - " + f, file=sys.stderr)
        return 1
    if verbose:
        print("\n✅ 自检全通（%d 条保留样本 + %d 条替换样本 + 3 条默认不误伤）"
              % (len(PRESERVE_CASES), len(REDACT_CASES)))
    return 0


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def _read_input(args: argparse.Namespace) -> tuple[str | None, int]:
    """读输入。返回 (内容, 退出码)；内容为 None 表示失败。

    ⚠️ `--input -` 只在 stdin 是**真实管道**时可用（例如 `cat 已落盘的文件 | ...`）。
       ⛔ 不要用未加引号的 heredoc 把文档喂进来 —— 内容里的反引号与 $(...)
       会被 shell 真的执行（命令注入 + 静默改内容）。首选路径见 SKILL.md §4 步骤 5。
    """
    if args.input == "-":
        if sys.stdin is None or sys.stdin.isatty():
            print("handoff: --input - 需要 stdin 是真实管道或重定向。"
                  "推荐改用：handoff.py --redact-file <已落盘路径>", file=sys.stderr)
            return None, 2
        return sys.stdin.read(), 0
    try:
        return Path(args.input).read_text(encoding="utf-8"), 0
    except OSError as exc:
        print("handoff: 读不到输入文件 %s：%s" % (args.input, exc), file=sys.stderr)
        return None, 2


def cmd_write(args: argparse.Namespace) -> int:
    """--write：从 --input 读内容 → 脱敏 → 落盘 → 写 LATEST → 打印绝对路径。"""
    content, code = _read_input(args)
    if content is None:
        return code
    if not content.strip():
        print("handoff: 输入为空，未落盘。", file=sys.stderr)
        return 2

    out_dir = resolve_dir(args.dir)
    path, counts = write_handoff(content, out_dir, pii=args.pii, stem=args.stem)

    if not args.quiet:
        _print_redact_summary(counts)
        print_resume(path, open_question=args.open_question or extract_open_question(path))
    return 0


def cmd_redact_file(args: argparse.Namespace) -> int:
    """--redact-file：就地脱敏已落盘的交接文档（**推荐路径**，Q7/Q8 收敛点）。"""
    path = Path(args.redact_file)
    if not path.exists():
        print("handoff: 找不到文件 %s" % path, file=sys.stderr)
        return 2
    path, counts = redact_file(path, pii=args.pii)
    if not args.quiet:
        _print_redact_summary(counts)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    """--scan：只体检查凭据，不落盘。退出码 0=干净 / 1=有命中（可当门禁）。"""
    content, code = _read_input(args)
    if content is None:
        return code
    counts = scan_only(content, pii=args.pii)
    if counts:
        summary = ", ".join("%s×%d" % (k, v) for k, v in sorted(counts.items()))
        print("命中凭据：%s" % summary)
        return 1
    print("未命中已知凭据模式（⛔ 非形式化保证，仍须人工扫一眼）")
    return 0


def cmd_state_show(args: argparse.Namespace) -> int:
    """--state-show：打印自检日志。查空时**非零退出 + stderr 指路**（Q16）。"""
    out_dir = resolve_dir(args.dir)
    state = load_state(out_dir)
    if not state or set(state) <= {"schema"}:
        print("handoff: %s 下没有 state 记录。" % out_dir.resolve(), file=sys.stderr)
        print("  可能原因：① 该目录从未跑过 --log；② 你在不同的 cwd 下运行"
              "（目录优先级：--dir > $HANDOFF_DIR > ./handoff）。", file=sys.stderr)
        return 1
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    """--log：静默追加一条自检记录（L0 也不出声，但**要留痕**以便事后回查）。

    ⚠️ 写文件不算出声 —— 它不破 SKILL.md §1.1 的 L0 静默默认。
    """
    out_dir = resolve_dir(args.dir)
    state = update_state(
        out_dir,
        turn=args.turn,
        hits=args.hits,
        verdict=args.verdict,
        tool_calls=args.tool_calls,
        files_read=args.files_read,
        output_scale=args.output_scale,
        artifacts=args.artifacts,
        note=args.note,
    )
    if not args.quiet:
        # 只回一行"已记账"，不是体检报告 —— 静默默认下这一行由 agent 自行吞掉。
        print("已记入 %s（共 %d 条）" % (state_path(out_dir), len(state.get("checks", []))))
    return 0


def cmd_latest(args: argparse.Namespace) -> int:
    """--latest：解析 resume 该读哪份文档（UX-U3 的解析顺序）。"""
    out_dir = resolve_dir(args.dir)
    if not out_dir.exists():
        print("handoff: %s 不存在，没有可接的交接文档。" % out_dir, file=sys.stderr)
        return 1
    target = read_latest(out_dir)
    if target is None:
        print("handoff: %s 下没有 HANDOFF-*.md。" % out_dir.resolve(), file=sys.stderr)
        return 1
    print(target.resolve())
    print("（来源：%s）" % ("LATEST 指针" if (out_dir / LATEST_FILENAME).exists() else "目录内 mtime 最新"))
    return 0


def cmd_fields(args: argparse.Namespace) -> int:
    """--fields：打印交接文档的固定 schema 字段顺序。

    意图：给其他 harness / 其他 agent 一个**无需读 SKILL.md 全文**的机器可读契约，
    也让"我漏了哪个字段"这件事可以被脚本而非模型来核对。
    """
    for i, name in enumerate(HANDOFF_FIELDS, 1):
        print("%2d. %s" % (i, name))
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    """--selftest：跑逐字保留 / 真凭据替换回归样本。"""
    return selftest(verbose=not args.quiet)


def _print_redact_summary(counts: dict[str, int]) -> None:
    if counts:
        summary = ", ".join("%s×%d" % (k, v) for k, v in sorted(counts.items()))
        print("已脱敏：%s（替换处已注明类型与原值用途；原值请回原会话查找）" % summary,
              file=sys.stderr)
    else:
        print("已脱敏：无命中（⛔ 这不代表没有凭据，请自行再扫一眼）", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff.py",
        description=(
            "工作交接（baton）落盘 / 脱敏 / state 工具。"
            "纯 python3 标准库（≥3.6），无硬编码绝对路径，只脱敏凭据、不动业务数字。"
            "⛔ 本脚本不能执行压缩，也不测量 token。"
        ),
        epilog=(
            "示例：\n"
            "  python3 handoff.py --help\n"
            "  python3 handoff.py --selftest\n"
            "  python3 handoff.py --redact-file ./handoff/HANDOFF-20260923-104500.md\n"
            "  python3 handoff.py --scan --input ./handoff/HANDOFF-20260923-104500.md\n"
            "  python3 handoff.py --write --input draft.md\n"
            "  python3 handoff.py --log --turn 12 --verdict WATCH --hits 1 --tool-calls 7\n"
            "  python3 handoff.py --latest\n"
            "  python3 handoff.py --state-show\n"
            "  python3 handoff.py --fields\n"
            "\n"
            "输出目录优先级：--dir > $HANDOFF_DIR > ./handoff\n"
            "置 HANDOFF_DISABLE=1 可整体静默关闭（--help 与 --selftest 仍然放行）。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--dir", metavar="DIR",
                        help="输出目录（默认 %s，可用环境变量 %s 覆盖）" % (DEFAULT_DIR, DIR_ENV))
    parser.add_argument("--quiet", action="store_true",
                        help="静默：只输出路径与 resume 指路，不打脱敏摘要")

    mode = parser.add_argument_group("模式（不指定则只打印 help）")
    mode.add_argument("--write", action="store_true", help="脱敏并落盘交接文档（次要路径）")
    mode.add_argument("--redact-file", metavar="PATH",
                      help="就地脱敏一个已落盘的交接文档（**推荐路径**）")
    mode.add_argument("--scan", action="store_true", help="只体检凭据、不落盘（退出码 0/1）")
    mode.add_argument("--latest", action="store_true", help="解析 resume 该读哪份文档")
    mode.add_argument("--state-show", action="store_true", help="打印自检日志")
    mode.add_argument("--log", action="store_true", help="静默追加一条自检记录")
    mode.add_argument("--fields", action="store_true", help="打印交接文档固定字段顺序")
    mode.add_argument("--selftest", action="store_true",
                      help="跑逐字保留 / 真凭据替换回归样本（退出码 0/1）")

    inp = parser.add_argument_group("输入")
    inp.add_argument("--input", metavar="PATH", default="-",
                     help="交接文档来源；'-' 表示 stdin（默认）")
    inp.add_argument("--stem", metavar="SLUG",
                     help="覆盖文件名时间戳片段（默认 YYYYMMDD-HHMMSS）")
    inp.add_argument("--open-question", metavar="TEXT", default="",
                     help="末行提示用：留给下一棒的未答问题")

    red = parser.add_argument_group("脱敏")
    red.add_argument("--pii", action="store_true",
                     help="额外脱敏 PII（邮箱/手机号/身份证），**只在强上下文命中**；"
                          "默认关闭，因为这几类正则极易误伤包版本号与单号")

    st = parser.add_argument_group("state / 自检记账")
    st.add_argument("--turn", type=int, help="当前用户轮数（agent 自报）")
    st.add_argument("--hits", type=int, choices=range(0, 6), metavar="0-5",
                    help="本次自检命中的**症状类别数**（0-5）")
    st.add_argument("--verdict", choices=["HEALTHY", "WATCH", "DEGRADED", "CRITICAL"],
                    help="本次自检结论")
    st.add_argument("--tool-calls", type=int, metavar="N",
                    help="本工作单元工具调用次数（agent 自己数的，不是 token 估计）")
    st.add_argument("--files-read", type=int, metavar="N",
                    help="本工作单元读取的文件数")
    st.add_argument("--output-scale", choices=["small", "medium", "large"],
                    help="本工作单元累计工具输出量级")
    st.add_argument("--artifacts", type=int, metavar="N",
                    help="本工作单元新增/修改的落盘产物数（用于算 no_artifact_streak）")
    st.add_argument("--note", metavar="TEXT", help="一句话补充")

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if os.environ.get(DISABLE_ENV) == "1":
        # 静默默认：被显式关闭时不出声、不做任何事。
        # ⚠️ 但 --help / --selftest 必须放行 —— 否则"关掉开关"会连带
        #    关掉使用者唯一的自诊断入口（v0 的实测缺陷，见 Q16）。
        if not ({"--help", "-h", "--selftest"} & set(argv)):
            return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.write:
        return cmd_write(args)
    if args.redact_file:
        return cmd_redact_file(args)
    if args.scan:
        return cmd_scan(args)
    if args.latest:
        return cmd_latest(args)
    if args.state_show:
        return cmd_state_show(args)
    if args.log:
        return cmd_log(args)
    if args.fields:
        return cmd_fields(args)
    if args.selftest:
        return cmd_selftest(args)

    # 无模式参数 → 打印 help（⛔ 不要改成"自动做点什么"）
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
