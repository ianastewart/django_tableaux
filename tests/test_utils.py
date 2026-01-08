import pytest
from django_tableaux.utils import parse_query_dict, merge_attrs
from django.http import QueryDict

from django_tableaux.views import TableauxView


def test_parse_query_dict():
    view = TableauxView()
    assert view.query_dict == {}
    param_string = "a=1&b=1&b=9&c=1&c=&query_string=xyz"
    qd = QueryDict(param_string)
    parse_query_dict(view, qd)
    assert view.query_dict["a"] == "1"
    # b should have latest value
    assert view.query_dict["b"] == "9"
    # c should not be present because its empty
    assert "c" not in view.query_dict
    # query_string always ignored
    assert "query_string" not in view.query_dict

