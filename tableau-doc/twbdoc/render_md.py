"""IR(Workbook) → Markdown仕様書・定義書。

出力先は `<out_dir>/<workbook名>/` 配下に固定ファイル名で書き出す:
README.md / datasources.md / calculations.md / worksheets.md /
dashboards.md / actions.md / parameters.md / lineage.md

mask_connections=True（既定）のとき、サーバー名・DB名・ポート・カスタムSQL本文を
「***」に置き換える。twbファイル自体をコミットしない方針と同じ理由で、
生成した仕様書に接続先の機微情報をそのまま載せないための既定挙動。
"""

from __future__ import annotations

import os
from pathlib import Path

from .mask import apply_connection_mask
from .model import Workbook


def _esc_cell(s: str | None) -> str:
    if not s:
        return ""
    return s.replace("|", r"\|").replace("\n", "<br>")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_該当なし_\n"
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_esc_cell(c) for c in row) + " |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------

def render_readme(wb: Workbook, mask_connections: bool) -> str:
    n_ds = len(wb.datasources)
    n_ws = len(wb.worksheets)
    n_db = len(wb.dashboards)
    n_calc = len(wb.all_calculated_fields())
    n_param = len(wb.parameters)
    n_action = len(wb.actions)

    lines = [
        f"# {os.path.basename(wb.source_path) or 'workbook'} 仕様書",
        "",
        f"twbdocにより自動生成。Tableauバージョン: `{wb.tableau_version or '不明'}`",
        "",
        "## 概要",
        "",
        f"| 項目 | 件数 |",
        f"|---|---|",
        f"| データソース | {n_ds} |",
        f"| ワークシート | {n_ws} |",
        f"| ダッシュボード | {n_db} |",
        f"| 計算フィールド | {n_calc} |",
        f"| パラメータ | {n_param} |",
        f"| アクション | {n_action} |",
        "",
        "## 目次",
        "",
        "- [datasources.md](./datasources.md) — データソース・接続・フィールド一覧",
        "- [calculations.md](./calculations.md) — 計算フィールドの定義と依存関係",
        "- [worksheets.md](./worksheets.md) — ワークシートごとのシェルフ・マーク・フィルタ",
        "- [dashboards.md](./dashboards.md) — ダッシュボードのレイアウト構成",
        "- [actions.md](./actions.md) — アクション一覧",
        "- [parameters.md](./parameters.md) — パラメータ定義",
        "- [lineage.md](./lineage.md) — フィールド依存関係図・未使用フィールド",
        "",
    ]

    if mask_connections:
        lines += [
            "> **接続情報はマスクしています。** サーバー名・DB名・カスタムSQL本文は",
            "> `***` で伏せています。表示するには `--show-connections` を付けて再生成してください。",
            "",
        ]

    lines += ["## 未対応要素", ""]
    if wb.unparsed:
        lines += [
            "このtwbには本ツールが認識できなかった要素が含まれていました。",
            "内容の欠落がないか、該当箇所は元のtwbファイルを直接確認してください。",
            "",
        ]
        rows = [[u.tag, u.path, str(u.count)] for u in sorted(wb.unparsed, key=lambda u: (-u.count, u.tag))]
        lines.append(_table(["タグ", "出現箇所", "件数"], rows))
    else:
        lines.append("_未対応要素はありませんでした。_")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# datasources.md
# ---------------------------------------------------------------------------

def render_datasources(wb: Workbook) -> str:
    lines = ["# データソース", ""]
    if not wb.datasources:
        return "\n".join(lines + ["_データソースはありませんでした。_"])

    for ds in wb.datasources.values():
        lines.append(f"## {ds.display_name}")
        lines.append("")
        lines.append(f"内部名: `{ds.name}`")
        lines.append("")

        lines.append("### 接続")
        lines.append("")
        conn_rows = [
            [c.class_, c.server or "", c.port or "", c.dbname or "", c.authentication or ""]
            for c in ds.connections
        ]
        lines.append(_table(["種別", "サーバー", "ポート", "DB名", "認証"], conn_rows))

        lines.append("### リレーション")
        lines.append("")
        rel_rows = []
        for r in ds.relations:
            if r.kind == "join":
                rel_rows.append(["結合", "-", f"結合種別: {r.join_type or '不明'}"])
            elif r.kind == "text":
                rel_rows.append(["カスタムSQL", r.name or "", r.sql or ""])
            else:
                rel_rows.append(["テーブル", r.name or "", r.table or ""])
        lines.append(_table(["種別", "名前", "詳細"], rel_rows))

        lines.append("### フィールド")
        lines.append("")
        field_rows = []
        for col in sorted(ds.columns.values(), key=lambda c: (c.folder or "", c.display_name)):
            kind = "計算" if col.is_calculated else ("グループ" if col.is_group else "通常")
            field_rows.append([
                col.display_name,
                col.folder or "",
                col.datatype or "",
                col.role or "",
                kind,
                "はい" if col.hidden else "",
                col.description or "",
            ])
        lines.append(_table(["フィールド名", "フォルダ", "型", "役割", "種別", "非表示", "説明"], field_rows))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# calculations.md
# ---------------------------------------------------------------------------

def render_calculations(wb: Workbook) -> str:
    calcs = wb.all_calculated_fields()
    lines = ["# 計算フィールド", ""]
    if not calcs:
        return "\n".join(lines + ["_計算フィールドはありませんでした。_"])

    lines.append(f"計 {len(calcs)} 件。")
    lines.append("")

    for ds, col in sorted(calcs, key=lambda t: t[1].display_name):
        lines.append(f"## {col.display_name}")
        lines.append("")
        lines.append(f"データソース: {ds.display_name}")
        lines.append("")
        flags = []
        if col.uses_lod:
            flags.append("LOD式")
        if col.uses_table_calc:
            flags.append("表計算")
        if flags:
            lines.append(f"**注意:** {' / '.join(flags)} を使用しています。DB直結レポート(Phase B)ではSQL変換の対象外になる可能性があります。")
            lines.append("")
        lines.append("```")
        lines.append(col.formula or "")
        lines.append("```")
        lines.append("")
        if col.depends_on:
            lines.append(f"依存フィールド: {', '.join(f'`{d}`' for d in col.depends_on)}")
            lines.append("")
        if col.referenced_by:
            lines.append(f"参照元: {', '.join(col.referenced_by)}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# worksheets.md
# ---------------------------------------------------------------------------

def render_worksheets(wb: Workbook) -> str:
    lines = ["# ワークシート", ""]
    if not wb.worksheets:
        return "\n".join(lines + ["_ワークシートはありませんでした。_"])

    for ws in wb.worksheets.values():
        lines.append(f"## {ws.name}")
        lines.append("")
        lines.append(f"- データソース: {', '.join(ws.datasources) or '不明'}")
        lines.append(f"- マーク種別: {ws.mark_class or '不明'}" + (f"（ペイン数: {ws.pane_count}）" if ws.pane_count > 1 else ""))
        lines.append("")

        lines.append("**列シェルフ:** `" + (ws.cols_raw or "(なし)") + "`  ")
        lines.append("**行シェルフ:** `" + (ws.rows_raw or "(なし)") + "`")
        lines.append("")

        if ws.encodings:
            lines.append("### エンコーディング")
            lines.append("")
            lines.append(_table(["チャネル", "フィールド"], [[e.channel, e.field_display] for e in ws.encodings]))

        if ws.filters:
            lines.append("### フィルタ")
            lines.append("")
            lines.append(_table(
                ["フィールド", "種別", "概要"],
                [[f.field_display, f.filter_class or "", f.summary or ""] for f in ws.filters],
            ))

        if ws.sorts:
            lines.append("### ソート")
            lines.append("")
            lines.append(_table(
                ["フィールド", "方向", "種別"],
                [[s.field_display, s.direction or "", s.sort_class or ""] for s in ws.sorts],
            ))

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# dashboards.md
# ---------------------------------------------------------------------------

def _zone_lines(zone, depth: int = 0) -> list[str]:
    indent = "  " * depth
    label = zone.worksheet_name or zone.zone_type or "(ゾーン)"
    coord = f"x={zone.x:.0f}, y={zone.y:.0f}, w={zone.w:.0f}, h={zone.h:.0f}"
    out = [f"{indent}- {label} `({coord})`"]
    for c in zone.children:
        out.extend(_zone_lines(c, depth + 1))
    return out


def render_dashboards(wb: Workbook) -> str:
    lines = ["# ダッシュボード", ""]
    if not wb.dashboards:
        return "\n".join(lines + ["_ダッシュボードはありませんでした。_"])

    for dash in wb.dashboards.values():
        lines.append(f"## {dash.name}")
        lines.append("")
        lines.append(f"サイズ: {dash.size_w or '自動'} × {dash.size_h or '自動'}")
        lines.append("")
        lines.append(f"含まれるシート: {', '.join(dash.worksheets_used) or 'なし'}")
        lines.append("")
        lines.append("### ゾーン構成")
        lines.append("")
        for z in dash.zones:
            lines.extend(_zone_lines(z))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# actions.md
# ---------------------------------------------------------------------------

def render_actions(wb: Workbook) -> str:
    lines = ["# アクション", ""]
    if not wb.actions:
        return "\n".join(lines + ["_アクションはありませんでした。_"])

    rows = []
    for a in wb.actions:
        rows.append([
            a.name or "(無題)",
            a.action_type,
            a.activation or "",
            ", ".join(a.source_sheets) or "(全シート)",
            ", ".join(a.target_sheets) or "",
        ])
    lines.append(_table(["名前", "種別", "実行契機", "ソース", "ターゲット"], rows))
    unknown = [a for a in wb.actions if a.action_type == "unknown"]
    if unknown:
        lines.append("")
        lines.append(f"> 種別を判別できなかったアクションが{len(unknown)}件あります。元のtwbで内容を確認してください。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# parameters.md
# ---------------------------------------------------------------------------

def render_parameters(wb: Workbook) -> str:
    lines = ["# パラメータ", ""]
    if not wb.parameters:
        return "\n".join(lines + ["_パラメータはありませんでした。_"])

    rows = []
    for p in wb.parameters.values():
        allowed = ", ".join(p.allowed_values) if p.allowed_values else ""
        range_s = f"{p.range_min or ''} 〜 {p.range_max or ''}" if (p.range_min or p.range_max) else ""
        rows.append([
            p.display_name, p.datatype or "", p.current_value or "",
            allowed or range_s or "", ", ".join(p.used_in) or "",
        ])
    lines.append(_table(["名前", "型", "現在値", "許容値/範囲", "使用箇所"], rows))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# lineage.md
# ---------------------------------------------------------------------------

def _mermaid_id(name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in name)
    return "f_" + safe[:60]


def render_lineage(wb: Workbook) -> str:
    lines = ["# フィールド依存関係（リネージ）", ""]
    calcs = wb.all_calculated_fields()

    if calcs:
        lines.append("```mermaid")
        lines.append("graph LR")
        emitted_edges: set[tuple[str, str]] = set()
        for ds, col in calcs:
            cid = _mermaid_id(col.name)
            lines.append(f'  {cid}["{col.display_name}"]')
            for dep in col.depends_on:
                dep_col = ds.columns.get(dep)
                dep_label = dep_col.display_name if dep_col else dep
                did = _mermaid_id(dep)
                edge = (did, cid)
                if edge not in emitted_edges:
                    lines.append(f'  {did}["{dep_label}"] --> {cid}')
                    emitted_edges.add(edge)
        lines.append("```")
        lines.append("")
    else:
        lines.append("_計算フィールドがないため依存関係図はありません。_")
        lines.append("")

    lines.append("## 未使用フィールド候補")
    lines.append("")
    lines.append("どのワークシート・どの計算フィールドからも参照されていないフィールドです。")
    lines.append("（アクション・パラメータからの間接参照など、本ツールが追えていない使用箇所がある可能性があります）")
    lines.append("")
    unused = []
    for ds in wb.datasources.values():
        for col in ds.columns.values():
            if not col.referenced_by and not col.hidden:
                unused.append([ds.display_name, col.display_name])
    if unused:
        lines.append(_table(["データソース", "フィールド"], unused))
    else:
        lines.append("_未使用フィールドは見つかりませんでした。_")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def write_docs(wb: Workbook, out_dir: str, mask_connections: bool = True) -> dict[str, str]:
    base_name = Path(wb.source_path).stem or "workbook"
    target_dir = Path(out_dir) / base_name
    target_dir.mkdir(parents=True, exist_ok=True)

    render_wb = apply_connection_mask(wb) if mask_connections else wb

    contents = {
        "README.md": render_readme(wb, mask_connections),
        "datasources.md": render_datasources(render_wb),
        "calculations.md": render_calculations(wb),
        "worksheets.md": render_worksheets(wb),
        "dashboards.md": render_dashboards(wb),
        "actions.md": render_actions(wb),
        "parameters.md": render_parameters(wb),
        "lineage.md": render_lineage(wb),
    }
    for filename, content in contents.items():
        (target_dir / filename).write_text(content, encoding="utf-8")

    return {str(target_dir / k): v for k, v in contents.items()}
