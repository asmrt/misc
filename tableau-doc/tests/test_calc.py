from twbdoc import calc


def test_strip_line_comment():
    cleaned = calc.strip_comments_and_strings("SUM([Sales]) // 売上合計\n+ 1")
    assert "売上合計" not in cleaned
    assert "[Sales]" in cleaned


def test_strip_block_comment():
    cleaned = calc.strip_comments_and_strings("/* memo [FakeField] */ SUM([Sales])")
    assert "FakeField" not in cleaned
    assert "[Sales]" in cleaned


def test_string_literal_with_bracket_not_misread_as_field():
    # 文字列リテラル内の "[" を角括弧参照と誤認しないこと（プラン上の最重要ケース）
    analysis = calc.analyze('"[要確認] " + [Category]')
    assert analysis.depends_on == ["Category"]


def test_depends_on_preserves_order_and_dedupes():
    analysis = calc.analyze("[A] + [B] + [A]")
    assert analysis.depends_on == ["A", "B"]


def test_lod_detection():
    analysis = calc.analyze("{FIXED [Customer ID] : SUM([Sales])}")
    assert analysis.uses_lod is True
    assert analysis.lod_kinds == ["FIXED"]
    assert analysis.uses_table_calc is False


def test_table_calc_detection():
    analysis = calc.analyze("RANK(SUM([Sales]))")
    assert analysis.uses_table_calc is True
    assert analysis.uses_lod is False


def test_no_flags_for_plain_calc():
    analysis = calc.analyze("SUM([Profit]) / SUM([Sales])")
    assert analysis.uses_lod is False
    assert analysis.uses_table_calc is False
    assert analysis.depends_on == ["Profit", "Sales"]


def test_empty_formula():
    analysis = calc.analyze("")
    assert analysis.depends_on == []
    assert analysis.uses_lod is False
    assert analysis.uses_table_calc is False


def test_extract_field_refs_from_shelf_string():
    refs = calc.extract_field_refs("[federated.0dw1].[sum:Sales:qk]")
    assert refs == ["Sales"]
