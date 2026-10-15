"""报告渲染：Markdown 与 HTML。

供两个场景使用：
1. 把某个合同类型的清单渲染成一份可勾选的空白清单，打印出来逐项过；
2. 把审计结果渲染成一份带条款覆盖、风险信号与基准比对的报告。

HTML 一律单文件自包含：内联 CSS 与 JS，不引用任何外部资源，
双击即可离线打开，便于直接发给业务方或归档。
"""

from __future__ import annotations

import html as html_lib

from .bench import LEVEL_LABELS, format_bench_rows
from .checklist import DIMENSION_ORDER, load_dimensions, risk_labels
from .evidence import STATUS_BODY, STATUS_HEADING, STATUS_MISSING

FORMATS = ("md", "html")

_RISK_COLORS = {
    "fatal": "#b3261e",
    "major": "#c2680f",
    "minor": "#1c6b52",
    "note": "#5b6470",
}


def _dimension_labels() -> dict[str, str]:
    dims = load_dimensions()["dimensions"]
    return {d["id"]: d["label"] for d in dims}


def _esc(text) -> str:
    return html_lib.escape(str(text or ""))


# ── Markdown ────────────────────────────────────────────────


def render_checklist(composed: dict) -> str:
    """渲染某个合同类型的空白审查清单。"""
    labels = risk_labels()
    dim_labels = _dimension_labels()
    dims = {d["id"]: d for d in load_dimensions()["dimensions"]}

    lines = [f"# {composed['label']} · 审查清单", ""]
    lines.append(f"- 合同类型标识：`{composed['type']}`")
    if composed.get("category"):
        lines.append(f"- 所属分类：{composed['category']}")
    if composed.get("summary"):
        lines.append(f"- 交易实质：{composed['summary']}")
    if composed.get("party"):
        lines.append(f"- 审查立场：**{composed['party']}**（结论与风险等级按该立场给出）")
    lines.append(f"- 清单来源：{' + '.join(composed['sources'])}")
    lines.append("")

    lines.append("## 一、定立场")
    lines.append("")
    steps = load_dimensions()["steps"]
    stance = next((s for s in steps if s["id"] == "stance"), None)
    if stance:
        lines.append(stance["question"])
        for out in stance.get("outputs", []):
            lines.append(f"- [ ] {out}")
    lines.append("")

    lines.append("## 二、分层审查要点")
    lines.append("")
    for idx, dim in enumerate(DIMENSION_ORDER, start=1):
        meta = dims.get(dim, {})
        lines.append(f"### {idx}. {dim_labels.get(dim, dim)}：{meta.get('question', '')}")
        lines.append("")
        for item in composed["checks"][dim]:
            level = labels.get(item["risk"], item["risk"])
            marker = f"（原级 {labels.get(item['risk'], '')}→按立场调整）" if item.get("risk_adjusted") else ""
            lines.append(f"- [ ] {item['question']}  `[{level}]{marker}`")
            guidance = (item.get("guidance") or "").strip()
            if guidance:
                lines.append(f"      {guidance}")
            if item.get("party_note"):
                lines.append(f"      本方立场：{item['party_note'].strip()}")
            if item.get("basis"):
                lines.append(f"      依据：{'；'.join(item['basis'])}")
        lines.append("")

    lines.append("## 三、条款标准")
    lines.append("")
    for clause in composed["clauses"]:
        must = "必备" if clause.get("required") else "可选"
        lines.append(f"### {clause['name']}　`{must}`")
        lines.append("")
        elements = clause.get("elements") or []
        if elements:
            lines.append("必备要素：")
            for element in elements:
                lines.append(f"- [ ] {element}")
            lines.append("")
        issues = clause.get("issues") or []
        if issues:
            lines.append("常见问题：" + "；".join(issues))
            lines.append("")
        if clause.get("redline"):
            lines.append("建议文本（按交易调整变量后再用）：")
            lines.append("")
            lines.append("> " + " ".join(str(clause["redline"]).split()))
            lines.append("")
        if clause.get("basis"):
            lines.append(f"依据：{'；'.join(clause['basis'])}")
            lines.append("")

    if composed["red_flags"]:
        lines.append("## 四、风险信号词")
        lines.append("")
        lines.append("| 信号 | 等级 | 命中词 | 说明 |")
        lines.append("| --- | --- | --- | --- |")
        for flag in composed["red_flags"]:
            level = labels.get(flag.get("risk", "note"), flag.get("risk", ""))
            words = "、".join(flag.get("patterns") or [])
            msg = " ".join((flag.get("message") or "").split())
            lines.append(f"| {flag['name']} | {level} | {words} | {msg} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_audit(result: dict) -> str:
    """把审计结果渲染成 Markdown 报告。"""
    labels = risk_labels()
    party = result.get("party")
    stance = f"（审查立场：{party}）" if party else "（审查立场：未指定，按中立口径）"
    lines = [f"# {result['label']} 审查速检报告 {stance}", ""]
    lines.append(f"- 条款标准：{result['clause_total']} 项")
    lines.append(f"- 已覆盖：{len(result['covered'])} 项")
    lines.append(f"- 条款覆盖率：{result['coverage']}%")
    lines.append(f"- 结论：{'未见硬伤' if result['clean'] else '存在待处理项'}")
    lines.append("")

    lines.append("## 未见的必备条款")
    lines.append("")
    if result["missing_required"]:
        for clause in result["missing_required"]:
            elements = "；".join(clause.get("elements") or [])
            lines.append(f"- **{clause['name']}**：{elements}")
            if clause.get("redline"):
                lines.append(f"  - 建议文本：{' '.join(str(clause['redline']).split())}")
    else:
        lines.append("无。")
    lines.append("")

    if result["missing_optional"]:
        lines.append("## 未见的选择性条款")
        lines.append("")
        for clause in result["missing_optional"]:
            lines.append(f"- {clause['name']}")
        lines.append("")

    lines.append("## 条款命中情况")
    lines.append("")
    lines.append("| 条款 | 必备 | 证据 | 行号 | 命中词 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in result.get("details") or []:
        must = "是" if row.get("required") else ""
        line = row.get("line") or ""
        lines.append(
            f"| {row['name']} | {must} | {row['status']} | {line} | {row.get('matched', '')} |"
        )
    lines.append("")

    lines.append("## 风险信号")
    lines.append("")
    if result["red_flags"]:
        for flag in result["red_flags"]:
            level = labels.get(flag.get("risk", "note"), flag.get("risk", ""))
            lines.append(f"### [{level}] {flag['name']}")
            lines.append("")
            where = f"　第 {flag['line']} 行" if flag.get("line") else ""
            lines.append(f"- 命中：{flag['matched']}{where}")
            lines.append(f"- 说明：{(flag.get('message') or '').strip()}")
            if flag.get("basis"):
                lines.append(f"- 依据：{'；'.join(flag['basis'])}")
            lines.append("")
    else:
        lines.append("未扫描到预置的风险信号词。")
        lines.append("")

    lines.append("## 量化条款与基准区间")
    lines.append("")
    lines.append(format_bench_rows(result.get("benchmarks") or []))
    lines.append("> 区间为市场惯例与法律上限的参照值，不是裁判标准，仅用于定位偏离。")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ── HTML ────────────────────────────────────────────────────

_CSS = """
:root{--ink:#1b2028;--muted:#5b6470;--line:#e3e7ec;--bg:#f7f8fa;--card:#ffffff;--accent:#1f4e79;}
*{box-sizing:border-box}
body{margin:0;padding:0 0 60px;background:var(--bg);color:var(--ink);
 font-family:"Microsoft YaHei","PingFang SC",-apple-system,"Segoe UI",sans-serif;
 font-size:15px;line-height:1.75;}
header{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);
 padding:14px 22px;}
.brand{font-size:17px;font-weight:700;color:var(--accent);}
.brand small{font-weight:400;color:var(--muted);margin-left:10px;font-size:13px;}
.bar{height:8px;background:var(--line);border-radius:4px;margin-top:10px;overflow:hidden;}
.bar>i{display:block;height:100%;width:0;background:var(--accent);border-radius:4px;transition:width .2s;}
.pct{font-size:12px;color:var(--muted);margin-top:4px;}
main{max-width:920px;margin:0 auto;padding:22px;}
h1{font-size:22px;color:var(--accent);margin:0 0 6px;}
h2{font-size:18px;margin:26px 0 10px;padding-left:10px;border-left:4px solid var(--accent);}
h3{font-size:15px;margin:16px 0 8px;}
.meta{color:var(--muted);font-size:13px;margin-bottom:18px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin-bottom:14px;}
label.item{display:flex;gap:10px;align-items:flex-start;padding:6px 0;}
label.item input{margin-top:5px;flex:none;width:16px;height:16px;}
.guide{color:var(--muted);font-size:13px;margin:2px 0 0 26px;}
.party{margin:4px 0 0 26px;font-size:13px;color:#8a4b00;background:#fff6e6;
 border-left:3px solid #e0a11b;padding:4px 8px;border-radius:0 4px 4px 0;}
.risk{display:inline-block;font-size:12px;padding:1px 7px;border-radius:10px;color:#fff;vertical-align:2px;}
.basis{margin:2px 0 0 26px;font-size:12px;color:var(--muted);}
.redline{margin:8px 0 0 26px;padding:8px 10px;background:#f2f6fa;border-left:3px solid var(--accent);
 font-size:13px;white-space:pre-wrap;border-radius:0 4px 4px 0;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top;}
th{background:#eef2f6;font-weight:600;}
.kpi{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;}
.kpi div{flex:1 1 130px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;}
.kpi b{display:block;font-size:22px;color:var(--accent);}
.kpi span{font-size:12px;color:var(--muted);}
.empty{color:var(--muted);font-size:13px;}
footer{max-width:920px;margin:26px auto 0;padding:0 22px;color:var(--muted);font-size:12px;}
"""

_JS = """
(function(){
  var boxes=document.querySelectorAll('input[type=checkbox]');
  var bar=document.querySelector('.bar>i');
  var pct=document.querySelector('.pct');
  function update(){
    var done=0;
    boxes.forEach(function(b){ if(b.checked) done++; });
    var rate=boxes.length? Math.round(done/boxes.length*100):0;
    if(bar) bar.style.width=rate+'%';
    if(pct) pct.textContent=done+' / '+boxes.length+' 项已核对（'+rate+'%）';
  }
  boxes.forEach(function(b){ b.addEventListener('change',update); });
  update();
})();
"""


def _risk_badge(risk: str, labels: dict) -> str:
    color = _RISK_COLORS.get(risk, "#5b6470")
    return f'<span class="risk" style="background:{color}">{_esc(labels.get(risk, risk))}</span>'


def _html_shell(title: str, subtitle: str, body: str, note: str = "") -> str:
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{_esc(title)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n"
        '<header><div class="brand">' + _esc(title) +
        '<small>' + _esc(subtitle) + "</small></div>\n"
        '<div class="bar"><i></i></div><div class="pct"></div></header>\n'
        f"<main>{body}</main>\n"
        f'<footer>{_esc(note)}</footer>\n'
        f"<script>{_JS}</script>\n</body>\n</html>\n"
    )


def render_checklist_html(composed: dict) -> str:
    """渲染单文件 HTML 可勾选审查清单。"""
    labels = risk_labels()
    dim_labels = _dimension_labels()
    dims = {d["id"]: d for d in load_dimensions()["dimensions"]}
    party = composed.get("party")

    meta = [f"类型标识：{_esc(composed['type'])}"]
    if composed.get("category"):
        meta.append(f"分类：{_esc(composed['category'])}")
    if composed.get("summary"):
        meta.append(f"交易实质：{_esc(composed['summary'])}")
    meta.append("审查立场：" + (_esc(party) if party else "未指定（中立口径）"))
    meta.append("清单来源：" + _esc(" + ".join(composed["sources"])))

    body: list[str] = [
        f"<h1>{_esc(composed['label'])} · 审查清单</h1>",
        '<div class="meta">' + "　".join(meta) + "</div>",
        "<h2>一、定立场</h2>",
        '<div class="card">',
    ]
    stance = next((s for s in load_dimensions()["steps"] if s["id"] == "stance"), None)
    if stance:
        body.append(f"<p>{_esc(stance['question'])}</p>")
        for out in stance.get("outputs", []):
            body.append(
                f'<label class="item"><input type="checkbox"><span>{_esc(out)}</span></label>'
            )
    body.append("</div>")

    body.append("<h2>二、分层审查要点</h2>")
    for idx, dim in enumerate(DIMENSION_ORDER, start=1):
        meta_dim = dims.get(dim, {})
        body.append(
            f"<h3>{idx}. {_esc(dim_labels.get(dim, dim))}：{_esc(meta_dim.get('question', ''))}</h3>"
        )
        body.append('<div class="card">')
        for item in composed["checks"][dim]:
            adjusted = "（按立场调整）" if item.get("risk_adjusted") else ""
            body.append(
                '<label class="item"><input type="checkbox"><span>'
                + _esc(item["question"])
                + " "
                + _risk_badge(item["risk"], labels)
                + _esc(adjusted)
                + "</span></label>"
            )
            if item.get("guidance"):
                body.append(f'<div class="guide">{_esc(item["guidance"])}</div>')
            if item.get("party_note"):
                body.append(f'<div class="party">本方立场：{_esc(item["party_note"])}</div>')
            if item.get("basis"):
                body.append(f'<div class="basis">依据：{_esc("；".join(item["basis"]))}</div>')
        body.append("</div>")

    body.append("<h2>三、条款标准</h2>")
    for clause in composed["clauses"]:
        must = "必备" if clause.get("required") else "可选"
        body.append(f'<div class="card"><h3>{_esc(clause["name"])}　<span class="risk" '
                    f'style="background:#5b6470">{must}</span></h3>')
        for element in clause.get("elements") or []:
            body.append(
                f'<label class="item"><input type="checkbox"><span>{_esc(element)}</span></label>'
            )
        if clause.get("issues"):
            body.append('<div class="guide">常见问题：' + _esc("；".join(clause["issues"])) + "</div>")
        if clause.get("redline"):
            body.append(f'<div class="redline">建议文本：\n{_esc(clause["redline"])}</div>')
        if clause.get("basis"):
            body.append(f'<div class="basis">依据：{_esc("；".join(clause["basis"]))}</div>')
        body.append("</div>")

    if composed["red_flags"]:
        body.append("<h2>四、风险信号词</h2>")
        body.append('<div class="card"><table><tr><th>信号</th><th>等级</th>'
                    "<th>命中词</th><th>说明</th></tr>")
        for flag in composed["red_flags"]:
            words = _esc("、".join(flag.get("patterns") or []))
            msg = _esc(" ".join((flag.get("message") or "").split()))
            body.append(
                f"<tr><td>{_esc(flag['name'])}</td><td>{_risk_badge(flag.get('risk', 'note'), labels)}</td>"
                f"<td>{words}</td><td>{msg}</td></tr>"
            )
        body.append("</table></div>")

    note = "本清单提供审查框架与条款标准，不构成法律意见；勾选状态仅保存在本页，刷新即清空。"
    subtitle = f"三观四步框架 · {'按 ' + party + ' 立场' if party else '中立口径'}"
    return _html_shell(f"{composed['label']} 审查清单", subtitle, "\n".join(body), note)


def render_audit_html(result: dict) -> str:
    """渲染单文件 HTML 审查速检报告。"""
    labels = risk_labels()
    party = result.get("party")
    status_colors = {STATUS_HEADING: "#1c6b52", STATUS_BODY: "#1f4e79", STATUS_MISSING: "#b3261e"}
    level_colors = {"danger": "#b3261e", "caution": "#c2680f", "standard": "#1c6b52"}

    total = result["clause_total"]
    covered = len(result["covered"])
    body: list[str] = [
        '<div class="kpi">',
        f'<div><b>{covered} / {total}</b><span>条款命中</span></div>',
        f'<div><b>{result["coverage"]}%</b><span>条款覆盖率</span></div>',
        f'<div><b>{len(result["red_flags"])}</b><span>风险信号</span></div>',
        f'<div><b>{len(result.get("benchmarks") or [])}</b><span>基准偏离项</span></div>',
        "</div>",
    ]

    body.append('<div class="meta">审查立场：'
                + (_esc(party) if party else "未指定（中立口径）")
                + f'　结论：{"未见硬伤，可进入逐条精审" if result["clean"] else "存在待处理项，见下"}'
                + "</div>")

    body.append("<h2>一、未见的必备条款</h2>")
    if result["missing_required"]:
        body.append('<div class="card">')
        for clause in result["missing_required"]:
            elements = _esc("；".join(clause.get("elements") or []))
            body.append(f'<p><b>{_esc(clause["name"])}</b>　{elements}</p>')
            if clause.get("redline"):
                body.append(f'<div class="redline">建议文本：\n{_esc(clause["redline"])}</div>')
        body.append("</div>")
    else:
        body.append('<div class="card"><p class="empty">无。</p></div>')

    body.append("<h2>二、条款命中情况</h2>")
    body.append('<div class="card"><table><tr><th>条款</th><th>必备</th><th>证据</th>'
                "<th>行号</th><th>命中词</th></tr>")
    for row in result.get("details") or []:
        color = status_colors.get(row["status"], "#5b6470")
        must = "是" if row.get("required") else ""
        body.append(
            f"<tr><td>{_esc(row['name'])}</td><td>{must}</td>"
            f'<td style="color:{color};font-weight:600">{_esc(row["status"])}</td>'
            f"<td>{row.get('line') or ''}</td><td>{_esc(row.get('matched', ''))}</td></tr>"
        )
    body.append("</table></div>")

    body.append("<h2>三、风险信号</h2>")
    if result["red_flags"]:
        body.append('<div class="card">')
        for flag in result["red_flags"]:
            where = f"　第 {flag['line']} 行" if flag.get("line") else ""
            body.append(
                f'<p>{_risk_badge(flag.get("risk", "note"), labels)}　<b>{_esc(flag["name"])}</b>'
                f'<span class="guide">　命中：{_esc(flag["matched"])}{_esc(where)}</span></p>'
            )
            body.append(f'<div class="guide">{_esc(flag.get("message", ""))}</div>')
            if flag.get("basis"):
                body.append(f'<div class="basis">依据：{_esc("；".join(flag["basis"]))}</div>')
        body.append("</div>")
    else:
        body.append('<div class="card"><p class="empty">未扫描到预置的风险信号词。</p></div>')

    body.append("<h2>四、量化条款与基准区间</h2>")
    rows = result.get("benchmarks") or []
    if rows:
        body.append('<div class="card"><table><tr><th>项目</th><th>检出值</th><th>判定</th>'
                    "<th>常规区间</th><th>说明</th></tr>")
        for row in rows:
            color = level_colors.get(row["level"], "#5b6470")
            value = f"{row['value']:g}{row['unit_label']}"
            marker = "（法律上限）" if row.get("legal_limit") else ""
            body.append(
                f"<tr><td>{_esc(row['name'])}{marker}</td><td>{_esc(value)}</td>"
                f'<td style="color:{color};font-weight:600">{_esc(LEVEL_LABELS.get(row["level"], ""))}</td>'
                f"<td>{_esc(row['levels']['standard'])}</td><td>{_esc(row['note'])}</td></tr>"
            )
        body.append("</table></div>")
    else:
        body.append('<div class="card"><p class="empty">未检出偏离常规区间的量化条款。</p></div>')

    note = ("速检只做提醒不判分：关键词未命中不等于条款缺失，命中也不等于条款无问题。"
            "基准区间为市场惯例与法律上限的参照值，不是裁判标准。")
    subtitle = f"{'按 ' + party + ' 立场' if party else '中立口径'} · 覆盖率 {result['coverage']}%"
    return _html_shell(f"{result['label']} 审查速检报告", subtitle, "\n".join(body), note)
