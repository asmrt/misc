from twbdoc import fieldref


def test_split_brackets_simple():
    assert fieldref.split_brackets("[Sales]") == ["Sales"]
    assert fieldref.split_brackets("[federated.0dw1].[Sales]") == ["federated.0dw1", "Sales"]


def test_split_brackets_escaped_bracket():
    # フィールド名中のリテラル "]" は "]]" とエスケープされる
    assert fieldref.split_brackets("[Weird]]Name]") == ["Weird]Name"]


def test_decode_plain_field():
    d = fieldref.decode("[Sales]")
    assert d.base_name == "Sales"
    assert d.aggregation is None
    assert d.display == "Sales"


def test_decode_aggregated_field():
    d = fieldref.decode("[federated.0dw1].[sum:Sales:qk]")
    assert d.datasource_token == "federated.0dw1"
    assert d.aggregation == "sum"
    assert d.base_name == "Sales"
    assert d.type_key == "qk"
    assert d.display == "SUM(Sales)"


def test_decode_unknown_aggregation_degrades_gracefully():
    d = fieldref.decode("[federated.0dw1].[weirdagg:Sales:qk]")
    # 未知の集計プレフィックスでも例外を投げず、コロンを含む生の値をbase_nameとして保持する
    assert d.base_name == "weirdagg:Sales:qk"


def test_humanize_resolves_caption():
    columns = {"Sales": "売上"}
    d = fieldref.humanize("[federated.0dw1].[sum:Sales:qk]", columns=columns)
    assert d.resolved is True
    assert d.display == "SUM(売上)"


def test_humanize_unresolved_field_keeps_display():
    d = fieldref.humanize("[federated.0dw1].[none:Ghost:nk]", columns={})
    assert d.resolved is False
    assert d.display == "Ghost"


def test_find_all_refs():
    refs = fieldref.find_all_refs("SUM([Profit]) / SUM([Sales])")
    assert refs == ["[Profit]", "[Sales]"]


def test_find_all_refs_no_refs():
    assert fieldref.find_all_refs("1 + 1") == []
