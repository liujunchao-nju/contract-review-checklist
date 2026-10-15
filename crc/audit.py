"""合同文本覆盖度审计。

给定一份合同文本与合同类型，做两件事：
1. 对照条款标准，看哪些必备条款没有出现（关键词未命中）；
2. 扫描风险信号词，提示可能存在的失衡条款。

与 gutachten-cn 的 check 一样，这里只做「提醒」不判分：
关键词未命中不等于条款真的缺失，可能只是换了表述；命中也不等于条款写得没问题。
它的价值在于把「有没有漏掉一整类条款」这种低级失误挡在交付之前。
"""

from __future__ import annotations

from .checklist import RISK_ORDER, compose, risk_labels


def _normalize(text: str) -> str:
    """去掉空白字符，避免因换行、空格造成漏配。"""
    return "".join(text.split())


def _hits(text: str, keywords: list[str]) -> list[str]:
    """返回在文本中命中的关键词。"""
    return [kw for kw in keywords if _normalize(kw) in text]


def audit(contract_type: str, text: str) -> dict:
    """对照清单审计合同文本。"""
    composed = compose(contract_type)
    body = _normalize(text)

    covered: list[dict] = []
    missing_required: list[dict] = []
    missing_optional: list[dict] = []
    for clause in composed["clauses"]:
        keywords = clause.get("keywords") or [clause["name"]]
        hit = _hits(body, keywords)
        if hit:
            covered.append({**clause, "matched": hit})
        elif clause.get("required"):
            missing_required.append(clause)
        else:
            missing_optional.append(clause)

    flags: list[dict] = []
    for flag in composed["red_flags"]:
        hit = _hits(body, flag.get("patterns") or [])
        if hit:
            flags.append({**flag, "matched": hit})
    flags.sort(key=lambda f: RISK_ORDER.index(f.get("risk", "note")))

    total = len(composed["clauses"])
    coverage = round(len(covered) / total * 100, 1) if total else 0.0
    blocking = [f for f in flags if f["risk"] in ("fatal", "major")]
    return {
        "type": composed["type"],
        "label": composed["label"],
        "clause_total": total,
        "covered": covered,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "red_flags": flags,
        "coverage": coverage,
        "clean": not missing_required and not blocking,
    }


def format_audit(result: dict) -> str:
    """把审计结果渲染成一段终端可读的文字。"""
    labels = risk_labels()
    lines = [
        f"合同类型：{result['label']}（{result['type']}）",
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
    if result["red_flags"]:
        lines.append("")
        lines.append(f"风险信号（{len(result['red_flags'])} 处）：")
        for flag in result["red_flags"]:
            level = labels.get(flag.get("risk", "note"), flag.get("risk", ""))
            lines.append(f"  - [{level}] {flag['name']}（命中：{'、'.join(flag['matched'])}）")
            lines.append(f"      {flag.get('message', '').strip()}")
    else:
        lines.append("")
        lines.append("未扫描到预置的风险信号词。")

    lines.append("")
    lines.append("结论：" + ("未见硬伤，可进入逐条精审。" if result["clean"] else "存在需处理项，见上。"))
    return "\n".join(lines)
