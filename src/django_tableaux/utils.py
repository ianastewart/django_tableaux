from pathlib import Path
from symtable import Class

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.shortcuts import render
from django.template import loader
from django.utils.safestring import mark_safe
from django_tables2 import Table


def _view_name(request):
    try:
        return request.resolver_match.view_name
    except AttributeError:
        return "test"


def save_columns_dict(
    request: HttpRequest, table: Table, bp: str, columns_dict: dict[str, bool]
):
    key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{bp}"
    request.session[key] = columns_dict


def load_columns_dict(request: HttpRequest, table: Table, bp: str) -> dict[str, bool]:
    key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{bp}"
    stored_dict = request.session.get(key)
    # Early versions stored visible columns as a list
    if not isinstance(stored_dict, dict):
        request.session[key] = {}
        stored_dict = None
    if stored_dict is None:
        stored_dict = default_columns_dict(table, bp)
    # Sync with table's current columns, adding new ones as False (not visible).
    columns_dict = {col: stored_dict.get(col, False) for col in table.sequence}
    save_columns_dict(request, table, bp, columns_dict)
    return columns_dict


def new_columns_dict(table: Table) -> dict:
    return {col: True for col in table.sequence}


def default_columns_dict(table: Table, bp: str) -> dict[str, bool]:
    columns_dict = new_columns_dict(table)
    for key in columns_dict.keys():
        if key not in table.columns_default:
            columns_dict[key] = False
    return columns_dict


# def save_columns(request: HttpRequest, table: Table, bp: str, column_list: list):
#     key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{bp}"
#     request.session[key] = column_list
#
#
# def load_columns(request: HttpRequest, table: Table, bp: str) -> list:
#     key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{bp}"
#     return request.session[key] if key in request.session else []


def set_column(
    request: HttpRequest, table: Table, bp: str, column_name: str, checked: bool
) -> list:
    column_dict = load_columns_dict(request, table, bp)
    column_dict[column_name] = checked
    save_columns_dict(request, table, bp, column_dict)


def visible_columns(
    request: HttpRequest, table_class, bp_dict: dict[str, int], bp: str
) -> list[str]:
    """
    Return the list of visible column names in correct sequence
    """
    table = table_class(data=[])  # Create a dummy table to inspect its properties
    define_columns(table, bp_dict, bp)  # Configure columns based on breakpoint
    columns_dict = load_columns_dict(request, table, bp)
    return [col for col, is_visible in columns_dict.items() if is_visible]


def set_select_column(table):
    """
    Set table.select_name to name of the (first) Selection column if one path.exists
    and update sequence if necessary.
    """
    table.select_name = next(
        (
            col.name
            for col in table.columns
            if col.column.__class__.__name__ == "SelectionColumn"
        ),
        "",
    )

    if table.select_name:
        # If user has not explicitly placed the selection column, move it to the front.
        meta_has_sequence = hasattr(table, "Meta") and hasattr(table.Meta, "sequence")
        if meta_has_sequence and table.select_name in table.Meta.sequence:
            return

        if table.select_name in table.sequence:
            index = table.sequence.index(table.select_name)
        if index > 0:
            table.sequence.remove(table.select_name)
            table.sequence.insert(0, table.select_name)


def define_columns(table, bp_dict: dict[str, int], bp: str = ""):
    """
    Add 4 lists of column names to table according to the breakpoint
      columns_fixed = columns that are always visible
      columns_optional = columns that the user can choose to show
      columns_default = default visible columns
      columns_editable = columns that can be edited in situ
    """
    table.responsive = False
    table.columns_fixed = []
    table.columns_default = table.sequence
    table.columns_editable = []
    # Ensure table.select_name path.exists for ease of testing
    if not hasattr(table, "select_name"):
        table.select_name = ""
    if table.Meta:
        col_dict = {}
        if hasattr(table.Meta, "editable"):
            if isinstance(table.Meta.editable, list):
                table.columns_editable = table.Meta.editable
            else:
                raise ImproperlyConfigured("Meta.editable must be a list")
        if hasattr(table.Meta, "columns"):
            if isinstance(table.Meta.columns, dict):
                col_dict = table.Meta.columns
            else:
                raise ImproperlyConfigured("Meta.columns must be a dictionary")
        # responsive overides any existing column definition
        if hasattr(table.Meta, "responsive"):
            if isinstance(table.Meta.responsive, dict):
                table.responsive = True
                col_dict = resolve_breakpoint(bp_dict, table.Meta.responsive, bp)
            else:
                raise ImproperlyConfigured("Meta.responsive must be a dictionary")
            # # todo attrs
        table.columns_fixed = col_dict.get("fixed", [])
        table.columns_default = col_dict.get("default", table.sequence)
        # Default columns always include fixed columns, but they may not have been specified.
        # Combine lists and remove duplicates, preserving order (requires Python 3.7+).
        table.columns_default = list(
            dict.fromkeys(table.columns_fixed + table.columns_default)
        )
        table.mobile = col_dict.get("mobile", False)
    if not table.columns_fixed:
        table.columns_fixed = table.sequence[:1]
        if table.columns_fixed[0] == table.select_name and len(table.sequence) > 1:
            table.columns_fixed = table.sequence[:2]
        if table.select_name and table.select_name not in table.columns_fixed:
            table.columns_fixed.append(table.select_name)
    table.columns_optional = [
        c
        for c in table.sequence
        if c not in table.columns_fixed and c != table.select_name
    ]


def resolve_breakpoint(
    bp_dict: dict[str, int], responsive: dict[str, dict], bp: str
) -> dict | None:
    """
    Finds the most appropriate responsive configuration for a given breakpoint.

    This function implements a "fall-forward" and "fall-back" logic:
    - If `bp` is defined in `responsive`, its configuration is used.
    - If `bp` is NOT defined, it uses the configuration of the next SMALLEST defined breakpoint.
    - If `bp` is smaller than any defined breakpoint, it uses the configuration
      of the FIRST available (i.e., smallest) defined breakpoint.
    - If `bp` is not a valid breakpoint key, it also falls back to the first
      available configuration.

    Args:
        bp_dict (dict): A dictionary of all possible breakpoint keys.
        responsive (dict): A dictionary mapping breakpoint keys to their configuration values.
        bp (str): The current breakpoint key to resolve.

    Returns:
        The resolved configuration value, or None if no responsive configurations are defined.
    """
    # The config of the first defined breakpoint encountered, used as a fallback.
    fallback_config = None
    # The config of the most recent defined breakpoint found during iteration.
    candidate_config = None
    if responsive is None:
        return None
    for key in bp_dict.keys():
        if key in responsive:
            candidate_config = responsive[key]
            if fallback_config is None:
                fallback_config = candidate_config
        # If we've reached the target breakpoint, the current candidate is the correct one.
        if key == bp and candidate_config:
            return candidate_config
    # No match so, we return the first defined breakpoint we found.
    return fallback_config


def set_column_states(table):
    """
    Control column visibility and add attribute 'columns_states' to the table
    This is a list of tuples used to create the column dropdown
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


def save_per_page(request: HttpRequest, value: int):
    key = f"per_page:{request.resolver_match.view_name}"
    request.session[key] = value


def load_per_page(request: HttpRequest):
    key = f"per_page:{request.resolver_match.view_name}"
    return request.session[key] if key in request.session else 0


DEFAULT_APP = "django_tableaux"
DEFAULT_LIBRARY = "basic"


def get_template_library():
    if hasattr(settings, "DJANGO_TABLEAUX_LIBRARY"):
        return settings.DJANGO_TABLEAUX_LIBRARY
    return DEFAULT_LIBRARY


def template_paths(library=None):
    app_path = Path(apps.get_app_config(DEFAULT_APP).path)
    default_path = app_path / "templates" / DEFAULT_APP / "basic"

    custom_path = None
    library = library or get_template_library()
    if library == "bootstrap4":
        try:
            from bootstrap4 import forms
        except ImportError:
            raise ImproperlyConfigured("django-bootstrap4 is not installed")
    if library == "bootstrap5":
        try:
            from django_bootstrap5 import forms
        except ImportError:
            raise ImproperlyConfigured("django-bootstrap5 is not installed")
    if library != DEFAULT_LIBRARY:
        if library.startswith("templates/"):
            custom_path = Path(settings.BASE_DIR) / library
        else:
            custom_path = app_path / "templates" / DEFAULT_APP / library
        if not custom_path.exists():
            raise ImproperlyConfigured(f"Template library '{library}' does not exist.")
    return default_path, custom_path


def get_template_path(template_name: str) -> str:
    """
    Return the full path for a template by first searching the custom directory
    then the default directory.
    """
    default_path, custom_path = template_paths()
    if custom_path:
        custom_file = custom_path / template_name
        if custom_file.exists():
            return str(custom_file)
    default_file = default_path / template_name
    if default_file.exists():
        return str(default_file)
    raise ValueError(f"Template '{template_name}' does not exist.")


def build_templates_dictionary(library=None):
    """
    Returns a dictionary with key=template name (without .html) and value=full template path
    """
    default_path, custom_path = template_paths(library=library)
    # Load default templates, then overwrite with any custom templates
    result = {p.stem: str(p) for p in default_path.glob("*.html")}
    if custom_path:
        custom_templates = {p.stem: str(p) for p in custom_path.glob("*.html")}
        result.update(custom_templates)
    return result


def render_editable_link(
    record=None, column=None, value=None, url="", template_name=None
):
    """
    Call this code in a 'render_foo' method with a table definition
    Renders an <a> tag with hx-get to fetch a form that is rendered inside the cell
    Note this does not use the template library code
    """
    template_name = template_name or "django_tableaux/bootstrap4/cell_edit.html"
    if record is None or column is None or value is None:
        raise ValueError(
            "Function render_editable() requires record, column and value to be specified"
        )
    context = {"id": record.id, "column": column, "value": value, "url": url}
    return mark_safe(loader.render_to_string(template_name, context))


def render_editable_form(
    request, record_id, column=None, value=None, form_class=None, template_name=None
):
    """
    Render a form inside a table cell so the cell value can be edited
    django_tableaux.js will send hx-post when a value is selected or entered
    Note this does not use the template library code
    """
    template_name = template_name or "django_tableaux/bootstrap4/cell_edit.html"
    form = form_class(initial={"value": value})
    context = {"id": record_id, "column": column, "value": value, "form": form}
    return render(request, template_name, context)
