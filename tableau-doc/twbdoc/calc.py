"""Tableau計算式の依存フィールド抽出、LOD式・表計算の検出。

完全な計算式パーサは作らない（過剰）。ここでやるのは:

1. コメント（`//`, `/* */`）と文字列リテラル（`"..."`, `'...'`）を先に除去する
   （除去しないと文字列中の `[` を参照と誤認する）
2. 残った本体からブラケット参照 `[...]` を拾って依存フィールドとする
3. LOD構文（`{FIXED`, `{INCLUDE`, `{EXCLUDE`）と表計算関数
   （`WINDOW_*`, `RANK`, `INDEX`, `LOOKUP`, `TOTAL`, `RUNNING_*`, `FIRST`, `LAST`,
    `PREVIOUS_VALUE`）の使用を検出してフラグを立てる
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import fieldref

_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_DQUOTE_STRING_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_SQUOTE_STRING_RE = re.compile(r"'(?:[^'\\]|\\.)*'")

_LOD_RE = re.compile(r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", re.IGNORECASE)
_TABLE_CALC_FUNCS = (
    "WINDOW_SUM", "WINDOW_AVG", "WINDOW_MIN", "WINDOW_MAX", "WINDOW_MEDIAN",
    "WINDOW_STDEV", "WINDOW_STDEVP", "WINDOW_VAR", "WINDOW_VARP", "WINDOW_COUNT",
    "WINDOW_COVAR", "WINDOW_COVARP", "WINDOW_CORR", "WINDOW_PERCENTILE",
    "RANK", "RANK_DENSE", "RANK_MODIFIED", "RANK_PERCENTILE", "RANK_UNIQUE",
    "INDEX", "SIZE", "LOOKUP", "TOTAL",
    "RUNNING_SUM", "RUNNING_AVG", "RUNNING_MIN", "RUNNING_MAX", "RUNNING_COUNT",
    "FIRST", "LAST", "PREVIOUS_VALUE", "SCRIPT_",
)
_TABLE_CALC_RE = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in _TABLE_CALC_FUNCS) + r")\w*\s*\(",
    re.IGNORECASE,
)


def strip_comments_and_strings(formula: str) -> str:
    """コメントと文字列リテラルを空白に置き換える（角括弧解析を誤らせないため）。

    行番号・文字位置をなるべく保つため、削除ではなく同じ長さの空白で置換する。
    """
    def blank(m: re.Match) -> str:
        return " " * len(m.group(0))

    text = formula
    # 文字列を先に潰す（文字列内の // や /* が誤ってコメント扱いされないように）
    text = _DQUOTE_STRING_RE.sub(blank, text)
    text = _SQUOTE_STRING_RE.sub(blank, text)
    text = _BLOCK_COMMENT_RE.sub(blank, text)
    text = _LINE_COMMENT_RE.sub(blank, text)
    return text


@dataclass
class CalcAnalysis:
    depends_on: list[str] = field(default_factory=list)  # base_name のリスト（重複排除・順序維持）
    uses_lod: bool = False
    uses_table_calc: bool = False
    lod_kinds: list[str] = field(default_factory=list)


def analyze(formula: str) -> CalcAnalysis:
    """計算式を解析し、依存フィールドとLOD/表計算フラグを返す。例外は投げない。"""
    if not formula:
        return CalcAnalysis()

    cleaned = strip_comments_and_strings(formula)

    refs = fieldref.find_all_refs(cleaned)
    seen: dict[str, None] = {}
    for raw in refs:
        decoded = fieldref.decode(raw)
        if decoded.base_name and decoded.base_name not in seen:
            seen[decoded.base_name] = None

    lod_kinds = sorted({m.group(1).upper() for m in _LOD_RE.finditer(cleaned)})
    uses_table_calc = bool(_TABLE_CALC_RE.search(cleaned))

    return CalcAnalysis(
        depends_on=list(seen.keys()),
        uses_lod=bool(lod_kinds),
        uses_table_calc=uses_table_calc,
        lod_kinds=lod_kinds,
    )


def extract_field_refs(text: str) -> list[str]:
    """rows/cols シェルフの文字列など、計算式以外の場所からフィールド参照(base_name)を拾う。

    コメント/文字列除去は行わない（シェルフ定義に自由記述の文字列リテラルは通常出てこないため）。
    """
    result: list[str] = []
    seen: dict[str, None] = {}
    for raw in fieldref.find_all_refs(text or ""):
        decoded = fieldref.decode(raw)
        if decoded.base_name and decoded.base_name not in seen:
            seen[decoded.base_name] = None
            result.append(decoded.base_name)
    return result
