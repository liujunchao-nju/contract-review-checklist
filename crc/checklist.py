"""合同审查清单：加载、校验与合成。

规则写在 data/contracts/*.yaml，本模块只负责读取、校验与合并。
新增一个合同类型不需要改代码，放一个 YAML 文件即可。

校验包含两件事：
1. 结构完整性（必填字段、checks 三层、clause 字段）
2. 引用合法性（所有 basis 引用的法条 key 必须在 laws.yaml 白名单内）
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
    law_index = load_laws()
    names: list[str] = []
    for path in sorted(CONTRACTS_DIR.glob("*.yaml")):
        doc = _read(path)
        _validate_contract(doc, path, law_index)
        names.append(doc["type"])
    if "common" not in names:
        raise ContractError("缺少 common.yaml（通用审查项）")
    return names


def compose(name: str) -> dict:
    """合成某个合同类型的完整清单：通用项在前，专属项在后。"""
    common = load_contract("common")
    if name == "common":
        return _merge([common])
    return _merge([common, load_contract(name)])


def _merge(docs: list[dict]) -> dict:
    checks: dict[str, list] = {dim: [] for dim in DIMENSION_ORDER}
    clauses: list[dict] = []
    red_flags: list[dict] = []
    basis: list[str] = []
    for doc in docs:
        for dim in DIMENSION_ORDER:
            checks[dim].extend(doc["checks"].get(dim) or [])
        clauses.extend(doc.get("clauses") or [])
        red_flags.extend(doc.get("red_flags") or [])
        basis.extend(doc.get("legal_basis") or [])
    return {
        "type": docs[-1]["type"],
        "label": docs[-1]["label"],
        "category": docs[-1].get("category", ""),
        "summary": docs[-1].get("summary", "").strip(),
        "sources": [d["type"] for d in docs],
        "checks": checks,
        "clauses": clauses,
        "red_flags": red_flags,
        "legal_basis": basis,
    }
