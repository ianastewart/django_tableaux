from urllib.parse import urlparse, parse_qs, quote
from django.http import HttpRequest


def _base_key(request):
    return request.resolver_match.view_name


def save_columns(request: HttpRequest, width: int, column_list: list):
    key = f"columns:{request.resolver_match.view_name}:{width}"
    request.session[key] = column_list


def load_columns(request: HttpRequest, width: int):
    key = f"columns:{request.resolver_match.view_name}:{width}"
    return request.session[key] if key in request.session else None


def set_column(
    request: HttpRequest, width: int, column_name: str, checked: bool
) -> list:
    columns = load_columns(request, width)
    if checked:
        if column_name not in columns:
            columns.append(column_name)
    elif column_name in columns:
        columns.remove(column_name)
    save_columns(request, width, columns)
    return columns


def visible_columns(request: HttpRequest, table_class, width):
    """
    Return the list of visible column names in correct sequence
    """
    table = table_class(data=[])
    define_columns(table, width)
    if not table.responsive:
        width = 0
    columns = load_columns(request, width)
    return [col for col in table.sequence if col in columns]


def define_columns(table, width):
    """
    Add 4 lists of column names to table:
    columns_fixed = columns that are always visible
    columns_optional = columns that the user can choose to show
    columns_default = default visible columns
    columns_editable = columns that can be edited in situ
    """
    table.responsive = False
    table.columns_fixed = []
    table.columns_default = table.sequence
    table.columns_editable = []
    if table.Meta:
        col_dict = {}
        if hasattr(table.Meta, "editable"):
            table.columns_editable = table.Meta.editable
        if hasattr(table.Meta, "columns"):
            col_dict = table.Meta.columns
        if hasattr(table.Meta, "responsive"):
            table.responsive = True
            key = 0
            for breakpoint in table.Meta.responsive.keys():
                if width >= breakpoint:
                    key = breakpoint
            col_dict = table.Meta.responsive.get(key, {})
            # todo attrs
        table.columns_fixed = col_dict.get("fixed", [])
        table.columns_default = col_dict.get("default", table.sequence)
        table.mobile = col_dict.get("mobile", False)
    if not table.columns_fixed:
        table.columns_fixed = table.sequence[:1]
        if "selection" in table.columns_fixed and len(table.sequence) > 1:
            table.columns_fixed = table.sequence[:2]
    table.columns_optional = [c for c in table.sequence if c not in table.columns_fixed]


def set_column_states(table):
    """
    Control column visibility and
    add attribute 'columns_states' - a list of tuples used to create the column dropdown
    Expects 'table.columns_visible' to have been updated beforehand
    """
    table.column_states = [
        (col, table.columns.columns[col].header, col in table.columns_visible)
        for col in table.columns_optional
    ]


def breakpoints(table):
    bps = (
        list(table.Meta.responsive.keys()) if hasattr(table.Meta, "responsive") else []
    )
    return {"breakpoints": bps}


def save_per_page(request: HttpRequest, value: str):
    key = f"per_page:{request.resolver_match.view_name}"
    request.session[key] = value


def load_per_page(request: HttpRequest):
    key = f"per_page:{request.resolver_match.view_name}"
    return request.session[key] if key in request.session else 0
