# Django Tableaux

**Django tables with Advanced User eXperience.**

Almost every Django project needs to display data in tabular form. For a few
rows and columns a plain list will do; for anything richer the established
choice is [django-tables2](https://github.com/jieter/django-tables2), often
paired with [django-filter](https://github.com/carltongibson/django-filter).
Together those packages cover the basics — sorting, filtering, pagination —
but a polished table involves a great deal more: column selection, responsive
layouts, bulk actions, inline editing, click-through behaviour, modal forms
and bookmarkable state. Building that from scratch every time is tedious and
the result is rarely consistent across an application.

**django-tableaux** wraps django-tables2 and django-filter in a single
class-based view (`TableauxView`) and uses [htmx](https://htmx.org/) to
deliver every interaction as a small fragment swap rather than a full page
reload. The result is a single place to declare a table, with a complete set
of user-experience features available as configuration rather than code.

## Features

### User-configurable column selection.
- Each user picks which optional
  columns are visible from a dropdown; choices are stored per view and
  per breakpoint in their session, so the layout is remembered when they
  return.
### Responsive column layouts
- Declare separate `fixed` and `default`
  column sets for any combination of breakpoints (`xs`, `sm`, `md`, `lg`,
  `xl`, `xxl`). 
- The table re-renders to match the user's current viewport
  with fall-forward / fall-back resolution between declared breakpoints.
- Freeze columns to the left of the viewport and set defined column widths

### Pagination options
- Paged mode with user selectable number of rows per page
- Infinite scroll mode - the next page is loaded
  automatically as the user scrolls to the bottom of the table.
- 'Load more' mode -  Same as infinite scroll, but appended on demand
  via a button

### Header options
- Stick header pins to the top of the viewport on scroll.
- Sort icons show the current sort order.

### Bulk actions on selected rows
- A selection column adds a checkbox to ecah row
 - Shift- and ctrl-click support multi-select
 - "select all on page" and
  "select all rows in the (filtered) table". 
 - The ids of selected rows are passed to your `handle_action` hook for processing.

### Row-level interactivity
- Configure a click on a row to issue either
  - Normal `GET` (redirect to a detail view, with a `return_url`) or an
  - 'hx-get` that swaps a modal into place; the table refreshes
  automatically when the modal closes.

### Cell-level interactivity
- Designate specific columns as interactive when clicked
- Route clicks to a `cell_clicked` hook with the column name.

### Inline cell editing
- Mark specific columns as editable
- supply a small form, and users can edit values directly in the table.

### Flexible filter placement
- Render the filter form in 1 of 3 places
  - In a toolbar above the table
  - In a modal opened from a toolbar button
  - Embedded beneath the table header

### Active filter pills
- Show active filter with one-click clear, and per-field clear "x"

### Bookmarkable state
- Sort, filter and page state is mirrored into
  the URL so any view configuration can be linked or refreshed.
- Option to not show the URL parameters in the browser's address bar.

### 3 Configurable toolbars
- A filter toolbar shows the filter form above the table when enabled
- The main toolbar typically shows the bulk action menu and row and column buttons
- The footer toolbar typically shows the pagination menu.
- The content of each menu can be defined form a list of `MenuItem`s

### Export
- CSV and xlsx exports are supported via
  `django_tables2.export.TableExport`.
- Selected-rows-only exports are supported.

### Three-tier settings cascade
- Class attributes win over a per-view
  `settings` dict, which wins over a project-wide `DJANGO_TABLEAUX`
  dictionary, so you can set defaults once and override where needed.

### Pluggable template library
- Ships with `basic` and `bootstrap` template libraries
- Point at your own directory to override individual templates

### Companion mixins
- `SelectedMixin` makes generic
   bulk-action target views slot cleanly into a tableaux
  workflow.