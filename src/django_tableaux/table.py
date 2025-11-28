import logging
import time
from enum import IntEnum
from django.utils.http import urlencode
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import QueryDict, HttpResponse
from django.shortcuts import render, reverse, redirect
from django.template.response import TemplateResponse
from django.urls.resolvers import NoReverseMatch
from django.core.paginator import Paginator

from typing import Any, Optional

from .utils import (
    breakpoints,
    define_columns,
    set_select_column,
    set_column_states,
    save_columns_dict,
    load_columns_dict,
)


def build_table(view, **kwargs):
    # This replaces get_table and use of RequestConfig in SingleTableMixin
    # This allows us to control pagination when sorting and add extra properties to the table
    # to manage column visibility
    table_class = view.get_table_class()
    table = table_class(data=view.object_list, **kwargs)

    table.request = view.request
    # Sorting
    order_by = view.request.GET.getlist(table.prefixed_order_by_field)
    if order_by:
        table.order_by = order_by
        table.last_order_by = view.last_order_by
    # Pagination
    kwargs = {"per_page": view.per_page,
              "page":  1}
    if hasattr(view, "paginator_class"):
        kwargs["paginator_class"] = view.paginator_class
    # update from the request
    for arg in ("per_page", "page"):
        name = getattr(table, f"prefixed_{arg}_field")
        value = view.request.GET.get(name)
        if value:
            kwargs[arg] = int(value)
    if view._page is not None:
        kwargs["page"] = view._page
    if view.last_order_by and "page" in kwargs:
        if order_by != view.last_order_by:
            kwargs["page"] = 1
    silent = kwargs.pop("silent", True)
    if not silent:
        table.paginate(**kwargs)
    else:
        try:
            table.paginate(**kwargs)
        except PageNotAnInteger:
            table.page = table.paginator.page(1)
        except EmptyPage:
            table.page = table.paginator.page(table.paginator.num_pages)

    # This adds dynamic attributes to the table instance
    table.prefix = view.prefix
    table.indicator = view.indicator
    table.last_sort = view.request.GET.get("sort", None)
    table.filter = view.filterset
    table.infinite_scroll = view.infinite_scroll
    table.infinite_load = view.infinite_load
    table.sticky_header = view.sticky_header
    # variables that control action when table is clicked
    table.click_action = view.click_action.value
    table.url = ""
    table.pk = False
    if view.click_url_name:
        # handle case when there is no PK passed (create)
        try:
            table.url = reverse(view.click_url_name)
        except NoReverseMatch:
            # Detail or update views have a pk
            try:
                table.url = reverse(view.click_url_name, kwargs={"pk": 0})[:-2]
                table.pk = True
            except NoReverseMatch:
                raise (
                    ImproperlyConfigured(
                        f"Cannot resolve click_url_name: '{view.click_url_name}'"
                    )
                )
    table.target = view.click_target

    set_select_column(table)
    # if view.get_bulk_actions() and not table.select_name:
    #     raise ImproperlyConfigured(
    #         "Bulk actions require a selection column to be defined"
    #     )
    # if table.select_name and not view.get_bulk_actions():
    #     raise ImproperlyConfigured("Selection column without bulk actions")

    # define possible columns depending upon the current breakpoint
    define_columns(table, view.get_breakpoint_values(), view._bp)

    # set visible columns according to saved setting
    columns_dict = load_columns_dict(view.request, table, view._bp)
    table.columns_visible = [col for col in columns_dict if columns_dict[col]]
    set_column_states(table)

    if table.filter:
        table.filter.style = view.filter_style
        # If filter is in header, build list of filters in same sequence as columns
        if view.filter_style == view.FilterStyle.HEADER:
            table.header_fields = []
            for col in table.sequence:
                if table.columns.columns[col].visible:
                    if col in table.filter.base_filters.keys():
                        table.header_fields.append(table.filter.form[col])
                    else:
                        table.header_fields.append(None)
    if view.sticky_header:
        if "class" not in table.attrs["thead"]:
            table.attrs["thead"]["class"] = "sticky"
        else:
            table.attrs["thead"]["class"] += " sticky"
    return table

