# Toolbar

There are three configurable toolbar zones:

| Attribute | Position | Default contents |
| --- | --- | --- |
| `toolbar` | Above the table | actions, record_count, filter_modal, columns, rows |
| `toolbar_filter` | Between the main toolbar and the table | filter fields, apply button, clear button |
| `toolbar_bottom` | Below the table | paginator |

All three are configured with the same mechanism: a dict on the view that
maps layout areas to item names.

---

## Layout — `toolbar`, `toolbar_filter`, `toolbar_bottom`

Each dict maps up to three area names (`left`, `center`, `right`) to a single
item name or a list of item names:

```python
toolbar = {
    "left":   "actions",
    "center": "record_count",
    "right":  ["filter_modal", "columns", "rows"],
}
toolbar_filter = {
    "left": ["filters", "filter_button", "filter_clear"],
}
toolbar_bottom = {
    "center": "paginator",
}
```

Items within an area are rendered in the order listed. The three areas use
flex auto-margins: `left` items sit at the start, `center` items are centred,
`right` items are pushed to the end. Any area can be omitted.

The same item name can appear in either toolbar — the set of valid names is
shared between `toolbar` and `toolbar_filter`.

---

## Valid item names

| Item | What it renders | Shown when |
| --- | --- | --- |
| `actions` | Bulk-actions dropdown | `get_bulk_actions()` returns entries |
| `buttons` | Toolbar buttons | `get_buttons()` returns entries |
| `columns` | Column-picker dropdown | `columns_control = True` |
| `rows` | Rows-per-page dropdown | `rows_control = True` |
| `filter_modal` | "Filter" button that opens the modal | `filterset_class` is set and `filter_style = FilterStyle.MODAL` |
| `filters` | Inline filter fields | `filter_style = FilterStyle.TOOLBAR` |
| `filter_button` | Apply button for the filter form | `filter_button = True` and filter toolbar active |
| `filter_clear` | Clear-all button | `filter_clear_button = True` and filter toolbar active |
| `record_count` | Record range text | Always (when included) |
| `paginator` | Page navigation links | `pagination = Pagination.PAGED` |

Passing an unrecognised item name raises `ImproperlyConfigured` at startup,
listing both the bad name and the full set of valid names.

---

## Default layout

The class-level defaults on `TableauxView` reproduce the original fixed layout:

```python
toolbar = {
    "left":   "actions",
    "center": "record_count",
    "right":  ["filter_modal", "columns", "rows"],
}
toolbar_filter = {
    "left": ["filters", "filter_button", "filter_clear"],
}
```

Override these on your subclass to rearrange, add, or remove items.

---

## `record_count`

When included, `record_count` renders a small muted text span showing how
many records the current page covers:

> Showing records 21 to 40 of 1 234

**Paginated tables** — shows the record range for the current page (`start`
to `end`) and the total filtered count. The end is clamped to the total so
the last page always reads correctly (e.g. "Showing records 1 221 to 1 234
of 1 234").

**Non-paginated tables** (`Pagination.NONE`) — shows just the total count:
"1 234 records".

Three context variables are available if you want to override the template
with a different format:

| Variable | Value |
| --- | --- |
| `record_count` | Total filtered record count |
| `record_start` | Index of the first record on the current page |
| `record_end` | Index of the last record on the current page |

---

## Responsive toolbars

You can change the toolbar layout at different breakpoints by including
`toolbar` or `toolbar_filter` in `responsive_settings`:

```python
responsive_settings = {
    "xs": {
        "filter_style": FilterStyle.MODAL,
        "toolbar": {
            "left":  "filter_modal",
            "right": "actions",
        },
        "toolbar_filter": {},   # filter toolbar not shown at xs
    },
}
```

`responsive_settings` entries are applied after the breakpoint is resolved,
so the class-level defaults are used for any breakpoint not listed.
