import logging
import time
from enum import IntEnum
from django.utils.http import urlencode
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.http import QueryDict, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, reverse, redirect
from django.template.response import TemplateResponse
from django.urls.resolvers import NoReverseMatch
from django.views.generic import TemplateView
from django_filters.filterset import filterset_factory
from django_htmx.http import (
    HttpResponseClientRefresh,
    HttpResponseClientRedirect,
    trigger_client_event,
    push_url,
    retarget,
    replace_url,
)
from django_tables2 import tables
from django_tables2.views import TableMixinBase, SingleTableMixin
from django_tables2.export.export import TableExport
from django_tableaux.table import build_table
from .utils import (
    breakpoints,
    define_columns,
    set_select_column,
    set_column_states,
    save_columns_dict,
    load_columns_dict,
    set_column,
    visible_columns,
    save_per_page,
    build_templates_dictionary,
    new_columns_dict,
    set_query_parameter,
    handle_sort_parameter,
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
    caption = ""
    template_name = "django_tableaux/tableaux.html"
    template_library = None

    table_data = None
    table_class = None
    model = None
    form_class = None
    filterset_class = None
    filterset_fields = None
    filterset = None

    table_pagination = {"per_page": 10}
    paginate_by = 10
    infinite_scroll = False
    infinite_load = False
    #
    context_filter_name = "filter"
    filter_style = FilterStyle.NONE
    filter_pills = False
    filter_button = False  # only relevant for TOOLBAR style
    #
    column_settings = False
    column_reset = True
    row_settings = False
    per_page = 15

    click_action = ClickAction.NONE
    click_url_name = ""
    click_target = "#modals-here"
    #
    sticky_header = False
    fixed_height = 0
    buttons = []
    object_name = ""
    #
    export_filename = "table"
    export_format = "csv"
    export_class = TableExport
    export_formats = (TableExport.CSV,)
    #
    indicator = True
    prefix = ""
    _bp = ""
    _page = None
    last_order_by = None
    ALLOWED_PARAMS = ["page", "per_page", "sort", "_bp"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.table = None
        self.selected_objects = None
        self.selected_ids = None
        self.templates = build_templates_dictionary(self.template_library)

    def get(self, request, *args, **kwargs):
        # If we have a filterset and an empty query string but initial data:
        #   create a query string containing the initial data and redirect

        if request.htmx:
            return self.get_htmx(request, *args, **kwargs)

        if self.filterset_class:
            uri = request.build_absolute_uri()
            if "?" not in uri:
                params = urlencode(self.get_initial_data())
                if params:
                    return redirect(f"{request.path}?{params}")

        table_class = self.get_table_class()

        # If initial Get and table is responsive ask client to repeat the request with the breakpoint parameter
        if "_bp" in request.GET:
            self._bp = request.GET["_bp"]
        elif hasattr(table_class, "Meta") and hasattr(table_class.Meta, "responsive"):
            return render(
                request,
                self.templates["bp_request"],
                context={"breakpoints": self.get_breakpoint_values()},
            )

        if "_export" in request.GET:
            return self.export_table()

        return self.render_template(self.template_name)

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

    def render_template(
        self,
        template_name=None,
        hx_target=None,
        trigger_client=True,
        update_url="",
        **kwargs,
    ):
        self.get_filtered_object_list()
        self.table = build_table(self, prefix=self.prefix, **kwargs)
        context = self.get_context_data(**kwargs)
        template_name = template_name or self.template_name
        response = self.render_to_response(template_name, context)
        if hx_target:
            response = retarget(response, f"#{self.table.prefix}{hx_target}")
        if trigger_client:
            response = trigger_client_event(response, "tableaux_init", after="swap")
        if update_url:
            response = replace_url(response, update_url)
            response = push_url(response, update_url)
        return response

    def render_table(self, update_url=""):
        return self.render_template(
            template_name=self.templates["render_table"],
            hx_target="table_wrapper",
            update_url=update_url,
        )

    def render_tableaux(self, update_url=""):
        return self.render_template(
            template_name=self.templates["render_tableaux"],
            hx_target="tableaux",
            update_url=update_url,
        )

    def render_row(self, id=None, template_name=None):
        # self.object_list = self.get_table_data().filter(id=id)
        #         # self.table = self.get_table_class()(data=self.object_list)
        #         # self.preprocess_table(self.table, self.filterset)
        self.get_filtered_object_list()
        self.table = build_table(self)
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
        # todo build table
        # self.preprocess_table(table)
        exclude_columns = [k for k, v in table.columns.columns.items() if not v.visible]
        exclude_columns.append("selection")
        exporter = self.export_class(
            export_format=export_format,
            table=table,
            exclude_columns=exclude_columns,
        )
        return exporter.response(filename=f"{self.export_filename}.{export_format}")

    def get_context_data(self, **kwargs):
        # We build context from scratch because calling super recreates the table
        context = {"view": self}
        if self.extra_context is not None:
            context.update(self.extra_context)
        buttons = self.get_buttons()
        actions = self.get_bulk_actions()
        toolbar_visible = (
            len(buttons) > 0
            or len(actions) > 0
            or self.row_settings
            or self.column_settings
            or self.filterset_class
            and self.filter_style == TableauxView.FilterStyle.MODAL
        )
        context.update(
            table=self.table,
            filter=self.filterset,
            object_list=self.get_filtered_object_list(),
            filters=[],
            buttons=buttons,
            actions=actions,
            rows=self.rows_list(),
            per_page=self.table_pagination["per_page"],
            breakpoints=breakpoints(self.table),
            templates=self.templates,
            toolbar_visible=toolbar_visible,
        )
        context["filter"] = self.filterset
        for key, value in self.request.GET.items():
            if key not in self.ALLOWED_PARAMS and value:
                context["filters"].append((key, value))
        return context

    def get_initial_data(self):
        """Initial values for filter"""
        if self.table_pagination:
            return self.table_pagination.copy()
        return {}

    def get_filterset(self, queryset=None):
        filterset_class = self.filterset_class
        filterset_fields = self.filterset_fields

        if filterset_class is None and filterset_fields:
            filterset_class = filterset_factory(self.model, fields=filterset_fields)

        if filterset_class is None:
            return None
        filter_data = self.request.GET.copy()
        per_page = filter_data.pop("per_page", None)
        if per_page:
            try:
                lines = int(per_page[0])
                self.table_pagination["per_page"] = lines
            except ValueError:
                pass
        initial = self.get_initial_data()
        for key, value in initial.items():
            if key == "per_page":
                lines = value
            elif key in filterset_class.base_filters and key not in filter_data:
                filter_data[key] = value

        return filterset_class(
            filter_data,
            queryset=queryset,
            request=self.request,
        )

    def get_htmx(self, request, *args, **kwargs):
        # Some actions depend on trigger_name; others on trigger
        if "_bp" in request.GET:
            self._bp = request.GET["_bp"]
        if "_filter" in request.GET:
            return self.render_table()

        trigger_name = request.htmx.trigger_name
        trigger = request.htmx.trigger

        # Deal with filter clear not working for datepicker ?
        if trigger is None and trigger_name is None:
            response = self.render_table(self.templates["render_tableaux"])
            return push_url(response, request.build_absolute_uri())

        if trigger_name is not None:
            match trigger_name:
                case "table_load":
                    return self.render_tableaux()

                case "page":
                    return self.render_tableaux()

                case "filter_modal" if self.filterset_class:
                    # show filter modal
                    context = {"filter": self.filterset_class(request.GET)}
                    return render(
                        request, self.templates["modal_filter"], context=context
                    )

                case "filter_now":
                    # filter button pressed
                    return self.render_table()

                case name if "clr_" in name:
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
                    return HttpResponseClientRedirect(
                        f"{request.path}?{qd.urlencode()}"
                    )

                case _:
                    # Check if it's a button
                    buttons = self.get_buttons()
                    if buttons:
                        for button in buttons:
                            if button.name == trigger_name:
                                result = self.handle_button(
                                    request, button.original_name()
                                )
                                if result is not None:
                                    return result
                                else:
                                    raise ImproperlyConfigured(
                                        f"No handler for trigger_name {trigger_name}"
                                    )

        if trigger is not None:
            bits = trigger.split("~")
            self.prefix = bits[0]
            match trigger:
                case trigger if "~col~" in trigger:
                    # Switch column visibility on or off
                    col_name = bits[2]
                    table = self.get_table()
                    if col_name == "_reset" in trigger:
                        # Reset default columns settings.
                        # To make sure the column drop down is correct we update the tableaux
                        define_columns(table, self.get_breakpoint_values(), self._bp)
                        columns_dict = new_columns_dict(table)
                        for column in columns_dict.keys():
                            if column not in table.columns_default:
                                columns_dict[column] = False
                        save_columns_dict(
                            request, table, self._bp, table.columns_default
                        )
                        return self.render_table()
                    # Click on a checkbox in the column dropdown re-renders the table data with new column settings.
                    # The column dropdown remains open
                    checked = f"{self.prefix}~col~{col_name}" in request.GET
                    set_column(request, table, self._bp, col_name, checked)
                    return self.render_table()

                case trigger if "~row~" in trigger:
                    # Change number of rows to display
                    rows = bits[2]
                    save_per_page(request, rows)
                    self.per_page = rows
                    new_url = set_query_parameter(
                        request.htmx.current_url, f"{bits[0]}per_page", rows
                    )
                    return self.render_tableaux(update_url=new_url)

                case name if "~sort~" in name:
                    new_url = handle_sort_parameter(
                        request.htmx.current_url, self.prefix + "sort", bits[2]
                    )
                    self.last_order_by = bits[2]
                    return self.render_tableaux(update_url=new_url)

                case name if "~page~" in name:
                    page = bits[2]
                    new_url = set_query_parameter(
                        request.htmx.current_url, f"{bits[0]}page", page
                    )
                    self._page = page
                    return self.render_tableaux(update_url=new_url)

                case trigger if "editcol" in trigger:
                    # display a form to edit a cell inline
                    bits = trigger.split("_")
                    id = bits[-1]
                    column = "_".join(bits[1:-1])
                    return self.render_cell_form(id, column)

                case "table_data":
                    # triggered refresh of table data after create or update
                    return self.render_table()

                case trigger if "tr_" in trigger:
                    # infinite scroll/load_more or click on row
                    if "_scroll" in request.GET:
                        return self.render_table(self.templates["render_rows"])

                    return self.row_clicked(
                        pk=trigger.split("_")[1],
                        target=request.htmx.target,
                        return_url=request.htmx.current_url,
                    )

                case trigger if "cell_" in trigger:
                    # cell clicked
                    bits = trigger.split("_")
                    return self.edit_cell(
                        pk=bits[1],
                        column_name=visible_columns(
                            request,
                            self.table_class,
                            self.get_breakpoint_values(),
                            self._bp,
                        )[int(bits[2])],
                        target=request.htmx.target,
                    )

                case trigger if "td_" in trigger:
                    # cell clicked
                    bits = trigger.split("_")
                    visible = visible_columns(
                            request,
                            self.table_class,
                            self.get_breakpoint_values(),
                            self._bp,
                        )
                    index = int(bits[2])
                    #todo this is a bit of a hack here
                    if "selection" in visible and visible[0] != "selection":
                        index -= 1
                    return self.cell_clicked(
                        pk=bits[1],
                        column_name=visible[index],
                        target=request.htmx.target,
                    )

                case trigger if "id_" in trigger:
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

                case _:
                    pass

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
        # todo fix patch if needed
        column_name = visible_columns(
            request, self.table_class, self.get_breakpoint_values(), int(bits[3])
        )[int(bits[2])]
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
        This handles the simple case of updating a field on a record
        For anything more complex, override this method.
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

    def get_breakpoint_values(self):
        # This dictionary specifies the upper limit for each category
        # e.g. md >= 768
        return {"xs": 576, "sm": 768, "md": 992, "lg": 1200, "xl": 1400, "xxl": 1600}

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
