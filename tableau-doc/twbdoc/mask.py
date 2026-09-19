"""接続情報のマスク処理。

twbファイル自体をコミットしない方針と同じ理由で、生成する仕様書・レポートにも
サーバー名・DB名・ポート・カスタムSQL本文をそのまま載せない（既定でマスク）。
render_md.py / render_html.py の両方から共通で使う。
"""

from __future__ import annotations

import copy

from .model import Workbook

MASK_TEXT = "***"


def apply_connection_mask(wb: Workbook) -> Workbook:
    """接続の機微情報を伏せた複製を返す。元のWorkbookは変更しない。"""
    masked = copy.deepcopy(wb)
    for ds in masked.datasources.values():
        for c in ds.connections:
            if c.server:
                c.server = MASK_TEXT
            if c.port:
                c.port = MASK_TEXT
            if c.dbname:
                c.dbname = MASK_TEXT
        for r in ds.relations:
            if r.kind == "text" and r.sql:
                r.sql = MASK_TEXT
    return masked
