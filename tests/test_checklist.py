"""测试清单加载、合成与校验。"""

from __future__ import annotations

import pytest

from crc.checklist import (
    DIMENSION_ORDER,
    PARTIES,
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


# ── 立场维度 ────────────────────────────────────────────────


def test_contract_type_count_and_new_types():
    names = {row["type"] for row in list_contracts()}
    assert len(names) == 15
    assert names >= {"nda", "guarantee", "entrust", "work", "capital_increase", "property"}


def test_compose_without_party_is_neutral():
    composed = compose("sales")
    assert composed["party"] == ""
    assert not any(i.get("party_note") for dim in DIMENSION_ORDER for i in composed["checks"][dim])


def test_compose_with_party_adds_notes():
    composed = compose("sales", "乙方")
    assert composed["party"] == "乙方"
    noted = [i for dim in DIMENSION_ORDER for i in composed["checks"][dim] if i.get("party_note")]
    assert noted, "指定立场后应当带出该立场的提示"


def test_party_can_adjust_risk_level():
    """同一条款对不同立场的严重性不同，风险等级应随之翻转。"""
    neutral = compose("sales")
    buyer = compose("sales", "乙方")
    pick = lambda c: next(i for dim in DIMENSION_ORDER
                          for i in c["checks"][dim] if i["id"] == "common-damages")
    assert pick(neutral)["risk"] == "major"
    assert pick(buyer)["risk"] == "fatal"
    assert pick(buyer)["risk_adjusted"] is True


def test_party_specific_guidance_differs():
    mode_a = next(i for i in compose("guarantee", "甲方")["checks"]["meso"]
                  if i["id"] == "guarantee-mode")
    mode_b = next(i for i in compose("guarantee", "乙方")["checks"]["meso"]
                  if i["id"] == "guarantee-mode")
    assert mode_a["party_note"] != mode_b["party_note"]
    assert "连带" in mode_a["party_note"]


def test_unknown_party_rejected():
    with pytest.raises(KeyError):
        compose("sales", "丙方")


def test_party_fields_validated(tmp_path, monkeypatch):
    """party_notes 出现非甲方乙方的键时应当报错。"""
    import crc.checklist as checklist

    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "type: bad\nlabel: 坏样本\n"
        "checks:\n"
        "  macro: [{id: a, question: q, risk: fatal, party_notes: {丙方: 提示}}]\n"
        "  meso: [{id: b, question: q, risk: fatal}]\n"
        "  micro: [{id: c, question: q, risk: fatal}]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checklist, "CONTRACTS_DIR", tmp_path)
    with pytest.raises(ContractError):
        checklist.validate_all()


def test_common_clauses_all_have_redline():
    """通用条款被所有类型复用，必须都给出可直接取的替代文本。"""
    common = load_contract("common")
    for clause in common["clauses"]:
        assert clause.get("redline"), f"通用条款「{clause['name']}」缺 redline"


def test_new_types_are_complete():
    """新增类型必须三层审查项齐备、有必备条款、条款带 keywords。"""
    for name in ("nda", "guarantee", "entrust", "work", "capital_increase", "property"):
        doc = load_contract(name)
        for dim in DIMENSION_ORDER:
            assert doc["checks"][dim], f"{name} 的 checks.{dim} 为空"
        assert [c for c in doc["clauses"] if c.get("required")], f"{name} 无必备条款"
        for clause in doc["clauses"]:
            assert clause.get("keywords"), f"{name} 的「{clause['name']}」缺 keywords"
            assert clause.get("redline"), f"{name} 的「{clause['name']}」缺 redline"


def test_parties_constant():
    assert PARTIES == ("甲方", "乙方")
