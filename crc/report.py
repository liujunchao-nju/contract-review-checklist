"""Markdown 报告渲染。

供两个场景使用：
1. 把某个合同类型的清单渲染成一份可勾选的空白清单，打印出来逐项过；
2. 把审计结果渲染成一份带条款覆盖与风险提示的报告。
"""

from __future__ import annotations

from .checklist import DIMENSION_ORDER, load_dimensions, risk_labels


def _dimension_labels() -> dict[str, str]:
    dims = load_dimensions()["dimensions"]
    return {d["id"]: d["label"] for d in dims}


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
            lines.append(f"- [ ] {item['question']}  `[{level}]`")
            guidance = (item.get("guidance") or "").strip()
            if guidance:
                lines.append(f"      {guidance}")
            if item.get("basis"):
                lines.append(f"      依据：{'；'.join(item['basis'])}")
        lines.append("")

    lines.append("## 三、条款标准")
    lines.append("")
    lines.append("| 条款 | 必备 | 必备要素 | 常见问题 |")
    lines.append("| --- | --- | --- | --- |")
    for clause in composed["clauses"]:
        name = clause["name"]
        must = "是" if clause.get("required") else ""
        elements = "；".join(clause.get("elements") or [])
        issues = "；".join(clause.get("issues") or [])
        lines.append(f"| {name} | {must} | {elements} | {issues} |")
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
    lines = [f"# {result['label']} 审查速检报告", ""]
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
    else:
        lines.append("无。")
    lines.append("")

    if result["missing_optional"]:
        lines.append("## 未见的选择性条款")
        lines.append("")
        for clause in result["missing_optional"]:
            lines.append(f"- {clause['name']}")
        lines.append("")

    lines.append("## 风险信号")
    lines.append("")
    if result["red_flags"]:
        for flag in result["red_flags"]:
            level = labels.get(flag.get("risk", "note"), flag.get("risk", ""))
            lines.append(f"### [{level}] {flag['name']}")
            lines.append("")
            lines.append(f"- 命中：{'、'.join(flag['matched'])}")
            lines.append(f"- 说明：{(flag.get('message') or '').strip()}")
            if flag.get("basis"):
                lines.append(f"- 依据：{'；'.join(flag['basis'])}")
            lines.append("")
    else:
        lines.append("未扫描到预置的风险信号词。")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
