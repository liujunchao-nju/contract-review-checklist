"""命令行入口。

六条命令：
  list       列出全部合同类型
  show       查看某类型的定位与法条依据
  checklist  生成某个类型的空白审查清单
  audit      对照清单速检一份合同文本
  laws       查看经核验的法条库
  verify     校验全部数据文件的结构与引用
"""

from __future__ import annotations

import argparse
import json
import sys

from .audit import audit, format_audit
from .checklist import compose, list_contracts, load_contract, validate_all
from .laws import load_laws, meta
from .report import render_audit, render_checklist

__all__ = ["main"]


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
    composed = compose(args.type)
    text = render_checklist(composed)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"已写入 {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def _cmd_audit(args) -> int:
    with open(args.file, encoding="utf-8") as fh:
        text = fh.read()
    result = audit(args.type, text)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.markdown:
        out = render_audit(result)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(out)
            print(f"已写入 {args.out}")
        else:
            sys.stdout.write(out)
    else:
        print(format_audit(result))
    return 0 if result["clean"] else 1


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
    names = validate_all()
    info = meta()
    print(f"合同类型 {len(names)} 个: {', '.join(names)}")
    print(f"法条库 {info['count']} 条，核验于 {info['verified_on']}")
    print("结构校验通过，引用全部命中法条库。")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="crc",
        description="中文合同审查清单：三观四步框架下的清单生成、速检与法条核验",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出全部合同类型").set_defaults(func=_cmd_list)

    show = sub.add_parser("show", help="查看某类型的定位与法条依据")
    show.add_argument("--type", required=True)
    show.set_defaults(func=_cmd_show)

    checklist = sub.add_parser("checklist", help="生成空白审查清单（Markdown）")
    checklist.add_argument("--type", required=True)
    checklist.add_argument("--out", help="输出文件；缺省打印到终端")
    checklist.set_defaults(func=_cmd_checklist)

    audit_cmd = sub.add_parser("audit", help="对照清单速检一份合同文本")
    audit_cmd.add_argument("--type", required=True)
    audit_cmd.add_argument("--file", required=True)
    audit_cmd.add_argument("--json", action="store_true", help="输出 JSON")
    audit_cmd.add_argument("--markdown", action="store_true", help="输出 Markdown 报告")
    audit_cmd.add_argument("--out", help="配合 --markdown 写入文件")
    audit_cmd.set_defaults(func=_cmd_audit)

    laws = sub.add_parser("laws", help="查看经核验的法条库")
    laws.add_argument("--key", help="查看某一条的原文")
    laws.set_defaults(func=_cmd_laws)

    sub.add_parser("verify", help="校验数据文件结构与法条引用").set_defaults(func=_cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
