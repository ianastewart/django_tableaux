# Templates

Django_tableaux uses several template fragments to render tables. These are organised
into template libraries.

There is a base template library that contains HTML code that is (with minor exceptions)
free of any CSS frameworks.

The base library is complemented by libraries that customise the HTML to support
specific CSS frameworks such as Bootstrap.

During initialisation `TableauxView` builds a dictionary of template names.
The dictionary key is the template name without the `.html` suffix and the value
is the full path of the template.

# Template Hierarchy

## HTMX Response Templates (entry points)

| Trigger | Template returned |
|---|---|
| `table_load` | `tableaux_outer` |
| resize / filter / sort / col_reset | `tableaux` |
| `~page~` | `tableaux_page_oob` |
| `~col~` (single column toggle) | `tableaux_table_wrapper` |
| `filter_modal` | `modal_filter` |
| initial GET (responsive, no `bp` yet) | `bp_request` |

## Include Hierarchy

```
tableaux_outer
└── tableaux
    ├── <form #filter_form>
    │   ├── toolbar_filter ──[bootstrap]──► toolbar_areas
    │   │                                       ├── tb_filters
    │   │                                       ├── tb_filter_button
    │   │                                       └── tb_filter_clear
    │   └── tb_filter_pills
    │
    ├── <div #toolbar_main>
    │   └── toolbar_main ────[bootstrap]──► toolbar_areas
    │                                           ├── tb_actions
    │                                           ├── tb_buttons
    │                                           ├── tb_record_count
    │                                           ├── tb_filter_modal
    │                                           ├── tb_columns
    │                                           └── tb_rows
    │
    └── tableaux_page_wrapper ◄────────────────────────────────────────┐
          ├── tableaux_table_wrapper                                   │
          │     ├── tableaux_header                                    │
          │     │     ├── svg_sort_up / svg_sort_down / svg_sortable   │
          │     │     └── tb_filter_field  [HEADER filter style only]  │
          │     ├── tableaux_rows                                      │
          │     │     ├── tableaux_row ──── select_checkbox            │
          │     │     ├── tableaux_row_mobile  [mobile only]           │
          │     │     └── load_more  [LOAD pagination only]            │
          │     └── tableaux_footer                                    │
          └── toolbar_bottom ──[bootstrap]──► toolbar_areas            │
                                                 ├── tb_record_count   │
                                                 └── tb_paginator      │
                                                       └── page_link   │
                                                                       │
tableaux_page_oob  (page change, OOB response)                         │
    ├── tableaux_page_wrapper ─────────────────────────────────────────┘
    └── <div #toolbar_main hx-swap-oob>
          └── toolbar_main (same as above)

modal_filter  (rendered into #modals-here)
    └── modal_base
          └── (modal_form blocks: title / body / footer)
```

## Standalone Templates

Returned directly by the view with no further includes.

| Template | Purpose |
|---|---|
| `bp_request` | Asks JS to send `bp=` then reload (responsive tables) |
| `tableaux_rows` | Infinite scroll row append only |
| `cell_form` | Inline cell edit form |
| `alert`, `button` | Utility fragments |

## Key Notes

- **`toolbar_areas.html`** (bootstrap only) is the shared partial rendering the left/center/right
  layout inside each toolbar. Basic library toolbars iterate `toolbar_areas` dict directly.
- **`tb_*` toolbar items** are discovered dynamically at runtime by scanning the `templates`
  dictionary for keys starting with `tb_`. Adding a new toolbar item only requires a template
  file named `tb_<itemname>.html`.
- The `<form #filter_form>` wraps `toolbar_filter` but **not** `toolbar_main` or `page_wrapper`.
  Page changes target `#page_wrapper` (outerHTML), so `toolbar_main` requires an OOB swap to
  update — handled by `tableaux_page_oob.html`.
- **`toolbar_mobile.html`** (bootstrap) exists for the mobile breakpoint and is not shown above.

