#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decision-record.py — 决策记录（DR）9字段 + 决策链可选字段：生成 / 校验 / HTML 单文件落盘

总案 v2.1 落位（D10/D20/F2/N2）：
  - DR9 契约与 SKILL.md / frameworks/fm-02 逐字一致
  - 决策链 = 可选字段：仅复合决策出现（值=关联 DR id 互引；写进"问题"字段会埋没审计线索，故独立成字段）
  - render 产出自包含 HTML 单文件（D10：阅读体验决定回看；内联 CSS、状态徽章含"快轨"橙标、内置复盘区）
  - 默认落盘 ./决策记录/（D20：用户工作区）；首次落盘前问一次，偏好存包外
  - 路径可配置（P2-3）：--out > 环境变量 PM_STRATEGIST_DR_DIR > 包外偏好文件 > 默认 ./决策记录

用法（脚本不在用户工程目录，须带 skill 目录前缀——先 `SKILL_DIR=~/.workbuddy/skills/pm-strategist` 再 `python3 "$SKILL_DIR/scripts/decision-record.py" …`）:
  python3 "$SKILL_DIR/scripts/decision-record.py" --template              # 打印文本模板（聊天内引导用）
  python3 "$SKILL_DIR/scripts/decision-record.py" <要点文件>               # 校验+渲染+落盘 HTML
  cat 要点.txt | python3 "$SKILL_DIR/scripts/decision-record.py" - --out /tmp/x
  python3 "$SKILL_DIR/scripts/decision-record.py" <要点文件> --stdout      # 只打印 HTML 不落盘
  python3 "$SKILL_DIR/scripts/decision-record.py" --self
退出码: 0=渲染成功; 1=缺必填/校验失败; 2=读入错误
"""
import sys, os, re, json, argparse, datetime, tempfile

DR_DATE = datetime.date.today().strftime("%Y%m%d")
FIELDS = ["问题", "选项", "决定", "依据", "反方意见", "风险", "假设清单", "复盘日期", "状态"]
REQUIRED = ["问题", "选项", "决定"]
CHAIN_FIELD = "决策链"
STATUS = ["草案", "已定", "复盘", "关闭"]
HINTS = {
    "问题": "一句决策问题（含场景号与决策者/截止时间）",
    "选项": "≥2个，必须含不做/维持现状",
    "决定": "用户拍板原文（以「用户拍板：」开头）；未拍板写推荐倾向",
    "依据": "引用哪个 ref/fm 的哪条（标注文件与条目）",
    "反方意见": "最强反方+什么数据/条件会推翻本决定",
    "风险": "6维度命中的风险点+验证方式（不替用户做风险结论）",
    "假设清单": "每条 ⚠️ 前缀「假设·待验证」；确无假设写「无——输入已全部确认」",
    "复盘日期": "YYYY-MM-DD",
    "状态": "草案/已定/复盘/关闭（快轨决策在状态后加「·快轨」= 橙色徽章）",
}
TEMPLATE = "# DR-%s-<slug>（日期已自动填入，编号/主题 slug 落盘时自动取自问题字段）\n" % DR_DATE + \
    "".join("- %s：%s\n" % (f, ("【待补充】" + HINTS[f])) for f in FIELDS) + \
    "- %s：（可选，仅复合决策填；引用关联 DR id，如 DR-20260902-001、DR-20260902-002）\n" % CHAIN_FIELD

_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 决策记录（DR）</title>
<style>
  :root{--ink:#1b1b1b;--muted:#807a70;--line:#e9e4da;--accent:#8a6d3b;--bg:#fbfaf7}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.8 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
  .wrap{max-width:840px;margin:0 auto;padding:56px 28px 80px}
  .kicker{color:var(--muted);font-size:12px;letter-spacing:.35em}
  h1{font-size:25px;font-weight:600;margin:10px 0 4px;letter-spacing:.02em;line-height:1.4}
  .meta{color:var(--muted);font-size:13px;margin-bottom:10px}
  .badges{margin:6px 0 26px}
  .badge{display:inline-block;font-size:12px;padding:3px 12px;border-radius:999px;border:1px solid var(--line);margin-right:8px;background:#fff}
  .badge.ok{background:#eef7ee;border-color:#bcd9bc}
  .badge.info{background:#eef2f8;border-color:#b9c9e0}
  .badge.draft{background:#f4f1ea}
  .badge.off{background:#f0f0f0;color:var(--muted)}
  .badge.fast{background:#fdf1df;border-color:#e5a13c;color:#92600a}
  table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line)}
  th,td{text-align:left;vertical-align:top;padding:12px 16px;border-bottom:1px solid var(--line)}
  tr:last-child th,tr:last-child td{border-bottom:none}
  th{width:96px;color:var(--muted);font-weight:500;white-space:nowrap}
  .review{margin-top:36px;border:1px dashed var(--line);background:#fff;padding:20px 22px}
  .review h2{font-size:14px;margin:0 0 8px;color:var(--accent);letter-spacing:.1em}
  .review p{color:var(--muted);font-size:13px;margin:4px 0}
  .foot{margin-top:30px;color:var(--muted);font-size:12px}
  @media print{body{background:#fff}.wrap{padding:12px}}
</style>
</head>
<body><div class="wrap">
<div class="kicker">PM-STRATEGIST · DECISION RECORD</div>
<h1>__TITLE__</h1>
<div class="meta">生成日期 __DATEFULL__ ｜ decision-record.py 渲染（总案 v2.1 · D10 HTML 单文件 / D20 默认落盘 ./决策记录/）</div>
<div class="badges">__BADGES__</div>
<table>
__ROWS__
</table>
<div class="review">
<h2>复盘区（复盘日期到时填）</h2>
<p>对照「当时前提 vs 实际结果」：证伪的假设回填检查单；前提过时 → 触发重验/更新前提库。方法见 fm-04复盘框架.md。</p>
<p>复盘结论追加于此区，不改动上方原始记录。</p>
</div>
<div class="foot">本文件为自包含 HTML 单文件，可直接归档/回看；来源标注遵循 SKILL.md 弹药引用纪律。</div>
</div></body></html>
"""


def parse_points(text):
    """key: value / key：value 逐行解析（全半角冒号兼容）；JSON 对象也认。"""
    pts = {}
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {k: str(v) for k, v in obj.items()}
    except (ValueError, TypeError):
        pass
    known = FIELDS + [CHAIN_FIELD]
    for line in text.splitlines():
        line = line.strip().lstrip("-• ")
        if not line or line.startswith("#"):
            continue
        for sep in ("：", ":"):
            if sep in line:
                k, v = line.split(sep, 1)
                k = k.strip()
                if k in known:
                    pts[k] = v.strip()
                break
    return pts


def validate(pts):
    missing = [f for f in REQUIRED if not pts.get(f)]
    problems = []
    st = pts.get("状态", "")
    st_base = st.split("·")[0].strip()
    if st_base and st_base not in STATUS:
        problems.append("状态非法（应为 草案/已定/复盘/关闭，可加「·快轨」后缀；当前: %s）" % st[:20])
    d = pts.get("复盘日期", "")
    if d and "待补充" not in d:
        if not re.search(r"\d{4}-\d{2}-\d{2}", d):
            problems.append("复盘日期格式应为 YYYY-MM-DD（当前: %s）" % d[:20])
    chain = pts.get(CHAIN_FIELD, "")
    if chain and "待补充" not in chain:
        ids = re.findall(r"DR-\d{8}[\w\-]*", chain)
        if not ids:
            problems.append("决策链字段应引用关联 DR id（如 DR-20260902-001，多个用顿号分隔）；当前: %s" % chain[:30])
    return missing, problems


def render_text(pts):
    lines = ["# DR-%s-<slug>（日期由脚本自动填入，slug 取自问题字段）" % DR_DATE]
    for f in FIELDS:
        v = pts.get(f, "").strip() or "【待补充】%s" % HINTS[f]
        lines.append("- %s：%s" % (f, v))
    if pts.get(CHAIN_FIELD, "").strip():
        lines.append("- %s：%s" % (CHAIN_FIELD, pts[CHAIN_FIELD].strip()))
    return "\n".join(lines)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def render_html(pts):
    st = pts.get("状态", "").strip() or "草案"
    st_base = st.split("·")[0].strip() or "草案"
    bcls = {"已定": "ok", "复盘": "info", "关闭": "off"}.get(st_base, "draft")
    badges = '<span class="badge %s">状态：%s</span>' % (bcls, esc(st))
    if "快轨" in st:
        badges += '<span class="badge fast">快轨（可逆且低影响 · 四件套流程）</span>'
    review = pts.get("复盘日期", "").strip()
    badges += '<span class="badge">复盘日期：%s</span>' % (esc(review) if review else "待填")
    rows = []
    for f in FIELDS:
        v = pts.get(f, "").strip() or "【待补充】" + HINTS[f]
        rows.append("<tr><th>%s</th><td>%s</td></tr>" % (f, esc(v)))
    if pts.get(CHAIN_FIELD, "").strip():
        rows.append("<tr><th>%s</th><td>%s</td></tr>" % (CHAIN_FIELD, esc(pts[CHAIN_FIELD].strip())))
    title = pts.get("问题", "").strip() or "DR-%s" % DR_DATE
    if len(title) > 46:
        title = title[:46] + "…"
    html = (_HTML
            .replace("__TITLE__", esc(title))
            .replace("__DATEFULL__", datetime.date.today().isoformat())
            .replace("__BADGES__", badges)
            .replace("__ROWS__", "\n".join(rows)))
    return html


def settings_file():
    d = os.environ.get("PM_STRATEGIST_PROFILE_DIR") or os.environ.get("PM_STRATEGIST_PROFILE")
    if d and os.path.isfile(d):
        d = os.path.dirname(d)
    d = d or os.path.expanduser("~/.workbuddy/pm-strategist")
    return os.path.join(d, "pm_settings.json")


def load_settings():
    try:
        return json.load(open(settings_file(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(s):
    try:
        os.makedirs(os.path.dirname(settings_file()), exist_ok=True)
        json.dump(s, open(settings_file(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def resolve_out_dir(ask=True):
    """落盘目录解析（P2-3 可配置默认；D20 首次问一次存包外）。"""
    env = os.environ.get("PM_STRATEGIST_DR_DIR")
    if env:
        return env, "环境变量 PM_STRATEGIST_DR_DIR"
    s = load_settings()
    if s.get("dr_dir"):
        return s["dr_dir"], "包外偏好（首次落盘时的选择，%s）" % settings_file()
    d = "./决策记录"
    if ask and sys.stdin.isatty():
        try:
            ans = input("DR 默认落盘到 %s/ ？（回车确认 / 输入其他目录）" % d).strip()
        except EOFError:
            ans = ""
        if ans:
            d = ans
        s["dr_dir"] = d
        save_settings(s)
        return d, "本次确认（已存包外偏好，下次不再问）"
    return d, "默认值（非交互环境未询问；可用 --out 或 PM_STRATEGIST_DR_DIR 覆盖）"


def self_test():
    good = {"问题": "示例占位：A品要不要砍（S2）", "选项": "砍/不砍（含维持现状）", "决定": "推荐先收缩后观察",
            "依据": "ref-02+fm-03", "反方意见": "若为渠道入场券则砍错；推翻条件=拿到各SKU条码对应的渠道合约条款", "风险": "供应链：库存",
            "假设清单": "⚠️ 假设·待验证：渠道合约Q4到期", "复盘日期": "2026-12-31", "状态": "草案"}
    m1, p1 = validate(good)
    ok = not m1 and not p1
    bad_missing, _ = validate({"问题": "x"})
    caught = bad_missing == ["选项", "决定"]
    comp = dict(good); comp[CHAIN_FIELD] = "DR-20260902-001、DR-20260902-002"
    chain_ok = not validate(comp)[1]
    badchain = dict(good); badchain[CHAIN_FIELD] = "就是那两个"
    chain_caught = bool(validate(badchain)[1])
    html = render_html(comp)
    html_ok = ("<!DOCTYPE html>" in html and "</html>" in html and CHAIN_FIELD in html and "复盘区" in html)
    fast = dict(good); fast["状态"] = "草案·快轨"
    fast_ok = "badge fast" in render_html(fast)
    tmp = tempfile.mkdtemp(prefix="drtest_")
    pth = os.path.join(tmp, "DR-test.html")
    open(pth, "w", encoding="utf-8").write(render_html(good))
    save_ok = os.path.isfile(pth) and os.path.getsize(pth) > 500
    badst = dict(good); badst["状态"] = "搞定"
    st_caught = bool(validate(badst)[1])
    all_ok = all([ok, caught, chain_ok, chain_caught, html_ok, fast_ok, save_ok, st_caught])
    print("self: 齐全%s 缺项拦截%s 决策链%s/%s HTML单文件%s 快轨橙标%s 落盘演练%s 非法状态拦截%s" % (
        "✓" if ok else "✗", "✓" if caught else "✗", "✓" if chain_ok else "✗", "✓" if chain_caught else "✗",
        "✓" if html_ok else "✗", "✓" if fast_ok else "✗", "✓" if save_ok else "✗", "✓" if st_caught else "✗"))
    return all_ok


def main():
    ap = argparse.ArgumentParser(description="pm-strategist 决策记录 DR9+决策链：校验 / 自包含HTML单文件落盘（默认 ./决策记录/，首次问一次）")
    ap.add_argument("input", nargs="?", help="要点文件（key: value 或 JSON），或 - 读 stdin")
    ap.add_argument("--template", action="store_true", help="打印文本模板（含可选字段说明）")
    ap.add_argument("--out", dest="out_dir", help="落盘目录（默认 ./决策记录；可用 PM_STRATEGIST_DR_DIR 覆盖）")
    ap.add_argument("--slug", help="文件名 slug（默认取问题字段清洗）")
    ap.add_argument("--stdout", action="store_true", help="HTML 打到 stdout，不落盘")
    ap.add_argument("--self", action="store_true", help="内置样例自检")
    a = ap.parse_args()
    if a.self:
        return 0 if self_test() else 1
    if a.template:
        print(TEMPLATE)
        return 0
    if not a.input:
        ap.print_help()
        return 2
    try:
        text = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
    except OSError as e:
        print("读入失败: %s" % e)
        return 2
    pts = parse_points(text)
    missing, problems = validate(pts)
    if missing or problems:
        print(render_text(pts))
        print("FAIL — 必填缺：%s%s" % ("/".join(missing) if missing else "",
              ("；" + "；".join(problems)) if problems else ""))
        if not pts:
            print("提示：一行一条「字段：内容」，字段名限 %s（%s 为可选）" % ("/".join(FIELDS), CHAIN_FIELD))
        return 1
    html = render_html(pts)
    if a.stdout:
        sys.stdout.write(html)
        sys.stderr.write("PASS — HTML 已输出（未落盘，--stdout 模式）\n")
        return 0
    if a.out_dir:
        out_dir, src = a.out_dir, "--out 参数"
    else:
        out_dir, src = resolve_out_dir()
    os.makedirs(out_dir, exist_ok=True)
    slug = a.slug or re.sub(r"[^\w\u4e00-\u9fff]+", "", pts.get("问题", ""))[:24] or "dr"
    path = os.path.join(out_dir, "DR-%s-%s.html" % (DR_DATE, slug))
    n = 2
    base = path[:-5]
    while os.path.exists(path):
        path = "%s-%d.html" % (base, n)
        n += 1
    open(path, "w", encoding="utf-8").write(html)
    print("PASS — DR 渲染成功，已落盘：%s（目录来源：%s）" % (path, src))
    print("复盘区已内置；复盘日期到点对照 fm-04 复盘；快轨 DR 状态徽章为橙色。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
