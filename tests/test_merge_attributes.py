from django_tableaux.utils import merge_attrs


def test_merges_attributes():
    col_attrs = {"th": {"class": "thcol"}, "td": {"class": "tdcol", "data-length": lambda value: len(value)}}
    table_attrs = {"table": {"class": "table"},
                   "th": {"class": "thtable"}, }
    result = merge_attrs(col_attrs, table_attrs)
    assert result["th"] == {"class": "thtable thcol"}
    assert result["td"]["class"] == "tdcol"
    assert callable(result["td"]["data-length"])


def test_column_attrs_supersede_table_attrs():
    table_attrs = {"th": {"class": "text-end"}}
    col_attrs = {"th": {"class": "numeric"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result == {"th": {"class": "text-end numeric"}}


def test_does_not_mutate_inputs():
    table_attrs = {"th": {"class": "text-end"}}
    col_attrs = {"th": {"class": "numeric"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result is not col_attrs
    assert result is not table_attrs


def test_style_attributes_are_semicolon_concatenated():
    table_attrs = {"td": {"style": "text-align: right;"}}
    col_attrs = {"td": {"style": "width: 5em;"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result["td"]["style"] == "text-align: right; width: 5em;"


def test_column_value_overrides_table_for_non_class_attributes():
    table_attrs = {"cell": {"data-test": "table"}}
    col_attrs = {"cell": {"data-test": "col"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result["cell"]["data-test"] == "col"


def test_table_attribute_applied_if_column_missing():
    col_attrs = {}
    table_attrs = {"th": {"aria-sort": "ascending"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result["th"]["aria-sort"] == "ascending"


def test_handles_table_empty():
    table_attrs = {}
    col_attrs = {"th": {"class": "text-end"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result["th"]["class"] == "text-end"


def test_ignores_irrelevant_table_sections():
    table_attrs = {
        "table": {"class": "table-striped"},
        "thead": {"class": "bg-dark"},
    }
    col_attrs = {"td": {"class": "numeric"}}
    result = merge_attrs(col_attrs, table_attrs)
    assert result == {"td": {"class": "numeric"}}
