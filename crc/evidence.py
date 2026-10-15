"""合同文本的证据匹配。

把 audit 的匹配从「关键词在不在」升级为三级证据：

  标题  关键词出现在条款标题行（如「第三条 价款与结算」）
  正文  关键词出现在正文段落
  缺失  全文未出现

并给出命中位置（行号）与命中词，便于人工复核。
与 gutachten-cn 的 check 一样，这里只做提醒不判分：
命中不等于条款写得没问题，未命中也可能只是换了表述。
"""

from __future__ import annotations

import re

STATUS_HEADING = "标题"
STATUS_BODY = "正文"
STATUS_MISSING = "缺失"

STATUS_ORDER = (STATUS_HEADING, STATUS_BODY, STATUS_MISSING)

# 条款标题的典型形态：Markdown 标题、第 X 条、1. /（一）/ 一、
# 全部按「去掉空白后」的文本匹配，因此「第 一 条」这类排版也能识别
_HEADING_PATTERNS = (
    re.compile(r"^#{1,6}\S"),
    re.compile(r"^第[一二三四五六七八九十百千零\d]+条"),
    re.compile(r"^\d{1,2}[.、]\S"),
    re.compile(r"^[（(][一二三四五六七八九十百千零\d]{1,3}[)）]\S"),
    re.compile(r"^[一二三四五六七八九十]+[、.]\S"),
)

# 标题行通常较短，超过这个长度基本可以判定为正文
_HEADING_MAX_LEN = 40


def normalize(text: str) -> str:
    """去掉所有空白字符，避免换行与空格造成漏配。"""
    return "".join(text.split())


def is_heading(line: str) -> bool:
    """判断一行是否像条款标题。按去掉空白后的文本判断，容忍排版空格。"""
    stripped = normalize(line)
    if not stripped or len(stripped) > _HEADING_MAX_LEN:
        return False
    return any(pattern.match(stripped) for pattern in _HEADING_PATTERNS)


def _rank(candidate: dict) -> tuple[int, int]:
    """排序键：标题优于正文，同级取靠前的一行。"""
    return (0 if candidate["status"] == STATUS_HEADING else 1, candidate["line"])


def match_terms(terms, text: str) -> dict:
    """在一篇合同文本里找一组同义表述，返回最佳证据。

    返回 dict：status / matched / line / excerpt。
    未命中时 status 为「缺失」，line 为 0。
    """
    body = normalize(text)
    if not body:
        return {"status": STATUS_MISSING, "matched": "", "line": 0, "excerpt": ""}

    lines = text.splitlines()
    best: dict | None = None

    for term in terms:
        term_n = normalize(str(term))
        if not term_n:
            continue
        for number, line in enumerate(lines, start=1):
            if term_n not in normalize(line):
                continue
            candidate = {
                "status": STATUS_HEADING if is_heading(line) else STATUS_BODY,
                "matched": str(term),
                "line": number,
                "excerpt": line.strip()[:60],
            }
            if best is None or _rank(candidate) < _rank(best):
                best = candidate
            break  # 同一个词只取首次出现

    return best or {"status": STATUS_MISSING, "matched": "", "line": 0, "excerpt": ""}


def clause_terms(clause: dict) -> list[str]:
    """取出一条条款标准用于匹配的全部表述：名称 + 关键词 + 别名。"""
    terms: list[str] = []
    for source in (clause.get("name"), *(clause.get("keywords") or []), *(clause.get("aliases") or [])):
        if not source:
            continue
        value = str(source)
        if value not in terms:
            terms.append(value)
    return terms


def flag_terms(flag: dict) -> list[str]:
    """取出一条风险信号用于匹配的全部表述。"""
    terms: list[str] = []
    for source in (flag.get("name"), *(flag.get("patterns") or [])):
        if not source:
            continue
        value = str(source)
        if value not in terms:
            terms.append(value)
    return terms
