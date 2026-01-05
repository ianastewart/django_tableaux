import itertools

import django_tables2 as tables
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.safestring import mark_safe

from .utils import get_template_path


class EditableColumn(tables.Column):
    def render(self, value, record):
        return value


class RightAlignedColumn(tables.Column):
    pass
    # def __init__(self, **kwargs):
    #     # super().__init__(attrs={"class": "text-end"})
    #     attrs = kwargs.pop("attrs", {})
    #
    #     # Merge / extend attrs safely
    #     td_attrs = attrs.get("td", {}).copy()
    #     th_attrs = attrs.get("th", {}).copy()
    #
    #     td_attrs.setdefault("class", "")
    #     th_attrs.setdefault("class", "")
    #
    #     td_attrs["class"] = f'{td_attrs["class"]} text-end'.strip()
    #     th_attrs["class"] = f'{th_attrs["class"]} text-end'.strip()
    #
    #     attrs["td"] = td_attrs
    #     attrs["th"] = th_attrs
    #
    #     kwargs["attrs"] = attrs
    #     super().__init__(**kwargs)

    # def set_attr(self, value):
    #     if "th" not in self.attrs:
    #         self.attrs["th"] = {}
    #     if "td" not in self.attrs:
    #         self.attrs["td"] = {}
    #     if "style" not in self.attrs["th"]:
    #         self.attrs["th"]["style"] = value
    #     else:
    #         self.attrs["th"]["style"] = value + " " + self.attrs["th"]["style"]
    #     if "style" not in self.attrs["td"]:
    #         self.attrs["td"]["style"] = value
    #     else:
    #         self.attrs["td"]["style"] = value + " " + self.attrs["td"]["style"]


class CenteredColumn(RightAlignedColumn):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_attr("text-align: center;")


class CenteredTrueColumn(CenteredColumn):
    def render(self, value):
        if value:
            return "\u2705"
        return ""


class CenteredTrueFalseColumn(CenteredColumn):
    def render(self, value):
        if value:
            return "\u2705"
        return "\u274c"


class CurrencyColumn(RightAlignedColumn):
    def __init__(self, **kwargs):
        self.integer = kwargs.pop("integer", None)
        self.prefix = kwargs.pop("prefix", "")
        self.suffix = kwargs.pop("suffix", "")
        super().__init__(**kwargs)

    def render(self, value):
        if self.integer:
            value = int(value)
        return mark_safe(f"{self.prefix}{intcomma(value)}{self.suffix}")


class CheckBoxColumn(tables.TemplateColumn):
    def __init__(self, **kwargs):
        kwargs["template_name"] = get_template_path("custom_checkbox.html")
        super().__init__(**kwargs)


class SelectionColumn(tables.TemplateColumn):
    def __init__(self, **kwargs):
        kwargs["template_name"] = get_template_path("select_checkbox.html")
        kwargs["verbose_name"] = ""
        kwargs["accessor"] = "id"
        kwargs["orderable"] = False
        super().__init__(**kwargs)


class CounterColumn(tables.Column):
    row_counter = None

    def __init__(self, **kwargs):
        kwargs["orderable"] = False
        kwargs["empty_values"] = ()
        kwargs["verbose_name"] = ""
        super().__init__(**kwargs)

    def render(self, value):
        if not self.row_counter:
            self.row_counter = itertools.count()
        return next(self.row_counter) + 1
