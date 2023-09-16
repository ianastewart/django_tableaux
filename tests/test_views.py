import pytest
from django.db.models import *
from django.test import RequestFactory, TestCase
from django_tables2 import tables
from myapp.models import *
from django_htmx.middleware import HtmxDetails

from src.django_tableaux.views import TableauxView


class Table1(tables.Table):
    class Meta:
        model = Model1


class View1(TableauxView):
    model = Model1

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# class MyView(TestCase):
#     def test_get(self):
#         request = RequestFactory().get("/")
#         view = TableauxView()
#         view.setup(request)


@pytest.mark.django_db
def test_empty_table():
    request = RequestFactory().get("/")
    request.htmx = ""
    request.session = {}
    response = View1.as_view()(request)
    assert response.status_code == 200
    response.render()
    assert "<table" in response.rendered_content
    assert "<td" not in response.rendered_content


@pytest.mark.django_db
def test_table_with_data():
    for x in range(2):
        Model1.objects.create(
            name=f"name_{x}", description=f"description_{x}", decimal=x
        )
    request = RequestFactory().get("/")
    request.htmx = ""
    request.session = {}
    response = View1.as_view()(request)
    assert response.status_code == 200
    response.render()
    p = response.rendered_content.find("<table")
    body = response.rendered_content[p:]
    assert body.count("<tr") == 10
