"""twbdoc CLI。

  twbdoc doc     workbook.twb -o docs/        # Markdown仕様書・定義書
  twbdoc viewer  workbook.twb -o spec.html    # 単一HTMLビューア
  twbdoc doc     workbook.twb -o docs/ --show-connections   # 接続情報マスク解除
"""

from __future__ import annotations

import argparse
import sys

from . import parse, render_html, render_md


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("twb", help="入力する .twb ファイルのパス")
    p.add_argument(
        "--show-connections", action="store_true",
        help="サーバー名・DB名・カスタムSQL本文などの接続情報をマスクせずに出力する",
    )


def cmd_doc(args: argparse.Namespace) -> int:
    wb = parse.parse_file(args.twb)
    out_dir = args.output or "docs"
    written = render_md.write_docs(wb, out_dir, mask_connections=not args.show_connections)
    print(f"Markdown仕様書を書き出しました: {len(written)} ファイル")
    for path in sorted(written):
        print(f"  {path}")
    if wb.unparsed:
        print(f"\n注意: 未対応要素が{len(wb.unparsed)}種類あります（README.mdの「未対応要素」節を参照）")
    return 0


def cmd_viewer(args: argparse.Namespace) -> int:
    wb = parse.parse_file(args.twb)
    out_path = args.output or "spec.html"
    render_html.write_viewer(wb, out_path, mask_connections=not args.show_connections)
    print(f"HTMLビューアを書き出しました: {out_path}")
    if wb.unparsed:
        print(f"注意: 未対応要素が{len(wb.unparsed)}種類あります（ビューア内「概要」タブを参照）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser_ = argparse.ArgumentParser(prog="twbdoc", description=__doc__)
    sub = parser_.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doc", help="Markdown仕様書・定義書を生成する")
    _add_common_args(p_doc)
    p_doc.add_argument("-o", "--output", help="出力ディレクトリ（既定: docs/）")
    p_doc.set_defaults(func=cmd_doc)

    p_viewer = sub.add_parser("viewer", help="単一HTMLビューアを生成する")
    _add_common_args(p_viewer)
    p_viewer.add_argument("-o", "--output", help="出力HTMLファイルパス（既定: spec.html）")
    p_viewer.set_defaults(func=cmd_viewer)

    return parser_


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
