import itertools
import django_tables2 as tables
from django.contrib.humanize.templatetags.humanize import intcomma
from .utils import get_template_prefix
from django.utils.safestring import mark_safe


class EditableColumn(tables.Column):
    def render(self, value, record):
        return value


class RightAlignedColumn(tables.Column):
    def __init__(self, **kwargs):
        super().__init__()
        if "th" not in self.attrs:
            self.attrs["th"] = {}
        if "td" not in self.attrs:
            self.attrs["td"] = {}
        self.attrs["th"]["style"] = "text-align: right;"
        self.attrs["td"]["style"] = "text-align: right;"


class CenteredColumn(tables.Column):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "th" not in self.attrs:
            self.attrs["th"] = {}
        if "td" not in self.attrs:
            self.attrs["td"] = {}
        self.attrs["th"]["style"] = "text-align: center;"
        self.attrs["td"]["style"] = "text-align: center;"


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
        kwargs["template_name"] = f"{get_template_prefix()}/custom_checkbox.html"
        super().__init__(**kwargs)


class SelectionColumn(tables.TemplateColumn):
    def __init__(self, **kwargs):
        kwargs["template_name"] = f"{get_template_prefix()}/select_checkbox.html"
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
