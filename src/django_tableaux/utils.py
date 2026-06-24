from pathlib import Path
from typing import Dict, Union

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


def _session_key(request: HttpRequest, table: Table, bp: str) -> str:
    return f"columns:{_view_name(request)}:{table.__class__.__name__}:{bp}"


def save_columns_dict(
    request: HttpRequest, table: Table, bp: str, columns_dict: dict[str, bool]
):
    if request.user.is_authenticated:
        from django_tableaux.models import UserTableSettings

        UserTableSettings.objects.update_or_create(
            user=request.user,
            table_name=table.__class__.__name__,
            breakpoint=bp,
            defaults={"visible_columns": columns_dict},
        )
    else:
        request.session[_session_key(request, table, bp)] = columns_dict


def load_columns_dict(
    request: HttpRequest,
    table: Table,
    bp: str,
    current_dict: dict[str, bool] | None = None,
) -> dict[str, bool]:
    if request.user.is_authenticated:
        from django_tableaux.models import UserTableSettings

        try:
            row = UserTableSettings.objects.get(
                user=request.user,
                table_name=table.__class__.__name__,
                breakpoint=bp,
            )
            stored_dict = row.visible_columns
        except UserTableSettings.DoesNotExist:
            stored_dict = (
                current_dict
                if current_dict is not None
                else default_columns_dict(table)
            )
    else:
        stored_dict = request.session.get(_session_key(request, table, bp))
        if stored_dict is None:
            stored_dict = (
                current_dict
                if current_dict is not None
                else default_columns_dict(table)
            )

    # Sync with the table's current sequence: new columns default to False.
    columns_dict = {col: stored_dict.get(col, False) for col in table.sequence}
    save_columns_dict(request, table, bp, columns_dict)
    return columns_dict


def new_columns_dict(table: Table) -> dict[str, bool]:
    # Every column is visible
    return {col: True for col in table.sequence}


def default_columns_dict(table: Table) -> dict[str, bool]:
    # Only default columns are visible
    columns_dict = new_columns_dict(table)
    for key in columns_dict.keys():
        if key not in table.columns_default:
            columns_dict[key] = False
    return columns_dict


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
    Parse Meta.columns dict of the form:
        { col_name: kind | (kind, pixel_width) }
    where kind is "frozen" | "fixed" | "default".

    Populates:
        table.columns_fixed    - frozen + fixed columns (always visible, user cannot hide)
        table.columns_frozen   - frozen columns as list of (name, width) tuples
        table.columns_default  - initially visible columns (fixed + default-marked)
        table.columns_optional - columns user can show/hide (non-fixed, non-selection)
        table.columns_editable - editable columns (from Meta.editable if present)
    """
    table.columns_fixed = []
    table.columns_frozen = []
    table.columns_default = []
    table.columns_editable = getattr(table.Meta, "editable", []) if table.Meta else []
    if not hasattr(table, "select_name"):
        table.select_name = ""
    valid_columns = set(table.sequence)

    table.responsive = False
    if table.Meta and hasattr(table.Meta, "responsive"):
        if not isinstance(table.Meta.responsive, dict):
            raise ImproperlyConfigured("Meta.responsive must be a dictionary")
        table.responsive = True
        col_meta = dict(resolve_breakpoint(bp_dict, table.Meta.responsive, bp) or {})
    else:
        col_meta = dict(getattr(table.Meta, "columns", {}) if table.Meta else {})

    table.mobile = col_meta.pop("mobile_template", False)

    invalid_editable = [c for c in table.columns_editable if c not in valid_columns]
    if invalid_editable:
        raise ImproperlyConfigured(
            f"{table.__class__.__name__}.Meta.editable contains unknown column(s) {invalid_editable!r}. "
            f"Valid columns are: {sorted(valid_columns)}"
        )

    # Parse each column entry; value can be a string or (string, width) tuple
    sized = []  # (col_name, width) for all columns with an explicit width
    for col_name, attr in col_meta.items():
        if col_name not in valid_columns:
            raise ImproperlyConfigured(
                f"{table.__class__.__name__}.Meta.columns: '{col_name}' is not a valid column. "
                f"Valid columns are: {sorted(valid_columns)}"
            )
        kind = attr[0] if isinstance(attr, tuple) else attr
        width = attr[1] if isinstance(attr, tuple) and len(attr) > 1 else None

        if kind in ("frozen", "fixed"):
            table.columns_fixed.append(col_name)
            if kind == "frozen":
                table.columns_frozen.append((col_name, width))
            elif width is not None:
                sized.append((col_name, width))
        elif kind == "default":
            table.columns_default.append(col_name)
            if width is not None:
                sized.append((col_name, width))

    # columns_default always includes fixed columns (fixed are a subset of default).
    # If no columns were defined at all, show every column by default.
    table.columns_default = list(
        dict.fromkeys(table.columns_fixed + table.columns_default)
    )
    if not table.columns_default:
        table.columns_default = list(table.sequence)

    # Reorder sequence: defined columns first (in definition order), then the rest
    # in their original order. Only applied when a columns definition was provided.
    if col_meta:
        defined_set = set(table.columns_default)
        rest = [c for c in table.sequence if c not in defined_set]
        table.sequence = table.columns_default + rest

    # columns_optional: all non-fixed columns the user can show/hide, excluding selection
    fixed_set = set(table.columns_fixed)
    table.columns_optional = [
        c for c in table.sequence if c not in fixed_set and c != table.select_name
    ]

    # Apply width-only attrs to fixed/default columns that have a pixel width
    for col_name, width in sized:
        size_style = f"width: {width}px; min-width: {width}px; max-width: {width}px;"
        size_attrs = {"th": {"style": size_style}, "td": {"style": size_style}}
        existing_attrs = table.columns[col_name].column.attrs
        table.columns[col_name].column.attrs = merge_attrs(size_attrs, existing_attrs)

    # Merge sticky left-offset attrs into frozen columns; frozen takes precedence on clash
    offset = 0
    for col_name, width in table.columns_frozen:
        if width is not None:
            style = f"left: {offset}px; width: {width}px; min-width: {width}px; max-width: {width}px;"
            frozen_attrs = {
                "th": {"class": "frozen", "style": style},
                "td": {"class": "frozen", "style": style},
            }
            existing_attrs = table.columns[col_name].column.attrs
            table.columns[col_name].column.attrs = merge_attrs(
                frozen_attrs, existing_attrs
            )
            offset += width


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


DEFAULT_APP = "django_tableaux"
DEFAULT_LIBRARY = "basic"


def get_template_library():
    if hasattr(settings, "DJANGO_TABLEAUX"):
        if isinstance(settings.DJANGO_TABLEAUX, dict):
            return settings.DJANGO_TABLEAUX.get("templates_library", DEFAULT_LIBRARY)
        raise ImproperlyConfigured(
            "DJANGO_TABLEAUX in settings.py must be a dictionary"
        )
    return DEFAULT_LIBRARY


def template_paths(library=None):
    app_path = Path(apps.get_app_config(DEFAULT_APP).path)
    default_path = app_path / "templates" / DEFAULT_APP / "basic"

    custom_path = None
    library = library or get_template_library()

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
    Call this code in a 'render_foo' method within a table definition
    Renders an <a> tag with hx-get to fetch a form that is rendered inside the cell
    Note this does not use the template library code
    """
    template_name = template_name or "django_tableaux/basic/cell_edit.html"
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
    template_name = template_name or "django_tableaux/basic/cell_edit.html"
    form = form_class(initial={"value": value})
    context = {"id": record_id, "column": column, "value": value, "form": form}
    return render(request, template_name, context)


def strip_prefix_from_keys(data: dict, prefix: str) -> dict:
    plen = len(prefix)
    return {
        (key[plen:] if key.startswith(prefix) else key): value
        for key, value in data.items()
    }


AttrValue = Union[str, dict]
AttrDict = Dict[str, dict[str, AttrValue]]


def merge_attrs(col_attrs: AttrDict, table_attrs: AttrDict) -> AttrDict:
    """
    Merge table attributes into column attributes.

    - Only relevant table sections (th/td/cell) are merged
    - Column attributes overlay table defaults
    - Class/style concatenated with column last
    - Callables preserved
    """
    RELEVANT_SECTIONS = {"th", "td", "cell"}
    result: Dict[str, dict[str, AttrValue]] = {}

    # First, copy column attributes
    for section, col_section in col_attrs.items():
        if isinstance(col_section, dict):
            result[section] = dict(col_section)
        else:
            result[section] = col_section

    # Merge relevant table sections
    for section in RELEVANT_SECTIONS:
        table_section = table_attrs.get(section)
        col_section = result.get(section, {})

        if isinstance(table_section, dict):
            merged = dict(table_section)  # start with table defaults

            if isinstance(col_section, dict):
                for key, col_value in col_section.items():
                    table_value = merged.get(key)

                    if isinstance(table_value, str) and isinstance(col_value, str):
                        if key == "class":
                            merged[key] = f"{table_value} {col_value}"
                        elif key == "style":
                            merged[key] = f"{table_value.rstrip(';')}; {col_value}"
                        else:
                            merged[key] = col_value
                    else:
                        # callable or mixed-type → column wins
                        merged[key] = col_value
            result[section] = merged

    return result


def bulk_action_namer(texts: list) -> list[tuple[str, str]] | None:
    result = []
    for text in texts:
        name = text.lower().replace(" ", "_")
        result.append((name, text))
