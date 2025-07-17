There are two ways in which you can include tables on a page:

- You can create a class-based view that inherits from Tableaux view and inside the template that you specify you can
include the "render_table" template to show the table. This is suitable for simpler view where the table is the main
element.

- You can create your own View, either function-based or class-based. In the template you can include a template tag
that references a DjangoTableaux view that will render the table. This is useful when your page contains many
components that you want to render asynchronously,

