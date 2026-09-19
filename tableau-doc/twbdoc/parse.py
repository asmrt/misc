"""twb XML → IR(Workbook) への変換。

方針: **未知の要素で例外を投げない**。公式XSD(2026.1/2026.2)は実務でよく使われる
古い版のtwbと要素構成が揺れる可能性があるため、想定外のタグ/属性に遭遇したら
`UnparsedElement` として収集し、処理は止めずに続行する。

このパーサが読み取るのはXML構造から機械的に判別できる範囲まで。
Tableau計算式の意味解析やshelf文字列の完全な構文解析は行わない
（`calc.py` が計算式から依存フィールドとLOD/表計算の有無だけを best-effort で拾う）。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

from . import calc, fieldref
from .model import (
    ActionSpec,
    Column,
    Connection,
    DataSource,
    Dashboard,
    Encoding,
    FilterSpec,
    Parameter,
    Relation,
    SortSpec,
    UnparsedElement,
    Workbook,
    Worksheet,
    Zone,
)

# セクションごとに「読み取り済みとして扱う」直下の子タグ名。
# ここに無いタグは UnparsedElement として記録するが、処理は継続する。
_HANDLED = {
    "workbook": {
        "preferences", "repository-location", "document-format-change-manifest",
        "_.fcp.ObjectModelEncapsulateLegacyFields.true...ObjectModelEncapsulateLegacyFields",
        "datasources", "worksheets", "dashboards", "windows", "actions",
        "datasource-dependencies", "style", "thumbnails", "shapes", "extensions",
        "explain-data-options", "_.fcp.SetMembershipControl.false...enable-set-toggle",
        "map-sources",
    },
    "datasource": {
        "connection", "column", "column-instance", "group", "folder",
        "folders-common", "folders-parameters",
        "drill-paths", "layout", "semantic-values", "extract", "aliases",
        "_.fcp.SchemaViewerObjectModel.true...object-graph", "object-graph",
    },
    "worksheet": {"table", "layout-options", "simple-id"},
    "dashboard": {"size", "zones", "devicelayouts", "simple-id"},
}


def _record_unparsed(wb: Workbook, tag: str, path: str, attrib: dict) -> None:
    sample = {k: v for k, v in list(attrib.items())[:4]}
    for u in wb.unparsed:
        if u.tag == tag and u.path == path:
            u.count += 1
            return
    wb.unparsed.append(UnparsedElement(tag=tag, path=path, count=1, sample_attrib=sample))


def _check_children(wb: Workbook, el: ET.Element, section: str, path: str) -> None:
    handled = _HANDLED.get(section, set())
    for child in el:
        tag = _local(child.tag)
        if tag not in handled:
            _record_unparsed(wb, tag, path, child.attrib)


def _local(tag: str) -> str:
    """`{namespace}tag` 形式から namespace を落として tag 名だけ返す。"""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _text(el: Optional[ET.Element]) -> Optional[str]:
    if el is None or el.text is None:
        return None
    t = el.text.strip()
    return t or None


def _desc_text(desc_el: Optional[ET.Element]) -> Optional[str]:
    """<desc><formatted-text><run>...</run></formatted-text></desc> からプレーンテキストを拾う。"""
    if desc_el is None:
        return None
    parts = [t.strip() for t in desc_el.itertext() if t and t.strip()]
    return "\n".join(parts) if parts else None


def parse_file(path: str) -> Workbook:
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        # XMLとして壊れている場合はここだけは例外を投げる（続行しようがないため）
        raise ValueError(f"twbファイルのXML解析に失敗しました: {e}") from e
    root = tree.getroot()
    return parse_root(root, source_path=path)


def parse_root(root: ET.Element, source_path: str = "") -> Workbook:
    wb = Workbook(source_path=source_path, tableau_version=root.attrib.get("version"))

    _check_children(wb, root, "workbook", "workbook")

    ds_el = root.find("datasources")
    if ds_el is not None:
        _parse_datasources(wb, ds_el)

    ws_el = root.find("worksheets")
    if ws_el is not None:
        _parse_worksheets(wb, ws_el)

    db_el = root.find("dashboards")
    if db_el is not None:
        _parse_dashboards(wb, db_el)

    actions_el = root.find("actions")
    if actions_el is not None:
        _parse_actions(wb, actions_el)

    _cross_reference(wb)
    return wb


# ---------------------------------------------------------------------------
# datasources / columns / parameters
# ---------------------------------------------------------------------------

def _parse_datasources(wb: Workbook, ds_root: ET.Element) -> None:
    for ds_el in ds_root.findall("datasource"):
        name = ds_el.attrib.get("name", "")
        caption = ds_el.attrib.get("caption")
        ds = DataSource(name=name, caption=caption, version=ds_el.attrib.get("version"))

        # 接続情報（<connection> は単独、または <named-connections><named-connection><connection>）
        for conn_el in ds_el.iter("connection"):
            attrib = conn_el.attrib
            if attrib.get("class") == "federated":
                # "federated" は複数接続をまとめる構造上のラッパーで、実体のバックエンド接続は
                # <named-connections> 配下に別途 <connection class='postgres'> 等として現れる。
                # ラッパー自体は情報を持たないので出力からは省く。
                continue
            ds.connections.append(Connection(
                class_=attrib.get("class", ""),
                server=attrib.get("server"),
                port=attrib.get("port"),
                dbname=attrib.get("dbname"),
                authentication=attrib.get("authentication"),
            ))

        # リレーション（テーブル / カスタムSQL / 結合）。ネストは平坦化しつつ join は種別だけ記録
        for rel_el in ds_el.iter("relation"):
            kind_attr = rel_el.attrib.get("type", "table")
            if kind_attr == "join":
                ds.relations.append(Relation(kind="join", join_type=rel_el.attrib.get("join")))
                continue
            if kind_attr == "text":
                ds.relations.append(Relation(
                    kind="text",
                    name=rel_el.attrib.get("name"),
                    sql=(rel_el.text or "").strip() or None,
                ))
                continue
            ds.relations.append(Relation(
                kind="table",
                name=rel_el.attrib.get("name"),
                table=rel_el.attrib.get("table"),
            ))

        # フォルダ割り当て（<folder><folder-item name='[Sales]'/></folder>）
        folder_of: dict[str, str] = {}
        # <folder> は <folders-common>/<folders-parameters> 配下に現れる（版によっては直下の場合もある）
        for folder_el in ds_el.iter("folder"):
            fname = folder_el.attrib.get("name", "")
            for item_el in folder_el.findall("folder-item"):
                item_name = item_el.attrib.get("name", "").strip("[]")
                if item_name:
                    folder_of[item_name] = fname

        for col_el in ds_el.findall("column"):
            col = _parse_column(col_el)
            col.folder = folder_of.get(col.name)
            ds.columns[col.name] = col

        for ci_el in ds_el.findall("column-instance"):
            # 集計付きの列インスタンス。参照先(source-column)が既存カラムにあれば
            # そのキャプションを引き継ぎ、無ければ最小限の情報で登録する
            ci_name = ci_el.attrib.get("name", "").strip("[]")
            src = ci_el.attrib.get("column", "").strip("[]")
            if ci_name and ci_name not in ds.columns:
                base = ds.columns.get(src)
                ds.columns[ci_name] = Column(
                    name=ci_name,
                    caption=(base.caption if base else None),
                    datatype=(base.datatype if base else None),
                    role=ci_el.attrib.get("type"),
                    default_aggregation=ci_el.attrib.get("derivation"),
                )

        for grp_el in ds_el.findall("group"):
            grp_name = grp_el.attrib.get("name", "").strip("[]")
            if grp_name:
                ds.columns.setdefault(grp_name, Column(name=grp_name, caption=grp_el.attrib.get("caption")))
                ds.columns[grp_name].is_group = True

        _check_children(wb, ds_el, "datasource", f"datasource[{name}]")

        if name == "Parameters" or (caption and caption.lower() == "parameters"):
            _absorb_parameters(wb, ds_el)
        else:
            wb.datasources[name] = ds


def _parse_column(col_el: ET.Element) -> Column:
    attrib = col_el.attrib
    col = Column(
        name=attrib.get("name", "").strip("[]"),
        caption=attrib.get("caption"),
        datatype=attrib.get("datatype"),
        role=attrib.get("role"),
        field_type=attrib.get("type"),
        default_aggregation=attrib.get("default-aggregation") or attrib.get("aggregation"),
        hidden=attrib.get("hidden", "false") == "true",
    )
    col.description = _desc_text(col_el.find("desc"))

    calc_el = col_el.find("calculation")
    if calc_el is not None:
        calc_class = calc_el.attrib.get("class")
        if calc_class in ("bin", "categorical-bin"):
            # ビン化フィールドは <calculation class='bin' column='[元フィールド]' size='...'/>
            # という形で表現され、<column> に formula を持つ通常の計算フィールドとは別扱い。
            col.has_bin = True
            src_col = calc_el.attrib.get("column", "").strip("[]")
            if src_col:
                col.depends_on = [src_col]
        elif calc_class in ("tableau", None):
            col.is_calculated = True
            col.formula = calc_el.attrib.get("formula")
            analysis = calc.analyze(col.formula or "")
            col.depends_on = analysis.depends_on
            col.uses_lod = analysis.uses_lod
            col.uses_table_calc = analysis.uses_table_calc
        # class == "passthrough" 等、上記以外は詳細不明のため素通りする
    return col


def _strip_quotes(v: Optional[str]) -> Optional[str]:
    """Tableauの `value` 属性は文字列定数をクォート付きのまま保持する
    （例: `value='&quot;直近12ヶ月&quot;'` → XML展開後は `"直近12ヶ月"`）。
    見た目の値として使えるよう外側のクォートを剥がし、`""` エスケープを戻す。
    """
    if v is None:
        return None
    v = v.strip()
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1].replace('""', '"')
    return v


def _absorb_parameters(wb: Workbook, ds_el: ET.Element) -> None:
    """データソース名が "Parameters" のときだけ呼ばれる。
    通常のカラムパースでは拾わない `value` / `range` / `members` を直接XMLから読む。
    """
    for col_el in ds_el.findall("column"):
        attrib = col_el.attrib
        name = attrib.get("name", "").strip("[]")
        if not name:
            continue
        param = Parameter(
            name=name,
            caption=attrib.get("caption"),
            datatype=attrib.get("datatype"),
            current_value=_strip_quotes(attrib.get("value")),
        )
        range_el = col_el.find("range")
        if range_el is not None:
            param.range_min = range_el.attrib.get("min")
            param.range_max = range_el.attrib.get("max")
            # 属性名は "granularity"（公式XSD 2026.1で確認）。念のため旧称 "step" も見る。
            param.range_step = range_el.attrib.get("granularity") or range_el.attrib.get("step")
        members_el = col_el.find("members")
        if members_el is not None:
            for m in members_el.findall("member"):
                v = _strip_quotes(m.attrib.get("value"))
                if v is not None:
                    param.allowed_values.append(v)
        wb.parameters[name] = param


# ---------------------------------------------------------------------------
# worksheets
# ---------------------------------------------------------------------------

def _parse_worksheets(wb: Workbook, ws_root: ET.Element) -> None:
    for ws_el in ws_root.findall("worksheet"):
        name = ws_el.attrib.get("name", "")
        ws = Worksheet(name=name)

        table_el = ws_el.find("table")
        if table_el is not None:
            for dep_el in table_el.iter("datasource-dependencies"):
                dsn = dep_el.attrib.get("datasource")
                if dsn and dsn not in ws.datasources:
                    ws.datasources.append(dsn)

            rows_el = table_el.find("rows")
            cols_el = table_el.find("cols")
            ws.rows_raw = _text(rows_el) or ""
            ws.cols_raw = _text(cols_el) or ""
            ws.row_fields = calc.extract_field_refs(ws.rows_raw)
            ws.col_fields = calc.extract_field_refs(ws.cols_raw)

            panes = list(table_el.iter("pane"))
            ws.pane_count = len(panes) or 1
            if panes:
                mark_el = panes[0].find("mark")
                if mark_el is not None:
                    ws.mark_class = mark_el.attrib.get("class")
                enc_el = panes[0].find("encodings")
                if enc_el is not None:
                    for child in enc_el:
                        channel = _local(child.tag)
                        raw = child.attrib.get("column", "")
                        if raw:
                            decoded = fieldref.decode(raw)
                            ws.encodings.append(Encoding(
                                channel=channel, field_raw=raw, field_display=decoded.display,
                            ))

            for filt_el in table_el.iter("filter"):
                raw = filt_el.attrib.get("column", "")
                decoded = fieldref.decode(raw) if raw else None
                members = filt_el.findall(".//groupfilter[@member]")
                summary = None
                if members:
                    summary = f"{len(members)}件の選択値"
                elif filt_el.find("min") is not None or filt_el.find("max") is not None:
                    lo = _text(filt_el.find("min"))
                    hi = _text(filt_el.find("max"))
                    summary = f"範囲: {lo or '?'} 〜 {hi or '?'}"
                ws.filters.append(FilterSpec(
                    field_raw=raw,
                    field_display=(decoded.display if decoded else raw),
                    filter_class=filt_el.attrib.get("class"),
                    summary=summary,
                ))

            # ソートは <sort> という単一タグではなく、種別ごとに
            # <manual-sort>/<computed-sort>（column属性を持つ）/
            # <natural-sort>/<alphabetic-sort>（属性なし）として現れる。
            # 後者2つは対象列を自身の属性に持たないため、直前の兄弟 <filter> の
            # column を対象とみなす（公式XSDの ViewSpecification-G が
            # (filter, sort)* という対で定義しているのに倣う）。
            _SORT_TAGS = ("manual-sort", "computed-sort", "natural-sort", "alphabetic-sort")
            preceding_filter_column = None
            for view_el in table_el.iter("view"):
                for child in view_el:
                    tag = _local(child.tag)
                    if tag == "filter":
                        preceding_filter_column = child.attrib.get("column")
                        continue
                    if tag not in _SORT_TAGS:
                        continue
                    raw = child.attrib.get("column") or preceding_filter_column or ""
                    if not raw:
                        continue
                    decoded = fieldref.decode(raw)
                    ws.sorts.append(SortSpec(
                        field_raw=raw,
                        field_display=decoded.display,
                        direction=child.attrib.get("direction"),
                        sort_class=tag,
                    ))

        wb.worksheets[name] = ws


# ---------------------------------------------------------------------------
# dashboards
# ---------------------------------------------------------------------------

def _to_float(v: Optional[str]) -> float:
    try:
        return float(v) if v is not None else 0.0
    except ValueError:
        return 0.0


def _parse_zone(zone_el: ET.Element) -> Zone:
    attrib = zone_el.attrib
    zone = Zone(
        zone_id=attrib.get("id"),
        x=_to_float(attrib.get("x")),
        y=_to_float(attrib.get("y")),
        w=_to_float(attrib.get("w")),
        h=_to_float(attrib.get("h")),
        zone_type=attrib.get("type") or attrib.get("param"),
        worksheet_name=attrib.get("name") if attrib.get("type") in (None, "", "worksheet") else None,
    )
    for child in zone_el.findall("zone"):
        zone.children.append(_parse_zone(child))
    return zone


def _parse_dashboards(wb: Workbook, db_root: ET.Element) -> None:
    for db_el in db_root.findall("dashboard"):
        name = db_el.attrib.get("name", "")
        dash = Dashboard(name=name)

        size_el = db_el.find("size")
        if size_el is not None:
            dash.size_w = size_el.attrib.get("maxwidth") or size_el.attrib.get("width")
            dash.size_h = size_el.attrib.get("maxheight") or size_el.attrib.get("height")

        zones_el = db_el.find("zones")
        if zones_el is not None:
            for zone_el in zones_el.findall("zone"):
                dash.zones.append(_parse_zone(zone_el))

        def collect_ws_names(z: Zone) -> None:
            if z.worksheet_name:
                dash.worksheets_used.append(z.worksheet_name)
            for c in z.children:
                collect_ws_names(c)

        for z in dash.zones:
            collect_ws_names(z)

        _check_children(wb, db_el, "dashboard", f"dashboard[{name}]")
        wb.dashboards[name] = dash


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def _infer_action_type(action_el: ET.Element) -> str:
    tags = {_local(c.tag) for c in action_el}
    if "filter" in tags:
        return "filter"
    if "highlight" in tags:
        return "highlight"
    if "url" in tags:
        return "url"
    if "parameter" in tags:
        return "parameter"
    if "sheet" in tags and len(tags) <= 2:
        return "go-to-sheet"
    if "set-value" in tags or "set" in tags:
        return "set"
    return "unknown"


def _parse_actions(wb: Workbook, actions_root: ET.Element) -> None:
    for action_el in actions_root.findall("action"):
        name = action_el.attrib.get("caption") or action_el.attrib.get("name") or ""
        action_type = _infer_action_type(action_el)
        activation = action_el.attrib.get("activation")

        source_sheets: list[str] = []
        target_sheets: list[str] = []
        source_el = action_el.find("source")
        if source_el is not None:
            for w in source_el.findall(".//worksheet"):
                wname = w.attrib.get("name")
                if wname:
                    source_sheets.append(wname)
        target_el = action_el.find("target") if action_el.find("target") is not None else action_el
        for w in target_el.findall(".//worksheet"):
            wname = w.attrib.get("name")
            if wname and wname not in target_sheets:
                target_sheets.append(wname)

        wb.actions.append(ActionSpec(
            name=name,
            action_type=action_type,
            activation=activation,
            source_sheets=source_sheets,
            target_sheets=target_sheets,
        ))


# ---------------------------------------------------------------------------
# 横断的な後処理: 被参照シート・未使用フィールドの解決
# ---------------------------------------------------------------------------

def _cross_reference(wb: Workbook) -> None:
    # 表示名をカラム定義で解決し直す（column-instance等でcaptionが後から埋まったケースに対応）
    all_columns: dict[str, str] = {}
    for ds in wb.datasources.values():
        for col in ds.columns.values():
            all_columns[col.name] = col.display_name

    for ws in wb.worksheets.values():
        for enc in ws.encodings:
            decoded = fieldref.humanize(enc.field_raw, columns=all_columns)
            enc.field_display = decoded.display
        for filt in ws.filters:
            if filt.field_raw:
                decoded = fieldref.humanize(filt.field_raw, columns=all_columns)
                filt.field_display = decoded.display
        for sort in ws.sorts:
            decoded = fieldref.humanize(sort.field_raw, columns=all_columns)
            sort.field_display = decoded.display

        referenced_names: set[str] = set()
        referenced_names.update(ws.row_fields)
        referenced_names.update(ws.col_fields)
        for enc in ws.encodings:
            decoded = fieldref.decode(enc.field_raw)
            if decoded.base_name:
                referenced_names.add(decoded.base_name)
        for filt in ws.filters:
            decoded = fieldref.decode(filt.field_raw)
            if decoded.base_name:
                referenced_names.add(decoded.base_name)

        for ds in wb.datasources.values():
            for col in ds.columns.values():
                if col.name in referenced_names and ws.name not in col.referenced_by:
                    col.referenced_by.append(ws.name)

    # 計算式が計算式を参照するケースも被参照に含める
    for ds in wb.datasources.values():
        for col in ds.columns.values():
            if not col.is_calculated:
                continue
            for dep_name in col.depends_on:
                target = ds.columns.get(dep_name)
                if target and f"計算フィールド: {col.display_name}" not in target.referenced_by:
                    target.referenced_by.append(f"計算フィールド: {col.display_name}")

    # パラメータの使用箇所（計算式・フィルタから拾えるものだけ、best-effort）
    param_names = set(wb.parameters.keys())
    if param_names:
        for ds in wb.datasources.values():
            for col in ds.columns.values():
                if col.is_calculated:
                    for dep in col.depends_on:
                        if dep in param_names:
                            wb.parameters[dep].used_in.append(f"計算フィールド: {col.display_name}")
