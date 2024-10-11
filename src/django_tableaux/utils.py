from os import listdir, path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.shortcuts import render
from django.template import loader
from django.utils.safestring import mark_safe


def _view_name(request):
    try:
        return request.resolver_match.view_name
    except AttributeError:
        return "test"


def save_columns(request: HttpRequest, table, width: int, column_list: list):
    key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{width}"
    request.session[key] = column_list


def load_columns(request: HttpRequest, table, width: int):
    key = f"columns:{_view_name(request)}:{table.__class__.__name__}:{width}"
    return request.session[key] if key in request.session else None


def set_column(
    request: HttpRequest, table, width: int, column_name: str, checked: bool
) -> list:
    columns = load_columns(request, table, width)
    if checked:
        if column_name not in columns:
            columns.append(column_name)
    elif column_name in columns:
        columns.remove(column_name)
    save_columns(request, table, width, columns)
    return columns


def visible_columns(request: HttpRequest, table_class, width):
    """
    Return the list of visible column names in correct sequence
    """
    table = table_class(data=[])
    define_columns(table, width)
    if not table.responsive:
        width = 0
    columns = load_columns(request, table, width)
    return [col for col in table.sequence if col in columns]


def set_select_column(table):
    """
    Set table.select_name to name of the (first) Selection column if one path.exists
    and update sequence if necessary.
    """
    table.select_name = ""
    for col in table.columns:
        if col.column.__class__.__name__ == "SelectionColumn":
            table.select_name = col.name
            break

    if table.select_name:
        # if user has defined the position of the selection column in Meta.sequence, respect it
        if (
            hasattr(table, "Meta")
            and hasattr(table.Meta, "sequence")
            and table.select_name in table.Meta.sequence
        ):
            return
        # else make sure that selection is the first column
        index = table.sequence.index(table.select_name)
        if index > 0:
            table.sequence.remove(table.select_name)
            table.sequence.insert(0, table.select_name)


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
    # Ensure table.select_name path.exists for ease of testing
    if not hasattr(table, "select_name"):
        table.select_name = ""
    if table.Meta:
        col_dict = {}
        if hasattr(table.Meta, "editable"):
            table.columns_editable = table.Meta.editable
        if hasattr(table.Meta, "columns"):
            if table.Meta.columns is dict:
                col_dict = table.Meta.columns
            else:
                raise ValueError("Meta.columns must be a dictionary")
        if hasattr(table.Meta, "responsive"):
            table.responsive = True
            key = 0
            for break_point in table.Meta.responsive.keys():
                if width >= break_point:
                    key = break_point
            col_dict = table.Meta.responsive.get(key, {})
            # todo attrs
        table.columns_fixed = col_dict.get("fixed", [])
        table.columns_default = col_dict.get("default", table.sequence)
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


def save_per_page(request: HttpRequest, value: str):
    key = f"per_page:{request.resolver_match.view_name}"
    request.session[key] = value


def load_per_page(request: HttpRequest):
    key = f"per_page:{request.resolver_match.view_name}"
    return request.session[key] if key in request.session else 0


DEFAULT_APP = "django_tableaux"
DEFAULT_LIBRARY = "bootstrap4"


def get_template_library():
    if hasattr(settings, "DJANGO_TABLEAUX_LIBRARY"):
        return settings.DJANGO_TABLEAUX_LIBRARY
    return DEFAULT_LIBRARY


def template_paths(library=None):
    app_path = apps.get_app_config(DEFAULT_APP).path
    default_path = path.join(app_path, "templates", DEFAULT_APP, DEFAULT_LIBRARY)
    custom_path = None
    library = library or get_template_library()
    if library != DEFAULT_LIBRARY:
        if library[:10] == "templates/":
            custom_path = settings.BASE_DIR / library
        else:
            custom_path = path.join(app_path, "templates", DEFAULT_APP, library)
        if not path.exists(custom_path):
            raise ImproperlyConfigured(
                f"Template library '{library}' does not exist."
            )
    return default_path, custom_path

def get_template_path(template_name) -> str:
    """
    Return the full path for a template by first searching the custom directory
    then the default directory
    """
    default_path, custom_path = template_paths()
    if custom_path:
        custom_name = path.join(custom_path, template_name)
        if path.exists(custom_name):
            return custom_name
    default_name = path.join(default_path, template_name)
    if path.exists(default_name):
        return default_name
    raise ValueError("Template {template_name} does not exist.")


def build_templates_dictionary(library=None):
    """
    Returns a dictionary with key=template name and value = template path
    """
    result = {}
    default_path, custom_path = template_paths(library=library)
    # iterate default library and add entries to result unless file path.exists in custom library
    for template in listdir(default_path):
        short_name = template[:-5]
        if custom_path and path.isfile(path.join(custom_path, template)):
            result[short_name] = path.join(custom_path, template)
        else:
            result[short_name] = path.join(default_path, template)
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
