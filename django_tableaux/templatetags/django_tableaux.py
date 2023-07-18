from django import template
from django.utils.safestring import mark_safe

register = template.Library()


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


@register.filter
def render_button(button):
    return button.render()


@register.filter
def td_attr(column, table):
    """
    Add td_edit class to td attributes if it is editable
    NB col.attrs is an immutable property
    """
    html = column.attrs["td"].as_html()
    if column.name in table.columns_editable and "td_edit" not in html:
        value = column.attrs["td"]["class"]
        if value:
            s = html.replace(value, f"td_edit {value}")
        else:
            s = html + ' class="td_edit"'
        return mark_safe(s)
    return html
