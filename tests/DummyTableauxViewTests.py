# tests/test_django_tableaux_htmx_get_options.py
import json
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

import django_tableaux.views as dt_views


class DummyFilterSet:
    # TableauxView.is_filter_name() checks filterset_class.declared_filters.keys()
    declared_filters = {"title": object(), "year": object()}


class DummyTableauxView(dt_views.TableauxView):
    """
    A minimal TableauxView subclass for unit-testing the HTMX GET parsing logic.

    We deliberately avoid configuring table_class/model because in the HTMX branch
    TableauxView.get() returns get_htmx(...) before it tries to build tables.
    """
    filterset_class = DummyFilterSet


@pytest.mark.django_db
def test_htmx_get_parses_filter_data_and_marks_filter_changed(monkeypatch):
    """
    If ~filter_data contains old filter values, and the new GET contains a different
    value for a filter param, TableauxView should mark _filter_changed=True and
    pass the merged query_dict onward to get_htmx.
    """
    captured = {}

    def fake_get_htmx(view, request, *args, **kwargs):
        captured["query_dict"] = dict(view.query_dict)
        captured["filter_data"] = dict(view.filter_data)
        captured["filter_changed"] = view._filter_changed
        return HttpResponse("OK")

    monkeypatch.setattr(dt_views, "get_htmx", fake_get_htmx)

    rf = RequestFactory()
    request = rf.get(
        "/tableaux/",
        data={
            # old filter values (what the modal had before)
            "~filter_data": "title=Old+Title&year=1999",
            # new values coming from this hx-get
            "title": "New Title",
            # non-filter params
            "prefix": "X",
            "query_string": "ignored=1",
        },
    )
    request.htmx = True  # minimal signal: take the HTMX branch

    response = DummyTableauxView.as_view()(request)
    assert response.status_code == 200

    # Old filter data is parsed out of ~filter_data
    assert captured["filter_data"] == {"title": "Old Title", "year": "1999"}

    # query_dict should NOT include ~filter_data / query_string / prefix after parsing
    assert "~filter_data" not in captured["query_dict"]
    assert "query_string" not in captured["query_dict"]
    assert "prefix" not in captured["query_dict"]

    # year should be merged in from ~filter_data because it was missing in the hx-get params
    assert captured["query_dict"]["title"] == "New Title"
    assert captured["query_dict"]["year"] == "1999"

    # filter change should be detected (Old Title -> New Title)
    assert captured["filter_changed"] is True


@pytest.mark.django_db
def test_htmx_get_search_json_is_parsed_and_removed_from_query_dict(monkeypatch):
    """
    'search' contains a JSON string of the full original query params (used for URL updates).
    It should be parsed into view.original_params and removed from view.query_dict.
    """
    captured = {}

    def fake_get_htmx(view, request, *args, **kwargs):
        captured["original_params"] = getattr(view, "original_params", None)
        captured["query_dict"] = dict(view.query_dict)
        return HttpResponse("OK")

    monkeypatch.setattr(dt_views, "get_htmx", fake_get_htmx)

    rf = RequestFactory()
    original = {"~page": "3", "title": "Aliens"}
    request = rf.get(
        "/tableaux/",
        data={
            "search": json.dumps(original),
            "prefix": "",
            "query_string": "",
        },
    )
    request.htmx = True

    response = DummyTableauxView.as_view()(request)
    assert response.status_code == 200

    assert captured["original_params"] == original
    assert "search" not in captured["query_dict"]


@pytest.mark.django_db
def test_htmx_get_prefix_is_extracted_and_query_string_is_dropped(monkeypatch):
    """
    'prefix' should be moved onto view.prefix (not left in query_dict),
    and 'query_string' should be discarded (it’s just echoed by the template tag).
    """
    captured = {}

    def fake_get_htmx(view, request, *args, **kwargs):
        captured["prefix"] = view.prefix
        captured["query_dict"] = dict(view.query_dict)
        return HttpResponse("OK")

    monkeypatch.setattr(dt_views, "get_htmx", fake_get_htmx)

    rf = RequestFactory()
    request = rf.get(
        "/tableaux/",
        data={
            "prefix": "PFX_",
            "query_string": "a=1&b=2",
            "title": "Something",
        },
    )
    request.htmx = True

    response = DummyTableauxView.as_view()(request)
    assert response.status_code == 200

    assert captured["prefix"] == "PFX_"
    assert "prefix" not in captured["query_dict"]
    assert "query_string" not in captured["query_dict"]
    assert captured["query_dict"]["title"] == "Something"


@pytest.mark.django_db
def test_htmx_get_filter_change_detects_new_non_empty_filter(monkeypatch):
    """
    If a filter param appears in query_dict but was not present in ~filter_data,
    and it is non-empty, that should count as a filter change.
    """
    captured = {}

    def fake_get_htmx(view, request, *args, **kwargs):
        captured["filter_changed"] = view._filter_changed
        captured["filter_data"] = dict(view.filter_data)
        captured["query_dict"] = dict(view.query_dict)
        return HttpResponse("OK")

    monkeypatch.setattr(dt_views, "get_htmx", fake_get_htmx)

    rf = RequestFactory()
    request = rf.get(
        "/tableaux/",
        data={
            "~filter_data": "year=1999",  # old filter state didn't include title
            "title": "Brand New Filter",
        },
    )
    request.htmx = True

    response = DummyTableauxView.as_view()(request)
    assert response.status_code == 200

    assert captured["filter_data"] == {"year": "1999"}
    assert captured["query_dict"]["title"] == "Brand New Filter"
    assert captured["filter_changed"] is True
