"""测试市场基准区间库：结构校验、阈值判定与文本扫描。"""

from __future__ import annotations

import pytest

from crc.bench import (
    BenchError,
    LEVEL_ORDER,
    _cn_number,
    evaluate,
    judge,
    load_benchmarks,
    validate_benchmarks,
)
from crc.laws import load_laws


def test_load_benchmarks_shape():
    rows = load_benchmarks()
    assert len(rows) >= 8
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "基准 id 不得重复"


def test_validate_benchmarks_passes_and_checks_law_refs():
    names = validate_benchmarks(load_laws())
    assert "penalty-ratio" in names


def test_benchmarks_basis_all_verified():
    """基准库的法条引用同样必须命中白名单。"""
    index = load_laws()
    for row in load_benchmarks():
        for key in row.get("basis") or []:
            assert key in index, f"{row['id']} 引用了未核验的法条: {key}"


def test_benchmark_structure_fields():
    for row in load_benchmarks():
        for level in LEVEL_ORDER:
            assert row["levels"].get(level), f"{row['id']} 缺 levels.{level}"
        assert row["thresholds"]["caution"]
        assert row["thresholds"]["danger"]


def test_cn_number_conversion():
    assert _cn_number("二十四") == 24
    assert _cn_number("二十") == 20
    assert _cn_number("三") == 3
    assert _cn_number("一百二十") == 120
    assert _cn_number("三十") == 30


def _bench(direction="high", caution=30, danger=50):
    return {"thresholds": {"caution": caution, "danger": danger}, "direction": direction}


def test_judge_high_direction():
    assert judge(10, _bench()) == "standard"
    assert judge(40, _bench()) == "caution"
    assert judge(80, _bench()) == "danger"


def test_judge_low_direction():
    bench = _bench(direction="low", caution=12, danger=6)
    assert judge(24, bench) == "standard"
    assert judge(8, bench) == "caution"
    assert judge(3, bench) == "danger"


def test_evaluate_detects_arabic_percent():
    text = "第三条 违约责任\n乙方违约的，应按合同总额的 80% 支付违约金。\n"
    rows = evaluate(text)
    hit = next((r for r in rows if r["id"] == "penalty-ratio"), None)
    assert hit is not None
    assert hit["value"] == 80
    assert hit["level"] == "danger"
    assert hit["line"] == 2


def test_evaluate_detects_chinese_percent():
    text = "乙方违约的，应按合同总额的百分之五十支付违约金。\n"
    rows = evaluate(text)
    hit = next((r for r in rows if r["id"] == "penalty-ratio"), None)
    assert hit is not None
    assert hit["value"] == 50
    assert hit["level"] == "caution"


def test_evaluate_detects_months_for_warranty():
    text = "质量保证期为三个月，自验收合格之日起算。\n"
    rows = evaluate(text)
    hit = next((r for r in rows if r["id"] == "warranty-period"), None)
    assert hit is not None
    assert hit["value"] == 3
    assert hit["level"] == "danger"


def test_evaluate_returns_nothing_when_no_anchor():
    rows = evaluate("本合同双方就合作事宜达成一致，未尽事宜另行协商。\n")
    assert rows == []


def test_evaluate_sorted_by_severity():
    text = ("违约金按合同总额的 80% 计算。\n质保期为三个月。\n")
    rows = evaluate(text)
    levels = [LEVEL_ORDER.index(r["level"]) for r in rows]
    assert levels == sorted(levels)


def test_legal_limit_flag_present():
    rows = load_benchmarks()
    flagged = [r["id"] for r in rows if r.get("legal_limit")]
    assert "non-compete" in flagged
    assert "lease-term" in flagged


def test_invalid_benchmark_rejected(monkeypatch):
    """基准条目缺字段时应当报错，而不是静默通过。"""
    import crc.bench as bench

    monkeypatch.setattr(
        bench,
        "load_benchmarks",
        lambda: [{"id": "bad", "name": "坏样本", "unit": "percent", "direction": "high",
                  "anchors": ["违约金"], "thresholds": {"caution": 30, "danger": 50},
                  "levels": {"standard": "a", "caution": "b", "danger": "c"},
                  "basis": ["幻想法第1条"]}],
    )
    with pytest.raises(BenchError):
        bench.validate_benchmarks(load_laws())
