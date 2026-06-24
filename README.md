# django-tableaux

**Django tables with Advanced User eXperience**

Almost every Django project has a need to display data in tabular form. Creating a simple table
is relatively easy, but if your data is complex with many columns you owe it to your users to present the
data in a format that suits them.
Different users may want to view different combinations of columns, be using very different devices and maywant to interactively work
with the table in different ways. Simple html tables don't meet those requirements well. That's where this package comes in.

Django-tableaux builds upon two well-established django apps: [django_tables2](https://github.com/jieter/django-tables2)
and [django_filter](https://github.com/carltongibson/django-filter) and enhances their functionality through a
sprinkling of [htmx](https://htmx.org) magic. It provides a single class-based [docs/source/TableauxView.md](TableauxView) in which 
you can enable multiple features to deliver a customised user experience that embodies the best practices for 
interactive tables.

> [!NOTE]
> This package is still in a beta stage but is already highly functional with few restrictions
on use.
The documentation is still under construction but should be sufficient to get started with the product.

## Key features

- User-definable columns selection with frozen columns and preset widths
- Fully responsive: Define different table layouts for mobile, tablet and desktop
- Perform bulk actions on selected rows or on all (possibly filtered) rows
- User-definable rows per page with options for infinite scroll and infinite load-more data
- Display filters in a toolbar, in a modal or embed them within the table header
- Show active filter pils with ability to clear individual filters
- Edit specific fields directly inside the table
- Easy integration with generic views for CRUD operations
- Configurable toolbars above and below the table data

See [docs/source/introduction.md](docs/source/introduction.md) for a more detailed walkthrough of these features.

## Installation

```
uv add django-tableaux
```

or

```
pip install django-tableaux
```


## Dependencies

At a minimum django-tableaux requires [django_tables2](https://github.com/jieter/django-tables2),
[django_filter](https://github.com/carltongibson/django-filter) and [htmx](https://htmx.org) to operate. If not already
loaded installing django-tableaux will also install suitable versions of those packages.
If you are using bootstrap and employing filtering, django-tableaux's standard templates use the
[https://github.com/zostera/django-bootstrap5](django-bootstrap5) package to display the filter form's fields.
This package is not automatically installed; you must install it separately if needed.

## Templates and CSS

Django-tableaux splits table generation into a hierarchy of templates. To properly present tables a minimum
amount of CSS is required. We provide a native CSS file that defines the minimum to make tables look good,
and include CSS variables that you can set to tailor the colours and presentation. We also supply ready-built
templates adapted for Bootstrap that work for both version 4 and version 5.

> [!NOTE]
> In this version we only support Bootstrap 5. Other CSS option will be supported in a subsequent release.

Internally, templates are organised in a template dictionary. This dictionary is loaded with a mixture of
basic templates, bootstrap-specific templates if required, and optionally user-specific templates.

See [docs/source/templates.md](docs/source/templates.md) for details on the template dictionary and how to override templates.

## Documentation

Full documentation is in [docs/source](docs/source):

- [Introduction](docs/source/introduction.md) — overview of the features django-tableaux provides
- [TableauxView](docs/source/TableauxView.md) — the main class-based view
- [Views](docs/source/views.md) — view configuration
- [Columns](docs/source/columns.md) — defining and customising columns
- [Attributes](docs/source/attributes.md) — view and column attributes reference
- [Settings](docs/source/settings.md) — project-wide settings
- [Templates](docs/source/templates.md) — the template dictionary and overriding templates
- [Toolbar](docs/source/toolbar.md) — toolbar and filter placement