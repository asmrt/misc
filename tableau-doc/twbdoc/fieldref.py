"""Tableauのフィールド参照文字列をデコードするユーティリティ。

twb内のフィールド参照は概ね次の形をとる:

    [federated.0h1abc2].[sum:Sales:qk]   # データソースID + 集計フィールド
    [federated.0h1abc2].[Sales]          # データソースID + 生フィールド
    [Sales]                              # データソースIDなし（単一データソースの文脈など）
    [none:Profit Ratio:qk]               # 集計なし（表計算フィールドなど）

`[sum:Sales:qk]` の内訳は `集計:フィールド名:型キー`。
型キー: qk=quantitative(連続), nk=nominal(離散/文字列), ok=ordinal。

これらは公開ドキュメントで正式に規定された文法ではなく、実ファイルの慣習的な表記を
もとにした最善努力のデコードである。未知の集計プレフィックスや型キーに遭遇しても
例外は投げず、分かる範囲だけを解釈してraw文字列を保持する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Tableau計算式エディタでの表記に合わせた集計名（言語非依存で認識しやすいため）
_AGGREGATION_DISPLAY = {
    "sum": "SUM",
    "avg": "AVG",
    "min": "MIN",
    "max": "MAX",
    "cnt": "COUNT",
    "cntd": "COUNTD",
    "median": "MEDIAN",
    "std": "STDEV",
    "stdp": "STDEVP",
    "var": "VAR",
    "varp": "VARP",
    "attr": "ATTR",
    "usr": "USER",
    "none": None,
    "year": "YEAR",
    "qtr": "QUARTER",
    "month": "MONTH",
    "week": "WEEK",
    "day": "DAY",
    "hour": "HOUR",
    "minute": "MINUTE",
    "second": "SECOND",
    "tyear": "TRUNC(YEAR)",
    "tqtr": "TRUNC(QUARTER)",
    "tmonth": "TRUNC(MONTH)",
    "tweek": "TRUNC(WEEK)",
    "tday": "TRUNC(DAY)",
}

_TYPE_DISPLAY = {
    "qk": "quantitative",
    "nk": "nominal",
    "ok": "ordinal",
}

_SPECIAL_FIELDS = {
    "Measure Names",
    "Measure Values",
    "Multi-Measure Names",
    "Multi-Measure Values",
    "Number of Records",
}


@dataclass
class DecodedField:
    raw: str
    datasource_token: Optional[str] = None
    aggregation: Optional[str] = None
    base_name: str = ""
    type_key: Optional[str] = None
    resolved: bool = False
    display: str = ""
    datasource_display: Optional[str] = None
    unrecognized: bool = False


def split_brackets(raw: str) -> list[str]:
    """`[a].[b]` のようなブラケット連結文字列を各グループに分解する。

    フィールド名中のリテラル `]` は Tableau の規約で `]]` とエスケープされるため、
    それを1文字の `]` として扱いつつグループ境界の `]` と区別する。
    """
    groups: list[str] = []
    buf: list[str] = []
    in_bracket = False
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if not in_bracket:
            if ch == "[":
                in_bracket = True
                buf = []
            i += 1
            continue
        # in_bracket
        if ch == "]":
            if i + 1 < n and raw[i + 1] == "]":
                buf.append("]")
                i += 2
                continue
            groups.append("".join(buf))
            in_bracket = False
            i += 1
            continue
        buf.append(ch)
        i += 1
    return groups


def _decode_inner(token: str) -> tuple[Optional[str], str, Optional[str]]:
    """`sum:Sales:qk` 形式の内側トークンを (aggregation, base_name, type_key) に分解する。

    コロンを含まない単純な `Sales` はそのまま base_name として返す。
    """
    if ":" not in token:
        return None, token, None
    parts = token.split(":")
    if len(parts) == 3:
        agg, name, type_key = parts
        if agg in _AGGREGATION_DISPLAY:
            return agg, name, type_key
    if len(parts) == 2:
        agg, name = parts
        if agg in _AGGREGATION_DISPLAY:
            return agg, name, None
    # コロンを含むが既知の形式に一致しない → フィールド名自体にコロンが
    # 含まれている可能性があるため、無理に分解せずそのまま返す
    return None, token, None


def decode(raw: str) -> DecodedField:
    """フィールド参照文字列を可能な範囲でデコードする。例外は投げない。"""
    groups = split_brackets(raw)
    if not groups:
        return DecodedField(raw=raw, base_name=raw.strip("[]"), display=raw, unrecognized=True)

    if len(groups) >= 2:
        ds_token, field_token = groups[0], groups[-1]
    else:
        ds_token, field_token = None, groups[0]

    if field_token in _SPECIAL_FIELDS:
        return DecodedField(
            raw=raw,
            datasource_token=ds_token,
            base_name=field_token,
            resolved=True,
            display=field_token,
        )

    agg, base_name, type_key = _decode_inner(field_token)
    display = base_name
    if agg is not None:
        agg_disp = _AGGREGATION_DISPLAY.get(agg)
        if agg_disp:
            display = f"{agg_disp}({base_name})"

    return DecodedField(
        raw=raw,
        datasource_token=ds_token,
        aggregation=agg,
        base_name=base_name,
        type_key=type_key,
        resolved=False,  # カラム定義と突き合わせるまでは未確定
        display=display,
    )


def humanize(raw: str, columns: Optional[dict[str, str]] = None,
             datasource_captions: Optional[dict[str, str]] = None) -> DecodedField:
    """カラム定義・データソースのキャプション一覧と突き合わせて表示名を仕上げる。

    columns: 内部名( `[Sales]` の中身 "Sales" 相当のキー) -> キャプション の辞書。
    datasource_captions: データソースの内部トークン -> キャプション の辞書。
    """
    decoded = decode(raw)
    if columns:
        caption = columns.get(decoded.base_name)
        if caption:
            decoded.resolved = True
            if decoded.aggregation and _AGGREGATION_DISPLAY.get(decoded.aggregation):
                decoded.display = f"{_AGGREGATION_DISPLAY[decoded.aggregation]}({caption})"
            else:
                decoded.display = caption
    if datasource_captions and decoded.datasource_token:
        decoded.datasource_display = datasource_captions.get(decoded.datasource_token, decoded.datasource_token)
    return decoded


_BRACKET_GROUP = r"\[[^\[\]]*(?:\]\][^\[\]]*)*\]"
# `[ds].[field]` の2連結を1つの参照としてまとめて拾う。
# 連結を考慮しないと `[federated.0dw1].[sum:Sales:qk]` のデータソース側トークンまで
# 独立したフィールド参照として誤検出してしまう。
_COMBINED_REF_RE = re.compile(_BRACKET_GROUP + r"(?:\." + _BRACKET_GROUP + r")?")


def find_all_refs(text: str) -> list[str]:
    """文字列中に現れるフィールド参照を列挙する。

    `[Sales]` のような単独参照と `[federated.0dw1].[sum:Sales:qk]` のような
    データソース連結参照の両方を、それぞれ1つの参照としてまとめて返す。
    calc.py 側で計算式・シェルフ文字列からの依存フィールド抽出に使う低レベルのヘルパー。
    """
    return _COMBINED_REF_RE.findall(text)
