Settings
========

The settings that control django_tableaux's behaviour ar runtime are implemented as class variables
of the TableauxView. Your view will inherit TableauxView and then specify the specific settings that
you wish to use.

Typically you will have a standard set of settings to give a consistent look to your tables. As an
alternative to specifying them in every View, you can define them in a settings dictionary and
reference it in your View through a class_variable called 'settings'.

You can also create a global settings dictionary in your django settings.py file under the name
'DJANGO_TABLEAUX".

Priority of settings
--------------------
Class variables that you define in your View class override any settings that are defined in a
settings dictionary.

A settings dictionary defined in your View, overrides any global settings dictionary defined in
settings.py.

Example

.. code-block:: python
    DJANGO_TABLEAUX = {
    "css": "bootstrap5",
    }

    tableaux_settings = {
        "rows_control": True,
        "columns_control: True,
        }

    class MyView(TableauxView):


