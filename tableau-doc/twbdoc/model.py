"""twbdocの内部表現(IR)。twb XMLをパースした結果を格納するdataclass群。

Tableauの実際のtwb構造は版によって揺れがあり、このIRは
「仕様書・定義書・HTMLレポートを作るのに必要十分な情報」を目的に設計している。
XMLの全属性を保持する網羅的なミラーではない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Connection:
    class_: str = ""                 # 例: "postgres", "excel-direct", "federated"
    server: Optional[str] = None
    port: Optional[str] = None
    dbname: Optional[str] = None
    authentication: Optional[str] = None


@dataclass
class Relation:
    kind: str = "table"               # "table" | "text"(カスタムSQL) | "join"
    name: Optional[str] = None
    table: Optional[str] = None       # kind="table" のときの物理テーブル名
    sql: Optional[str] = None         # kind="text" のときのカスタムSQL本文
    join_type: Optional[str] = None   # kind="join" のときの結合種別
    children: list["Relation"] = field(default_factory=list)


@dataclass
class Column:
    name: str = ""                    # twb内の内部名（ブラケットの中身）
    caption: Optional[str] = None     # 表示名。無ければnameを使う
    datatype: Optional[str] = None    # string/integer/real/date/datetime/boolean 等
    role: Optional[str] = None        # dimension | measure
    field_type: Optional[str] = None  # nominal | ordinal | quantitative
    default_aggregation: Optional[str] = None
    folder: Optional[str] = None
    description: Optional[str] = None
    hidden: bool = False
    is_calculated: bool = False
    formula: Optional[str] = None
    has_bin: bool = False
    is_group: bool = False

    # calc.py が埋める
    depends_on: list[str] = field(default_factory=list)      # 依存する他フィールドの内部名
    uses_lod: bool = False
    uses_table_calc: bool = False

    # render時に埋める
    referenced_by: list[str] = field(default_factory=list)   # 参照しているワークシート名

    @property
    def display_name(self) -> str:
        return self.caption or self.name


@dataclass
class DataSource:
    name: str = ""                    # 内部トークン。field参照の先頭 [xxx] と対応
    caption: Optional[str] = None
    version: Optional[str] = None
    connections: list[Connection] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    columns: dict[str, Column] = field(default_factory=dict)  # key = Column.name

    @property
    def display_name(self) -> str:
        return self.caption or self.name


@dataclass
class Parameter:
    name: str = ""
    caption: Optional[str] = None
    datatype: Optional[str] = None
    current_value: Optional[str] = None
    allowed_values: list[str] = field(default_factory=list)
    range_min: Optional[str] = None
    range_max: Optional[str] = None
    range_step: Optional[str] = None
    used_in: list[str] = field(default_factory=list)  # 使用しているワークシート/計算式名

    @property
    def display_name(self) -> str:
        return self.caption or self.name


@dataclass
class Encoding:
    channel: str = ""      # color / size / text / lod(詳細) / tooltip / shape / path など
    field_raw: str = ""
    field_display: str = ""


@dataclass
class FilterSpec:
    field_raw: str = ""
    field_display: str = ""
    filter_class: Optional[str] = None   # categorical / quantitative / relative-date 等
    summary: Optional[str] = None        # 値の要約（best-effort）


@dataclass
class SortSpec:
    field_raw: str = ""
    field_display: str = ""
    direction: Optional[str] = None
    sort_class: Optional[str] = None


@dataclass
class Worksheet:
    name: str = ""
    datasources: list[str] = field(default_factory=list)
    rows_raw: str = ""
    cols_raw: str = ""
    row_fields: list[str] = field(default_factory=list)   # rows_rawから抽出した参照
    col_fields: list[str] = field(default_factory=list)
    mark_class: Optional[str] = None
    pane_count: int = 1
    encodings: list[Encoding] = field(default_factory=list)
    filters: list[FilterSpec] = field(default_factory=list)
    sorts: list[SortSpec] = field(default_factory=list)


@dataclass
class Zone:
    zone_id: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    zone_type: Optional[str] = None
    worksheet_name: Optional[str] = None
    children: list["Zone"] = field(default_factory=list)


@dataclass
class Dashboard:
    name: str = ""
    size_w: Optional[str] = None
    size_h: Optional[str] = None
    zones: list[Zone] = field(default_factory=list)
    worksheets_used: list[str] = field(default_factory=list)


@dataclass
class ActionSpec:
    name: str = ""
    action_type: str = "unknown"   # filter | highlight | url | parameter | go-to-sheet | unknown
    activation: Optional[str] = None
    source_sheets: list[str] = field(default_factory=list)
    target_sheets: list[str] = field(default_factory=list)


@dataclass
class UnparsedElement:
    tag: str
    path: str
    count: int = 1
    sample_attrib: dict = field(default_factory=dict)


@dataclass
class Workbook:
    source_path: str = ""
    tableau_version: Optional[str] = None
    datasources: dict[str, DataSource] = field(default_factory=dict)
    worksheets: dict[str, Worksheet] = field(default_factory=dict)
    dashboards: dict[str, Dashboard] = field(default_factory=dict)
    actions: list[ActionSpec] = field(default_factory=list)
    parameters: dict[str, Parameter] = field(default_factory=dict)
    unparsed: list[UnparsedElement] = field(default_factory=list)

    def all_calculated_fields(self) -> list[tuple[DataSource, Column]]:
        result = []
        for ds in self.datasources.values():
            for col in ds.columns.values():
                if col.is_calculated:
                    result.append((ds, col))
        return result
