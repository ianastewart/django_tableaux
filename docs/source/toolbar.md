# Toolbar

There are three configurable toolbar zones:

| Attribute | Position                                                   | Default contents                              |
| --- |------------------------------------------------------------|-----------------------------------------------|
| `toolbar_filter` | Appears at the top of the area allocated to the tableaux   | Filter fields, filter apply and clear buttons 
| `toolbar` | Under thge filter toolbar, directly above the table header | Actions, columns, rows                        |
| `toolbar_bottom` | Below the table                                            | record count, paginator                       |

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

It is not recommended to use left, center and right simultaneously as it can lead to a congested layout on smaller screens.
The best strategy is to use left and right together or just center.

---

## Valid item names

| Item | What it renders                            | Shown when |
| --- |--------------------------------------------| --- |
| `actions` | Bulk-actions dropdown                      | `get_bulk_actions()` returns entries |
| `buttons` | Assignable toolbar buttons                 | `get_buttons()` returns entries |
| `columns` | Column-picker dropdown                     | `columns_control = True` |
| `rows` | Rows-per-page dropdown                     | `rows_control = True` |
| `filter_modal` | "Filter" button that opens the modal       | `filterset_class` is set and `filter_style = FilterStyle.MODAL` |
| `filters` | A row of filter fields                     | `filter_style = FilterStyle.TOOLBAR` |
| `filter_button` | Button to apply changes in the filter form | `filter_button = True` and filter toolbar active |
| `filter_clear` | Clear-all filter settings button           | `filter_clear_button = True` and filter toolbar active |
| `record_count` | Record range text                          | Always (when included) |
| `paginator` | Page navigation links                      | `pagination = Pagination.PAGED` |

Passing an unrecognised item name raises `ImproperlyConfigured` at startup,
listing both the bad name and the full set of valid names.

---

## Default layout

The class-level defaults on `TableauxView` produce the following default layout below. Override these on your subclass
to rearrange, add, or remove items.

```python
toolbar_filter = {
    "left": ["filters", "filter_button", "filter_clear"],
}
toolbar = {
    "left":   "actions",
    "right":  ["filter_modal", "columns", "rows"],
}

```
The toolbar_filter only appears when filter_style=FilterStyle.TOOLBAR.
The filter_modal button only appears when filter_style=FilterStyle.MODAL.


---

## `record_count`

When included, `record_count` renders a small muted text span showing how
many records the current page covers:

> Showing records 21 to 40 of 1234

**Paginated tables** — The standard paginator shows the record range for the current page (`start`
to `end`) and the total filtered count. The end is clamped to the total so
the last page always reads correctly (e.g. "Showing records 1221 to 1234
of 1234").
If you use a LazyPaginator the display does not show the total count.

**Non-paginated tables** (`Pagination.NONE`) — shows just the total count:
"1234 records".

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
