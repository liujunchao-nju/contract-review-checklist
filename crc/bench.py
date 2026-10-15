"""市场基准阈值库：加载、校验与扫描。

与法条库的分工必须分清：

  laws.yaml        法律规定。条号与原文一一对应，引用错误是硬错误。
  benchmarks.yaml  市场惯例区间与法律硬性上限的参照值。
                    不是法律规定，只用于发现「明显离谱」的条款，
                    不得当作谈判依据或裁判标准写进对外文件。

两者共用同一条纪律：引用的法条 key 必须在 laws.yaml 白名单内，
否则 `crc verify` 与单元测试会报错。
"""

from __future__ import annotations

import re

import yaml

from .evidence import normalize
from .laws import DATA_DIR, verify_references

BENCH_FILE = DATA_DIR / "benchmarks.yaml"

LEVEL_ORDER = ("danger", "caution", "standard")
LEVEL_LABELS = {"standard": "常规", "caution": "偏严", "danger": "危险"}

UNITS = {
    "percent": "%",
    "months": "个月",
    "days": "日",
    "years": "年",
}

DIRECTIONS = ("high", "low")

# 取数窗口：命中锚点行之后再看两行，覆盖「标题写条款名、正文写数值」的常见排版
_WINDOW = 3

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}

_UNIT_PATTERNS = {
    "percent": (
        re.compile(r"(\d+(?:\.\d+)?)\s*[%％]"),
        re.compile(r"百分之([零〇一两二三四五六七八九十百千\d]+(?:\.\d+)?)"),
    ),
    "months": (
        re.compile(r"(\d+(?:\.\d+)?)\s*个月"),
        re.compile(r"([零〇一两二三四五六七八九十百千]+)\s*个月"),
    ),
    "days": (
        re.compile(r"(\d+(?:\.\d+)?)\s*(?:个?自然日|个?工作日|日|天)"),
        re.compile(r"([零〇一两二三四五六七八九十百千]+)\s*(?:个?自然日|个?工作日|日|天)"),
    ),
    "years": (
        re.compile(r"(\d+(?:\.\d+)?)\s*年"),
        re.compile(r"([零〇一两二三四五六七八九十百千]+)\s*年"),
    ),
}

_REQUIRED_FIELDS = ("id", "name", "unit", "direction", "anchors", "thresholds", "levels")


class BenchError(ValueError):
    """基准库结构或引用不合法。"""


def _cn_number(text: str) -> float | None:
    """把「二十四」「一百二十」这类中文数字转成阿拉伯数字。"""
    section = 0
    number = 0
    for char in text:
        if char in _CN_UNITS:
            section += (number or 1) * _CN_UNITS[char]
            number = 0
        elif char in _CN_DIGITS:
            number = _CN_DIGITS[char]
        elif char.isdigit() or char == ".":
            return None  # 混排数字交给正则分支处理
        else:
            return None
    return float(section + number)


def _to_number(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return _cn_number(raw)


def _numbers_in(line: str, unit: str) -> list[float]:
    """从一行文本里抽出指定单位的全部数值。"""
    found: list[float] = []
    for index, pattern in enumerate(_UNIT_PATTERNS[unit]):
        for match in pattern.finditer(line):
            value = _to_number(match.group(1))
            if value is None or value <= 0:
                continue
            # 阿拉伯分支已是数字；中文分支经 _cn_number 转换
            if index == 0 and not re.match(r"^\d", match.group(1).strip()):
                value = _cn_number(match.group(1)) or value
            found.append(value)
    return found


def load_benchmarks() -> list[dict]:
    """读取基准库。"""
    with BENCH_FILE.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or "benchmarks" not in doc:
        raise BenchError("benchmarks.yaml 结构不合法：缺少 benchmarks 字段")
    return doc["benchmarks"]


def validate_benchmarks(law_index: dict | None = None) -> list[str]:
    """校验基准库，返回 id 列表；不合法则抛错。"""
    from .laws import load_laws

    index = law_index if law_index is not None else load_laws()
    rows = load_benchmarks()
    seen: set[str] = set()
    names: list[str] = []
    for row in rows:
        lack = [field for field in _REQUIRED_FIELDS if not row.get(field)]
        if lack:
            raise BenchError(f"基准条目 {row.get('id', '?')} 缺少 {', '.join(lack)}")
        ident = row["id"]
        if ident in seen:
            raise BenchError(f"benchmarks.yaml 中存在重复 id: {ident}")
        seen.add(ident)
        if row["unit"] not in UNITS:
            raise BenchError(f"{ident} 的 unit 非法: {row['unit']}")
        if row["direction"] not in DIRECTIONS:
            raise BenchError(f"{ident} 的 direction 非法: {row['direction']}")
        thresholds = row["thresholds"]
        for level in ("caution", "danger"):
            if not isinstance(thresholds.get(level), (int, float)):
                raise BenchError(f"{ident} 的 thresholds.{level} 必须是数值")
        for level in LEVEL_ORDER:
            if not row["levels"].get(level):
                raise BenchError(f"{ident} 的 levels.{level} 为空")
        unknown = verify_references(row.get("basis") or [], index)
        if unknown:
            raise BenchError(f"{ident} 引用了未核验的法条: {', '.join(sorted(set(unknown)))}")
        names.append(ident)
    return names


def judge(value: float, bench: dict) -> str:
    """按方向与阈值判定区间。"""
    caution = float(bench["thresholds"]["caution"])
    danger = float(bench["thresholds"]["danger"])
    if bench.get("direction", "high") == "high":
        if value > danger:
            return "danger"
        return "caution" if value > caution else "standard"
    if value < danger:
        return "danger"
    return "caution" if value < caution else "standard"


def _scan(bench: dict, lines: list[str], norm_lines: list[str]) -> dict | None:
    """在一篇合同文本里扫描一条基准。"""
    anchors = [normalize(str(a)) for a in bench["anchors"] if str(a).strip()]
    unit = bench["unit"]
    hits: list[tuple[float, int, str]] = []

    for number, norm in enumerate(norm_lines):
        if not any(anchor in norm for anchor in anchors):
            continue
        for offset in range(_WINDOW):
            position = number + offset
            if position >= len(lines):
                break
            for value in _numbers_in(lines[position], unit):
                hits.append((value, position + 1, lines[position].strip()[:60]))
            if hits:
                break
        if hits:
            break  # 取首个命中锚点即可，避免过度扫描

    if not hits:
        return None

    # 取最不利的那个值：偏高为患取最大，偏低为患取最小，属保守判断
    adverse = max if bench.get("direction", "high") == "high" else min
    value, line, excerpt = adverse(hits, key=lambda item: item[0])
    level = judge(value, bench)
    return {
        "id": bench["id"],
        "name": bench["name"],
        "value": value,
        "unit": unit,
        "unit_label": UNITS[unit],
        "level": level,
        "line": line,
        "excerpt": excerpt,
        "levels": bench["levels"],
        "basis": bench.get("basis") or [],
        "note": (bench.get("note") or "").strip(),
        "legal_limit": bool(bench.get("legal_limit")),
    }


def evaluate(text: str, benchmarks: list[dict] | None = None) -> list[dict]:
    """扫描合同文本，返回偏离常规区间的基准项。"""
    benches = benchmarks if benchmarks is not None else load_benchmarks()
    lines = text.splitlines()
    norm_lines = [normalize(line) for line in lines]
    rows = []
    for bench in benches:
        hit = _scan(bench, lines, norm_lines)
        if hit:
            rows.append(hit)
    rows.sort(key=lambda row: (LEVEL_ORDER.index(row["level"]), row["id"]))
    return rows


def format_bench(rows: list[dict], laws: dict | None = None) -> str:
    """把基准扫描结果渲染成终端可读的文字。"""
    lines: list[str] = []
    if not rows:
        return "未检出偏离常规区间的量化条款。"
    for row in rows:
        label = LEVEL_LABELS.get(row["level"], row["level"])
        marker = "（法律上限）" if row["legal_limit"] else ""
        value = f"{row['value']:g}{row['unit_label']}"
        lines.append(f"  - [{label}] {row['name']}：{value}{marker}（第 {row['line']} 行）")
        lines.append(f"      区间：常规 {row['levels']['standard']}；"
                     f"偏严 {row['levels']['caution']}；危险 {row['levels']['danger']}")
        if row["note"]:
            lines.append(f"      {row['note']}")
        if row["basis"]:
            lines.append(f"      依据：{'；'.join(row['basis'])}")
    return "\n".join(lines)


def format_bench_rows(rows: list[dict]) -> str:
    """渲染成 Markdown 表格行，供报告复用。"""
    if not rows:
        return "未检出偏离常规区间的量化条款。\n"
    out = ["| 项目 | 检出值 | 判定 | 常规区间 | 说明 |", "| --- | --- | --- | --- | --- |"]
    for row in rows:
        label = LEVEL_LABELS.get(row["level"], row["level"])
        value = f"{row['value']:g}{row['unit_label']}"
        note = " ".join((row["note"] or "").split())
        out.append(
            f"| {row['name']} | {value} | {label} | {row['levels']['standard']} | {note} |"
        )
    return "\n".join(out) + "\n"
