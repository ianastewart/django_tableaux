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
