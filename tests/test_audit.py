"""测试合同速检。

以 examples/contract_sample.md 为回归样本：这份示例合同刻意留有缺口，
审计结果一旦变化，说明规则或匹配逻辑被改动了，应当重新审视。
"""

from __future__ import annotations

import pathlib

from crc.audit import audit, format_audit

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "examples" / "contract_sample.md"

EXPECTED_MISSING = {
    "争议解决条款",
    "保密条款",
    "不可抗力条款",
    "通知与送达条款",
    "所有权与风险转移条款",
}


def _sample_text() -> str:
    return SAMPLE.read_text(encoding="utf-8")


def test_sample_audit_missing_required():
    result = audit("sales", _sample_text())
    missing = {c["name"] for c in result["missing_required"]}
    assert missing == EXPECTED_MISSING
    assert result["clean"] is False
    assert result["coverage"] == 50.0


def test_sample_audit_red_flags():
    result = audit("sales", _sample_text())
    flags = {f["name"] for f in result["red_flags"]}
    assert "最终解释权条款" in flags
    assert "违约金畸高" in flags
    assert flags <= {
        "最终解释权条款",
        "概不负责的全面免责",
        "单方变更条款",
        "放弃救济权利的表述",
        "违约金畸高",
        "自动续约且无退出机制",
        "验收期短至无法完成检验",
    }


def test_red_flags_sorted_by_severity():
    result = audit("sales", _sample_text())
    order = ["fatal", "major", "minor", "note"]
    risks = [f["risk"] for f in result["red_flags"]]
    assert risks == sorted(risks, key=order.index)


def test_full_coverage_contract_is_clean():
    text = (
        "争议解决 管辖 保密 不可抗力 通知 送达 合同生效 合同变更 "
        "标的物 价款 交付 验收 所有权转移 质保期"
    )
    result = audit("sales", text)
    assert result["missing_required"] == []
    assert result["coverage"] == 100.0
    assert result["clean"] is True


def test_audit_handles_whitespace():
    """关键词与文本中的空白不应影响匹配。"""
    text = "争 议 解 决\n管\t辖"
    result = audit("sales", text)
    covered = {c["name"] for c in result["covered"]}
    assert "争议解决条款" in covered


def test_format_audit_text():
    result = audit("sales", _sample_text())
    text = format_audit(result)
    assert "合同类型：买卖合同" in text
    assert "必备条款未见" in text
    assert "风险信号" in text
