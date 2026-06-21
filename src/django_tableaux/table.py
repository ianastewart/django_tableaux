from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.shortcuts import reverse
from django.urls.resolvers import NoReverseMatch
from django_tableaux.utils import merge_attrs

from .models import Pagination, FilterStyle
from .utils import (
    define_columns,
    set_select_column,
    set_column_states,
    load_columns_dict,
)


def build_table(view, **kwargs):
    # This replaces get_table and use of RequestConfig in SingleTableMixin
    # This allows us to control pagination when sorting and add extra properties to the table
    # to manage column visibility
    table_class = view.get_table_class()
    table = table_class(data=view.object_list, **kwargs)
    # Merge table-level with column attributes
    for bound_column in table.columns:
        col = bound_column.column
        col.attrs = merge_attrs(col.attrs, table.attrs)

    # Sorting
    order_by = view.query_dict.get("~order_by", "")
    if order_by:
        table.order_by = order_by

    # Pagination
    if view.pagination != Pagination.NONE:
        kwargs = {
            "per_page": view.query_dict.get("~per_page", view.page_size),
            "page": view.query_dict.get("~page", 1),
        }
        if hasattr(view, "paginator_class"):
            kwargs["paginator_class"] = view.paginator_class
        # Changing sort order or filtering resets page to 1
        if view._order_by_changed or view._filter_changed:
            kwargs["page"] = 1
            # view.query_dict["~page"] = 1
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

    table.sticky_header = view.sticky_header
    # variables that control action when table is clicked
    table.url = ""
    table.pk = False
    if view.click_url_name:
        # handle case when there is no PK passed (create)
        try:
            table.url = reverse(view.click_url_name)
        except NoReverseMatch:
            # Detail or update views have a pk
            try:
                sentinel = 987654321
                table.url = reverse(view.click_url_name, kwargs={"pk": sentinel}).replace(str(sentinel), "__pk__")
                table.pk = True
            except NoReverseMatch:
                raise (ImproperlyConfigured(f"Cannot resolve click_url_name: '{view.click_url_name}'"))
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

    # Detect breakpoint change; if the bp has changed and the new one has no saved
    # settings, seed it from the previous bp's settings rather than defaulting.
    prev_bp_key = f"tbx:prev_bp:{table.__class__.__name__}"
    prev_bp = view.request.session.get(prev_bp_key)
    view.request.session[prev_bp_key] = view._bp
    if prev_bp and prev_bp != view._bp:
        current_dict = load_columns_dict(view.request, table, prev_bp)
    else:
        current_dict = None

    # set visible columns according to saved setting
    columns_dict = load_columns_dict(view.request, table, view._bp, current_dict=current_dict)
    table.columns_visible = [col for col in columns_dict if columns_dict[col]]
    set_column_states(table)

    # If filter is in header, build list of filters in same sequence as columns
    if view.filter_style == FilterStyle.HEADER:
        table.header_fields = []
        for col in table.sequence:
            if table.columns.columns[col].visible:
                if col in view.filterset.base_filters.keys():
                    table.header_fields.append(view.filterset.form[col])
                else:
                    table.header_fields.append(None)
    if view.sticky_header:
        if "class" not in table.attrs["thead"]:
            table.attrs["thead"]["class"] = "sticky"
        else:
            table.attrs["thead"]["class"] += " sticky"
    return table
