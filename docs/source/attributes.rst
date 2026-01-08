Attributes
==========

Django_tableaux follows the method used to define attributes in django_tables2, namely that attributes can be defined
at table level and also at column level.

In django_tables2, when an attribute with the same key is defined in both the table and the column, the column
attributes are applied the table attribute is ignored. That behaviour is not ideal, particularly when defining
classes. Django_tableaux handles this differently: For class and style attributes, the attributes are merged at the
Other attributes are copies accross verbaitim, and callable attributes will contimneu to work.

For example:

``` import django_tables2 as tables

class MyTable(tables.Table):
    class Meta:
        attrs = {"th": {"class": "bg-dark"}}

    name = tables.Column(attrs={"th": {"class": "strong"}

When rendered using django_tables2 the name column header would be rendered with class="bg-dark" applied, whereas with
django_tableaux it would be rendered as class="bg-dark strong".

Note that when multiple classes are defined, the specificity is defined by the sequence in which they are
defined in the Bootstrap css file - not their order in which thgey a[pear in the class.