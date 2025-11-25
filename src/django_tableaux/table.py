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
    table = table_class(data=view.get_filtered_object_list(), **kwargs)
    paginate = view.get_table_pagination(table)

    table.request = view.request

    order_by = view.request.GET.getlist(table.prefixed_order_by_field)
    if order_by:
        table.order_by = order_by
        table.last_order_by = view.last_order_by
    if paginate:
        if hasattr(paginate, "items"):
            kwargs = dict(paginate)
        else:
            kwargs = {}
        # extract some options from the request
        for arg in ("page", "per_page"):
            name = getattr(table, f"prefixed_{arg}_field")
            try:
                kwargs[arg] = int(view.request.GET[name])
            except (ValueError, KeyError):
                pass
        if view.last_order_by and "page" in kwargs:
            if order_by[0] != view.last_order_by:
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
    table.id = view.id  # f"tbx_{table.__class__.__name__.lower()}"
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


def get_table_pagination(view, table):
    """
    Return pagination options passed to `.RequestConfig`:
        - True for standard pagination (default),
        - False for no pagination,
        - a dictionary for custom pagination.

    `ListView`s pagination attributes are taken into account, if `table_pagination` does not
    define the corresponding value.

    Override this method to further customize pagination for a `View`.
    """
    paginate = view.table_pagination
    if paginate is False:
        return False

    paginate = {}

    # Obtains and set page size from get_paginate_by
    paginate_by = view.paginate_by
    paginate["per_page"] = paginate_by

    if hasattr(view, "paginator_class"):
        paginate["paginator_class"] = view.paginator_class

    if getattr(view, "paginate_orphans", 0) != 0:
        paginate["orphans"] = view.paginate_orphans

    # table_pagination overrides any MultipleObjectMixin attributes
    if view.table_pagination:
        paginate.update(view.table_pagination)

    # we have no custom pagination settings, so just use the default.
    if not paginate and view.table_pagination is None:
        return True

    return paginate


def get_paginate_by(view) -> Optional[int]:
    """
    Determines the number of items per page, or ``None`` for no pagination.

    Args:
        table_data: The table's data.

    Returns:
        Optional[int]: Items per page or ``None`` for no pagination.
    """
    return getattr(view, "paginate_by", None)
