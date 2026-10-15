"""测试命令行接口与数据一致性。"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

from crc.checklist import _iter_basis, list_contracts, load_dimensions
from crc.cli import main
from crc.laws import load_laws, verify_references
from crc.report import render_audit, render_checklist

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "crc" / "data" / "contracts"
SAMPLE = ROOT / "examples" / "contract_sample.md"


def test_cli_list(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "sales" in out
    assert "买卖合同" in out


def test_cli_show(capsys):
    assert main(["show", "--type", "lease"]) == 0
    out = capsys.readouterr().out
    assert "租赁合同" in out
    assert "民法典第705条" in out


def test_cli_checklist(capsys):
    assert main(["checklist", "--type", "equity"]) == 0
    out = capsys.readouterr().out
    assert "股权转让合同" in out
    assert "定立场" in out


def test_cli_audit_exit_code(capsys):
    code = main(["audit", "--type", "sales", "--file", str(SAMPLE)])
    assert code == 1
    assert "必备条款未见" in capsys.readouterr().out


def test_cli_audit_json(capsys):
    code = main(["audit", "--type", "sales", "--file", str(SAMPLE), "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["type"] == "sales"
    assert data["clean"] is False


def test_cli_laws_key(capsys):
    assert main(["laws", "--key", "民法典第496条"]) == 0
    out = capsys.readouterr().out
    assert "格式条款" in out


def test_cli_laws_unknown_key(capsys):
    assert main(["laws", "--key", "民法典第99999条"]) == 1


def test_cli_verify(capsys):
    assert main(["verify"]) == 0
    assert "结构校验通过" in capsys.readouterr().out


def test_all_basis_references_verified():
    """所有清单文件的法条引用都必须命中白名单。"""
    index = load_laws()
    for path in sorted(CONTRACTS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        unknown = verify_references(_iter_basis(doc), index)
        assert not unknown, f"{path.name} 引用了未核验的法条: {unknown}"


def test_every_contract_has_required_clause():
    for row in list_contracts():
        required = [c for c in row.get("clauses") or [] if c.get("required")]
        assert required, f"{row['type']} 没有任何必备条款"


def test_every_clause_has_keywords():
    for row in list_contracts():
        for clause in row.get("clauses") or []:
            assert clause.get("keywords"), f"{row['type']} 的「{clause['name']}」缺 keywords"


def test_render_checklist_covers_all_dimensions():
    from crc.checklist import compose

    text = render_checklist(compose("tech"))
    assert "宏观" in text
    assert "中观" in text
    assert "微观" in text
    assert "技术开发合同" in text
    assert "风险信号词" in text


def test_render_audit_markdown():
    from crc.audit import audit

    result = audit("sales", SAMPLE.read_text(encoding="utf-8"))
    text = render_audit(result)
    assert "审查速检报告" in text
    assert "未见的必备条款" in text


def test_dimensions_file_present():
    dims = load_dimensions()
    assert dims["framework"] == "sanguan-sibu"
