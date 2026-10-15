"""合同文本覆盖度审计。

给定一份合同文本与合同类型，做三件事：
1. 对照条款标准，按三级证据（标题 / 正文 / 缺失）看哪些必备条款没有出现；
2. 扫描风险信号词，提示可能存在的失衡条款；
3. 扫描量化条款，与市场基准区间比对，标出明显偏离。

与 gutachten-cn 的 check 一样，这里只做「提醒」不判分：
关键词未命中不等于条款真的缺失，可能只是换了表述；命中也不等于条款写得没问题。
它的价值在于把「有没有漏掉一整类条款」这种低级失误挡在交付之前。

审查结果依附于立场：同一条款对甲方是优势、对乙方就是风险，
因此 audit 接受 party 参数，并把立场写进结果，供报告标注。
"""

from __future__ import annotations

from .bench import evaluate, load_benchmarks
from .checklist import PARTIES, RISK_ORDER, compose, risk_labels
from .evidence import STATUS_MISSING, clause_terms, flag_terms, match_terms

BLOCKING_RISKS = ("fatal", "major")


def audit(
    contract_type: str,
    text: str,
    party: str | None = None,
    benchmarks: bool = True,
) -> dict:
    """对照清单审计合同文本。

    party 为「甲方」或「乙方」时，结果会带上立场标注。
    benchmarks 为 True 时额外扫描量化条款并与基准区间比对。
    """
    if party and party not in PARTIES:
        raise KeyError(f"未知的审查立场: {party}；可用: {'、'.join(PARTIES)}")

    composed = compose(contract_type, party)

    details: list[dict] = []
    covered: list[dict] = []
    missing_required: list[dict] = []
    missing_optional: list[dict] = []

    for clause in composed["clauses"]:
        hit = match_terms(clause_terms(clause), text)
        record = {
            **clause,
            "status": hit["status"],
            "matched": hit["matched"],
            "line": hit["line"],
            "excerpt": hit["excerpt"],
        }
        details.append(record)
        if hit["status"] == STATUS_MISSING:
            if clause.get("required"):
                missing_required.append(clause)
            else:
                missing_optional.append(clause)
        else:
            covered.append(record)

    flags: list[dict] = []
    for flag in composed["red_flags"]:
        hit = match_terms(flag_terms(flag), text)
        if hit["status"] == STATUS_MISSING:
            continue
        flags.append({**flag, "matched": hit["matched"], "line": hit["line"],
                      "excerpt": hit["excerpt"]})
    flags.sort(key=lambda f: RISK_ORDER.index(f.get("risk", "note")))

    rows = evaluate(text, load_benchmarks()) if benchmarks else []

    total = len(composed["clauses"])
    coverage = round(len(covered) / total * 100, 1) if total else 0.0
    blocking = [f for f in flags if f.get("risk") in BLOCKING_RISKS]
    return {
        "type": composed["type"],
        "label": composed["label"],
        "party": party or "",
        "clause_total": total,
        "covered": covered,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "details": details,
        "red_flags": flags,
        "benchmarks": rows,
        "coverage": coverage,
        "clean": not missing_required and not blocking,
        "blocking": blocking,
    }


def format_audit(result: dict) -> str:
    """把审计结果渲染成一段终端可读的文字。"""
    from .bench import format_bench

    labels = risk_labels()
    party = result.get("party")
    stance = f"　审查立场：{party}" if party else "　审查立场：未指定（结论按中立口径）"
    lines = [
        f"合同类型：{result['label']}（{result['type']}）{stance}",
        f"条款标准：{result['clause_total']} 项，"
        f"命中 {len(result['covered'])} 项，"
        f"覆盖率 {result['coverage']}%",
    ]

    if result["missing_required"]:
        lines.append("")
        lines.append(f"必备条款未见（{len(result['missing_required'])} 项）：")
        for clause in result["missing_required"]:
            lines.append(f"  - {clause['name']}")
    if result["missing_optional"]:
        lines.append("")
        lines.append(f"可选条款未见（{len(result['missing_optional'])} 项）：")
        for clause in result["missing_optional"]:
            lines.append(f"  - {clause['name']}")

    lines.append("")
    if result["red_flags"]:
        lines.append(f"风险信号（{len(result['red_flags'])} 处）：")
        for flag in result["red_flags"]:
            level = labels.get(flag.get("risk", "note"), flag.get("risk", ""))
            where = f"　第 {flag['line']} 行" if flag.get("line") else ""
            lines.append(f"  - [{level}] {flag['name']}（命中：{flag['matched']}）{where}")
            lines.append(f"      {flag.get('message', '').strip()}")
    else:
        lines.append("未扫描到预置的风险信号词。")

    lines.append("")
    lines.append("量化条款与基准区间比对：")
    lines.append(format_bench(result.get("benchmarks") or []))

    lines.append("")
    lines.append("结论：" + ("未见硬伤，可进入逐条精审。" if result["clean"] else "存在需处理项，见上。"))
    return "\n".join(lines)
