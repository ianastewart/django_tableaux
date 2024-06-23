import logging
from enum import IntEnum
from os import listdir
from os.path import isfile, join

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import QueryDict, HttpResponse
from django.shortcuts import render, reverse
from django.template.response import TemplateResponse
from django.urls.resolvers import NoReverseMatch
from django.views.generic import TemplateView
from django_filters.filterset import filterset_factory
from django_htmx.http import (
    HttpResponseClientRefresh,
    HttpResponseClientRedirect,
    trigger_client_event,
)
from django_tables2 import SingleTableMixin
from django_tables2.export.export import TableExport

from .utils import (
    breakpoints,
    define_columns,
    set_select_column,
    set_column_states,
    save_columns,
    load_columns,
    set_column,
    visible_columns,
    save_per_page,
    build_templates_dictionary,
    render_editable_form,
)

logger = logging.getLogger(__name__)


class TableauxView(SingleTableMixin, TemplateView):
    class FilterStyle(IntEnum):
        NONE = 0
        TOOLBAR = 1
        MODAL = 2
        HEADER = 3

    class ClickAction(IntEnum):
        NONE = 0
        GET = 1
        HX_GET = 2
        CUSTOM = 3

    title = ""
    template_name = "django_tableaux/bootstrap4/tableaux.html"
    template_library = "bootstrap4"

    model = None
    form_class = None
    filterset_class = None
    filterset_fields = None
    filterset = None

    table_pagination = {"per_page": 10}
    infinite_scroll = False
    infinite_load = False
    #
    context_filter_name = "filter"
    filter_style = FilterStyle.NONE
    filter_pills = False
    filter_button = False  # only relevant for TOOLBAR style
    #
    column_settings = False
    row_settings = False

    click_action = ClickAction.NONE
    click_url_name = ""
    click_target = "#modals-here"
    #
    sticky_header = False
    buttons = []
    object_name = ""
    #
    export_filename = "table"
    export_format = "csv"
    export_class = TableExport
    export_formats = (TableExport.CSV,)

    ALLOWED_PARAMS = ["page", "per_page", "sort", "_width"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table = None
        self.width = 0
        # self.object_list = None
        self.selected_objects = None
        self.selected_ids = None
        self.templates = build_templates_dictionary()

    def get(self, request, *args, **kwargs):
        table_class = self.get_table_class()
        # If table is responsive and no width parameter was sent,
        # tell client to repeat request adding the width parameter
        if hasattr(table_class, "Meta") and hasattr(table_class.Meta, "responsive"):
            if "_width" in request.GET:
                self.width = int(request.GET["_width"])
            else:
                return render(request, self.templates["width_request"])
        if request.htmx:
            return self.get_htmx(request, *args, **kwargs)

        if "_export" in request.GET:
            return self.export_table()

        return self.render_table()

    def get_queryset(self):
        if hasattr(self, "queryset"):
            return self.queryset
        if self.model is not None:
            return self.model._default_manager.all()
        else:
            raise ImproperlyConfigured(
                "%(cls)s is missing a QuerySet. Define "
                "%(cls)s.model, %(cls)s.queryset, or override "
                "%(cls)s.get_queryset()." % {"cls": self.__class__.__name__}
            )

    def get_filtered_object_list(self):
        self.object_list = self.get_table_data()
        self.filterset = self.get_filterset(self.object_list)
        if self.filterset is not None:
            self.object_list = self.filterset.qs
        self.object_list = self.process_filtered_object_list()
        return self.object_list

    def process_filtered_object_list(self):
        """
        Overide this to do further processing on objects list after filtering
        """
        return self.object_list

    def render_table(self, template_name=None):
        """
        Use the TemplateResponse Mixin to render the table, optionally using a specific template
        """
        self.get_filtered_object_list()
        self.table = self.get_table()
        self.preprocess_table(self.table, self.filterset)
        context = self.get_context_data()
        template_name = template_name or self.template_name
        return self.render_to_response(template_name, context)

    def render_rows(self, template_name=None):
        template_name = template_name or self.templates["render_rows"]
        return self.render_table(template_name)

    def render_row(self, id=None, template_name=None):
        self.object_list = self.get_table_data().filter(id=id)
        self.table = self.get_table_class()(data=self.object_list)
        self.preprocess_table(self.table, self.filterset)
        context = self.get_context_data(oob=True, row=self.table.rows[0])
        template_name = template_name or self.templates["render_row"]
        return self.render_to_response(template_name, context)

    def render_to_response(self, template_name, context, **response_kwargs):
        response_kwargs.setdefault("content_type", self.content_type)
        return TemplateResponse(
            request=self.request,
            template=[template_name],
            context=context,
            **response_kwargs,
        )

    def export_table(self):
        self.get_filtered_object_list()
        subset = self.request.GET.get("_subset", None)
        if subset:
            if subset == "selected":
                self.object_list = self.object_list.filter(
                    id__in=self.request.session.get("selected_ids", [])
                )
            elif subset == "all":
                self.filterset = self.get_filterset(self.object_list)
                self.object_list = self.filterset.qs
        export_format = self.request.GET.get("_export", self.export_format)
        # Use tablib to export in desired format
        table = self.get_table()
        self.preprocess_table(table)
        exclude_columns = [k for k, v in table.columns.columns.items() if not v.visible]
        exclude_columns.append("selection")
        exporter = self.export_class(
            export_format=export_format,
            table=table,
            exclude_columns=exclude_columns,
        )
        return exporter.response(filename=f"{self.export_filename}.{export_format}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            table=self.table,
            filter=self.filterset,
            object_list=self.object_list,
            title=self.title,
            filter_button=self.filter_button,
            filter_pills=self.filter_pills,
            filters=[],
            buttons=self.get_buttons(),
            actions=self.get_bulk_actions(),
            rows=self.rows_list(),
            per_page=self.request.GET.get(
                "per_page", self.table_pagination.get("per_page", 25)
            ),
            breakpoints=breakpoints(self.table),
            width=self.width,
            templates=self.templates,
        )
        if "_width" in self.request.GET:
            context["breakpoints"] = None

        for key, value in self.request.GET.items():
            if key not in self.ALLOWED_PARAMS and value:
                context["filters"].append((key, value))
        return context

    def get_filterset(self, queryset=None):
        filterset_class = self.filterset_class
        filterset_fields = self.filterset_fields

        if filterset_class is None and filterset_fields:
            filterset_class = filterset_factory(self.model, fields=filterset_fields)

        if filterset_class is None:
            return None

        return filterset_class(
            self.request.GET,
            queryset=queryset,
            request=self.request,
        )

    def get_htmx(self, request, *args, **kwargs):
        # Some actions depend on trigger_name; others on trigger
        trigger_name = request.htmx.trigger_name
        trigger = request.htmx.trigger

        if trigger_name is not None:
            if trigger_name == "filter" and self.filterset_class:
                # show filter modal
                context = {"filter": self.filterset_class(request.GET)}
                return render(request, self.templates["modal_filter"], context)

            elif trigger_name == "filter_form":
                # a filter value was changed
                return self.render_table(self.templates["render_table_data"])

            elif "clr_" in trigger_name:
                # cancel a filter
                filter = trigger_name.split("_")[1]
                qd = request.GET.copy()
                if filter == "all":
                    keys = list(qd.keys())
                    for key in keys:
                        if key not in self.ALLOWED_PARAMS:
                            qd.pop(key)
                else:
                    qd.pop(filter)
                return HttpResponseClientRedirect(f"{request.path}?{qd.urlencode()}")

            buttons = self.get_buttons()
            if buttons:
                for button in buttons:
                    if button.name == trigger_name:
                        result = self.handle_button(request, button.original_name())
                        if result is not None:
                            return result
                        else:
                            raise ImproperlyConfigured(
                                f"No handler for trigger_name {trigger_name}"
                            )

        if trigger is not None:
            if "editcol" in trigger:
                # display a form to edit a cell inline
                bits = trigger.split("_")
                id = bits[-1]
                column = "_".join(bits[1:-1])
                return self.render_cell_form(id, column)

            if trigger == "table_data":
                # triggered refresh of table data after create or update
                return self.render_table(self.templates["render_rows"])

            elif "id_row" in trigger:
                # change number of rows to display
                rows = trigger_name
                save_per_page(request, rows)
                url = self._update_parameter(request, "per_page", rows)
                return HttpResponseClientRedirect(url)

            elif "tr_" in trigger:
                # infinite scroll/load_more or click on row
                if "_scroll" in request.GET:
                    return self.render_table(self.templates["render_rows"])

                return self.row_clicked(
                    pk=trigger.split("_")[1],
                    target=request.htmx.target,
                    return_url=request.htmx.current_url,
                )

            elif "cell_" in trigger:
                # cell clicked
                bits = trigger.split("_")
                return self.edit_cell(
                    pk=bits[1],
                    column_name=visible_columns(request, self.table_class, self.width)[
                        int(bits[2])
                    ],
                    target=request.htmx.target,
                )

            elif "td_" in trigger:
                # cell clicked
                bits = trigger.split("_")
                return self.cell_clicked(
                    pk=bits[1],
                    column_name=visible_columns(request, self.table_class, self.width)[
                        int(bits[2])
                    ],
                    target=request.htmx.target,
                )

            # Column handling
            elif "id_col_reset" in trigger:
                # Reset default columns settings.
                # To make sure the column drop down is correctly updated we do a full client refresh,
                table = self.get_table_class([])
                define_columns(table, self.width)
                save_columns(request, table, self.width, table.columns_default)
                return HttpResponseClientRefresh()

            elif "id_col" in trigger:
                # Click on a column checkbox in the dropdown re-renders the table data with new column settings.
                # The column dropdown does not need to be rendered because the checkboxes are in the correct state,
                self.object_list = self.get_queryset()
                table = self.get_table()
                col_name = trigger_name[5:]
                checked = trigger_name in request.GET
                set_column(request, table, self.width, col_name, checked)
                return self.render_table(self.templates["render_table_data"])

            elif "id_" in trigger:
                if trigger == request.htmx.target:
                    # Clear filter value triggered by  click on X in input-prepend
                    qd = request.GET.copy()
                    qd.pop(trigger_name)
                    return HttpResponseClientRedirect(
                        f"{request.path}?{qd.urlencode()}"
                    )
                #
                # Filter value changed
                url = self._update_parameter(
                    request, trigger_name, request.GET.get(trigger_name, "")
                )
                return HttpResponseClientRedirect(url)

        raise ValueError("Bad htmx get request")

    def rows_list(self):
        return [10, 15, 20, 25, 50, 100]

    def get_buttons(self):
        return []

    def get_bulk_actions(self):
        """
        Return a list or tuple with element in format (action_name, "Action text")
        """
        return []

    def render_cell_form(self, id, column):
        """
        Override this method to show a form so user can edit the cell value
        """
        return HttpResponse(f"No form for column '{column}'")

    def patch(self, request, *args, **kwargs):
        # PATCH is used to update a cell after inline editing
        params = QueryDict(request.body)
        bits = request.htmx.target.split("_")
        column_name = visible_columns(request, self.table_class, int(bits[3]))[
            int(bits[2])
        ]
        value = params.get(column_name, None)
        print(bits[1], value)
        if value:
            return self.cell_changed(
                record_pk=bits[1],
                column_name=column_name,
                value=params[column_name],
                target=request.htmx.target,
            )
        return HttpResponse("x")

    def post(self, request, *args, **kwargs):

        if request.htmx:
            # check for inline edit request
            if request.htmx.trigger and "editcol" in request.htmx.trigger:
                bits = request.htmx.trigger.split("_")
                id = bits[-1]
                column = "_".join(bits[1:-1])
                value = request.POST[column]
                return self.handle_cell_changed(id, column, value)

            # Assume this is an action performed on a queryset
            self.selected_ids = None
            self.selected_objects = None
            if "select_all" in request.POST:
                subset = "all"
                self.selected_ids = []
                self.selected_objects = self.filtered_query_set(request)
            else:
                subset = "selected"
                if request.POST.get("selected_ids", None):
                    self.selected_ids = request.POST["selected_ids"].split(",")
                    self.selected_objects = self.get_queryset().filter(
                        pk__in=self.selected_ids
                    )
            if request.htmx.trigger_name:
                if "export" in request.htmx.trigger_name:
                    # Export is a special case. It redirects to a regular GET that returns the file
                    request.session["selected_ids"] = self.selected_ids
                    bits = request.htmx.trigger_name.split("_")
                    export_format = bits[-1] if bits[-1] != "export" else "csv"
                    path = request.path + request.POST["query"]
                    if len(request.POST["query"]) > 1:
                        path += "&"
                    return HttpResponseClientRedirect(
                        f"{path}_export={export_format}&_subset={subset}"
                    )

                response = self.handle_action(request, request.htmx.trigger_name)
                if response:
                    return response
        return HttpResponseClientRefresh()

    def handle_cell_changed(self, id, column, value):
        """
        This handles the simple cae of updating a field on a record
        For anything mpre complex, override this method.
        """
        record = self.get_queryset().filter(id=id).first()
        if hasattr(record, column):
            setattr(record, column, value)
            record.save()
            return self.render_row(id=id)
        return HttpResponse(f"Missing attribute {column} in handle_cell_edit()")

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        if kwargs["data"]:
            qd = kwargs["data"].copy()
            if "filter_save" in qd.keys():
                qd.pop("filter_save")
                kwargs["data"] = qd
        return kwargs

    def filtered_query_set(self, request, next=False):
        """Recreate the queryset used in GET for use in POST"""
        query_set = self.get_queryset()
        qd = self.query_dict(request)
        if next:
            if "page" not in qd:
                qd["page"] = "2"
            else:
                qd["page"] = str(int(qd["page"]) + 1)
        if self.filterset_class:
            return self.filterset_class(qd, queryset=query_set, request=request).qs
        return query_set

    def query_dict(self, request):
        bits = request.htmx.current_url.split("?")
        if len(bits) == 2:
            return QueryDict(bits[1]).copy()
        return QueryDict().copy()

    def handle_action(self, request, action):
        """
        self.selected_objects is a queryset that contains the objects to be processed.
        self.selected_ids is a list of model ids that were selected, empty for 'All rows'
        Possible return values:
        - None: (default) - reloads the last path
        - HttpResponse to be returned
        """
        return None

    def handle_button(self, request, button_name):
        return None

    def cell_clicked(self, pk, column_name, target, return_url):
        """
        User clicked on a cell with custom action
        """
        return HttpResponseClientRefresh()

    def edit_cell(self, pk, column_name, target):
        """
        User clicked on an editable cell
        """
        if not self.model:
            raise ImproperlyConfigured(
                "Model must be specified or cell_clicked must be overriden for editable cells",
            )
        if not self.form_class:
            raise ImproperlyConfigured(
                "You must specify the form_class for editable cells"
            )
        try:
            record = self.model.objects.get(pk=pk)
            form = self.form_class({column_name: getattr(record, column_name)})
            context = {"field": form[column_name], "target": target}
            return render(self.request, self.templates["cell_form"], context)
        except Exception as e:
            raise ValueError(f"Error {str(e)} while editing field {column_name}")

    def cell_changed(self, record_pk, column_name, value, target):
        """
        Editable cell value changed
        """
        try:
            record = self.model.objects.get(pk=record_pk)
            setattr(record, column_name, value)
            record.save()
        except ValueError:
            return render(
                self.request,
                self.templates["cell_error"],
                {"error": "Value error", "column": column_name, "target": target},
            )
        return HttpResponseClientRefresh()

    def preprocess_table(self, table, _filter=None):
        """
        Add extra attributes needed for rendering to the table
        """
        table.filter = _filter
        table.infinite_scroll = self.infinite_scroll
        table.infinite_load = self.infinite_load
        table.sticky_header = self.sticky_header
        # variables that control action when table is clicked
        table.click_action = self.click_action
        table.url = ""
        table.pk = False
        if self.click_url_name:
            # handle case when there is no PK passed (create)
            try:
                table.url = reverse(self.click_url_name)
            except NoReverseMatch:
                # Detail or update views have a pk
                try:
                    table.url = reverse(self.click_url_name, kwargs={"pk": 0})[:-2]
                    table.pk = True
                except NoReverseMatch:
                    raise (
                        ImproperlyConfigured(
                            f"Cannot resolve click_url_name: '{self.click_url_name}'"
                        )
                    )
        table.target = self.click_target

        set_select_column(table)
        if self.get_bulk_actions() and not table.select_name:
            raise ImproperlyConfigured(
                "Bulk actions require a selection column to be defined"
            )
        if table.select_name and not self.get_bulk_actions():
            raise ImproperlyConfigured("Selection column without bulk actions")

        # define possible columns depending upon the current width
        define_columns(table, width=self.width)

        # set visible columns according to saved setting
        table.columns_visible = load_columns(self.request, self.table, width=self.width)
        if not table.columns_visible:
            table.columns_visible = table.columns_default
            save_columns(
                self.request,
                table,
                width=self.width,
                column_list=table.columns_visible,
            )
        else:
            # ensure all fixed columns are in the visible list in case table definitions have been changed
            for entry in table.columns_fixed:
                if entry not in table.columns_visible:
                    table.columns_visible.append(entry)

        set_column_states(table)

        if table.filter:
            table.filter.style = self.filter_style
            # If filter is in header, build list of filters in same sequence as columns
            if self.filter_style == self.FilterStyle.HEADER:
                table.header_fields = []
                for col in table.sequence:
                    if table.columns.columns[col].visible:
                        if col in table.filter.base_filters.keys():
                            table.header_fields.append(table.filter.form[col])
                        else:
                            table.header_fields.append(None)

    @staticmethod
    def _update_parameter(request, key, value):
        query_dict = request.GET.copy()
        query_dict[key] = value
        return f"{request.path}?{query_dict.urlencode()}"

    def has_filter_toolbar(self):
        return (
            self.filterset is not None
            and self.filter_style == TableauxView.FilterStyle.TOOLBAR
        )

    def has_filter_pills(self):
        return self.filter_pills


class SelectedMixin:
    """
    Use in views that are called to perform an action on selected objects.
    Selected objects can be obtained from a list of ids passed in the session,
    or from a query passed as GET parameters.
    Returns a queryset of the selected objects
    """

    model = None
    filterset_class = None

    def get_query_set(self):
        if self.model is None:
            raise ImproperlyConfigured("Model must be specified for SelectedMixin")
        ids = self.request.session.get("selected_ids", [])
        if ids:
            return self.model.objects.filter(id__in=ids)
        query_set = self.model.objects.all()
        if self.filterset_class:
            return self.filterset_class(
                self.request.GET, queryset=query_set, request=self.request
            ).qs
        return query_set


class ModalMixin:
    """Mixin to convert generic views to operate as modal views when called by hx-get"""

    title = ""

    def get_template_names(self):
        # handle case where same view can have different templates
        if self.request.htmx:
            if hasattr(self, "modal_template_name"):
                return [self.modal_template_name]
        if hasattr(self, "template_name"):
            return [self.template_name]
        raise ValueError("Template name missing")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url = self.request.resolver_match.route
        if "<int:pk>" in url and self.object:
            url = url.replace("<int:pk>", str(self.object.pk))
        context["modal_url"] = "/" + url
        return context

    def reload_table(self):
        response = HttpResponse("")
        return trigger_client_event(
            response, "reload", {"url": self.request.htmx.current_url_abs_path}
        )


def bulk_action_namer(texts: list):
    result = []
    for text in texts:
        name = text.lower().replace(" ", "_")
        result.append((name, text))
