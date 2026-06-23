# CSS Attributes

Django_tableaux follows the method used to define CSS attributes in django_tables2, namely that attributes
can be defined at table level and also at column level.

In django_tables2, when an attribute with the same key is defined in both the table and the column,
the column attribute is applied and the table attribute is ignored. That behaviour is not ideal,
particularly when defining classes. Django_tableaux handles this differently: for `class` and `style`
attributes, the values are merged. Other attributes are copied across verbatim, and callable attributes
continue to work.

For example:

```python
import django_tables2 as tables

class MyTable(tables.Table):
    class Meta:
        attrs = {"th": {"class": "bg-dark"}}

    name = tables.Column(attrs={"th": {"class": "strong"}})
```

When rendered using django_tables2 the name column header would have `class="bg-dark"` applied,
whereas with django_tableaux it would be rendered as `class="bg-dark strong"`.

Note that when multiple classes are defined, specificity is determined by the sequence in which they
are defined in the CSS file, not the order in which they appear in the `class` attribute.
