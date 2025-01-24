from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from .utils import get_template_path


class Button:
    template_name = "button.html"
    prefix = "btn_"
    name = ""

    def __init__(
        self, content="", name="", typ="button", css="btn btn-primary", **kwargs
    ):
        if content == "" and name == "":
            raise ValueError("Button content and name cannot both be empty.")
        self.name = (
            f"{self.prefix}{name}"
            if name
            else f"{self.prefix}{slugify(content).replace('-', '_')}"
        )
        self.context = {
            "element": "a" if kwargs.get("href") else "button",
            "content": content,
            "name": self.name,
            "class": css,
        }
        if self.context["element"] == "button":
            self.context["type"] = typ
        self.context.update(kwargs)

    def render(self):
        html = mark_safe(
            render_to_string(
                template_name=get_template_path(self.template_name),
                context=self.context,
            )
        )
        return html

    def original_name(self):
        """
        Return the button name without the prefix added
        """
        return self.name[len(self.prefix) :]
