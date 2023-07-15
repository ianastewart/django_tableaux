import logging
from enum import IntEnum

from django.http import QueryDict, HttpResponse
from django.shortcuts import render, reverse
from django.urls.resolvers import NoReverseMatch
from django_filters.views import FilterView
from django_htmx.http import (
    HttpResponseClientRefresh,
    HttpResponseClientRedirect,
    retarget,
    trigger_client_event,
)
from django_tables2 import SingleTableMixin
from django_tables2.export.export import TableExport

from django_tableaux.utils import (
    breakpoints,
    define_columns,
    set_column_states,
    save_columns,
    load_columns,
    set_column,
    visible_columns,
    save_per_page,
)

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


class DjangoTableauxView(SingleTableMixin, FilterView):
    class FilterStyle(IntEnum):
        NONE = 0
        TOOLBAR = 1
        MODAL = 2
        HEADER = 3

    title = ""
    template_name = "django_tableaux/django_tableaux.html"
    templates = {
        "filter": "django_tableaux/modal_filter.html",
        "table_data": "django_tableaux/render_table_data.html",
        "rows": "django_tableaux/render_rows.html",
        "cell_form": "django_tableaux/cell_form.html",
        "cell_error": "django_tableaux/cell_error.html",
    }

    model = None
    form_class = None

    table_pagination = {"per_page": 10}
    infinite_scroll = False
    infinite_load = False
    #
    context_filter_name = "filter"
    filter_style = FilterStyle.TOOLBAR
    filter_button = False  # only relevant for TOOLBAR style
    #
    column_settings = False
    row_settings = False
    #
    click_method = "get"
    click_url_name = ""
    click_target = "#modals-here"
    #
    sticky_header = False
    buttons = []
    object_name = ""
    #
    export_format = "csv"
    export_class = TableExport
    export_name = "table"
    dataset_kwargs = None

    export_formats = (TableExport.CSV,)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table = None
        self.width = 0
        self.selected_objects = None
        self.selected_ids = None

    def get_export_filename(self, export_format):
        return f"{self.export_name}.{export_format}"

    def get_dataset_kwargs(self):
        return self.dataset_kwargs

    def get(self, request, *args, **kwargs):
        table = self.get_table()
        # If table is responsive and no width parameter was sent,
        # tell client to repeat request adding the width parameter
        if hasattr(table, "Meta") and hasattr(table.Meta, "responsive"):
            if "_width" in request.GET:
                self.width = int(request.GET["_width"])
            else:
                return render(request, "django_tableaux/width_request.html")

        if request.htmx:
            return self.get_htmx(request, *args, **kwargs)

        if "_export" in request.GET:
            export_format = request.GET.get("_export", self.export_format)
            qs = self.get_queryset()
            subset = request.GET.get("_subset", None)
            if subset:
                if subset == "selected":
                    qs = qs.filter(id__in=request.session.get("selected_ids", []))
                elif subset == "all":
                    filterset_class = self.get_filterset_class()
                    filterset = self.get_filterset(filterset_class)
                    if (
                        not filterset.is_bound
                        or filterset.is_valid()
                        or not self.get_strict()
                    ):
                        qs = filterset.qs
            filename = "Export"
            # Use tablib to export in desired format
            self.object_list = qs
            self.preprocess_table(table)
            table.before_render(request)
            exclude_columns = [
                k for k, v in table.columns.columns.items() if not v.visible
            ]
            exclude_columns.append("selection")
            exporter = self.export_class(
                export_format=export_format,
                table=table,
                exclude_columns=exclude_columns,
                dataset_kwargs=self.get_dataset_kwargs(),
            )
            return exporter.response(filename=f"{filename}.{export_format}")
        return super().get(request, *args, **kwargs)

    def get_htmx(self, request, *args, **kwargs):

        if request.htmx.trigger == "table_data":
            # triggered refresh of table data after create or update
            return self.render_template(self.templates["table_data"], *args, **kwargs)

        elif request.htmx.trigger_name == "filter" and self.filterset_class:
            # show filter modal
            context = {"filter": self.filterset_class(request.GET)}
            return render(request, self.templates["filter"], context)

        elif request.htmx.trigger_name == "filter_form":
            # a filter value was changed
            return self.render_template(self.templates["table_data"], *args, **kwargs)

        elif "id_row" in request.htmx.trigger:
            # change number of rows to display
            rows = request.htmx.trigger_name
            save_per_page(request, rows)
            url = self._update_parameter(request, "per_page", rows)
            return HttpResponseClientRedirect(url)

        elif "tr_" in request.htmx.trigger:
            # infinite scroll/load_more or click on row
            if "_scroll" in request.GET:
                return self.render_template(self.templates["rows"], *args, **kwargs)

            return self.row_clicked(
                pk=request.htmx.trigger.split("_")[1],
                target=request.htmx.target,
                return_url=request.htmx.current_url,
            )

        elif "td_" in request.htmx.trigger:
            # cell clicked
            bits = request.htmx.trigger.split("_")
            return self.cell_clicked(
                pk=bits[1],
                column_name=visible_columns(request, self.table_class, self.width)[
                    int(bits[2])
                ],
                target=request.htmx.target,
            )

        # Column handling
        elif "id_col_reset" in request.htmx.trigger:
            # Reset default columns settings.
            # To make sure the column drop down is correctly updated we do a client refresh,
            table = self.table_class([])
            define_columns(table, self.width)
            save_columns(request, self.width, table.columns_default)
            return HttpResponseClientRefresh()

        elif "id_col" in request.htmx.trigger:
            # Click on a column checkbox in the dropdown re-renders the table data with new column settings.
            # The column dropdown does not need to be rendered because the checkboxes are in the correct state,
            col_name = request.htmx.trigger_name[5:]
            checked = request.htmx.trigger_name in request.GET
            set_column(request, self.width, col_name, checked)
            return self.render_template(self.templates["table_data"], *args, **kwargs)

        elif "id_" in request.htmx.trigger:
            # Filter value changed
            url = self._update_parameter(
                request,
                request.htmx.trigger_name,
                request.GET.get(request.htmx.trigger_name, ""),
            )
            return HttpResponseClientRedirect(url)
        raise ValueError("Bad htmx get request")

    def rows_list(self):
        return [10, 15, 20, 25, 50, 100]

    def get_buttons(self):
        return []

    def get_actions(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.table = context["table"]
        self.preprocess_table(self.table, context["filter"])
        context.update(
            title=self.title,
            filter_button=self.filter_button,
            buttons=self.get_buttons(),
            actions=self.get_actions(),
            rows=self.rows_list(),
            per_page=self.request.GET.get(
                "per_page", self.table_pagination.get("per_page", 25)
            ),
            breakpoints=breakpoints(self.table),
            width=self.width,
            filters=[]
        )
        if "_width" in self.request.GET:
            context["breakpoints"] = None
        for key, value in self.request.GET.items():
            if key not in ["page", "sort", "_width"] and value:
                context['filters'].append(key)
        return context

    def put(self, request, *args, **kwargs):
        # PUT is used to update a cell after inline editing
        params = QueryDict(request.body)
        bits = request.htmx.target.split("_")
        column_name = visible_columns(request, self.table_class, int(bits[3]))[
            int(bits[2])
        ]
        return self.cell_changed(
            record_pk=bits[1],
            column_name=column_name,
            value=params[column_name],
            target=request.htmx.target,
        )

    def post(self, request, *args, **kwargs):
        # Posts are an action performed on a queryset
        if "select_all" in request.POST:
            subset = "all"
            self.selected_ids = []
            self.selected_objects = self.filtered_query_set(request)
        else:
            subset = "selected"
            self.selected_ids = request.POST.getlist("select-checkbox")
            self.selected_objects = self.get_queryset().filter(pk__in=self.selected_ids)

        if request.htmx.trigger_name:
            if "export" in request.htmx.trigger_name:
                # Export is a special case which must redirect to a regular GET that returns the file
                request.session["selected_ids"] = self.selected_ids
                bits = request.htmx.trigger_name.split("_")
                export_format = bits[1] if len(bits) > 1 else "csv"
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

    def get_export_format(self):
        return self.export_format

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
        The action is also in the request.POST dictionary.
        self.selected_objects is a queryset that contains the objects to be processed.
        self.selected_ids is a list of model ids that were selected, empty for 'All rows'
        Possible return values:
        - None: (default) - reloads the last path
        - HttpResponse to be returned
        """
        return None

    def row_clicked(self, pk, target, return_url):
        """User clicked on a row without defining a click_url"""
        return HttpResponseClientRefresh()

    def cell_clicked(self, pk, column_name, target):
        """User clicked on an editable cell"""
        if not self.model:
            raise ConfigurationError(
                "Model must be specified or cell_clicked must be overriden for editable cells",
            )
        if not self.form_class:
            raise ConfigurationError(
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
        """Editable cell value changed"""
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
        table.method = self.click_method
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
                    pass
        table.target = self.click_target

        # define possible columns depending upon the current width
        define_columns(table, width=self.width)

        # set visible columns according to saved setting
        table.columns_visible = load_columns(self.request, width=self.width)
        if not table.columns_visible:
            table.columns_visible = table.columns_default
            save_columns(
                self.request, width=self.width, column_list=table.columns_visible
            )

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

    def render_template(self, template_name, *args, **kwargs):
        saved = self.template_name
        self.template_name = template_name
        response = super().get(self.request, *args, **kwargs)
        self.template_name = saved
        return response

    @staticmethod
    def _update_parameter(request, key, value):
        query_dict = request.GET.copy()
        query_dict[key] = value
        return f"{request.path}?{query_dict.urlencode()}"


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
            raise ConfigurationError("Model must be specified for SelectedMixin")
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
