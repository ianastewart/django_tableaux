=========
Templates
=========

Django_tableaux uses several template fragments to render tables. These are organised
into template libraries.

There is a base template library that contains HTML code that is (with moinor exceptions)
fee of any css frameworks.

The base library is complemented by libraries that customise the HTML to support
specific css frameworks such as Bootstrap.

During initialisation TableauxView builds a dictionary of template names.
The dictionary key is the template name without the .html suffix and the value
is the full path of the template.

