===============
Django Tableaux
===============

The aim of this project is to make it easy to create truly user-friendly HTML
tables. Almost every Django project needs a way to show multiple objects in
tabular form. In simple projects with few rows and columns you might use a
simple bulleted list view. When there are more rows and columns, the goto
package is django_tables2.

Django_tables2 is great for creating HTML tables from your Django models.
It supports sorting and pagination and when used with django_filters, another
great package, supports easy custom filtering. But many desirable features are
missing.

User configurable column selection
----------------------------------

If you want to view your table on an iPad or, worse still, on a mobile,
chances are it won't fit properly and won't be friendly to use. If your
data has more than a few columns you will have
to scroll horizontally to view the rightmost columns, losing the leftmost
columns in the process. Similarly as you scroll down, you lose the headers.

Django tableaux gives the user full control over which columns are visible.
The selected column layouts are stored in session variables so that they
persist when the user leaves then returns to a sepcific view.

Responsive column layouts
-------------------------
As a developer you can define different default column combinations for
different viewport sizes and have the table automatially reformat to match the
user's current device.

Pagination
----------
Pagination is provided by off the shelf by django_tables2, but the standard
functionality results in the whole page being refreshed.
Django_tableaux implements paging using htmx-calls which can refreshes only
the table, leaving the position in the page intact.

Infinite scroll
---------------
As an alternative to fixed page sizes you can enable infinite scroll. Whenever
the user scrolls to the bottom of the current set of rows, a new page-sized set
of rows is displayed.

Load more
---------
Another alternative is to show a "load more" button at the bottom of the current
page and display the next page-sized set of rows when clicked.

Sticky header
-------------
Whe this option is turned on the table's header row remains visible at the top
of the page when scrolling down.


Bulk actions on specific rows
-----------------------------
A common requirement when working with tabular data is to select one or more rows
and then perform a specific action on them. Django's admin system provides that
by default, but it is missing in django_tables2.

Django_tableaux adds the ability to add a checkbox to each row and supports the
common conventions of using shift and control to select multiple columns.
When data is paged, if you select all the rows on a page, you can optionally allow
selection of all rows in the table.

The bulk actions that can be performed are defined in a list, and the selected
objects are then passed to your code to process them.

Row level interactivity
-----------------------
Another common requirement is to open a detail view when clicking on a specific
row. Django_Tableaux supports this with two variations. In each case you provide the
name of the target url. You can then define this to be called by either a regular get
request or an hx-get request. The primary key of the object in the clicked row is
passed in both cases.


    1. You can define a url name that a table click will redirect to with a GET request
    In this case the url of the table is passed in a return_url parameter
    2. You can define a url name that is called by hx-get
    In this case typically the detail page will be displayed in a modal and the table
    will be automatically refreshed when the modal is closed.
In each case the primary key of the object in the clicked row is passed.

Cell level interactivity
------------------------
if you want to call a particular function when a cell is clicked, specific columns
can be designated to be interactive.
A typical use for such functionality is to show a set of choices. Django_Tableaux has
built in handling for that case


Django Tableaux addresses that problem, and many other aspects of the user experience when working with
tabular data. It comprises a single class-based view with many options and hooks to gib=ve you full control
over the presentation of data.


Technically it achives m the functionality using HTMX

What's in a name?

vie

, but  and
many rows you will find that it is difficult to dsplay the data in a way that gives
user the command over the display that they expect.
Some examples
