"""测试清单加载、合成与校验。"""

from __future__ import annotations

import pytest

from crc.checklist import (
    DIMENSION_ORDER,
    ContractError,
    compose,
    list_contracts,
    load_contract,
    load_dimensions,
    risk_labels,
    validate_all,
)


def test_validate_all_passes():
    names = validate_all()
    assert "common" in names
    assert set(names) >= {"sales", "lease", "service", "loan", "labor", "equity", "tech", "construction"}


def test_list_contracts_common_first():
    rows = list_contracts()
    assert rows[0]["type"] == "common"
    assert all(r.get("_file") for r in rows)


def test_load_contract_unknown():
    with pytest.raises(KeyError):
        load_contract("不存在的类型")


def test_compose_merges_common_and_type():
    composed = compose("sales")
    assert composed["sources"] == ["common", "sales"]
    clause_names = [c["name"] for c in composed["clauses"]]
    assert "争议解决条款" in clause_names
    assert "标的条款" in clause_names


def test_compose_keeps_three_dimensions():
    composed = compose("lease")
    for dim in DIMENSION_ORDER:
        assert composed["checks"][dim], dim


def test_compose_common_only():
    composed = compose("common")
    assert composed["sources"] == ["common"]
    assert composed["checks"]["macro"]


def test_every_check_has_risk_and_question():
    for row in list_contracts():
        for dim in DIMENSION_ORDER:
            for item in row["checks"][dim]:
                assert item["question"].strip()
                assert item["risk"] in risk_labels()


def test_dimensions_shape():
    dims = load_dimensions()
    assert [d["id"] for d in dims["dimensions"]] == list(DIMENSION_ORDER)
    assert [r["id"] for r in dims["risk_levels"]] == ["fatal", "major", "minor", "note"]
    assert any(s["id"] == "stance" for s in dims["steps"])


def test_invalid_risk_rejected(tmp_path, monkeypatch):
    """风险等级写错时应当报错，而不是静默通过。"""
    import crc.checklist as checklist

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "type: bad\nlabel: 坏样本\n"
        "checks:\n"
        "  macro: [{id: a, question: q, risk: 超级致命}]\n"
        "  meso: [{id: b, question: q, risk: fatal}]\n"
        "  micro: [{id: c, question: q, risk: fatal}]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checklist, "CONTRACTS_DIR", tmp_path)
    with pytest.raises(ContractError):
        checklist.validate_all()
