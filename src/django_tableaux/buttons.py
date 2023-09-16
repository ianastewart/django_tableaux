from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from .utils import get_template_prefix


class Button:
    template_name = "button.html"

    def __init__(self, content, name="", typ="button", css="btn btn-primary", **kwargs):
        self.context = {
            "element": "a" if kwargs.get("href") else "button",
            "content": content,
            "name": slugify(content) if not name else name,
            "class": css,
        }
        if self.context["element"] == "button":
            self.context["type"] = typ
        self.context.update(kwargs)

    def render(self):
        html = mark_safe(
            render_to_string(
                template_name=f"{get_template_prefix()}/{self.template_name}",
                context=self.context,
            )
        )
        return html
