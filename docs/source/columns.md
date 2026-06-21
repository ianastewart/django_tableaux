# Column layouts

django-tableaux adds a column configuration system on top of django-tables2.
At its simplest it requires nothing extra — you declare columns the
django-tables2 way and everything works. As your needs grow you can
progressively add fixed columns, user-togglable optional columns, pixel
widths, sticky "frozen" columns and finally per-breakpoint responsive layouts.

---

## 1. Simple columns — no configuration needed

If you do nothing, all columns listed in `Meta.fields` (or explicitly declared
on the table class) are shown. The user cannot toggle them and they don't
respond to viewport width changes.

```python
import django_tables2 as tables
from .models import Invoice

class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "total")
        attrs = {"class": "table table-hover"}
```

This is standard django-tables2 behaviour. Nothing else is needed unless you
want column selection or responsive layouts.

---

## 2. Static column configuration — `Meta.columns`

When you want to control which columns are always visible and which the user
can toggle, add a `columns` dict to `Meta`. Each entry maps a column name to
one of three **kinds**:

| Kind | Visible | User can hide? | Notes |
|---|---|---|---|
| `"frozen"` | Always | No | Horizontally sticky; requires a pixel width |
| `"fixed"` | Always | No | Always visible but not sticky |
| `"default"` | Initially | Yes (if `columns_control = True`) | Visible until the user hides it |

Columns **not** listed in `Meta.columns` are hidden by default and can be
revealed through the column picker (if `columns_control = True`).

```python
class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "due", "total", "status", "notes")
        columns = {
            "number":   "fixed",      # always shown, not sticky
            "customer": "fixed",
            "issued":   "default",    # shown initially, user can hide
            "total":    "default",
            "status":   "default",
            # "due" and "notes" are not listed — hidden by default
        }
```

### Pixel widths

Append a pixel width to any entry by passing a 2-tuple instead of a string.
Widths are mandatory for `frozen` columns (they are needed to calculate the
sticky left offset) and optional for `fixed` and `default`.

```python
columns = {
    "selection": ("frozen", 30),    # sticky, 30 px wide
    "number":    ("frozen", 120),   # sticky, 120 px wide
    "customer":  ("fixed",  200),   # always visible, 200 px wide
    "issued":    "default",         # always visible, natural width
    "total":     ("default", 100),  # initially visible, 100 px wide
}
```

### Enabling the column picker

Set `columns_control = True` on the view to show the dropdown that lets users
toggle optional (`default`) columns on and off. Each user's choice is stored
per view and per breakpoint in their session so it is remembered across visits.

```python
class InvoiceListView(TableauxView):
    model = Invoice
    table_class = InvoiceTable
    columns_control = True      # shows the column picker dropdown
    column_reset = True         # adds a "Reset to defaults" option (default True)
```

---

## 3. Responsive column layouts — `Meta.responsive`

When a `responsive` dict is present, the first request is served a tiny
template that asks the browser to detect its viewport width and re-issue
the request with a `?bp=<name>` query parameter. All subsequent fragment
re-renders carry the breakpoint forward so the table always matches the
current viewport.

`Meta.responsive` maps breakpoint names to per-breakpoint column dicts. Each
value has exactly the same structure as `Meta.columns` described above.

### Breakpoint names

| Name | Upper bound (px) |
|---|---|
| `xs` | 576 |
| `sm` | 768 |
| `md` | 992 |
| `lg` | 1200 |
| `xl` | 1400 |
| `xxl` | 1600 |

You do not need to declare every breakpoint — only the ones where the layout
changes. Resolution is **fall-forward then fall-back**: if the detected
viewport doesn't match a declared breakpoint, the next *smaller* declared
breakpoint is used; if none exists, the smallest declared breakpoint wins.

### Example

```python
class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "due", "total", "status")
        responsive = {
            "xs": {
                "number":  ("frozen", 80),
                "total":   "default",
                "status":  "default",
                # Only three columns on narrow phones
            },
            "md": {
                "number":   ("frozen", 100),
                "customer": ("frozen", 180),
                "issued":   "default",
                "total":    "default",
                "status":   "default",
                # "due" hidden by default at medium widths
            },
            "xl": {
                "number":   ("frozen", 100),
                "customer": ("frozen", 180),
                "issued":   "default",
                "due":      "default",
                "total":    "default",
                "status":   "default",
                # All columns on wide screens
            },
        }
```

A viewport of 900 px resolves to the `md` layout because `md`'s upper bound
is 992 px. A viewport of 1300 px uses `xl`. A viewport of 400 px uses `xs`.

### Reusing layout dicts

You can define layouts as module-level variables and reference them in
`responsive` to avoid repetition:

```python
class InvoiceTable(tables.Table):
    _narrow = {
        "number": ("frozen", 80),
        "total":  "default",
        "status": "default",
    }
    _wide = {
        "number":   ("frozen", 100),
        "customer": ("frozen", 180),
        "issued":   "default",
        "due":      "default",
        "total":    "default",
        "status":   "default",
    }

    class Meta:
        model = Invoice
        fields = ("number", "customer", "issued", "due", "total", "status")
        responsive = {
            "xs": InvoiceTable._narrow,
            "sm": InvoiceTable._narrow,
            "md": _wide,   # can't reference InvoiceTable inside class body
            "xl": _wide,
        }
```

Note: inside the `class Meta` body you can reference a name already defined
in the enclosing class body (like `_narrow` defined before `Meta`) but not
the class itself (`InvoiceTable`).

---

## 4. Mobile template

Set `"mobile_template": True` in a breakpoint's column dict to switch to an
alternative row template optimised for narrow screens. This is a special key
that is stripped before the column definitions are processed.

```python
responsive = {
    "xs": {
        "mobile_template": True,   # use the mobile row template
        "number":   ("frozen", 80),
        "customer": "default",
    },
    "md": {
        "number":   ("frozen", 100),
        "customer": ("frozen", 180),
        "issued":   "default",
        "total":    "default",
    },
}
```

---

## 5. Error checking

If a column name listed in `Meta.columns`, `Meta.responsive`, or `Meta.editable`
does not exist on the table, an `ImproperlyConfigured` exception is raised at
startup with a message naming the table class, the bad column and the list of
valid column names. This catches typos early rather than producing a silent
layout error at runtime.

---

## 6. Summary of Meta options

| Option | Type | Purpose |
|---|---|---|
| `columns` | `dict` | Static layout for all viewports |
| `responsive` | `dict` | Per-breakpoint layouts; takes priority over `columns` when `bp` is set |
| `editable` | `list` | Column names that render as inline-editable cells |

The `columns` option is used when there is no responsive layout, or as a
fallback when `bp` is not yet known. If both `columns` and `responsive` are
present, `responsive` takes precedence once the breakpoint is resolved.
