from django import template
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe
from django.urls import reverse, NoReverseMatch

register = template.Library()


@register.simple_tag(takes_context=False)
def django_tableaux_script():
    return mark_safe(
        '<script src="/static/django_tableaux/js/django_tableaux.js"></script>'
    )


@register.simple_tag(takes_context=True)
def attrs(context):
    """Convert context into a string of html attributes, converting '_' to '-'"""
    result = ""
    for key, value in context.flatten().items():
        if key not in ["True", "False", "None", "content", "element"]:
            if "hx_" in key:
                key = key.replace("_", "-")
            result += f' {key}="{value}"'
    return mark_safe(result)


@register.simple_tag(takes_context=True)
def load_table(context, url_name, prefix=""):
    try:
        url = reverse(url_name)
    except NoReverseMatch:
        raise ImproperlyConfigured(f"Tableaux: {url_name} is not a valid url name")
    query_string = context.request.GET.urlencode()
    hx_vals = f"js:{{ '_bp': getCurrentBreakpoint(), 'prefix': '{prefix}', 'query_string': '{query_string}' }}"
    code = f'<div id="{prefix}load_{url_name}" name="table_load" hx-trigger="load" hx-get="{url}" hx-vals="{hx_vals}" hx-swap="outerHTML" hx-target="#{prefix}load_{url_name}"></div>'
    return mark_safe(code)


@register.filter
def render_button(button):
    return button.render()


@register.filter
def td_attr(column, table):
    """
    Add td-edit class to td attributes if it is editable
    NB col.attrs is an immutable property
    """
    html = column.attrs["td"].as_html()
    td_edit = "td-edit"
    if column.name in table.columns_editable and td_edit not in html:
        value = column.attrs["td"]["class"]
        if value:
            s = html.replace(value, f"{td_edit} {value}")
        else:
            s = html + f' class="{td_edit}"'
        return mark_safe(s)
    return html


@register.filter
def has_filter_toolbar(view):
    return view.filterset is not None and view.filterstyle == view.filterstyle.TOOLBAR


@register.filter
def is_selection(column):
    if column.__class__.__name__ == "BoundColumn":
        return column.column.__class__.__name__ == "SelectionColumn"
    return False
