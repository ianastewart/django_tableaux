"""
Django tables with Advanced User eXperience
===============
This project builds upon two well-established django apps: `django_tables2 <https://github.com/jieter/django-tables2>`_
and `django_filter <https://github.com/carltongibson/django-filter>`_ and enhances their functionality through a
sprinkling of `htmx <https://htmx.org>`_ magic. It provides a single class-based view in which you can enable multiple
features to deliver a customised user experience that embodies the best practice for interactive tables.

Key features
============
* The columns to display can be user-defined
* Fully responsive: Define different column layouts for mobile, tablet and desktop
* Bulk actions on selected rows or on all (possibly filtered) rows
* Infinite scroll
* Infinite load-more data
* Position filters in a toolbar, in a modal or embed them within the table header
* Show active filters with ability to clear individual filters
* Edit specific fields directly inside the table
* Easy integration with generic views for CRUD operations

The project is still in beta but is fully usable.

Full documentation to follow.
"""
__version__ = "0.3"
