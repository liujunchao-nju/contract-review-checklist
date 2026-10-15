"""测试三级证据匹配：标题 / 正文 / 缺失，以及命中位置。"""

from __future__ import annotations

from crc.evidence import (
    STATUS_BODY,
    STATUS_HEADING,
    STATUS_MISSING,
    clause_terms,
    is_heading,
    match_terms,
    normalize,
)


def test_normalize_strips_whitespace():
    assert normalize("争 议 解 决\n管\t辖") == "争议解决管辖"


def test_heading_detection():
    assert is_heading("第三条 价款与结算")
    assert is_heading("## 争议解决")
    assert is_heading("1. 标的")
    assert is_heading("（二）保密义务")
    assert is_heading("一、通知与送达")
    # 正文段落不应被误判为标题
    assert not is_heading("甲方应当在收到货物后七日内完成验收并书面通知乙方，逾期视为合格。")


def test_match_heading_preferred_over_body():
    text = "第三条 争议解决\n双方发生争议应协商解决，协商不成的提交仲裁。\n"
    hit = match_terms(["争议解决"], text)
    assert hit["status"] == STATUS_HEADING
    assert hit["line"] == 1


def test_match_body_when_not_in_heading():
    text = "双方发生争议时应先行协商。\n"
    hit = match_terms(["争议解决", "争议"], text)
    assert hit["status"] == STATUS_BODY
    assert hit["line"] == 1


def test_match_missing():
    hit = match_terms(["不存在的条款"], "甲方与乙方就货物买卖达成一致。\n")
    assert hit["status"] == STATUS_MISSING
    assert hit["line"] == 0
    assert hit["matched"] == ""


def test_match_reports_line_number():
    text = "第一条 标的\n第二条 价款\n甲方应在十日内支付价款。\n"
    hit = match_terms(["价款"], text)
    assert hit["line"] == 2  # 取最靠前的命中，且标题优先


def test_match_handles_whitespace_inside_text():
    """文本内的空格既不应影响匹配，也不应影响标题行的判定。"""
    text = "第 一 条　争 议 解 决\n"
    hit = match_terms(["争议解决"], text)
    assert hit["status"] == STATUS_HEADING
    assert hit["matched"] == "争议解决"
    assert hit["line"] == 1


def test_clause_terms_merges_name_keywords_and_aliases():
    clause = {
        "name": "保密条款",
        "keywords": ["保密", "商业秘密"],
        "aliases": ["机密信息"],
    }
    terms = clause_terms(clause)
    assert terms == ["保密条款", "保密", "商业秘密", "机密信息"]


def test_empty_text_is_missing():
    assert match_terms(["保密"], "")["status"] == STATUS_MISSING
