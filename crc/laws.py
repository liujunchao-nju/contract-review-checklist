"""法条库：加载经核验的条文，并校验清单引用。

本模块的作用是把「引用法条」这件事从「凭记忆」变成「查白名单」。
做法：data/laws.yaml 是唯一合法的引用来源，任何清单项引用的法条
都必须以 key 的形式存在于该文件；否则 load_contracts() 会直接报错，
单元测试也会失败。这样就不会出现条号记错、引用已废止条文的情况。
"""

from __future__ import annotations

import pathlib

import yaml

DATA_DIR = pathlib.Path(__file__).parent / "data"
LAWS_FILE = DATA_DIR / "laws.yaml"
CONTRACTS_DIR = DATA_DIR / "contracts"


class LawError(ValueError):
    """法条库或引用不合法。"""


def load_laws() -> dict:
    """读取法条库，返回 {key: 记录}。"""
    with LAWS_FILE.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or "laws" not in doc:
        raise LawError(f"{LAWS_FILE.name} 结构不合法：缺少 laws 字段")
    index: dict[str, dict] = {}
    for record in doc["laws"]:
        for field in ("key", "law", "article", "title", "text"):
            if not record.get(field):
                raise LawError(f"{LAWS_FILE.name} 中有一条记录缺少 {field}: {record}")
        key = record["key"]
        if key in index:
            raise LawError(f"{LAWS_FILE.name} 中存在重复 key: {key}")
        index[key] = record
    if not index:
        raise LawError(f"{LAWS_FILE.name} 中没有任何法条")
    return index


def meta() -> dict:
    """返回法条库的元信息（核验日期、核验方式等）。"""
    with LAWS_FILE.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return {
        "verified_on": doc.get("verified_on", ""),
        "verified_by": doc.get("verified_by", ""),
        "count": len(doc.get("laws", [])),
    }


def look_up(key: str, index: dict | None = None) -> dict:
    """按 key 取回一条法条记录。"""
    index = index if index is not None else load_laws()
    if key not in index:
        raise LawError(f"引用了未核验的法条: {key}")
    return index[key]


def verify_references(keys, index: dict | None = None) -> list[str]:
    """检查一批引用是否都在白名单内，返回未核验的 key 列表。"""
    index = index if index is not None else load_laws()
    return [k for k in keys if k not in index]


def format_law(key: str, index: dict | None = None) -> str:
    """把 key 渲染成一句便于阅读的引用说明。"""
    record = look_up(key, index)
    return (
        f"{record['law']}第{record['article']}条"
        f"（{record['title']}，{record['effective_from']} 施行）"
    )
