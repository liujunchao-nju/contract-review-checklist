"""命令行入口。

七条命令：
  list       列出全部合同类型
  show       查看某类型的定位与法条依据
  checklist  生成某个类型的空白审查清单（Markdown / HTML）
  audit      对照清单速检一份合同文本（文本 / JSON / Markdown / HTML）
  bench      查看市场基准区间参照表
  laws       查看经核验的法条库
  verify     校验全部数据文件的结构与引用
"""

from __future__ import annotations

import argparse
import json
import sys

from .audit import audit, format_audit
from .bench import LEVEL_LABELS, UNITS, format_bench, load_benchmarks
from .checklist import PARTIES, compose, list_contracts, load_contract, validate_all
from .laws import load_laws, meta
from .report import FORMATS, render_audit, render_audit_html, render_checklist, render_checklist_html

__all__ = ["main"]


def _write(text: str, out: str | None) -> None:
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"已写入 {out}")
    else:
        sys.stdout.write(text)


def _cmd_list(args) -> int:
    rows = list_contracts()
    width = max(len(str(r.get("type", ""))) for r in rows)
    for row in rows:
        cat = row.get("category", "")
        suffix = f"　[{cat}]" if cat else ""
        print(f"{str(row.get('type', '')).ljust(width)}  {row.get('label', '')}{suffix}")
    return 0


def _cmd_show(args) -> int:
    doc = load_contract(args.type)
    print(f"类型: {doc['type']}")
    print(f"名称: {doc['label']}")
    print(f"分类: {doc.get('category', '')}")
    print(f"文件: {doc['_file']}")
    if doc.get("summary"):
        print(f"交易实质: {str(doc['summary']).strip()}")
    basis = doc.get("legal_basis") or []
    if basis:
        laws = load_laws()
        print("主要依据:")
        for key in basis:
            record = laws.get(key)
            if record:
                print(f"  {record['law']}第{record['article']}条　{record['title']}")
            else:
                print(f"  {key}（未核验）")
    return 0


def _cmd_checklist(args) -> int:
    composed = compose(args.type, args.party)
    if args.format == "html":
        text = render_checklist_html(composed)
    else:
        text = render_checklist(composed)
    _write(text, args.out)
    return 0


def _cmd_audit(args) -> int:
    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()
    result = audit(args.type, text, party=args.party, benchmarks=not args.no_bench)
    if args.json or args.format == "json":
        _write(json.dumps(result, ensure_ascii=False, indent=2), args.out)
    elif args.format == "html":
        _write(render_audit_html(result), args.out)
    elif args.format == "md":
        _write(render_audit(result), args.out)
    else:
        _write(format_audit(result) + "\n", args.out)
    return 0 if result["clean"] else 1


def _cmd_bench(args) -> int:
    rows = load_benchmarks()
    if args.key:
        row = next((r for r in rows if r["id"] == args.key), None)
        if not row:
            print(f"未找到基准项: {args.key}", file=sys.stderr)
            return 1
        print(f"{row['name']}（{row['id']}）")
        print(f"计量：{row['metric']}　单位：{UNITS[row['unit']]}")
        print(f"判定方向：{'越高越不利' if row['direction'] == 'high' else '越低越不利'}")
        print(f"阈值：偏严 {row['thresholds']['caution']}　危险 {row['thresholds']['danger']}")
        for level in ("standard", "caution", "danger"):
            print(f"  {LEVEL_LABELS[level]}：{row['levels'][level]}")
        if row.get("legal_limit"):
            print("注意：本项为法律硬性上限，不是惯例区间。")
        print(f"说明：{row.get('note', '').strip()}")
        print(f"依据：{'；'.join(row.get('basis') or [])}")
        return 0

    print(f"共 {len(rows)} 项基准（市场惯例与法律上限的参照值，不是裁判标准）")
    print("")
    for row in rows:
        mark = "　[法律上限]" if row.get("legal_limit") else ""
        print(f"{row['id']}　{row['name']}　常规 {row['levels']['standard']}{mark}")
    return 0


def _cmd_laws(args) -> int:
    index = load_laws()
    if args.key:
        record = index.get(args.key)
        if not record:
            print(f"未找到法条: {args.key}", file=sys.stderr)
            return 1
        print(f"{record['law']}第{record['article']}条　{record['title']}")
        print(f"施行日期: {record['effective_from']}　效力层级: {record['authority']}")
        print("原文:")
        print(f"  {record['text']}")
        return 0
    info = meta()
    print(f"共 {info['count']} 条，核验于 {info['verified_on']}")
    print(f"来源: {info['verified_by']}")
    print("")
    width = max(len(k) for k in index)
    for key, record in index.items():
        print(f"{key.ljust(width)}  {record['title']}")
    return 0


def _cmd_verify(args) -> int:
    from .bench import validate_benchmarks

    names = validate_all()
    benches = validate_benchmarks()
    info = meta()
    print(f"合同类型 {len(names)} 个: {', '.join(names)}")
    print(f"基准项 {len(benches)} 个")
    print(f"法条库 {info['count']} 条，核验于 {info['verified_on']}")
    print("结构校验通过，引用全部命中法条库。")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="crc",
        description="中文合同审查清单：三观四步框架下的清单生成、速检、基准比对与法条核验",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出全部合同类型").set_defaults(func=_cmd_list)

    show = sub.add_parser("show", help="查看某类型的定位与法条依据")
    show.add_argument("--type", required=True)
    show.set_defaults(func=_cmd_show)

    checklist = sub.add_parser("checklist", help="生成空白审查清单")
    checklist.add_argument("--type", required=True)
    checklist.add_argument("--party", choices=PARTIES, help="审查立场：甲方或乙方")
    checklist.add_argument("--format", choices=FORMATS, default="md", help="输出格式")
    checklist.add_argument("--out", help="输出文件；缺省打印到终端")
    checklist.set_defaults(func=_cmd_checklist)

    audit_cmd = sub.add_parser("audit", help="对照清单速检一份合同文本")
    audit_cmd.add_argument("--type", required=True)
    audit_cmd.add_argument("--file", required=True)
    audit_cmd.add_argument("--party", choices=PARTIES, help="审查立场：甲方或乙方")
    audit_cmd.add_argument(
        "--format", choices=("text", "json", "md", "html"), default="text", help="输出格式"
    )
    audit_cmd.add_argument("--json", action="store_true", help="等价于 --format json")
    audit_cmd.add_argument("--no-bench", action="store_true", help="跳过基准区间比对")
    audit_cmd.add_argument("--out", help="写入文件；缺省打印到终端")
    audit_cmd.set_defaults(func=_cmd_audit)

    bench = sub.add_parser("bench", help="查看市场基准区间参照表")
    bench.add_argument("--key", help="查看某一项的完整阈值")
    bench.set_defaults(func=_cmd_bench)

    laws = sub.add_parser("laws", help="查看经核验的法条库")
    laws.add_argument("--key", help="查看某一条的原文")
    laws.set_defaults(func=_cmd_laws)

    sub.add_parser("verify", help="校验数据文件结构与法条引用").set_defaults(func=_cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
