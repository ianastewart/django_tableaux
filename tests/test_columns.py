from django.db import models
from django.test import RequestFactory
from django_tables2 import tables

from django_tableaux.utils import new_columns_dict
from src.django_tableaux.columns import SelectionColumn
from src.django_tableaux.utils import (
    define_columns,
    set_select_column,
    resolve_breakpoint,
    save_columns_dict,
    load_columns_dict,
    set_column,
)


class TestModel(models.Model):
    a = models.CharField(max_length=20)
    b = models.CharField(max_length=20)
    c = models.CharField(max_length=20)
    d = models.CharField(max_length=20)


BP_DICT = {"sm": 768, "md": 992, "lg": 1200, "xl": 1400, "xxl": 1600}


class TestTable1(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel


def test_resolve_breakpoint():
    responsive = {"md": {"MD": None}, "lg": {"LG": None}, "xl": {"LG": None}}
    assert resolve_breakpoint(BP_DICT, responsive, "sm") == {"MD": None}
    assert resolve_breakpoint(BP_DICT, responsive, "md") == {"MD": None}
    assert resolve_breakpoint(BP_DICT, responsive, "lg") == {"LG": None}
    assert resolve_breakpoint(BP_DICT, responsive, "xl") == {"LG": None}
    assert resolve_breakpoint(BP_DICT, responsive, "xxl") == {"LG": None}


def test_define_columns_no_fields_means_all_fixed():
    table = TestTable1([])
    define_columns(table, BP_DICT, bp="")
    assert table.columns_fixed == ["id"]
    assert table.columns_optional == ["a", "b", "c", "d"]
    assert table.columns_default == ["id", "a", "b", "c", "d"]


class TestTable2(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c"]


def test_define_columns_fields():
    table = TestTable2([])
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["a"]
    assert table.columns_optional == ["b", "c"]
    assert table.columns_default == ["a", "b", "c"]


class TestTable3(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c"]
        sequence = ["c", "b", "a"]


def test_define_columns_sequence():
    table = TestTable3([])
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["c"]
    assert table.columns_optional == ["b", "a"]
    assert table.columns_default == ["c", "b", "a"]


class TestTable4(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        columns = {"fixed": ["a", "b"], "default": ["c"]}


def test_define_columns_fixed_and_default_without_fixed_entries():
    table = TestTable4([])
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["a", "b"]
    assert table.columns_optional == ["c", "d"]
    assert table.columns_default == ["a", "b", "c"]


class TestTable4A(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        columns = {"fixed": ["a", "b"], "default": ["a", "b", "c"]}


def test_define_columns_fixed_and_default_without_fixed_entries():
    table = TestTable4A([])
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["a", "b"]
    assert table.columns_optional == ["c", "d"]
    assert table.columns_default == ["a", "b", "c"]


class TestTable5(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        responsive = {
            "sm": {"fixed": ["a"]},
            "md": {"fixed": ["a", "b"], "default": ["a", "b", "c"]},
            "lg": {"fixed": ["a", "b", "c"], "default": ["a", "b", "c", "d"]},
        }


def test_define_columns_responsive():
    table = TestTable5([])
    define_columns(table, BP_DICT, bp="sm")
    assert table.columns_fixed == ["a"]
    assert table.columns_optional == ["b", "c", "d"]
    assert table.columns_default == ["a", "b", "c", "d"]
    define_columns(table, BP_DICT, bp="md")
    assert table.columns_fixed == ["a", "b"]
    assert table.columns_optional == ["c", "d"]
    assert table.columns_default == ["a", "b", "c"]
    define_columns(table, BP_DICT, bp="lg")
    assert table.columns_fixed == ["a", "b", "c"]
    assert table.columns_optional == ["d"]
    assert table.columns_default == ["a", "b", "c", "d"]


class TestTable6(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        responsive = {
            "sm": {"fixed": ["a"]},
            "lg": {},
        }


def test_define_columns_responsive_no_defaults():
    table = TestTable6([])
    define_columns(table, BP_DICT, bp="sm")
    assert table.columns_fixed == ["a"]
    # default = all fields if default not specified
    assert table.columns_default == ["a", "b", "c", "d"]
    define_columns(table, BP_DICT, bp="lg")
    # Only first field is fixed if fixed not specified
    assert table.columns_fixed == ["a"]
    # default is every field if no fixed and no default
    assert table.columns_default == ["a", "b", "c", "d"]


class TestTable7(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]

    selection = SelectionColumn()


def test_define_columns_with_selection_not_in_sequence():
    table = TestTable7([])
    set_select_column(table)
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["selection", "a"]


class TestTable8(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        sequence = ["selection", "..."]

    selection = SelectionColumn()


def test_define_columns_with_selection_first_in_sequence():
    table = TestTable8([])
    table.select_name = "selection"
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["selection", "a"]


class TestTable9(tables.Table):
    """@DynamicAttrs"""

    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        sequence = ["a", "selection", "..."]

    selection = SelectionColumn()


def test_define_columns_with_selection_not_first_in_sequence():
    table = TestTable9([])
    table.select_name = "selection"
    define_columns(table, BP_DICT)
    assert table.columns_fixed == ["a", "selection"]


def test_load_empty_columns_dictionary_returns_default_settings_no_bp():
    table = TestTable4([])
    define_columns(table, BP_DICT)
    request = RequestFactory().get("/")
    request.session = {}
    columns_dict = load_columns_dict(request, table, bp="")
    assert columns_dict["a"]
    assert columns_dict["b"]
    assert columns_dict["c"]
    assert not columns_dict["d"]


def test_load_empty_columns_dictionary_returns_default_settings_for_bp():
    table = TestTable5([])
    request = RequestFactory().get("/")
    request.session = {}
    define_columns(table, BP_DICT, bp="sm")
    columns_dict = load_columns_dict(request, table, bp="sm")
    assert columns_dict["a"]
    assert columns_dict["b"]
    assert columns_dict["c"]
    assert columns_dict["d"]
    request.session = {}
    define_columns(table, BP_DICT, "md")
    columns_dict = load_columns_dict(request, table, "md")
    assert columns_dict["a"]
    assert columns_dict["b"]
    assert columns_dict["c"]
    assert not columns_dict["d"]
    request.session = {}
    define_columns(table, BP_DICT, "lg")
    columns_dict = load_columns_dict(request, table, "lg")
    assert columns_dict["a"]
    assert columns_dict["b"]
    assert columns_dict["c"]
    assert columns_dict["d"]

def test_save_all_columns():
    table = TestTable8([])
    request = RequestFactory().get("/")
    request.session = {}
    columns_dict = new_columns_dict(table)
    save_columns_dict(request, table, bp="", columns_dict=columns_dict)
    assert load_columns_dict(request, table, bp="") == columns_dict


def test_save_columns_a_and_c():
    table = TestTable8([])
    request = RequestFactory().get("/")
    request.session = {}
    columns_dict = new_columns_dict(table)
    save_columns_dict(request, table, bp="", columns_dict=columns_dict)
    assert load_columns_dict(request, table, bp="") == columns_dict


# def test_update_url_empty():
#     url = "http://test.com/"
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?per_page=25"
#
#
# def test_update_url_existing_empty():
#     url = "http://test.com/?per_page="
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?per_page=25"
#
#
# def test_update_url_existing_empty_middle():
#     url = "http://test.com/?x=1&per_page=&y=2"
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?x=1&per_page=25&y=2"
#
#
# def test_update_url_existing_empty_end():
#     url = "http://test.com/?x=1&per_page="
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?x=1&per_page=25"
#
#
# def test_update_url_existing_sole():
#     url = "http://test.com/?per_page=10"
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?per_page=25"
#
#
# def test_update_url_existing_middle():
#     url = "http://test.com/?x=1&per_page=10&y=2"
#     result = update_url(url, "per_page", 25)
#     assert result == "http://test.com/?x=1&per_page=25&y=2"
#
#
# def test_update_url_quoted_string():
#     url = "http://test.com/?x=1&per_page=10&y=2"
#     result = update_url(url, "per_page", "a&b=c")
#     assert result == "http://test.com/?x=1&per_page=a%26b%3Dc&y=2"
