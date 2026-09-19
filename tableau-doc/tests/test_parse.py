from pathlib import Path

import pytest

from twbdoc import parse
from twbdoc.mask import apply_connection_mask

SAMPLE = Path(__file__).parent.parent / "samples" / "synthetic.twb"


@pytest.fixture(scope="module")
def wb():
    return parse.parse_file(str(SAMPLE))


def test_datasources_keyed_by_internal_name(wb):
    # <group> や <column-instance> のパース中に外側の変数名を上書きして
    # データソース名を取り違える回帰を防ぐ
    assert set(wb.datasources.keys()) == {"federated.0dw1", "federated.0dw2"}
    assert wb.datasources["federated.0dw1"].caption == "Sales (Orders)"


def test_parameters_datasource_excluded_from_datasources(wb):
    assert "Parameters" not in wb.datasources


def test_parameters_parsed_with_value_and_range(wb):
    p1 = wb.parameters["Parameter 1"]
    assert p1.current_value == "0.15"
    assert (p1.range_min, p1.range_max, p1.range_step) == ("0", "1", "0.01")

    p2 = wb.parameters["Parameter 2"]
    assert p2.current_value == "直近12ヶ月"
    assert p2.allowed_values == ["直近3ヶ月", "直近12ヶ月", "全期間"]


def test_federated_wrapper_connection_excluded(wb):
    conns = wb.datasources["federated.0dw1"].connections
    assert len(conns) == 1
    assert conns[0].class_ == "postgres"
    assert conns[0].server == "db.example.internal"


def test_calculated_field_count_and_flags(wb):
    calcs = {col.name: col for _, col in wb.all_calculated_fields()}
    assert len(calcs) == 6
    assert calcs["Calculation_1000000000003"].uses_lod is True
    assert calcs["Calculation_1000000000004"].uses_table_calc is True
    assert calcs["Calculation_1000000000001"].uses_lod is False


def test_string_literal_bracket_not_treated_as_dependency(wb):
    calcs = {col.name: col for _, col in wb.all_calculated_fields()}
    label_calc = calcs["Calculation_1000000000006"]
    assert label_calc.depends_on == ["Category"]


def test_zone_nesting_preserved(wb):
    dash = wb.dashboards["地域ドリルダウン"]
    assert len(dash.zones) == 1
    root = dash.zones[0]
    assert root.zone_type == "layout-basic"
    assert len(root.children) == 3  # layout-flow(見出し) + 2ワークシート
    flow = root.children[0]
    assert flow.zone_type == "layout-flow"
    assert len(flow.children) == 1
    assert flow.children[0].zone_type == "text"


def test_dashboard_worksheets_used_collected_recursively(wb):
    dash = wb.dashboards["地域ドリルダウン"]
    assert set(dash.worksheets_used) == {"利益率散布図", "顧客別集計(クロス集計)"}


def test_unparsed_elements_recorded_not_raised(wb):
    tags = {u.tag for u in wb.unparsed}
    assert "semantic-model-refs" in tags
    assert "parameters-are-actually-different-in-2027" in tags
    assert "future-layout-hint" in tags
    # パス情報が正しいデータソース名を指していること（変数シャドーイング回帰の確認）
    ds_unparsed = next(u for u in wb.unparsed if u.tag == "parameters-are-actually-different-in-2027")
    assert ds_unparsed.path == "datasource[federated.0dw1]"


def test_action_types_inferred(wb):
    by_name = {a.name: a for a in wb.actions}
    assert by_name["地域でフィルタ"].action_type == "filter"
    assert by_name["詳細をWebで見る"].action_type == "url"
    assert by_name["将来のアクション種別"].action_type == "unknown"


def test_unused_fields_detected(wb):
    unused = {
        col.name
        for ds in wb.datasources.values()
        for col in ds.columns.values()
        if not col.referenced_by and not col.hidden
    }
    assert "Order ID" in unused
    assert "Ship Date" in unused
    # 使用されているフィールドは未使用リストに出ない
    assert "Sales" not in unused
    assert "Region" not in unused


def test_mask_connections_does_not_mutate_original(wb):
    masked = apply_connection_mask(wb)
    original_conn = wb.datasources["federated.0dw1"].connections[0]
    masked_conn = masked.datasources["federated.0dw1"].connections[0]
    assert original_conn.server == "db.example.internal"
    assert masked_conn.server == "***"
    assert masked.datasources["federated.0dw2"].relations[0].sql == "***"


def test_malformed_xml_raises_value_error(tmp_path):
    bad = tmp_path / "broken.twb"
    bad.write_text("<workbook><datasources>", encoding="utf-8")
    with pytest.raises(ValueError):
        parse.parse_file(str(bad))


def test_unknown_top_level_tag_does_not_raise(tmp_path):
    xml = """<?xml version='1.0'?>
    <workbook version='18.1'>
      <totally-unknown-future-section foo='bar'/>
      <datasources/>
      <worksheets/>
      <dashboards/>
    </workbook>"""
    p = tmp_path / "future.twb"
    p.write_text(xml, encoding="utf-8")
    wb2 = parse.parse_file(str(p))
    assert any(u.tag == "totally-unknown-future-section" for u in wb2.unparsed)
