# Getting Started

## Installation

Install with uv:

```
uv add django-tableaux
```

Or with pip:

```
pip install django-tableaux
```

This also installs the required dependencies: `django-tables2`, `django-filter`, and `django-htmx`.
While the latest versions are recommended, Django-tableaux works well with older versions of these packages.
If you want to control exactly which versions are loaded, you can install them separately.

If you are using Bootstrap and want filtering, install `django-bootstrap5` separately:

```
uv add django-bootstrap5
```

## Project setup

### INSTALLED_APPS

Add `django_tableaux` and its dependencies to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...
    "django.contrib.staticfiles",
    "django_tables2",
    "django_filters",
    "django_htmx",
    "django_tableaux",
    # Optional — required if using Bootstrap templates with filtering:
    "django_bootstrap5",
    ...
]
```

### Middleware

Add `HtmxMiddleware` to `MIDDLEWARE`:

```python
MIDDLEWARE = [
    ...
    "django_htmx.middleware.HtmxMiddleware",
]
```

### Settings (optional)

You can set project-wide defaults in `settings.py`. Any attribute that can be set on a `TableauxView`
subclass can also be set here and will apply to all views unless overridden:

```python
DJANGO_TABLEAUX = {
    "template_library": "bootstrap",  # "basic" (default) or "bootstrap"
    "per_page": 25,
}
```

## Templates

You template for displaying tables will typically extend a base template. Your template should include
3 template tags from the django_tableaux template library:
- `{% tableaux_css %}` This is the base stylesheet.
- `{% tableaux_js %}` This includes the JavaScript that enables table functionality.
- `{% tableaux %}` This renders your table. If you have multiple tables on a page this template
- tag should be repeated for each table, with a prefix to distinguish them.

```html
{% load django_tableaux %}
<head>
    ...
    {% tableaux_css %}
</head>
<body>
    {% tableaux %}
    {% tableaux_js %}
</body>
```

Both tableaux_css and tableaux.js include a `?v=` cache-busting query string tied to the installed package
version.

## A minimal view

Define a `django_tables2` table class, then subclass `TableauxView`:


```python
# views.py
import django_tables2 as tables
from django_tableaux.views import TableauxView
from .models import MyModel

class MyTable(tables.Table):
    class Meta:
        model = MyModel
        fields = ["name", "email", "created"]

class MyTableView(TableauxView):
    title = "My Records"
    table_class = MyTable
    model = MyModel
    template_library = "bootstrap"  # or "basic"
```
I recommend defining your table class adjacent to your view following the principle of
[Locality of Behaviour](https://htmx.org/essays/locality-of-behaviour/),
but you can also define table classes in a separate folder if you prefer.

```python
# urls.py
from django.urls import path
from .views import MyTableView

urlpatterns = [
    path("my-records/", MyTableView.as_view(), name="my_records"),
]
```

That's all that's required for a working paginated, sortable table. From here you can
enable additional features — filtering, bulk actions, column selection, infinite scroll
and more — by adding attributes to your view. See [TableauxView](TableauxView.md) for the
full attribute reference.