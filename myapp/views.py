from src.django_tableaux.views import TableauxView
from .models import Model1
from django_tables2 import Table
from django.shortcuts import render
from django_htmx.http import retarget
from src.django_tableaux.buttons import Button
from src.django_tableaux.columns import SelectionColumn


class View1(TableauxView):
    model = Model1


class Table1(Table):
    class Meta:
        model = Model1
        fields = (
            "name",
            "description",
            "decimal",
        )
        sequence = ["decimal", "name", "..."]
        attrs = {
            "class": "table table-hover",
            "selected": "table-info",
        }

    selection = SelectionColumn()


class View2(TableauxView):
    model = Model1
    table_class = Table1
    row_settings = True
    column_settings = True

    def get_queryset(self):
        if Model1.objects.count() < 30:
            create_objects(30)
        return Model1.objects.all()

    def get_bulk_actions(self):
        return (
            ("action_message", "Action with message"),
            ("export", "Export to csv"),
            ("export_xlsx", "Export as xlsx"),
        )

    def get_buttons(self):
        return [Button("Button 1"), Button("Button 2")]

    def handle_action(self, request, action):
        if action == "action_message":
            context = {
                "message": f"Action on {self.selected_objects.count()} rows",
                "alert_class": "alert-success",
            }
            response = render(request, self.templates["alert"], context)
            return retarget(response, "#messages")


def create_objects(count):
    for x in range(count):
        Model1.objects.create(
            name=f"name_{x}", description=f"description_{x}", decimal=x
        )
    return Model1.objects.all()
