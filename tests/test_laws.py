"""测试法条库：加载、唯一性、引用校验。"""

from __future__ import annotations

import pytest

from crc.laws import LawError, format_law, load_laws, look_up, meta, verify_references


def test_laws_load_and_unique():
    index = load_laws()
    assert len(index) >= 40
    assert len(index) == len(set(index))


def test_laws_required_fields():
    for key, record in load_laws().items():
        assert record["law"], key
        assert isinstance(record["article"], int), key
        assert record["title"], key
        assert record["text"], key
        assert record["effective_from"], key


def test_meta_matches_index():
    info = meta()
    assert info["count"] == len(load_laws())
    assert info["verified_on"]
    assert info["verified_by"]


def test_look_up_hit_and_miss():
    record = look_up("民法典第585条")
    assert record["article"] == 585
    assert "违约金" in record["text"]

    with pytest.raises(LawError):
        look_up("民法典第99999条")


def test_verify_references():
    assert verify_references(["民法典第585条", "合同编通则解释第15条"]) == []
    assert verify_references(["民法典第585条", "幻想法第1条"]) == ["幻想法第1条"]


def test_format_law_contains_title():
    text = format_law("民法典第585条")
    assert "中华人民共和国民法典第585条" in text
    assert "违约金的约定与司法调整" in text
    assert "2021-01-01" in text


def test_key_article_correspondence():
    """抽查条号与内容是否对应，防止张冠李戴。"""
    index = load_laws()
    assert "格式条款" in index["民法典第496条"]["text"]
    assert "二十年" in index["民法典第705条"]["text"]
    assert "百分之三十" in index["合同编通则解释第65条"]["text"]
    assert "五年内缴足" in index["公司法第47条"]["text"]
    assert "不得超过二年" in index["劳动合同法第24条"]["text"]
