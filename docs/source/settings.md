# Settings

The settings that control django_tableaux's behaviour at runtime are implemented as class variables
of `TableauxView`. Your view will inherit `TableauxView` and then specify the specific settings
that you wish to use.

Typically you will have a standard set of settings to give a consistent look to your tables. As an
alternative to specifying them in every view, you can define them in a settings dictionary and
reference it in your view through a class variable called `settings`.

You can also create a global settings dictionary in your `settings.py` file under the key
`DJANGO_TABLEAUX`.

## Priority of settings

Class variables that you define in your view class override any settings defined in a settings
dictionary.

A settings dictionary defined in your view overrides any global settings dictionary defined in
`settings.py`.

### Example

```python
# settings.py
DJANGO_TABLEAUX = {
    "css": "bootstrap5",
}
```

```python
# views.py
tableaux_settings = {
    "rows_control": True,
    "columns_control": True,
}

class MyView(TableauxView):
    settings = tableaux_settings
```
