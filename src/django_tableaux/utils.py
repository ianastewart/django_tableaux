from os import listdir
from os.path import isfile, join, exists

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
    Set table.select_name to name of the (first) Selection column if one exists
    and update sequence if necessary
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
    # Ensure table.select_name exists for ease of testing
    if not hasattr(table, "select_name"):
        table.select_name = ""
    if table.Meta:
        col_dict = {}
        if hasattr(table.Meta, "editable"):
            table.columns_editable = table.Meta.editable
        if hasattr(table.Meta, "columns"):
            if type(table.Meta.columns) == dict:
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
    Control column visibility and add attribute 'column_states' to the table
    This is a list of tuples used to create the column dropdown
    Expects 'table.columns_visible' to have been updated beforehand
    """
    table.column_states = [
        (col, table.columns.columns[col].header, col in table.columns_visible)
        for col in table.columns_optional
    ]


def breakpoints(table):
    return (
        list(table.Meta.responsive.keys()) if hasattr(table.Meta, "responsive") else []
    )


def save_per_page(request: HttpRequest, value: str):
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


def get_template_prefix():
    # used for components that directly specify their template
    library = get_template_library()
    return library if library[:10] == "templates/" else f"{DEFAULT_APP}/{library}"


def build_templates_dictionary(library=""):
    """
    Returns a dictionary with key=template name (without .html suffix) and value=template path
    """
    result = {}
    library = library or get_template_library()
    app_path = apps.get_app_config(DEFAULT_APP).path
    lib_files = []
    prefix = ""
    if library != DEFAULT_LIBRARY:
        if library[:10] == "templates/":
            full_path = settings.BASE_DIR / library
            if not exists(full_path):
                raise ImproperlyConfigured(
                    f"Template library '{library}' does not exist."
                )
            prefix = full_path
        else:
            # check if in own app
            full_path = join(app_path, "templates", DEFAULT_APP, library)
            if exists(full_path):
                prefix = f"{DEFAULT_APP}/{library}"
                lib_files = [
                    f for f in listdir(full_path) if isfile(join(full_path, f))
                ]
    # iterate default library and add entries to result unless file exists in specified library
    for file in listdir(join(app_path, "templates", DEFAULT_APP, DEFAULT_LIBRARY)):
        name = file.split(".")[0]
        if file in lib_files:
            result[name] = join(prefix, file)
        else:
            result[name] = join(DEFAULT_APP, DEFAULT_LIBRARY, file)
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
