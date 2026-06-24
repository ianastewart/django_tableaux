# django-tableaux



# `TableauxView` — Developer Reference

`django_tableaux.views.TableauxView` is the single class-based view that powers
django-tableaux. It is a subclass of Django's `TemplateView`, augmented with
HTMX-driven sorting, filtering, pagination, column selection, bulk actions,
click-through behaviour, inline editing and responsive column layouts.

You use the package by writing your own subclass and enable the features you want by setting class attributes or
by overriding methods.

```python
from django_tableaux.views import TableauxView
from .models import Invoice
from .tables import InvoiceTable

class InvoiceListView(TableauxView):
    model = Invoice
    table_class = InvoiceTable
    page_size = 25
    columns_control = True
    rows_control = True
```

This document is a complete reference for every public attribute, hook and
companion class on the view.

---

## Contents

1. Quick start
2. How a request is handled
3. Class attributes (configuration)
4. Methods and hooks you can override
5. Companion `Table` class — `Meta` options used by tableaux
6. Built-in columns
7. Buttons and bulk actions
8. Filtering
9. Pagination, infinite scroll and "load more"
10. Row and cell interactivity
11. Inline cell editing
12. Responsive column layouts
13. Settings: instance, view and project level
14. Template library and customisation
15. Companion mixins — `SelectedMixin`, `ModalMixin`
16. Helper — `bulk_action_namer`

---

## 1. Quick start

A minimal view needs at most a model (or `queryset`) and, for anything beyond
the auto-generated table, a `table_class`.

```python
# urls.py
path("invoices/", InvoiceListView.as_view(), name="invoice_list"),

# views.py
from django_tableaux.views import TableauxView
from .models import Invoice
from .tables import InvoiceTable

class InvoiceListView(TableauxView):
    title = "Invoices"
    model = Invoice
    table_class = InvoiceTable
```

```python
# tables.py
import django_tables2 as tables
from django_tableaux.columns import SelectionColumn, CurrencyColumn
from .models import Invoice

class InvoiceTable(tables.Table):
    selection = SelectionColumn()
    total = CurrencyColumn(prefix="£")

    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "total")
        attrs = {"class": "table table-hover"}
```

In your project template directory you do **not** need to provide a template
unless you want to override the default. The view renders
`django_tableaux/tableaux.html` from the chosen template library (see
section 14).

## 2. How a request is handled

`TableauxView` distinguishes plain HTTP requests from HTMX requests by
inspecting `request.htmx` (provided by `django-htmx`).

A regular `GET` renders the full page. If the table declares a responsive
layout (see section 12) and no `bp` query parameter is present, the view first
returns a small template that asks the browser to detect its breakpoint and
re-issue the request with `?bp=md` (or similar). After that, the table is
rendered for that breakpoint.

An HTMX `GET` is dispatched in `get_htmx.py` based on the `HX-Trigger` and
`HX-Trigger-Name` headers. Every interaction — sorting, paging, toggling a
column, changing a filter, opening the filter modal, clicking a row — comes
back through this single endpoint and re-renders only the affected fragment.

`POST` is reserved for two things: the value submitted by an inline cell
editor, and bulk actions performed on the rows the user has selected.

`PATCH` is used by inline editing to commit a new cell value.

You generally do not override `get`, `post` or `patch` directly. Instead you
override the named hooks listed in section 4.

## 3. Class attributes (configuration)

Every attribute below is a class variable on `TableauxView` that you override
in your subclass. Defaults shown are the values declared on the base class.

### Identity and template

| Attribute | Default | Description |
| --- | --- | --- |
| `title` | `""` | Page title, available to the template as `view.title`. |
| `caption` | `""` | Optional caption rendered above the table. |
| `template_name` | `"django_tableaux/tableaux.html"` | The wrapper template rendered for non-HTMX requests. Override to embed the table in your own page. |
| `template_library` | `"basic"` | Selects which template library to use. See section 14. |

### Data source

| Attribute | Default | Description |
| --- | --- | --- |
| `model` | `None` | Django model to list. Used by `get_queryset` if you do not override it. |
| `queryset` | *unset* | If declared on the subclass, takes priority over `model`. |
| `table_data` | `None` | Static iterable of rows, used in place of a queryset. |
| `table_class` | `None` | The `django_tables2.Table` subclass to render. If omitted, `SingleTableMixin` builds a default table from `model`. |
| `form_class` | `None` | Form used when editing a cell inline (see section 11). |

### Filtering

| Attribute | Default | Description |
| --- | --- | --- |
| `filterset_class` | `None` | A `django_filters.FilterSet` subclass. |
| `filterset_fields` | `None` | Shortcut: list of field names. If `filterset_class` is `None` and this is set, a filterset is auto-generated via `filterset_factory`. |
| `filter_style` | `FilterStyle.NONE` | Where to render the filter form. One of `NONE`, `TOOLBAR`, `MODAL`, `HEADER`. |
| `filter_pills` | `False` | When true, active filters are shown as removable pills above the table. |
| `filter_button` | `False` | If true, filter changes only apply when the user clicks an Apply button (otherwise filter inputs auto-submit on change). |
| `filter_clear_button` | `True` | Show a "clear all" button alongside the filter form. |
| `filter_clear_field` | `True` | Show a small "x" inside each filter input that clears that field. |

### Pagination

| Attribute | Default | Description |
| --- | --- | --- |
| `pagination` | `Pagination.PAGED` | One of `PAGED`, `INFINITE`, `LOAD`, `NONE`. See section 9. |
| `page_size` | `20` | Default rows per page. |

### User controls

| Attribute | Default | Description |
| --- | --- | --- |
| `columns_control` | `False` | Show the column-picker dropdown. Users toggle which optional columns are visible; choices persist in their session. |
| `column_reset` | `True` | Show a "Reset to defaults" entry in the column picker. |
| `rows_control` | `False` | Show the rows-per-page dropdown. |

### Click behaviour

| Attribute | Default | Description |
| --- | --- | --- |
| `click_action` | `ClickAction.NONE` | What happens when a row or cell is clicked. One of `NONE`, `GET`, `HX_GET`, `CUSTOM`. |
| `click_url_name` | `""` | URL name resolved with the row's `pk`. If `pk` is not part of the URL, the URL is used as-is (suitable for create views). |
| `click_target` | `"#modals-here"` | CSS selector that the HTMX response is swapped into. Used with `ClickAction.HX_GET`. |

### Layout

| Attribute | Default | Description |
| --- | --- | --- |
| `sticky_header` | `True` | Pins the table header to the top of the viewport on scroll. |
| `sticky_bottom_toolbar` | `True` | Pins the bottom toolbar to the bottom of the viewport on scroll. |
| `fixed_height` | `0` | Optional fixed scroll-area height in pixels. |

### Toolbar

| Attribute | Default | Description |
| --- | --- | --- |
| `buttons` | `[]` | Default list of `Button` objects rendered in the toolbar. Usually you override `get_buttons()` instead. |
| `object_name` | `""` | Singular name for the items being listed (e.g. `"invoice"`), used in messages such as "3 invoices selected". |
| `toolbar` | see [Toolbar](toolbar.md) | Dict controlling which items appear in the main toolbar and where. |
| `toolbar_filter` | see [Toolbar](toolbar.md) | Dict controlling which items appear in the filter toolbar and where. |
| `toolbar_bottom` | see [Toolbar](toolbar.md) | Dict controlling which items appear in the bottom toolbar. Default places `record_count` on the left and `paginator` in the centre. |

### Export

| Attribute | Default | Description |
| --- | --- | --- |
| `export_filename` | `"table"` | Base filename used for downloads. |
| `export_format` | `"csv"` | Default export format. |
| `export_class` | `TableExport` | The exporter from `django_tables2.export`. |
| `export_formats` | `(TableExport.CSV,)` | Tuple of formats offered to the user. |

### URL and HTMX behaviour

| Attribute | Default | Description |
| --- | --- | --- |
| `update_url` | `True` | If true, the browser address bar is kept in sync with the current sort/filter/page so the view is bookmarkable. |
| `indicator` | `True` | Show the HTMX request indicator while a fragment is loading. |
| `prefix` | `""` | Optional id prefix. Set this when you embed multiple tableaux on the same page so their query parameters and DOM ids don't collide. |
| `debug` | `False` | Convenience flag, exposed to the template. |
| `responsive_settings` | `{}` | Per-breakpoint overrides for view attributes. Each key is a breakpoint name; the value is a dict of attribute names to values applied when the viewport is at or below that breakpoint. See section 12. |

### Internal

`LOCAL_PARAMS = ["page", "per_page", "order_by"]` — query parameters managed
internally by tableaux. Filter parameters are detected via the filterset's
declared filters. State parameters are prefixed with `~` in the query string
to keep them separate from your application's own parameters.

## 4. Methods and hooks you can override

The methods below are designed to be overridden. Methods not listed here are
internal and should not normally need overriding.

### Data and filtering

`get_queryset(self)` — Return the base queryset. The default returns
`self.queryset` if declared, else `self.model._default_manager.all()`.
Raises `ImproperlyConfigured` if neither is set.

`process_filtered_object_list(self)` — Called after the filterset has been
applied to `self.object_list`. Override to apply additional logic that
shouldn't be expressible as a filter (annotations, ordering, post-filtering).
Must return the (possibly modified) object list.

`get_filterset(self, queryset=None)` — Build the filterset bound to the
current request. The default constructs `self.filterset_class` (or one
generated from `filterset_fields`) using the parsed query dict.

### Toolbar

`get_buttons(self)` — Return the list of `Button` instances to render in the
toolbar. Defaults to `[]`.

`get_bulk_actions(self)` — Return a list of `(action_name, "Display label")`
tuples. Each entry produces an item in the bulk-actions dropdown that becomes
visible when the user selects rows. The helper `bulk_action_namer(["Send",
"Archive"])` builds the slugged tuples for you.

`handle_button(self, request, button_name)` — Called when a toolbar button is
clicked. `button_name` is the button's `name` with the `btn_` prefix removed
(see `Button.original_name`). Return an `HttpResponse` to control what
happens; return `None` to let HTMX refresh the page.

`handle_action(self, request, action)` — Called when a bulk action is
selected. `self.selected_objects` is a queryset of the chosen rows;
`self.selected_ids` is a list of their primary keys (empty list when "all
rows" was selected). Return an `HttpResponse` (e.g. a redirect, a partial,
or a rendered alert via `django_htmx.http.retarget`); return `None` to
trigger a client-side refresh.

`rows_list(self)` — Return the choices offered in the rows-per-page
dropdown. Default: `[20, 50, 100]`.

### Click and cell hooks

`cell_clicked(self, pk, column_name, target, return_url)` — Called when the
user clicks a non-editable cell whose column was registered as interactive.
Default: triggers a client refresh. Override to return any `HttpResponse`.

`edit_cell(self, pk, column_name, target)` — Called when the user clicks an
editable cell. Default: builds a one-field form from `self.form_class` and
renders the cell-edit template. Raises `ImproperlyConfigured` if `model` or
`form_class` is missing.

`render_cell_form(self, id, column)` — Lower-level hook used to display a
form inside an editable cell from a custom dropdown trigger.

`cell_changed(self, record_pk, column_name, value, target)` — Called when an
editable cell's value is committed via PATCH. Default: writes the attribute
on the record and triggers a client refresh. Raises a `ValueError` rendering
on failure.

`handle_cell_changed(self, id, column, value)` — Higher-level alternative
used when the change is submitted as POST. Default: assigns and saves, then
re-renders the row.

### Rendering

`render_template(self, template_name=None, hx_target=None, ...)` — Builds
the table, prepares the context and returns a `TemplateResponse`. Used
internally and rarely overridden.

`render_table(self)`, `render_tableaux(self, hx_target="tableaux")`,
`render_row(self, id=None, template_name=None)` — Convenience wrappers that
re-render specific fragments for HTMX swaps.

`get_context_data(self, **kwargs)` — The template context includes:
`view`, `url`, `table`, `filter`, `object_list`, `templates`, `filters`,
`buttons`, `actions`, `rows`, `page`, `per_page`, `order_by`, `bp`,
`breakpoints`, `toolbar_visible`, plus the `Pagination`, `FilterStyle` and
`ClickAction` enums.

### Breakpoints

`get_breakpoint_values(self)` — Returns the breakpoint thresholds used for
the responsive layout. Default:
`{"xs": 576, "sm": 768, "md": 992, "lg": 1200, "xl": 1400, "xxl": 1600}`.
Override to change where the layout switches.

## 5. Companion `Table` class — `Meta` options used by tableaux

You define a `django_tables2.Table` subclass as usual; tableaux honours the
existing `Meta.fields`, `Meta.sequence`, `Meta.attrs`, `Meta.row_attrs` and
so on. In addition it understands these tableaux-specific `Meta` options:

`columns` (dict) — A static layout. Keys recognised:

  - `fixed`: list of column names that are always visible and cannot be
    toggled off.
  - `default`: list of columns visible by default. Always implicitly
    includes the fixed columns.
  - `mobile`: boolean — declare this layout as the mobile view.

`responsive` (dict) — Per-breakpoint layouts. Each key is a breakpoint name
(`xs`, `sm`, `md`, `lg`, `xl`, `xxl`) and each value is a `columns`-style
dict. Resolution is "fall-forward then fall-back": if the current breakpoint
isn't declared, the next smaller declared breakpoint is used; failing that,
the first declared breakpoint wins.

`editable` (list) — Names of columns that should render as inline editable
cells. Used together with the view's `form_class`.

### Attribute merging

`django_tables2` lets you set `attrs` at table level and at column level. In
upstream behaviour, when a key (e.g. `class`) is defined at both levels, the
column wins and the table-level value is dropped. Tableaux changes this so
that `class` and `style` attributes from the table and the column are
**merged** (concatenated). Other attributes still let the column override the
table. Callable attribute values continue to work.

```python
class Meta:
    attrs = {"th": {"class": "bg-dark"}}

name = tables.Column(attrs={"th": {"class": "strong"}})
# Renders as <th class="bg-dark strong">
```

### Dynamic attributes set on the table at render time

`build_table` adds a number of attributes that downstream templates rely on:
`prefix`, `indicator`, `sticky_header`, `url`, `pk`, `target`, `select_name`,
`columns_fixed`, `columns_default`, `columns_optional`, `columns_editable`,
`columns_visible`, `column_states`, `header_fields`, `responsive`, `mobile`.
You generally don't read these directly; they exist to support the templates.

## 6. Built-in columns

These live in `django_tableaux.columns` and slot into a `Table` definition
exactly like `tables.Column`.

`EditableColumn` — Marks a regular column as editable. Pair with `form_class`
on the view and list its name in `Meta.editable`.

`RightAlignedColumn`, `CenteredColumn` — Apply `text-end` (or centred styles)
to both `<th>` and `<td>`.

`CenteredTrueColumn`, `CenteredTrueFalseColumn` — Render booleans as a green
tick (and optionally a red cross), centred.

`CurrencyColumn(prefix="£", suffix="", integer=False)` — Right-aligned,
thousands-separated. `integer=True` truncates to whole units. The prefix and
suffix are emitted as marked-safe HTML.

`CheckBoxColumn` — Renders a custom checkbox using
`templates/.../custom_checkbox.html`.

`SelectionColumn` — The column that opts a table into bulk selection. Add
one of these (named anything you like — convention is `selection`) for
shift/ctrl multi-select, "select all on page" and "select all rows in table"
to work. Tableaux moves it to the front of the column sequence automatically
unless you've placed it explicitly in `Meta.sequence`.

`CounterColumn` — A non-orderable, non-data column that renders the row
number, useful when you want a visible row index regardless of sorting.

## 7. Buttons and bulk actions

`Button(content="", name="", typ="button", css="btn btn-primary", **kwargs)`
— Construct buttons in `get_buttons()`:

```python
from django_tableaux.buttons import Button

def get_buttons(self):
    return [
        Button("New invoice", href=reverse_lazy("invoice_create")),
        Button("Refresh", name="refresh"),
    ]

def handle_button(self, request, button_name):
    if button_name == "refresh":
        return self.render_table()
```

If `href` is supplied the button renders as `<a>`, otherwise as `<button>`.
Names are auto-prefixed with `btn_` and de-duplicated by slugifying the
content if no `name` is given.

Bulk actions are pure tuples and live alongside buttons:

```python
def get_bulk_actions(self):
    return (
        ("send", "Send to customer"),
        ("archive", "Archive"),
        ("export", "Export to CSV"),     # the "export" prefix is special
        ("export_xlsx", "Export as XLSX"),
    )

def handle_action(self, request, action):
    if action == "send":
        for invoice in self.selected_objects:
            invoice.send()
        return self.render_alert(f"Sent {self.selected_ids and len(self.selected_ids) or 'all'} invoices")
```

When the action name begins with `export`, tableaux short-circuits the POST
and routes the request back through `GET` with `_export=<format>` and
`_subset=selected|all`, calling `export_table()`. The session key
`selected_ids` is used to filter the queryset in that GET request.

## 8. Filtering

Filtering uses `django-filter`. Three integration points:

1. Provide either `filterset_class` (preferred) or `filterset_fields`.
2. Choose a `filter_style`:

  - `FilterStyle.NONE` — no filters.
  - `FilterStyle.TOOLBAR` — the filter form is rendered above the table.
  - `FilterStyle.MODAL` — a "Filter" toolbar button opens the form in a
    modal; the filter is applied when the user submits.
  - `FilterStyle.HEADER` — each filter field is rendered inside the
    matching table header cell, in column order.

3. Optionally enable `filter_pills` to show active filters as removable
   pills, and `filter_button` to require an explicit Apply.

State parameters that belong to tableaux (page, per_page, order_by, prefixed
internal markers) are kept distinct from filter parameters by prefixing them
with `~`. Filter names are detected by inspecting the filterset's declared
filters, so any field name that exists in your filterset is treated as a
filter parameter.

## 9. Pagination, infinite scroll and "load more"

Set `pagination` to one of:

- `Pagination.PAGED` — classic pager. HTMX swaps only the table fragment, so
  scroll position is preserved across page changes.
- `Pagination.INFINITE` — the next page is fetched and appended automatically
  when the user scrolls to the bottom.
- `Pagination.LOAD` — same as infinite, but appended only when the user
  clicks a "Load more" button.
- `Pagination.NONE` — disables pagination entirely.

Page size defaults to `page_size = 20`. If `rows_control` is true, the user
can pick a different size from `rows_list()`; the choice is stored in the
session keyed by view name.

Sorting and changing filters automatically reset the page to 1.

You may declare a custom `paginator_class` on the view; it will be passed
through to `table.paginate`.

## 10. Row and cell interactivity

Set `click_action` on the view:

- `ClickAction.NONE` — rows are not clickable.
- `ClickAction.GET` — clicking a row issues a normal GET to
  `click_url_name` resolved with the row's `pk`. The current table URL is
  passed as a `return_url` query parameter.
- `ClickAction.HX_GET` — clicking a row issues an HTMX GET; the response
  is swapped into `click_target` (default `#modals-here`). When the modal
  closes, the table is reloaded automatically.
- `ClickAction.CUSTOM` — the click is delivered to your `cell_clicked()`
  hook with the column name. Use this when the action depends on which cell
  was clicked.

If the URL pattern named by `click_url_name` doesn't take a `pk`, the URL
is used as-is — handy for "create" links wired to a row.

To make individual columns interactive when `click_action` is `CUSTOM`,
override `cell_clicked` and inspect `column_name`.

## 11. Inline cell editing

Steps to enable:

1. List the columns in `Meta.editable` on the table.
2. Use `EditableColumn` for those columns.
3. Set `form_class` on the view to a `forms.Form` (or `ModelForm`) whose
   field names match the editable column names.

When a user clicks an editable cell, tableaux calls `edit_cell()`, which
renders a one-field form bound to the current value. On submit the value is
PATCHed back and `cell_changed()` writes it to the record. Override either
hook to add validation, audit logging or business rules.

The helpers `render_editable_link()` and `render_editable_form()` in
`django_tableaux.utils` let you build editable rendering inside a column's
`render_<col>` method without using `EditableColumn` directly.

## 12. Responsive column layouts

Declare layouts per breakpoint inside the table's `Meta`:

```python
class Meta:
    fields = ("number", "customer", "issued", "due", "total", "status")
    responsive = {
        "xs": {
            "fixed": ["number"],
            "default": ["number", "total", "status"],
            "mobile": True,
        },
        "md": {
            "fixed": ["number", "customer"],
            "default": ["number", "customer", "issued", "total", "status"],
        },
        "xl": {
            "fixed": ["number", "customer"],
            "default": ["number", "customer", "issued", "due", "total", "status"],
        },
    }
```

When a responsive layout is declared, the first request is served a small
template that uses JavaScript to detect the viewport and re-issue the
request with the matching `bp` query parameter. From then on, fragment
re-renders carry the breakpoint forward.

Each user can still toggle their own optional columns on top of the
breakpoint default; choices are stored under a session key that includes the
view name, table class and breakpoint, so the same table can have different
column selections on different devices.

The breakpoint thresholds in `get_breakpoint_values()` are upper bounds — a
viewport of 990px resolves to `md` because `md`'s threshold is 992px.

## 13. Settings: instance, view and project level

There are three layers, in priority order:

1. **Class attributes on your view** — highest priority. Always win.
2. **A `settings` dict on your view** — applied only where the class
   attribute hasn't been explicitly set on the subclass. Useful for sharing
   a configuration across several views in one app.
3. **`DJANGO_TABLEAUX` in `settings.py`** — applied last, only where
   neither of the above is set. This is a project-wide default.

```python
# project/settings.py
DJANGO_TABLEAUX = {
    "template_library": "bootstrap",
    "filter_clear_field": True,
}
```

```python
# myapp/views.py
my_defaults = {
    "rows_control": True,
    "columns_control": True,
    "pagination": "paged",
}

class CustomerListView(TableauxView):
    settings = my_defaults
    model = Customer
    page_size = 50  # this class-level value still wins
```

The `setup()` method walks the dictionary and only writes attributes that
are declared on the base class, so unknown keys are silently ignored.

## 14. Template library and customisation

Templates are organised under
`src/django_tableaux/templates/django_tableaux/<library>/`. The shipping
libraries are:

- `basic` — minimal markup with a small CSS file you can override.
- `bootstrap` — adapted to Bootstrap 5.

Choose one with `template_library = "bootstrap5"` (or via the settings dict
or `DJANGO_TABLEAUX`). At setup time tableaux builds a dictionary mapping
each template's stem (`tableaux`, `tableaux_table_wrapper`, `tableaux_row`,
`modal_filter`, `cell_form`, `cell_error`, `alert`, `button.html`, …) to
its full path.

You can also point `template_library` at a directory inside your project by
passing a path that begins with `templates/`. The path is resolved relative
to `BASE_DIR`. Any `.html` files you place there override the same-named
templates in the default library; missing files fall back to the default.

`get_template_path("foo.html")` resolves a single template name through
the same search.

## 15. Companion mixins — `SelectedMixin`, `ModalMixin`

Both live in `django_tableaux.views`.

### `SelectedMixin`

Use this on the *target* view of a bulk action — the page that does
something with the selected rows. It pulls `selected_ids` from the session
(set by tableaux when the action was triggered) and falls back to the
filterset if no specific selection was made.

```python
class BulkArchiveView(SelectedMixin, FormView):
    model = Invoice
    filterset_class = InvoiceFilterSet
    template_name = "invoices/bulk_archive.html"
    form_class = ConfirmForm

    def form_valid(self, form):
        self.get_query_set().update(archived=True)
        return redirect("invoice_list")
```

Attributes: `model`, `filterset_class`, `return_url`. Method:
`get_query_set()` returns the queryset of selected (or filtered) objects.

### `ModalMixin`

A small mixin for generic CRUD views that should render full-page on a
direct visit but render as a modal when called via HTMX. It picks
`modal_template_name` if defined and the request is HTMX, otherwise
`template_name`. It also exposes a `reload_table()` helper that emits the
`reload` HTMX event so any tableaux on the parent page refreshes after the
modal closes.

```python
class InvoiceUpdateView(ModalMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/invoice_form.html"
    modal_template_name = "invoices/invoice_form_modal.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        return self.reload_table() if self.request.htmx else response
```

## 16. Helper — `bulk_action_namer`

```python
from django_tableaux.utils import bulk_action_namer

def get_bulk_actions(self):
    return bulk_action_namer(["Send to customer", "Archive", "Mark as paid"])
# -> [("send_to_customer", "Send to customer"),
#     ("archive", "Archive"),
#     ("mark_as_paid", "Mark as paid")]
```

A trivial convenience that lowercases and slugifies each label to produce
the action name. Equivalent to writing the tuples by hand.

---

## Worked example

```python
# tables.py
import django_tables2 as tables
from django_tableaux.columns import (
    SelectionColumn, CurrencyColumn, CenteredTrueFalseColumn,
)
from .models import Invoice

class InvoiceTable(tables.Table):
    selection = SelectionColumn()
    total = CurrencyColumn(prefix="£")
    paid = CenteredTrueFalseColumn()

    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "due", "total", "paid")
        attrs = {"class": "table table-hover", "selected": "table-info"}
        editable = ["due"]
        responsive = {
            "xs": {"fixed": ["number"], "default": ["number", "total", "paid"], "mobile": True},
            "md": {"fixed": ["number", "customer"], "default": ["number", "customer", "issued", "total", "paid"]},
            "xl": {"fixed": ["number", "customer"], "default": ["number", "customer", "issued", "due", "total", "paid"]},
        }
```

```python
# forms.py
from django import forms
from .models import Invoice

class InvoiceCellForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["due"]
```

```python
# views.py
from django.shortcuts import render
from django_htmx.http import retarget
from django_tableaux.views import TableauxView, bulk_action_namer
from django_tableaux.buttons import Button
from django_tableaux.models import FilterStyle, ClickAction, Pagination

from .filters import InvoiceFilterSet
from .forms import InvoiceCellForm
from .models import Invoice
from .tables import InvoiceTable


class InvoiceListView(TableauxView):
    title = "Invoices"
    model = Invoice
    table_class = InvoiceTable
    form_class = InvoiceCellForm

    template_library = "bootstrap"
    filterset_class = InvoiceFilterSet
    filter_style = FilterStyle.TOOLBAR
    filter_pills = True

    pagination = Pagination.PAGED
    page_size = 25
    rows_control = True
    columns_control = True
    sticky_header = True

    click_action = ClickAction.HX_GET
    click_url_name = "invoice_detail"

    object_name = "invoice"

    def get_buttons(self):
        return [Button("New invoice", href="/invoices/new/")]

    def get_bulk_actions(self):
        return bulk_action_namer(["Send to customer", "Archive", "Export"])

    def handle_action(self, request, action):
        if action == "send_to_customer":
            for invoice in self.selected_objects:
                invoice.send()
            ctx = {"message": f"Sent {self.selected_objects.count()} invoices",
                   "alert_class": "alert-success"}
            return retarget(render(request, self.templates["alert"], ctx),
                             "#messages")
        if action == "archive":
            self.selected_objects.update(archived=True)
        # Returning None falls through to a client refresh.
```

That subclass gives you: a sortable, filterable, paginated, responsive
table; column picker and rows-per-page controls; sticky header; row-click
opens an HTMX modal; bulk actions on selected or all rows; inline editing
of the due date; CSV export of selected rows.
