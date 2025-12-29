===============
django-tableaux
===============
**Django tables with Advanced User eXperience**

Almost every Django project has a need to display data in tabular form. Creating a simple table
is relatively easy, but if your data is complex with many columns you owe it to your users to present the
data in a format that suits them.
Different users may want to view different columns, be using very different devices and want to interactively work
with the table in different ways. Simple html tables don't meet those requirements well. That's where this package comes in.

Django-tableaux builds upon two well-established django apps: `django_tables2 <https://github.com/jieter/django-tables2>`_
and `django_filter <https://github.com/carltongibson/django-filter>`_ and enhances their functionality through a
sprinkling of `htmx <https://htmx.org>`_ magic. It provides a single class-based view in which you can enable multiple
features to deliver a customised user experience that embodies the best practices for interactive tables.

Key features
============
* The columns to display can be user-defined
* Fully responsive: Define different column layouts for mobile, tablet and desktop
* Perform bulk actions on selected rows or on all (possibly filtered) rows
* Infinite scroll
* Infinite load-more data
* Position filters in a toolbar, in a modal or embed them within the table header
* Show active filters with ability to clear individual filters
* Edit specific fields directly inside the table
* Easy integration with generic views for CRUD operations

Installation
------------
    uv add django-tableaux
or

    pip install django-tableaux

Dependencies
------------

At a minimum django-tableaux requires django-tables2, django-filter and django-htmx to operate. If not already
loaded installing django-tableaux will also install suitable versions of those packages.
If you are using bootstrap4 and employing filtering, django-tableaux's standard templates use the
django-boostrap4 package to display the filter form's fields. If you are using bootstrap5, it uses
django-bootstrap5. These packages are not automatically installed; you must install them separately if needed.

Templates and css
-----------------

Django-tableaux splits table generation into a hierarchy of templates. To properly predsnt tables a minimum
amount of css is required. We provide a native css file that defines the minimum to make tables look good,
and include variables that you can set to tailor the colours and presentation. We also supply ready-built
templates adapted for bootstrap version 5 and version 4.

Internally, templates are organised in a template dictionary. This dictioanary is loaded with a mixture of
basic templates, bootstrap-specific templates is required, and optionally user-specific templates.
