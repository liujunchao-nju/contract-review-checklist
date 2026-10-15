"""合同审查清单：加载、校验与合成。

规则写在 data/contracts/*.yaml，本模块只负责读取、校验与合并。
新增一个合同类型不需要改代码，放一个 YAML 文件即可。

校验包含三件事：
1. 结构完整性（必填字段、checks 三层、clause 字段）
2. 引用合法性（所有 basis 引用的法条 key 必须在 laws.yaml 白名单内）
3. 基准库结构及其法条引用（benchmarks.yaml）
"""

from __future__ import annotations

import pathlib

import yaml

from .laws import CONTRACTS_DIR, load_laws, verify_references

DIMENSIONS_FILE = CONTRACTS_DIR.parent / "dimensions.yaml"

REQUIRED_TOP = ("type", "label")
REQUIRED_CHECK = ("id", "question", "risk")
DIMENSION_ORDER = ("macro", "meso", "micro")
RISK_ORDER = ("fatal", "major", "minor", "note")

# 立场：审查结论依附于「代表哪一方」，同一条款对甲方是优势、对乙方就是风险
PARTIES = ("甲方", "乙方")


class ContractError(ValueError):
    """合同类型文件不合法。"""


def _read(path: pathlib.Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict):
        raise ContractError(f"{path.name} 内容必须是映射")
    return doc


def _iter_basis(node) -> list[str]:
    """递归收集文档中所有 basis 字段引用的法条 key。"""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "basis" and isinstance(value, list):
                found.extend(str(v) for v in value)
            else:
                found.extend(_iter_basis(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_iter_basis(item))
    return found


def load_dimensions() -> dict:
    """加载三观四步审查框架定义。"""
    doc = _read(DIMENSIONS_FILE)
    if "dimensions" not in doc or "risk_levels" not in doc:
        raise ContractError("dimensions.yaml 缺少 dimensions 或 risk_levels 字段")
    return doc


def risk_labels() -> dict[str, str]:
    """返回 {risk_id: 中文标签}。"""
    return {r["id"]: r["label"] for r in load_dimensions()["risk_levels"]}


def _validate_party_fields(doc: dict, path: pathlib.Path) -> None:
    """校验立场相关字段：键只能是甲方或乙方，风险等级只能是四级之一。"""
    for dim in DIMENSION_ORDER:
        for item in doc.get("checks", {}).get(dim) or []:
            ident = item.get("id", "?")
            notes = item.get("party_notes")
            if notes is not None:
                if not isinstance(notes, dict):
                    raise ContractError(f"{path.name} 的 {ident} 的 party_notes 必须是映射")
                unknown = [k for k in notes if k not in PARTIES]
                if unknown:
                    raise ContractError(
                        f"{path.name} 的 {ident} 出现未知立场 {', '.join(map(str, unknown))}"
                    )
            by_party = item.get("risk_by_party")
            if by_party is not None:
                if not isinstance(by_party, dict):
                    raise ContractError(
                        f"{path.name} 的 {ident} 的 risk_by_party 必须是映射"
                    )
                for party, risk in by_party.items():
                    if party not in PARTIES:
                        raise ContractError(f"{path.name} 的 {ident} 出现未知立场 {party}")
                    if risk not in RISK_ORDER:
                        raise ContractError(
                            f"{path.name} 的 {ident} 在 {party} 下出现未知风险等级 {risk}"
                        )


def _validate_contract(doc: dict, path: pathlib.Path, law_index: dict) -> None:
    missing = [k for k in REQUIRED_TOP if not doc.get(k)]
    if missing:
        raise ContractError(f"{path.name} 缺少必要字段: {', '.join(missing)}")

    checks = doc.get("checks")
    if not isinstance(checks, dict):
        raise ContractError(f"{path.name} 缺少 checks 字段或格式不对")
    for dim in DIMENSION_ORDER:
        items = checks.get(dim)
        if not items:
            raise ContractError(f"{path.name} 的 checks.{dim} 必须是非空列表")
        for item in items:
            lack = [k for k in REQUIRED_CHECK if not item.get(k)]
            if lack:
                raise ContractError(
                    f"{path.name} 的 checks.{dim} 有一条缺少 {', '.join(lack)}: {item}"
                )
            if item["risk"] not in RISK_ORDER:
                raise ContractError(
                    f"{path.name} 的 checks.{dim} 出现未知风险等级 {item['risk']}"
                )
    _validate_party_fields(doc, path)

    for clause in doc.get("clauses") or []:
        if not clause.get("name"):
            raise ContractError(f"{path.name} 的 clauses 有一条缺少 name")

    unknown = verify_references(_iter_basis(doc), law_index)
    if unknown:
        raise ContractError(
            f"{path.name} 引用了未核验的法条: {', '.join(sorted(set(unknown)))}"
        )


def list_contracts() -> list[dict]:
    """列出全部合同类型，common 排在最前，其余按 label 排序。"""
    docs: list[dict] = []
    for path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        doc = _read(path)
        doc["_file"] = path.name
        docs.append(doc)
    docs.sort(key=lambda d: (d.get("type") != "common", d.get("label", "")))
    return docs


def load_contract(name: str) -> dict:
    """按 type 加载单个合同类型文件。"""
    for doc in list_contracts():
        if doc.get("type") == name:
            return doc
    available = ", ".join(d.get("type", "?") for d in list_contracts())
    raise KeyError(f"未知的合同类型: {name}；可用: {available}")


def validate_all() -> list[str]:
    """校验全部合同类型文件，返回类型名列表；不合法则抛错。"""
    from .bench import validate_benchmarks

    law_index = load_laws()
    names: list[str] = []
    for path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        doc = _read(path)
        _validate_contract(doc, path, law_index)
        names.append(doc["type"])
    if "common" not in names:
        raise ContractError("缺少 common.yaml（通用审查项）")
    validate_benchmarks(law_index)
    return names


def _apply_party(item: dict, party: str | None) -> dict:
    """按审查立场改写一条审查项：补立场提示，必要时调整风险等级。"""
    if not party:
        return dict(item)
    out = dict(item)
    note = (item.get("party_notes") or {}).get(party)
    if note:
        out["party_note"] = str(note).strip()
    risk = (item.get("risk_by_party") or {}).get(party)
    if risk:
        out["risk"] = risk
        out["risk_adjusted"] = risk != item.get("risk")
    return out


def compose(name: str, party: str | None = None) -> dict:
    """合成某个合同类型的完整清单：通用项在前，专属项在后。

    party 为「甲方」或「乙方」时，审查项会带上该立场的提示与风险等级。
    """
    if party and party not in PARTIES:
        raise KeyError(f"未知的审查立场: {party}；可用: {'、'.join(PARTIES)}")
    common = load_contract("common")
    docs = [common] if name == "common" else [common, load_contract(name)]
    return _merge(docs, party)


def _merge(docs: list[dict], party: str | None = None) -> dict:
    checks: dict[str, list] = {dim: [] for dim in DIMENSION_ORDER}
    clauses: list[dict] = []
    red_flags: list[dict] = []
    basis: list[str] = []
    for doc in docs:
        for dim in DIMENSION_ORDER:
            for item in doc["checks"].get(dim) or []:
                checks[dim].append(_apply_party(item, party))
        clauses.extend(doc.get("clauses") or [])
        red_flags.extend(doc.get("red_flags") or [])
        basis.extend(doc.get("legal_basis") or [])
    return {
        "type": docs[-1]["type"],
        "label": docs[-1]["label"],
        "category": docs[-1].get("category", ""),
        "summary": docs[-1].get("summary", "").strip(),
        "sources": [d["type"] for d in docs],
        "party": party or "",
        "checks": checks,
        "clauses": clauses,
        "red_flags": red_flags,
        "legal_basis": basis,
    }
