import pytest
from django_tables2 import tables
from django_tableaux.columns import SelectionColumn
from django_tableaux.buttons import Button
from django.db.models import *
from django_tableaux.utils import define_columns


class TestModel(Model):
    a = CharField(max_length=20)
    b = CharField(max_length=20)
    c = CharField(max_length=20)
    d = CharField(max_length=20)


class TestTable1(tables.Table):
    class Meta:
        model = TestModel


def test_define_columns_no_fields_means_all_fixed():
    table = TestTable1([])
    define_columns(table, width=0)
    assert table.columns_fixed == ["id"]
    assert table.columns_optional == ["a", "b", "c", "d"]
    assert table.columns_default == ["id", "a", "b", "c", "d"]


class TestTable2(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c"]


def test_define_columns_fields():
    table = TestTable2([])
    define_columns(table, width=0)
    assert table.columns_fixed == ["a"]
    assert table.columns_optional == ["b", "c"]
    assert table.columns_default == ["a", "b", "c"]


class TestTable3(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c"]
        sequence = ["c", "b", "a"]


def test_define_columns_sequence():
    table = TestTable3([])
    define_columns(table, width=0)
    assert table.columns_fixed == ["c"]
    assert table.columns_optional == ["b", "a"]
    assert table.columns_default == ["c", "b", "a"]


class TestTable4(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c"]
        columns = {"fixed": ["a", "b"], "default": ["a", "b", "c"]}


def test_define_columns_fixed_and_default():
    table = TestTable4([])
    define_columns(table, width=0)
    assert table.columns_fixed == ["a", "b"]
    assert table.columns_optional == ["c"]
    assert table.columns_default == ["a", "b", "c"]


class TestTable5(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        columns = {"fixed": ["a", "b", "c", "d"]}
        responsive = {
            100: {"fixed": ["a"]},
            500: {"fixed": ["a", "b"], "default": ["a", "b", "c"]},
            1000: {"fixed": ["a", "b", "c"], "default": ["a", "b", "c", "d"]},
        }


def test_define_columns_responsive():
    table = TestTable5([])
    define_columns(table, width=100)
    assert table.columns_fixed == ["a"]
    assert table.columns_optional == ["b", "c", "d"]
    assert table.columns_default == ["a", "b", "c", "d"]
    define_columns(table, width=500)
    assert table.columns_fixed == ["a", "b"]
    assert table.columns_optional == ["c", "d"]
    assert table.columns_default == ["a", "b", "c"]
    define_columns(table, width=1000)
    assert table.columns_fixed == ["a", "b", "c"]
    assert table.columns_optional == ["d"]
    assert table.columns_default == ["a", "b", "c", "d"]
    assert table.columns_default == ["a", "b", "c", "d"]


class TestTable6(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        responsive = {
            100: {"fixed": ["a"]},
            1000: {},
        }


def test_define_columns_responsive_no_defaults():
    table = TestTable6([])
    define_columns(table, width=100)
    assert table.columns_fixed == ["a"]
    ## default=all fields if default not specified
    assert table.columns_default == ["a", "b", "c", "d"]
    define_columns(table, width=1000)
    # Only first field is fixed if fixed not specified
    assert table.columns_fixed == ["a"]
    # default is every field if no fixed and no default
    assert table.columns_default == ["a", "b", "c", "d"]


class TestTable7(tables.Table):
    class Meta:
        model = TestModel
        fields = ["a", "b", "c", "d"]
        sequence = ["selection", "..."]

    selection = SelectionColumn()


def test_define_columns_with_selection():
    table = TestTable7([])
    define_columns(table, width=0)
    assert table.columns_fixed == ["selection", "a"]


def test_default_button():
    button = Button("Test button")
    html = button.render()
    assert "<button" in html
    assert 'type="button"' in html
    assert 'class="btn btn-primary"' in html
    assert 'name="test-button"' in html
    assert ">Test button</button" in html


def test_button_renders_attributes():
    button = Button(
        "Test button",
        css="btn btn-secondary",
        type="submit",
        name="test_name",
        hx_get="/test",
        hx_target="#target",
    )
    html = button.render()
    assert 'class="btn btn-secondary"' in html
    assert 'type="submit"' in html
    assert 'name="test_name"' in html
    assert 'hx-get="/test"' in html
    assert 'hx-target="#target"' in html


def test_link_button_when_href_present():
    button = Button("Test button", href="url")
    html = button.render()
    assert "<a" in html
    assert 'href="url"' in html
    assert "type" not in html


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
